"""Flask web dashboard for the lead generation tool."""

import os
import csv
import io
import json
import threading
import traceback
from datetime import datetime
from flask import (
    Flask,
    render_template_string,
    request,
    jsonify,
    Response,
)

from scraper_pw import scrape_google_maps
from analyzer import analyze_leads
import config

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

MIN_RESULTS = 1
MAX_RESULTS = 1000
IS_VERCEL = bool(os.environ.get("VERCEL"))

# In-memory store for current session results
_jobs = {} # job_id -> { status, progress, total, message, results }
_job_counter = 0
_lock = threading.Lock()

# IMPROVEMENT 1: Added proper logging
def log_error(job_id, error_msg, exc_info=None):
    """Log errors to console and file for debugging"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] JOB {job_id} ERROR: {error_msg}"
    print(log_msg) # Console me dikhega
    if exc_info:
        print(traceback.format_exc()) # Full error trace

    # Save to file
    os.makedirs(config.LOG_DIR, exist_ok=True)
    log_file = os.path.join(config.LOG_DIR, f"error_{datetime.now().strftime('%Y%m%d')}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")
        if exc_info:
            f.write(traceback.format_exc() + "\n\n")

# ─── HTML Templates ────────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Attrix Lead Generator</title>
<style>
  :root {
    --bg: #0f1117;
    --card: #1a1d27;
    --accent: #6c63ff;
    --accent2: #00d2ff;
    --text: #e4e4e7;
    --muted: #71717a;
    --green: #22c55e;
    --yellow: #eab308;
    --red: #ef4444;
    --orange: #f97316;
    --border: #27272a;
  }
    * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }
 .container { max-width: 1400px; margin: 0 auto; padding: 24px; }

  /* Header */
 .header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 32px; flex-wrap: wrap; gap: 16px;
  }
 .header h1 {
    font-size: 28px; font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
 .header p { color: var(--muted); font-size: 14px; }

  /* Search form */
 .search-panel {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 24px; margin-bottom: 24px;
  }
 .search-row {
    display: flex; gap: 12px; flex-wrap: wrap; align-items: end;
  }
 .field { display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 200px; }
 .field label { font-size: 13px; color: var(--muted); font-weight: 500; }
 .field input,.field select {
    padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border);
    background: var(--bg); color: var(--text); font-size: 14px; outline: none;
  }
 .field input:focus,.field select:focus { border-color: var(--accent); }
 .btn {
    padding: 10px 24px; border-radius: 8px; border: none;
    font-weight: 600; font-size: 14px; cursor: pointer;
    transition: all.2s;
  }
 .btn-primary {
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    color: #fff;
  }
 .btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
 .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
 .btn-secondary {
    background: var(--border); color: var(--text);
  }
 .btn-secondary:hover { background: #333; }

  /* Progress */
 .progress-bar-outer {
    background: var(--border); border-radius: 8px; height: 8px;
    margin: 16px 0 8px; overflow: hidden; display: none;
  }
 .progress-bar-inner {
    height: 100%; border-radius: 8px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    transition: width 0.3s;
    width: 0%;
  }
 .progress-text { font-size: 13px; color: var(--muted); display: none; }

  /* Stats bar */
 .stats-row {
    display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap;
  }
 .stat-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 10px; padding: 16px 24px; flex: 1; min-width: 150px;
  }
 .stat-card.num { font-size: 28px; font-weight: 700; }
 .stat-card.label { font-size: 12px; color: var(--muted); margin-top: 4px; }
 .stat-card.hot.num { color: var(--red); }
 .stat-card.warm.num { color: var(--orange); }
 .stat-card.cold.num { color: var(--green); }

  /* Table */
 .table-container {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; overflow: hidden;
  }
 .table-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 16px 20px; border-bottom: 1px solid var(--border);
  }
 .table-header h3 { font-size: 16px; }
  table { width: 100%; border-collapse: collapse; }
  thead th {
    text-align: left; padding: 12px 16px; font-size: 12px;
    color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border); cursor: pointer;
    user-select: none;
  }
  thead th:hover { color: var(--text); }
  tbody td {
    padding: 12px 16px; font-size: 13px; border-bottom: 1px solid var(--border);
    vertical-align: top;
  }
  tbody tr:hover { background: rgba(108, 99, 255, 0.05); }
  tbody tr:last-child td { border-bottom: none; }

  /* Score badge */
 .score-badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 700;
  }
 .score-hot { background: rgba(239,68,68,0.15); color: var(--red); }
 .score-warm { background: rgba(249,115,22,0.15); color: var(--orange); }
 .score-medium { background: rgba(234,179,8,0.15); color: var(--yellow); }
 .score-cold { background: rgba(34,197,94,0.15); color: var(--green); }

 .issues-list { list-style: none; }
 .issues-list li {
    font-size: 12px; color: var(--muted); padding: 2px 0;
  }
 .issues-list li::before { content: "⚠ "; color: var(--yellow); }

 .link { color: var(--accent2); text-decoration: none; font-size: 12px; }
 .link:hover { text-decoration: underline; }

 .no-website { color: var(--red); font-weight: 600; font-size: 12px; }

 .hidden { display: none; }

  /* Filter tabs */
 .filter-tabs { display: flex; gap: 8px; }
 .filter-tab {
    padding: 6px 16px; border-radius: 6px; font-size: 12px;
    cursor: pointer; border: 1px solid var(--border);
    background: transparent; color: var(--muted);
  }
 .filter-tab.active { background: var(--accent); color: #fff; border-color: var(--accent); }

  /* IMPROVEMENT: Error message styling */
 .error-banner {
    background: rgba(239,68,68,0.1);
    border: 1px solid var(--red);
    color: var(--red);
    padding: 12px 16px;
    border-radius: 8px;
    margin: 16px 0;
    font-size: 14px;
  }

  @media (max-width: 768px) {
   .search-row { flex-direction: column; }
   .stats-row { flex-direction: column; }
   .table-container { overflow-x: auto; }
    table { min-width: 900px; }
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1>📈 Attrix Lead Generator</h1>
<p>
Developed by
<a href="https://vijaygoswami.com" target="_blank" class="link">Vijay Goswami</a>
•
<a href="https://www.attrixtech.com" target="_blank" class="link">Attrix Technologies</a>
•
Technology Partner:
<a href="https://infusionn.in" target="_blank" class="link">Infusionn Pvt. Ltd.</a>
</p>
    </div>
  </div>

  <!-- Search -->
  <div class="search-panel">
    <form id="searchForm" onsubmit="startSearch(event)">
      <div class="search-row">
        <div class="field">
          <label>Business Type</label>
          <input type="text" id="businessType" placeholder="e.g. restaurants, plumbers, dentists" required>
        </div>
        <div class="field">
          <label>Location</label>
          <input type="text" id="location" placeholder="e.g. Agra, Bhopal, Aligarh" value="Agra" required>
        </div>
        <div class="field">
          <label>Country</label>
          <input type="text" id="country" list="countryOptions" value="India" placeholder="Choose or type any country" required>
          <datalist id="countryOptions">
            {% for country in country_options %}
            <option value="{{ country }}"></option>
            {% endfor %}
          </datalist>
        </div>
        <div class="field" style="max-width:130px">
          <label>Max Results</label>
          <input type="number" id="maxResults" value="20" min="1" max="1000">
        </div>
        <button type="submit" class="btn btn-primary" id="searchBtn">🔍 Search</button>
      </div>
    </form>
    <div class="progress-bar-outer" id="progressOuter">
      <div class="progress-bar-inner" id="progressInner"></div>
    </div>
    <div class="progress-text" id="progressText"></div>
    <!-- IMPROVEMENT: Error banner -->
    <div id="errorBanner" class="error-banner hidden"></div>
  </div>

  <!-- Stats -->
  <div class="stats-row hidden" id="statsRow">
    <div class="stat-card">
      <div class="num" id="statTotal">0</div>
      <div class="label">Total Leads</div>
    </div>
    <div class="stat-card hot">
      <div class="num" id="statHot">0</div>
      <div class="label">🔥 Hot (No/Bad Site)</div>
    </div>
    <div class="stat-card warm">
      <div class="num" id="statWarm">0</div>
      <div class="label">🟠 Warm (Outdated)</div>
    </div>
    <div class="stat-card cold">
      <div class="num" id="statCold">0</div>
      <div class="label">🟢 Low Priority</div>
    </div>
  </div>

  <!-- Results Table -->
  <div class="table-container hidden" id="resultsContainer">
    <div class="table-header">
      <h3>Lead Results</h3>
      <div style="display:flex;gap:8px;align-items:center;">
        <div class="filter-tabs">
          <button class="filter-tab active" onclick="filterLeads('all',this)">All</button>
          <button class="filter-tab" onclick="filterLeads('hot',this)">🔥 Hot</button>
          <button class="filter-tab" onclick="filterLeads('warm',this)">🟠 Warm</button>
          <button class="filter-tab" onclick="filterLeads('cold',this)">🟢 Low</button>
        </div>
        <button class="btn btn-secondary" onclick="exportCSV()">📥 Export CSV</button>
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th onclick="sortTable('lead_score')">#Score</th>
          <th onclick="sortTable('name')">Business</th>
          <th onclick="sortTable('category')">Category</th>
          <th>Contact</th>
          <th>Email</th>
          <th>Website</th>
          <th>Issues</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody id="resultsBody"></tbody>
    </table>
  </div>

  <footer style="text-align:center; padding:24px 0 8px; color:var(--muted); font-size:12px;">
    &copy; <span id="footerYear"></span>
Attrix Technologies. Developed by
<a href="https://vijaygoswami.com" class="link" target="_blank">Vijay Goswami</a>.
Technology Partner:
<a href="https://infusionn.in" class="link" target="_blank">Infusionn Pvt. Ltd.</a>
  </footer>
</div>

<script>
let allLeads = [];
let currentFilter = 'all';
let pollInterval = null;
let currentJobId = null;
document.getElementById('footerYear').textContent = new Date().getFullYear();

async function startSearch(e) {
  e.preventDefault();
  const biz = document.getElementById('businessType').value.trim();
  const loc = document.getElementById('location').value.trim();
  const country = document.getElementById('country').value.trim();
  const max = Math.min(Math.max(parseInt(document.getElementById('maxResults').value, 10) || 20, 1), 1000);
  if (!biz ||!loc ||!country) return;

  const btn = document.getElementById('searchBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Scraping...';
  allLeads = [];
  currentJobId = null;
  showProgress(true);
  hideError();
  updateProgress(0, 100, 'Starting...');

  try {
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({business_type: biz, location: loc, country: country, max_results: max})
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Search failed');
    }
    if (data.results) {
      allLeads = data.results || [];
      renderLeads(allLeads);
      btn.disabled = false;
      btn.textContent = '🔍 Search';
      updateProgress(allLeads.length, allLeads.length || 1, data.message || 'Done');
      setTimeout(() => showProgress(false), 500);
      return;
    }
    if (data.job_id) {
      currentJobId = data.job_id;
      pollInterval = setInterval(() => pollJob(data.job_id), 1500);
    }
  } catch(err) {
    showError('Error: ' + err.message);
    btn.disabled = false;
    btn.textContent = '🔍 Search';
    showProgress(false);
  }
}

async function pollJob(jobId) {
  try {
    const res = await fetch('/api/status/' + jobId);
    const data = await res.json();
    updateProgress(data.progress || 0, data.total || 100, data.message || '');

    if (data.status === 'done') {
      clearInterval(pollInterval);
      allLeads = data.results || [];
      renderLeads(allLeads);
      document.getElementById('searchBtn').disabled = false;
      document.getElementById('searchBtn').textContent = '🔍 Search';
      setTimeout(() => showProgress(false), 500);
    } else if (data.status === 'error') {
      clearInterval(pollInterval);
      showError(data.message || 'Unknown error occurred');
      document.getElementById('searchBtn').disabled = false;
      document.getElementById('searchBtn').textContent = '🔍 Search';
      showProgress(false);
    }
  } catch(err) {
    console.error(err);
  }
}

function showProgress(show) {
  document.getElementById('progressOuter').style.display = show? 'block' : 'none';
  document.getElementById('progressText').style.display = show? 'block' : 'none';
}

function showError(msg) {
  const banner = document.getElementById('errorBanner');
  banner.textContent = msg;
  banner.classList.remove('hidden');
}

function hideError() {
  document.getElementById('errorBanner').classList.add('hidden');
}

function updateProgress(current, total, msg) {
  const pct = total > 0? Math.round((current / total) * 100) : 0;
  document.getElementById('progressInner').style.width = pct + '%';
  document.getElementById('progressText').textContent = `${current}/${total} — ${msg}`;
}

function scoreBadge(score) {
  if (score >= 80) return `<span class="score-badge score-hot">${score} 🔥</span>`;
  if (score >= 60) return `<span class="score-badge score-warm">${score}</span>`;
  if (score >= 30) return `<span class="score-badge score-medium">${score}</span>`;
  return `<span class="score-badge score-cold">${score}</span>`;
}

function scoreCategory(score) {
  if (score >= 80) return 'hot';
  if (score >= 50) return 'warm';
  return 'cold';
}

function escapeHtml(value) {
  return String(value?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
}

function safeUrl(value) {
  if (!value) return '#';
  try {
    const url = new URL(value, window.location.origin);
    return ['http:', 'https:'].includes(url.protocol)? url.href : '#';
  } catch {
    return '#';
  }
}

function renderLeads(leads) {
  document.getElementById('statsRow').classList.remove('hidden');
  document.getElementById('resultsContainer').classList.remove('hidden');

  const hot = leads.filter(l => (l.lead_score || 0) >= 80).length;
  const warm = leads.filter(l => (l.lead_score || 0) >= 50 && (l.lead_score || 0) < 80).length;
  const cold = leads.length - hot - warm;
  document.getElementById('statTotal').textContent = leads.length;
  document.getElementById('statHot').textContent = hot;
  document.getElementById('statWarm').textContent = warm;
  document.getElementById('statCold').textContent = cold;

  const filtered = currentFilter === 'all'? leads :
    leads.filter(l => scoreCategory(l.lead_score || 0) === currentFilter);

  const tbody = document.getElementById('resultsBody');
  tbody.innerHTML = '';
  filtered.forEach(lead => {
    const r = lead.website_report || {};
    const issues = (r.issues || []).map(i => `<li>${escapeHtml(i)}</li>`).join('');
    const websiteCell = lead.website
     ? `<a class="link" href="${escapeHtml(safeUrl(r.url || lead.website))}" target="_blank" rel="noopener noreferrer">${escapeHtml(lead.website)}</a>
         <br><small style="color:var(--muted)">${escapeHtml((r.tech_signals||[]).join(', ') || '')}</small>`
      : '<span class="no-website">NO WEBSITE</span>';
    const emailCell = lead.email
      ? `<a class="link" href="mailto:${escapeHtml(lead.email)}">${escapeHtml(lead.email)}</a>`
      : '<small style="color:var(--muted)">N/A</small>';

    tbody.innerHTML += `<tr>
      <td>${scoreBadge(lead.lead_score || 0)}</td>
      <td><strong>${escapeHtml(lead.name || 'N/A')}</strong><br>
        <small style="color:var(--muted)">${escapeHtml(lead.rating || '')} ★ · ${escapeHtml(lead.reviews || 0)} reviews</small></td>
      <td>${escapeHtml(lead.category || 'N/A')}</td>
      <td>${escapeHtml(lead.phone || 'N/A')}<br><small style="color:var(--muted)">${escapeHtml(lead.address || '')}</small></td>
      <td>${emailCell}</td>
      <td>${websiteCell}</td>
      <td><ul class="issues-list">${issues}</ul></td>
      <td><a class="link" href="${escapeHtml(safeUrl(lead.maps_url))}" target="_blank" rel="noopener noreferrer">📍 Maps</a></td>
    </tr>`;
  });
}

function filterLeads(filter, el) {
  currentFilter = filter;
  document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  renderLeads(allLeads);
}

function sortTable(key) {
  allLeads.sort((a, b) => {
    const aVal = a[key] || '';
    const bVal = b[key] || '';
    if (typeof aVal === 'number') return bVal - aVal;
    return String(aVal).localeCompare(String(bVal));
  });
  renderLeads(allLeads);
}

async function exportCSV() {
  if (!allLeads.length) return alert('No data to export');
  if (currentJobId) {
    window.location.href = '/api/export/' + encodeURIComponent(currentJobId);
    return;
  }

  const res = await fetch('/api/export', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({leads: allLeads})
  });
  if (!res.ok) return alert('Export failed');

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'leads.csv';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
</script>
</body>
</html>
"""

