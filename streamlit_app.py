"""Streamlit version of Attrix Lead Generator - Flask code ko touch nahi kiya"""

import subprocess
import sys
import os
import html as html_lib

# Playwright browser install on Streamlit Cloud - sabse pehle
# NOTE: We only install the Chromium *browser binary* here (no --with-deps /
# install-deps). The system-level libraries Chromium needs (libnss3, libatk,
# etc.) are installed separately by Streamlit Cloud via packages.txt at
# BUILD time, when the process *does* have root. Calling "install-deps"
# here at runtime tries to run apt-get without root and always fails.
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

import streamlit as st
import pandas as pd
from datetime import datetime
from scraper_pw import scrape_google_maps  # Tumhara existing scraper
from analyzer import analyze_leads         # Tumhara existing analyzer
import config

st.set_page_config(
    page_title="Attrix Lead Generator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Dark theme CSS — matches the Flask dashboard's look ─────────────────
st.markdown("""
<style>
    .stApp {
        background-color: #0f1117;
        color: #e4e4e7;
    }
    .stButton>button {
        background: linear-gradient(135deg, #6c63ff, #00d2ff);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
    }
    .stButton>button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
    }
    /* Dark-theme the input widgets, which default to white */
    .stTextInput input, .stNumberInput input {
        background-color: #18181b !important;
        color: #e4e4e7 !important;
        border: 1px solid #3f3f46 !important;
    }
    .stSelectbox > div > div {
        background-color: #18181b !important;
        color: #e4e4e7 !important;
        border: 1px solid #3f3f46 !important;
    }
    /* Stat cards */
    div[data-testid="stMetric"] {
        background-color: #18181b !important;
        border: 1px solid #27272a !important;
        border-radius: 10px !important;
        padding: 16px 18px !important;
    }
    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] * {
        color: #d4d4d8 !important;
        opacity: 1 !important;
    }
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] div,
    div[data-testid="stMetric"] [data-testid="stMetricValue"] * {
        color: #f4f4f5 !important;
        opacity: 1 !important;
    }
    /* Tabs */
    .stTabs [data-baseweb="tab"] { color: #a1a1aa; }
    .stTabs [aria-selected="true"] { color: #e4e4e7 !important; }
    /* Leads table safety-net: ensures any cell without an explicit inline
       color still renders as visible light text on the dark background */
    .ngtable td, .ngtable th { color: #d4d4d8; }
    .ngtable a { color: #38bdf8; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("# 📈 Attrix Lead Generator")
st.markdown(
    """
**AI-Powered Google Maps Lead Generator**

Developed by **Vijay Goswami**  
🌐 https://vijaygoswami.com

Powered by **Attrix Technologies**  
https://www.attrixtech.com

Technology Partner: **Infusionn Pvt. Ltd.**  
https://infusionn.in
"""
)
st.divider()

# Search Form
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

with col1:
    business_type = st.text_input("Business Type", "Gym", placeholder="e.g. restaurants, plumbers")

with col2:
    location = st.text_input("Location", "Agra", placeholder="e.g. Bhopal, Aligarh")

with col3:
    country = st.selectbox("Country", config.COUNTRY_OPTIONS, index=config.COUNTRY_OPTIONS.index("India"))

with col4:
    max_results = st.number_input("Max Results", min_value=1, max_value=1000, value=20)

search_button = st.button("🔍 Search Leads", use_container_width=True)

# Session state for results
if 'leads_df' not in st.session_state:
    st.session_state.leads_df = None

if search_button:
    if not business_type or not location or not country:
        st.error("Business Type, Location, and Country are required")
    else:
        query = f"{business_type.strip()} in {location.strip()}, {country.strip()}"

        progress_bar = st.progress(0)
        status_text = st.empty()

        def progress_callback(current, total, msg):
            pct = int((current / total) * 100) if total > 0 else 0
            progress_bar.progress(pct)
            status_text.text(f"{current}/{total} — {msg}")

        try:
            with st.spinner("Scraping Google Maps..."):
                leads = scrape_google_maps(
                    query,
                    max_results=max_results,
                    progress_callback=progress_callback
                )

                for lead in leads:
                    lead["country"] = country

                status_text.text("Analyzing websites...")
                progress_bar.progress(0)

                analyze_leads(leads, progress_callback=progress_callback)

                st.session_state.leads_df = pd.DataFrame(leads)
                progress_bar.progress(100)
                status_text.success(f"✅ Done! Found {len(leads)} leads")

        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.exception(e)


# ── Custom HTML table renderer (mirrors the Flask dashboard) ────────────
def _score_color(score):
    if score >= 80:
        return "#f97316"   # hot
    if score >= 50:
        return "#fb923c"   # warm
    return "#22c55e"       # low priority


def render_leads_table(df):
    if df.empty:
        st.info("No leads in this category.")
        return

    rows_html = []
    for _, lead in df.iterrows():
        raw_score = lead.get("lead_score")
        score = int(raw_score) if pd.notna(raw_score) else 0
        color = _score_color(score)

        name = html_lib.escape(str(lead.get("name")) if pd.notna(lead.get("name")) else "N/A")
        rating = html_lib.escape(str(lead.get("rating")) if pd.notna(lead.get("rating")) else "N/A")
        reviews = html_lib.escape(str(lead.get("reviews")) if pd.notna(lead.get("reviews")) else "0")
        category = html_lib.escape(str(lead.get("category")) if pd.notna(lead.get("category")) else "N/A")
        phone = html_lib.escape(str(lead.get("phone")) if pd.notna(lead.get("phone")) else "N/A")
        address = html_lib.escape(str(lead.get("address")) if pd.notna(lead.get("address")) else "")

        email = lead.get("email")
        if pd.notna(email) and str(email).strip():
            email_safe = html_lib.escape(str(email))
            email_html = f'<a href="mailto:{email_safe}" style="color:#38bdf8;">{email_safe}</a>'
        else:
            email_html = '<span style="color:#71717a;">N/A</span>'

        website = lead.get("website")
        has_website = pd.notna(website) and str(website).strip()
        report = lead.get("website_report")
        issues = report.get("issues") if isinstance(report, dict) else None
        if issues:
            issues_html = "".join(f'<li style="font-size:12px;color:#fbbf24;">⚠ {html_lib.escape(str(i))}</li>' for i in issues)
        else:
            issues_html = '<li style="font-size:12px;color:#71717a;">None</li>'

        if has_website:
            site_url = str(website) if str(website).startswith("http") else f"https://{website}"
            site_url_safe = html_lib.escape(site_url)
            site_text_safe = html_lib.escape(str(website))
            website_html = f'<a href="{site_url_safe}" target="_blank" rel="noopener noreferrer" style="color:#38bdf8;">{site_text_safe}</a>'
        else:
            website_html = '<span style="color:#ef4444;font-weight:700;">NO WEBSITE</span>'

        maps_url_raw = lead.get("maps_url")
        maps_url = html_lib.escape(str(maps_url_raw)) if pd.notna(maps_url_raw) else "#"
        maps_html = f'<a href="{maps_url}" target="_blank" rel="noopener noreferrer" style="color:#a78bfa;text-decoration:none;">📍 Maps</a>'

        score_badge = f'<div style="width:30px;height:30px;border-radius:50%;background:{color}22;border:2px solid {color};display:flex;align-items:center;justify-content:center;font-weight:700;color:{color};font-size:11px;">{score}</div>'

        cellstyle = 'padding:8px;word-wrap:break-word;overflow-wrap:break-word;vertical-align:top;font-size:13px;'

        row = "<tr style=\"border-bottom:1px solid #27272a;\">"
        row += f'<td style="{cellstyle}">{score_badge}</td>'
        row += f'<td style="{cellstyle}color:#e4e4e7;"><strong style="color:#f4f4f5;">{name}</strong><br><small style="color:#a1a1aa;">{rating} ★ · {reviews} reviews</small></td>'
        row += f'<td style="{cellstyle}color:#d4d4d8;">{category}</td>'
        row += f'<td style="{cellstyle}color:#d4d4d8;">{phone}</td>'
        row += f'<td style="{cellstyle}color:#a1a1aa;">{address}</td>'
        row += f'<td style="{cellstyle}">{email_html}</td>'
        row += f'<td style="{cellstyle}">{website_html}</td>'
        row += f'<td style="{cellstyle}"><ul style="margin:0;padding-left:14px;">{issues_html}</ul></td>'
        row += f'<td style="{cellstyle}">{maps_html}</td>'
        row += "</tr>"
        rows_html.append(row)

    header = '<tr style="background:#18181b;text-align:left;"><th style="padding:8px;color:#a1a1aa;font-size:11px;">SCORE</th><th style="padding:8px;color:#a1a1aa;font-size:11px;">BUSINESS</th><th style="padding:8px;color:#a1a1aa;font-size:11px;">CATEGORY</th><th style="padding:8px;color:#a1a1aa;font-size:11px;">PHONE</th><th style="padding:8px;color:#a1a1aa;font-size:11px;">ADDRESS</th><th style="padding:8px;color:#a1a1aa;font-size:11px;">EMAIL</th><th style="padding:8px;color:#a1a1aa;font-size:11px;">WEBSITE</th><th style="padding:8px;color:#a1a1aa;font-size:11px;">ISSUES</th><th style="padding:8px;color:#a1a1aa;font-size:11px;">ACTIONS</th></tr>'

    table_html = '<div class="ngtable" style="overflow-x:auto;border:1px solid #27272a;border-radius:10px;">'
    table_html += '<table style="width:100%;table-layout:fixed;border-collapse:collapse;color:#d4d4d8;">'
    table_html += '<colgroup>'
    table_html += '<col style="width:6%">'
    table_html += '<col style="width:14%">'
    table_html += '<col style="width:10%">'
    table_html += '<col style="width:10%">'
    table_html += '<col style="width:18%">'
    table_html += '<col style="width:12%">'
    table_html += '<col style="width:12%">'
    table_html += '<col style="width:12%">'
    table_html += '<col style="width:6%">'
    table_html += '</colgroup>'
    table_html += f'<thead>{header}</thead>'
    table_html += f'<tbody>{"".join(rows_html)}</tbody>'
    table_html += '</table></div>'

    st.markdown(table_html, unsafe_allow_html=True)


# ── Display Results ───────────────────────────────────────────────────
if st.session_state.leads_df is not None and not st.session_state.leads_df.empty:
    df = st.session_state.leads_df

    st.divider()

    hot = len(df[df['lead_score'] >= 80])
    warm = len(df[(df['lead_score'] >= 50) & (df['lead_score'] < 80)])
    cold = len(df[df['lead_score'] < 50])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Leads", len(df))
    col2.metric("🔥 Hot", hot)
    col3.metric("🟠 Warm", warm)
    col4.metric("🟢 Low Priority", cold)

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["All", "🔥 Hot", "🟠 Warm", "🟢 Low"])

    with tab1:
        render_leads_table(df)

    with tab2:
        render_leads_table(df[df['lead_score'] >= 80])

    with tab3:
        render_leads_table(df[(df['lead_score'] >= 50) & (df['lead_score'] < 80)])

    with tab4:
        render_leads_table(df[df['lead_score'] < 50])

    st.divider()

    # Download CSV
    csv_df = df.drop(columns=["website_report"], errors="ignore")
    csv = csv_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name=f"attrix_leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True
    )

# Footer
st.divider()
st.markdown(
    f"<p style='text-align: center; color: #71717a; font-size: 12px;'>"
    f"&copy; {datetime.now().year} © {datetime.now().year} Attrix Technologies

Developed by Vijay Goswami

Technology Partner: Infusionn Pvt. Ltd. All rights reserved."
    f"</p>",
    unsafe_allow_html=True
)
