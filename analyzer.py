"""Website analysis engine used by Attrix Lead Generator."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import threading
import config

# Streamlit's UI calls (like a progress bar) only work when called from a
# thread that has Streamlit's "script run context" attached. Our website
# checks run in a background ThreadPoolExecutor, so on Streamlit deployments
# we need to manually propagate that context into each worker thread. This
# is a no-op (and totally safe) when streamlit isn't installed, e.g. the
# plain Flask app — it just won't try to attach anything.
try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
    _STREAMLIT_AVAILABLE = True
except ImportError:
    _STREAMLIT_AVAILABLE = False

def normalize_url(url):
    """Ensure URL has a proper scheme."""
    if not url:
        return None
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Domains/extensions that commonly show up as false positives (tracking
# pixels, template placeholders, image filenames) rather than real contact
# emails.
_EMAIL_IGNORE_DOMAINS = (
    "sentry.io", "wixpress.com", "example.com", "godaddy.com",
    "schema.org", "w3.org", "gstatic.com", "google.com", "cloudflare.com",
)
_EMAIL_IGNORE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")

def _extract_email(soup, html_text):
    """
    Try to find a real contact email on the page.

    Prefers explicit mailto: links (most reliable), then falls back to a
    filtered regex scan of the raw HTML for anything that looks like an
    email address but isn't obviously a tracking/template artifact.
    """
    for link in soup.find_all("a", href=re.compile(r"^mailto:", re.I)):
        candidate = link["href"].split("mailto:", 1)[1].split("?")[0].strip()
        if candidate and EMAIL_REGEX.fullmatch(candidate):
            return candidate

    for match in EMAIL_REGEX.findall(html_text):
        domain = match.split("@")[-1].lower()
        if match.lower().endswith(_EMAIL_IGNORE_EXTENSIONS):
            continue
        if any(bad in domain for bad in _EMAIL_IGNORE_DOMAINS):
            continue
        return match

    return None

def check_website(url):
    """
    Analyze a business website and generate a quality report for lead qualification.

    Returns a dict with:
        - exists: bool
        - is_responsive: bool
        - has_ssl: bool
        - load_time: float (seconds)
        - has_modern_meta: bool
        - tech_signals: list of detected tech clues
        - issues: list of issues found
        - email: str or None
        - score: int (0-100, higher = more likely to need web dev)
    """
    report = {
        "url": url,
        "exists": False,
        "is_responsive": False,
        "has_ssl": False,
        "load_time": None,
        "has_modern_meta": False,
        "tech_signals": [],
        "issues": [],
        "email": None,
        "score": config.SCORE_NO_WEBSITE,
    }

    normalized = normalize_url(url)
    if not normalized:
        report["issues"].append("No website URL provided")
        return report

    report["url"] = normalized

    try:
        resp = requests.get(
            normalized,
            timeout=config.WEBSITE_CHECK_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
            allow_redirects=True,
        )
        report["load_time"] = resp.elapsed.total_seconds()
    except requests.exceptions.SSLError:
        report["exists"] = True
        report["issues"].append("SSL certificate error")
        report["score"] = config.SCORE_BAD_WEBSITE
        return report
    except requests.exceptions.ConnectionError:
        report["issues"].append("Website unreachable / domain dead")
        report["score"] = config.SCORE_NO_WEBSITE
        return report
    except requests.exceptions.Timeout:
        report["exists"] = True
        report["issues"].append("Website extremely slow (timed out)")
        report["score"] = config.SCORE_BAD_WEBSITE
        return report
    except Exception as e:
        report["issues"].append(f"Error checking website: {e}")
        return report

    report["exists"] = True

    # SSL check
    if resp.url.startswith("https://"):
        report["has_ssl"] = True
    else:
        report["issues"].append("No HTTPS / SSL")

    # Slow load
    if report["load_time"] and report["load_time"] > 5:
        report["issues"].append(f"Very slow load time: {report['load_time']:.1f}s")

    # Parse HTML
    soup = BeautifulSoup(resp.text, "html.parser")
    html_lower = resp.text.lower()

    report["email"] = _extract_email(soup, resp.text)

    # Viewport meta (responsive)
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if viewport:
        report["is_responsive"] = True
    else:
        report["issues"].append("No viewport meta tag (not mobile-friendly)")

    # Modern meta tags
    og_tags = soup.find_all("meta", attrs={"property": re.compile(r"^og:")})
    if og_tags:
        report["has_modern_meta"] = True
        report["tech_signals"].append("Open Graph tags")

    # Technology detection
    if "wordpress" in html_lower or "wp-content" in html_lower:
        report["tech_signals"].append("WordPress")
    if "wix.com" in html_lower:
        report["tech_signals"].append("Wix")
    if "squarespace" in html_lower:
        report["tech_signals"].append("Squarespace")
    if "shopify" in html_lower:
        report["tech_signals"].append("Shopify")
    if "weebly" in html_lower:
        report["tech_signals"].append("Weebly")
    if "godaddy" in html_lower:
        report["tech_signals"].append("GoDaddy Website Builder")
    if "react" in html_lower or "next.js" in html_lower or "__next" in html_lower:
        report["tech_signals"].append("React/Next.js")
    if "angular" in html_lower:
        report["tech_signals"].append("Angular")
    if "vue" in html_lower:
        report["tech_signals"].append("Vue.js")

    # Copyright year check
    copyright_match = re.search(
        r'(?:©|&copy;|copyright)\s*(\d{4})', html_lower
    )
    if copyright_match:
        year = int(copyright_match.group(1))
        if year < 2023:
            report["issues"].append(f"Copyright year outdated: {year}")

    # Check for basic builder indicators of a poor site
    all_links = soup.find_all("a", href=True)
    all_images = soup.find_all("img")

    if len(all_links) < 3:
        report["issues"].append("Very few links (sparse site)")
    if len(all_images) < 2:
        report["issues"].append("Almost no images")

    # Check for broken images (src missing or placeholder)
    broken_imgs = [
        img for img in all_images
        if not img.get("src") or img["src"].startswith("data:image/svg")
    ]
    if len(broken_imgs) > 2:
        report["issues"].append("Multiple placeholder/broken images")

    # Title tag
    title = soup.find("title")
    if not title or not title.text.strip():
        report["issues"].append("Missing page title")

    # Meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if not desc:
        report["issues"].append("Missing meta description")

    # --- Scoring ---
    issue_count = len(report["issues"])

    if not report["is_responsive"] and issue_count >= 3:
        report["score"] = config.SCORE_BAD_WEBSITE
    elif issue_count >= 4:
        report["score"] = config.SCORE_BAD_WEBSITE
    elif issue_count >= 2:
        report["score"] = config.SCORE_OUTDATED_WEBSITE
    elif issue_count >= 1:
        report["score"] = config.SCORE_DECENT_WEBSITE
    else:
        report["score"] = config.SCORE_GOOD_WEBSITE

    return report

def analyze_leads(leads, progress_callback=None):
    """
    Analyze websites for a list of scraped leads.

    Args:
        leads: list of dicts from scraper (must have 'website' key)
        progress_callback: optional callable(current, total, message)

    Returns:
        leads list updated in-place with website analysis data.
    """
    total = len(leads)
    completed = 0
    main_thread_ctx = get_script_run_ctx() if _STREAMLIT_AVAILABLE else None

    def _check_one(lead):
        nonlocal completed
        # Propagate Streamlit's context into this worker thread so that
        # progress_callback (which may touch Streamlit UI elements like
        # st.progress) doesn't raise NoSessionContext. Safe no-op outside
        # of a Streamlit run.
        if main_thread_ctx is not None:
            add_script_run_ctx(threading.current_thread(), main_thread_ctx)

        url = lead.get("website")
        if url:
            report = check_website(url)
        else:
            report = {
                "url": None,
                "exists": False,
                "is_responsive": False,
                "has_ssl": False,
                "load_time": None,
                "has_modern_meta": False,
                "tech_signals": [],
                "issues": ["No website at all"],
                "email": None,
                "score": config.SCORE_NO_WEBSITE,
            }
        lead["website_report"] = report
        lead["lead_score"] = report["score"]
        lead["email"] = report.get("email")
        completed += 1
        if progress_callback:
            progress_callback(
                completed, total, f"Checked: {lead.get('name', '?')}"
            )
        return lead

    with ThreadPoolExecutor(max_workers=config.MAX_CONCURRENT_CHECKS) as pool:
        futures = {pool.submit(_check_one, lead): lead for lead in leads}
        for future in as_completed(futures):
            future.result() # propagate exceptions

    # Sort by score descending (best leads first)
    leads.sort(key=lambda x: x.get("lead_score", 0), reverse=True)
    return leads