# ─── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(
        DASHBOARD_HTML,
        country_options=config.COUNTRY_OPTIONS,
    )

def _parse_max_results(value):
    try:
        requested = int(value)
    except (TypeError, ValueError):
        requested = 20
    return max(MIN_RESULTS, min(requested, MAX_RESULTS))

def _build_search_query(business_type, location, country):
    parts = [location.strip()]
    if country:
        parts.append(country.strip())
    return f"{business_type.strip()} in {', '.join(parts)}"

def _search_and_analyze(query, max_results, country, progress_callback=None):
    leads = scrape_google_maps(
        query, max_results=max_results, progress_callback=progress_callback
    )
    for lead in leads:
        lead["country"] = country
    analyze_leads(leads)
    return leads

@app.route("/api/search", methods=["POST"])
def api_search():
    global _job_counter
    data = request.get_json(silent=True) or {}
    biz_type = data.get("business_type", "").strip()
    location = data.get("location", "").strip()
    country = data.get("country", "").strip()
    max_results = _parse_max_results(data.get("max_results", 20))

    if not biz_type or not location or not country:
        return jsonify({"error": "business_type, location, and country are required"}), 400

    with _lock:
        _job_counter += 1
        job_id = str(_job_counter)
        _jobs[job_id] = {
            "status": "running",
            "progress": 0,
            "total": max_results,
            "message": "Starting...",
            "results": [],
            "business_type": biz_type,
            "location": location,
            "country": country,
        }

    query = _build_search_query(biz_type, location, country)

    if IS_VERCEL:
        try:
            leads = _search_and_analyze(query, max_results, country)
        except Exception as exc:
            log_error(job_id, f"Vercel search failed: {exc}", exc_info=True)
            return jsonify({"error": str(exc)}), 500
        return jsonify({
            "status": "done",
            "message": f"Done! Found {len(leads)} leads.",
            "results": leads,
        })

    def run_job():
        job = _jobs[job_id]

        def on_scrape_progress(current, total, msg):
            job["progress"] = current
            job["total"] = total
            job["message"] = f"[Scraping] {msg}"
            print(f"[JOB {job_id}] [Scraping] {current}/{total} - {msg}")

        try:
            print(f"[JOB {job_id}] Starting: {query}")
            leads = scrape_google_maps(
                query, max_results=max_results, progress_callback=on_scrape_progress
            )
            for lead in leads:
                lead["country"] = country

            job["message"] = "Analyzing websites..."
            job["progress"] = 0
            job["total"] = len(leads)

            def on_analyze_progress(current, total, msg):
                job["progress"] = current
                job["total"] = total
                job["message"] = f"[Analyzing] {msg}"
                print(f"[JOB {job_id}] [Analyzing] {current}/{total} - {msg}")

            analyze_leads(leads, progress_callback=on_analyze_progress)

            job["results"] = leads
            job["status"] = "done"
            job["message"] = f"Done! Found {len(leads)} leads."
            print(f"[JOB {job_id}] Complete: {len(leads)} leads")

        except Exception as exc:
            # IMPROVEMENT 2: Detailed error logging
            log_error(job_id, f"Job failed: {exc}", exc_info=True)
            job["status"] = "error"
            job["message"] = str(exc)

    thread = threading.Thread(target=run_job, daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})

@app.route("/api/status/<job_id>")
def api_status(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

def _csv_response(leads):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Score", "Name", "Category", "Phone", "Email", "Address", "Country",
        "Website", "Rating", "Reviews", "Issues", "Maps URL",
    ])
    for lead in leads:
        report = lead.get("website_report", {})
        writer.writerow([
            lead.get("lead_score", ""),
            lead.get("name", ""),
            lead.get("category", ""),
            lead.get("phone", ""),
            lead.get("email", "") or "",
            lead.get("address", ""),
            lead.get("country", ""),
            lead.get("website", "None"),
            lead.get("rating", ""),
            lead.get("reviews", ""),
            " | ".join(report.get("issues", [])),
            lead.get("maps_url", ""),
        ])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=attrix_leads_{timestamp}.csv"
        },
    )

@app.route("/api/export/<job_id>")
def api_export_job(job_id):
    job = _jobs.get(job_id)
    if not job:
        return "Job not found", 404
    return _csv_response(job.get("results", []))

@app.route("/api/export", methods=["GET", "POST"])
def api_export():
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        return _csv_response(payload.get("leads", []))

    raw = request.args.get("data", "[]")
    try:
        leads = json.loads(raw)
    except json.JSONDecodeError:
        return "Invalid data", 400
    return _csv_response(leads)

if __name__ == "__main__":
    print(
    f"\n📈 Attrix Lead Generator\n"
    f"Developed by Vijay Goswami\n"
    f"Running at http://{config.FLASK_HOST}:{config.FLASK_PORT}\n"
)
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
