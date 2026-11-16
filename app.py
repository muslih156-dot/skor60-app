"""
app.py
TRADING BOLA MENIT 60 – LAST GOAL SYSTEM
FIX FINAL: Stadion jadi HERO BANNER GEDE di atas (bukan background samar)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from zoneinfo import ZoneInfo

try:
    from config import CURRENCY, DEFAULT_STAKE, MATCHES_JSON_PATH, MIN_SAMPLE_SIZE_RELIABLE, SIMULATED_ODDS, TIMEZONE_NAME
except Exception:
    CURRENCY = "Rp"
    DEFAULT_STAKE = 50000
    MIN_SAMPLE_SIZE_RELIABLE = 20
    SIMULATED_ODDS = 1.90
    TIMEZONE_NAME = "Asia/Makassar"
    from pathlib import Path
    MATCHES_JSON_PATH = Path("data/matches.json")

try:
    from database import TradingDatabase, load_scan_metadata
except Exception:
    TradingDatabase = None
    def load_scan_metadata():
        return {}

try:
    from settlement import audit_result
except Exception:
    def audit_result(record):
        return {"label": record.get("activity_label", "NORMAL"), "explanation": "Audit cadangan", "audit_passed": True, "issues": []}

try:
    from statistics import compute_full_dashboard_statistics
except Exception:
    compute_full_dashboard_statistics = None

try:
    from data_loader import load_matches_from_old_repo
except Exception:
    load_matches_from_old_repo = None

try:
    from scanner import run_scan as _run_scan_from_scanner
except Exception:
    try:
        from espn_scanner import run_scan as _run_scan_from_scanner
    except Exception:
        try:
            from live_scanner import scan_live as _run_scan_from_scanner
        except Exception:
            _run_scan_from_scanner = None

def _try_run_scan():
    if _run_scan_from_scanner is None:
        return {"ok": False, "msg": "File scanner.py belum ada / nama fungsinya beda"}
    try:
        result = _run_scan_from_scanner()
        return {"ok": True, "msg": str(result)}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

WITA_TZ = ZoneInfo(TIMEZONE_NAME)

def style_fig(fig):
    fig.update_layout(template="plotly_dark", paper_bgcolor="#131A26", plot_bgcolor="#131A26", font=dict(color="#E2E8F0", size=12), title_font=dict(color="#FFFFFF", size=14, family="Arial Black"), xaxis=dict(gridcolor="#2A3550", zerolinecolor="#2A3550", tickfont=dict(color="#94A3B8")), yaxis=dict(gridcolor="#2A3550", zerolinecolor="#2A3550", tickfont=dict(color="#94A3B8")), legend=dict(bgcolor="#131A26", font=dict(color="#E2E8F0")), margin=dict(l=10, r=10, t=50, b=10))
    return fig

def style_dark_table(df):
    return df.style.set_properties(**{"background-color": "#1A2436", "color": "#E2E8F0", "border-color": "#2A3550"}).set_table_styles([{"selector": "th", "props": [("background-color", "#1E3A5F"), ("color", "white"), ("border-color", "#2A3550"), ("font-weight", "800")]}, {"selector": "td", "props": [("border-color", "#2A3550")]}])

def color_profit_vivid(val):
    s = str(val).strip()
    if s.startswith("-"):
        return "background-color: #FF5252; color: #FFFFFF; font-weight: 800;"
    if s.startswith("Rp0") or s == "Rp0 (Pending)" or s == "NOT AVAILABLE":
        return "background-color: #2A3550; color: #94A3B8; font-weight: 600;"
    if s.startswith("Rp"):
        return "background-color: #00C853; color: #FFFFFF; font-weight: 800;"
    return ""

def color_profit(val):
    return color_profit_vivid(val)

def color_win_rate_vivid(val):
    try:
        num = float(str(val).replace("%", ""))
        if num >= 65:
            return "background-color: #00C853; color: #FFFFFF; font-weight: 800;"
        if num >= 55:
            return "background-color: #FFAB00; color: #000000; font-weight: 800;"
        return "background-color: #FF5252; color: #FFFFFF; font-weight: 800;"
    except Exception:
        return ""

def color_win_rate(val):
    return color_win_rate_vivid(val)

def color_roi(val):
    try:
        num = float(str(val).replace("%", ""))
        if num > 0:
            return "background-color: #00BFA5; color: #FFFFFF; font-weight: 800;"
        if num < 0:
            return "background-color: #FF5252; color: #FFFFFF; font-weight: 800;"
        return "background-color: #2A3550; color: #94A3B8;"
    except Exception:
        return ""

def color_rekor(val):
    try:
        s = str(val).upper()
        if "W" in s and "L" in s:
            w = int(s.split("W")[0].strip().split()[-1])
            l = int(s.split("-")[1].replace("L", "").strip())
            if w > l:
                return "background-color: #00C853; color: #FFFFFF; font-weight: 800;"
            if w < l:
                return "background-color: #FF5252; color: #FFFFFF; font-weight: 800;"
            return "background-color: #FFAB00; color: #000000; font-weight: 800;"
    except Exception:
        pass
    return ""

def pill(text, bg, fg="#FFFFFF"):
    return f'<span style="display:inline-block; padding:3px 10px; border-radius:20px; background:{bg}; color:{fg}; font-weight:800; font-size:11px; white-space:nowrap;">{text}</span>'

def render_match_table_html(table_rows):
    header_style = "background: linear-gradient(90deg, #1E3A5F, #6D28D9); color:white; padding:8px 6px; font-size:12px; font-weight:800; text-align:center; white-space:nowrap;"
    html = []
    html.append('<div style="overflow-x:auto; border:1px solid #2A3550; border-radius:12px;">')
    html.append('<table style="width:100%; border-collapse:collapse; font-size:12px; color:#fff;">')
    html.append('<thead><tr>')
    for h in ["No", "Match ID", "Match", "League", "Badge", "Activity", "Min", "Entry", "Odds", "Current", "Final", "Result", "Profit", "Day"]:
        html.append(f'<th style="{header_style}">{h}</th>')
    html.append('</tr></thead><tbody>')
    for i, r in enumerate(table_rows):
        bg_row = "#1A2436" if i % 2 == 0 else "#131A26"
        badge = str(r["Badge"]).upper()
        if badge == "MAJOR":
            badge_html = pill("MAJOR", "#2979FF")
        elif badge == "MINOR":
            badge_html = pill("MINOR", "#FFAB00", "#000")
        else:
            badge_html = pill("UNKNOWN", "#78909C")
        act = str(r["Activity"]).upper()
        if act == "AKTIF":
            act_html = pill("AKTIF", "#00C853")
        elif act == "PASIF":
            act_html = pill("PASIF", "#FF5252")
        elif "NO_STATS" in act:
            act_html = pill("NO DATA", "#FF6D00")
        else:
            act_html = pill(act, "#37474F")
        league = str(r["League"])
        if "SERIE A" in league.upper() or "PREMIER" in league.upper() or "LA LIGA" in league.upper():
            league_html = pill(league, "#7C4DFF")
        elif "UNKNOWN" in league.upper():
            league_html = pill(league, "#37474F", "#CFD8DC")
        else:
            league_html = pill(league, "#00695C")
        res = str(r["Result"]).upper()
        if res == "WIN":
            res_html = pill("WIN", "#00C853")
        elif res == "LOSE":
            res_html = pill("LOSE", "#FF5252")
        elif res == "LIVE":
            res_html = pill("LIVE", "#2979FF")
        elif res == "PENDING":
            res_html = pill("PENDING", "#FFAB00", "#000")
        elif res == "VOID":
            res_html = pill("VOID", "#78909C")
        else:
            res_html = pill(res, "#FF6D00")
        profit = str(r["Profit"])
        if profit.startswith("-"):
            profit_html = pill(profit, "#FF5252")
        elif profit.startswith("Rp") and "Rp0" not in profit:
            profit_html = pill(profit, "#00C853")
        else:
            profit_html = pill(profit, "#2A3550", "#94A3B8")
        cell = f"padding:7px 6px; text-align:center; border-bottom:1px solid #2A3550; background:{bg_row};"
        cell_left = f"padding:7px 6px; text-align:left; border-bottom:1px solid #2A3550; background:{bg_row}; font-weight:600;"
        html.append(f"""<tr><td style="{cell}"><b style="background:#1E3A5F; padding:3px 8px; border-radius:8px;">{r['No']}</b></td><td style="{cell}">{r['Match ID']}</td><td style="{cell_left}">{r['Match']}</td><td style="{cell}">{league_html}</td><td style="{cell}">{badge_html}</td><td style="{cell}">{act_html}</td><td style="{cell}"><span style="background:#01579B; padding:3px 8px; border-radius:8px; font-weight:800;">{r['Min Entry']}</span></td><td style="{cell}"><b style="color:#FFCC80;">{r['Entry Score']}</b></td><td style="{cell}">{r['Entry Odds']}</td><td style="{cell}"><b>{r['Current Score']}</b></td><td style="{cell}"><b style="color:#B3E5FC;">{r['Final Score']}</b></td><td style="{cell}">{res_html}</td><td style="{cell}">{profit_html}</td><td style="{cell}"><span style="background:#4527A0; padding:3px 8px; border-radius:8px; font-weight:700;">{r['Trading Day']}</span></td></tr>""")
    html.append('</tbody></table></div>')
    return "".join(html)

st.set_page_config(page_title="TRADING BOLA MENIT 60 – LAST GOAL SYSTEM", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

# ===== BACKGROUND BALIK HITAM POLOS - STADION PINDAH KE HERO BANNER =====
st.markdown("""
<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMainBlockContainer"], [data-testid="stHeader"] { background: #0A0F1A !important; background-color: #0A0F1A !important; }
[data-testid="stMainBlockContainer"] { padding-top: 10px !important; max-width: 100% !important; }
h1, h2, h3, h4, p, span, div, label, li { color: #E2E8F0 !important; }
small, .stCaption, [data-testid="stCaptionContainer"] { color: #94A3B8 !important; }
h3 { border-left: 5px solid #10B981 !important; padding-left: 12px !important; }
[data-testid="stExpander"], [data-testid="stTabs"], [data-testid="stSelectbox"], [data-testid="stDataFrame"] { background-color: #131A26 !important; border: 1px solid #2A3550 !important; border-radius: 14px !important; }
[data-testid="stExpander"] summary, button[data-baseweb="tab"] { color: #E2E8F0 !important; background-color: #131A26 !important; }
button[data-baseweb="tab"][aria-selected="true"] { background-color: #1E293B !important; color: #FFFFFF !important; border-bottom: 3px solid #10B981 !important; }
div[data-baseweb="select"] > div, input { background-color: #1A2436 !important; color: #FFFFFF !important; border-color: #2A3550 !important; }
.stButton > button { background: linear-gradient(90deg, #0EA5E9, #10B981) !important; color: #FFFFFF !important; border: none !important; font-weight: 700 !important; border-radius: 10px !important; box-shadow: 0 4px 18px rgba(16,185,129,0.35) !important; }
[data-testid="stDataFrame"], [data-testid="stDataFrame"] > div, [data-testid="stDataFrame"] iframe { background-color: #131A26 !important; color: #E2E8F0 !important; }
[data-testid="stPlotlyChart"], [data-testid="stPlotlyChart"] > div { background-color: #131A26 !important; border: 1px solid #2A3550 !important; border-radius: 14px !important; padding: 8px !important; box-shadow: 0 6px 24px rgba(0,0,0,0.35) !important; }
[data-testid="stAlert"] { background-color: #131A26 !important; color: #E2E8F0 !important; border: 1px solid #2A3550 !important; border-left: 5px solid #10B981 !important; border-radius: 12px !important; }
[data-testid="stAlert"] p, [data-testid="stAlert"] span, [data-testid="stAlert"] div { color: #E2E8F0 !important; }
[data-testid="stMetric"] { background-color: #131A26 !important; border: 1px solid #2A3550 !important; border-radius: 14px !important; padding: 12px !important; }
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #FFFFFF !important; }
.section-card { background: linear-gradient(90deg, #1A2436 0%, #131A26 100%); border: 1px solid #2A3550; border-left: 5px solid #F59E0B; border-radius: 12px; padding: 12px 16px; margin: 18px 0 10px 0; }
.section-card-blue { border-left: 5px solid #3B82F6 !important; }
.section-card-green { border-left: 5px solid #10B981 !important; }
.section-card-pink { border-left: 5px solid #EC4899 !important; }
.audit-card-blue { background: linear-gradient(180deg, #1E3A5F 0%, #131A26 100%); border: 1px solid #3B82F6; border-top: 4px solid #3B82F6; border-radius: 14px; padding: 14px; }
.audit-card-gold { background: linear-gradient(180deg, #4A3410 0%, #131A26 100%); border: 1px solid #FFAB00; border-top: 4px solid #FFAB00; border-radius: 14px; padding: 14px; }
.audit-card-green { background: linear-gradient(180deg, #0F3D33 0%, #131A26 100%); border: 1px solid #00C853; border-top: 4px solid #00C853; border-radius: 14px; padding: 14px; }

/* ===== HERO STADION GEDE - INI YANG BAKAL KELIATAN JELAS ===== */
.hero-stadium {
    height: 300px;
    border-radius: 18px;
    border: 3px solid #FBBF24;
    overflow: hidden;
    position: relative;
    margin-bottom: 14px;
    background:
        radial-gradient(220px 90px at 10% 12%, rgba(255,255,220,1) 0%, rgba(255,255,180,0.85) 22%, rgba(255,255,180,0.25) 48%, transparent 62%),
        radial-gradient(220px 90px at 30% 12%, rgba(255,255,220,1) 0%, rgba(255,255,180,0.85) 22%, rgba(255,255,180,0.25) 48%, transparent 62%),
        radial-gradient(220px 90px at 70% 12%, rgba(255,255,220,1) 0%, rgba(255,255,180,0.85) 22%, rgba(255,255,180,0.25) 48%, transparent 62%),
        radial-gradient(220px 90px at 90% 12%, rgba(255,255,220,1) 0%, rgba(255,255,180,0.85) 22%, rgba(255,255,180,0.25) 48%, transparent 62%),
        linear-gradient(180deg, #020617 0% 18%, #1E3A8A 18% 48%, #0F5132 48% 52%, #16A34A 52% 78%, #22C55E 78% 100%);
    box-shadow: 0 10px 40px rgba(0,0,0,0.6);
}
.hero-stadium .tribun { position: absolute; top: 22%; left: 0; right: 0; height: 28%; background: repeating-linear-gradient(90deg, #1E3A8A 0 14px, #1D4ED8 14px 28px, #172554 28px 32px); border-top: 4px solid #FBBF24; border-bottom: 4px solid #FBBF24; opacity: 0.95; }
.hero-stadium .tribun::after { content: "👥 👥 👥 👥 👥 👥 👥 👥 👥 👥 👥 👥 👥 👥 👥 👥 👥 👥 👥 👥"; position: absolute; top: 6px; left: 0; right: 0; text-align: center; font-size: 22px; letter-spacing: 6px; }
.hero-stadium .lapangan { position: absolute; bottom: 0; left: 0; right: 0; height: 48%; background: repeating-linear-gradient(90deg, #16A34A 0 80px, #22C55E 80px 160px); border-top: 4px solid #FFFFFF; }
.hero-stadium .garis-tengah { position: absolute; bottom: 0; left: 50%; width: 4px; height: 48%; background: #FFFFFF; transform: translateX(-50%); }
.hero-stadium .lingkaran { position: absolute; bottom: 8%; left: 50%; width: 120px; height: 120px; border: 4px solid #FFFFFF; border-radius: 50%; transform: translateX(-50%); }
.hero-stadium .bola { position: absolute; bottom: 18%; left: 50%; transform: translateX(-50%); font-size: 44px; z-index: 3; filter: drop-shadow(0 6px 10px rgba(0,0,0,0.6)); }
.hero-stadium .gawang-kiri { position: absolute; bottom: 18%; left: 2%; width: 70px; height: 90px; border: 5px solid #FFFFFF; border-left: none; background: rgba(255,255,255,0.15); }
.hero-stadium .gawang-kanan { position: absolute; bottom: 18%; right: 2%; width: 70px; height: 90px; border: 5px solid #FFFFFF; border-right: none; background: rgba(255,255,255,0.15); }
.hero-stadium .teks { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding-top: 52px; text-align: center; z-index: 5; text-shadow: 0 3px 12px rgba(0,0,0,0.9), 0 0 2px #000; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.main-header { background: linear-gradient(90deg, #0F172A 0%, #1E3A5F 45%, #0F3D33 100%); color: #f8fafc; padding: 1.2rem 1.6rem; border-radius: 14px; border-left: 6px solid #10B981; border: 1px solid #2A3550; box-shadow: 0 8px 30px rgba(0,0,0,0.45); margin-bottom: 1.2rem; }
.metric-card { background: linear-gradient(180deg, #1A2436 0%, #131A26 100%); color: #f8fafc; padding: 1.1rem; border-radius: 14px; border: 1px solid #2A3550; height: 100%; box-shadow: 0 6px 20px rgba(0,0,0,0.30); }
.metric-title { font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: #94A3B8; margin-bottom: 0.35rem; }
.metric-value { font-size: 1.55rem; font-weight: 800; color: #ffffff; }
.metric-sub { font-size: 0.82rem; color: #CBD5E1; margin-top: 0.3rem; }
.profit-green { color: #34D399 !important; } .profit-red { color: #F87171 !important; }
.accent-blue { color: #60A5FA !important; } .accent-gold { color: #FBBF24 !important; } .accent-purple { color: #A78BFA !important; }
.insight-card { background: linear-gradient(180deg, #1A2436 0%, #131A26 100%); border: 1px solid #2A3550; border-radius: 14px; padding: 14px; text-align: center; }
.insight-label { font-size: 0.75rem; letter-spacing: 0.08em; color: #94A3B8; text-transform: uppercase; }
.insight-value { font-size: 1.35rem; font-weight: 800; margin-top: 6px; }
.insight-sub { font-size: 0.80rem; color: #CBD5E1; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

def format_idr(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    formatted = f"{abs(int(amount)):,}".replace(",", ".")
    return f"{sign}Rp{formatted}"

def get_peak_hours_label(now_wita: datetime) -> str:
    h = now_wita.hour
    if 13 <= h < 19:
        return "13:00–19:00 WITA: Jendela Potensi Pertandingan Asia"
    if h >= 20 or h < 2:
        return "20:00–02:00 WITA: Jendela Potensi Pertandingan Eropa"
    if 2 <= h < 7:
        return "02:00–07:00 WITA: Jendela Potensi Pertandingan Amerika"
    return "07:00–13:00 WITA: Jam Transisi (Aktivitas Pertandingan Reguler Rendah)"

def render_dashboard() -> None:
    # ===== HERO STADION - LANGSUNG KELIATAN, TIDAK KETUTUP KARTU =====
    st.markdown("""
    <div class="hero-stadium">
        <div class="tribun"></div>
        <div class="lapangan"></div>
        <div class="garis-tengah"></div>
        <div class="lingkaran"></div>
        <div class="gawang-kiri"></div>
        <div class="gawang-kanan"></div>
        <div class="bola">⚽</div>
        <div class="teks">
            <div style="font-size:13px; letter-spacing:4px; font-weight:800; color:#FDE68A;">🏟️ STADION MALAM HARI &nbsp;•&nbsp; LAMPU SOROT MENYALA</div>
            <div style="font-size:34px; font-weight:900; color:white; line-height:1.1; margin-top:6px;">TRADING BOLA MENIT 60<br><span style="color:#34D399;">LAST GOAL SYSTEM</span></div>
            <div style="margin-top:8px; background:rgba(0,0,0,0.65); padding:6px 14px; border-radius:20px; font-size:13px; font-weight:700; color:white; border:1px solid #FBBF24;">OVER 0.5 GOAL &nbsp;•&nbsp; ENTRY 60'-66' &nbsp;•&nbsp; SKOR 0-0 &nbsp;•&nbsp; CUT-OFF 12:00 WITA</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🔄 Live Scan ESPN")
    c_scan1, c_scan2, c_scan3 = st.columns([1, 1, 3])
    with c_scan1:
        if st.button("🔄 Scan Sekarang", use_container_width=True):
            with st.spinner("Lagi scan ESPN..."):
                res = _try_run_scan()
                if res["ok"]:
                    st.success(f"Scan berhasil: {res['msg']}")
                else:
                    st.warning(f"Scan belum jalan: {res['msg']} | Masih pakai data lama, tidak error.")
                st.rerun()
    with c_scan2:
        if st.button("🧹 Clear Cache & Reload", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with c_scan3:
        st.caption("Kalau tombol Scan bilang 'scanner.py belum ada', berarti file scanner bapak namanya beda. Kirim nama file scanner-nya, saya sesuaikan import-nya. Data lama tetap tampil, tidak hilang.")
    all_records = []
    if load_matches_from_old_repo:
        try:
            all_records = load_matches_from_old_repo() or []
        except Exception:
            all_records = []
    if not all_records and TradingDatabase:
        try:
            db = TradingDatabase()
            all_records = db.get_all_matches()
        except Exception:
            all_records = []
    try:
        scan_meta = load_scan_metadata() or {}
    except Exception:
        scan_meta = {}
    if not scan_meta:
        scan_meta = {"scan_timestamp_wita": "DARI REPO LAMA skor60", "source_status": "LOADED_FROM_OLD_REPO", "live_matches_seen": len(all_records)}
    try:
        if "last_scan_time" not in st.session_state:
            st.session_state.last_scan_time = None
        _now_ts = datetime.now(timezone.utc).timestamp()
        _last_ts = st.session_state.last_scan_time or 0
        if (_now_ts - _last_ts) > 900:
            _res_auto = _try_run_scan()
            if _res_auto["ok"]:
                st.session_state.last_scan_time = _now_ts
                try:
                    _fresh = load_matches_from_old_repo() or []
                    if _fresh:
                        all_records = _fresh
                except Exception:
                    pass
    except Exception:
        pass
    stats = compute_full_dashboard_statistics(all_records)
    now_wita = datetime.now(timezone.utc).astimezone(WITA_TZ)
    last_scan_wita = scan_meta.get("scan_timestamp_wita") or "BELUM TERSEDIA"
    source_status = scan_meta.get("source_status") or "NEVER_SCANNED"
    last_db_update_str = "DARI REPO LAMA skor60 (via data_loader.py)"
    st.markdown(f"""<div class="main-header"><h2 style="margin:0; font-weight:800;">⚽ TRADING BOLA MENIT 60 — <span style="color:#34D399;">LAST GOAL SYSTEM</span></h2><p style="margin:6px 0 10px 0; color:#94A3B8;">Market: <b style="color:#FBBF24;">OVER 0.5 GOAL AFTER ENTRY (Menit 60'–66', Skor Entry 0-0)</b> | Cut-Off Trading Day: <b style="color:#fff;">12:00 WITA</b></p><div style="display:flex; flex-wrap:wrap; gap:18px; font-size:0.86rem;"><span>🟢 <b>System Status:</b> {source_status}</span><span>📡 <b>Data Source:</b> ESPN API (All + Multi-League)</span><span>🕒 <b>Last Scan:</b> {last_scan_wita}</span><span>💾 <b>Last DB Update:</b> {last_db_update_str}</span><span>⏰ <b>Current WITA:</b> {now_wita.strftime('%Y-%m-%d %H:%M:%S')}</span><span>⚽ <b>Total Matches:</b> {len(all_records)}</span></div></div>""", unsafe_allow_html=True)
    st.info(f"🕒 **Panduan Monitoring Jam Aktif (WITA):** {get_peak_hours_label(now_wita)} *(Panduan monitoring, bukan jaminan jumlah pertandingan).* Pertandingan LIVE terdeteksi pada scan terakhir: **{scan_meta.get('live_matches_seen', 0)}**")
    sim_stats = stats["simulated"]
    act_stats = stats["actual"]
    major_stats = stats["by_league_tier"]["MAJOR"]
    cols = st.columns(5)
    with cols[0]:
        st.markdown(f"""<div class="metric-card" style="border-top: 4px solid #60A5FA;"><div class="metric-title">💰 CARD 1 – MODAL PER MATCH</div><div class="metric-value accent-blue">{format_idr(DEFAULT_STAKE)}</div><div class="metric-sub">Odds Simulasi: <b>{SIMULATED_ODDS:.2f}</b> ({CURRENCY})</div></div>""", unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f"""<div class="metric-card" style="border-top: 4px solid #F59E0B;"><div class="metric-title">📤 CARD 2 – TOTAL MODAL KELUAR</div><div class="metric-value accent-gold">{format_idr(sim_stats['total_stake_settled'])}</div><div class="metric-sub">Settled: <b>{sim_stats['settled_matches']}</b> Match (Excl. Pending/Void)</div></div>""", unsafe_allow_html=True)
    with cols[2]:
        act_profit_label = (f"{format_idr(act_stats['net_profit'])} (ROI {act_stats['roi']:.2f}%)" if act_stats["available"] else "ACTUAL ODDS: NOT AVAILABLE")
        profit_color = "profit-green" if sim_stats['net_profit'] >= 0 else "profit-red"
        st.markdown(f"""<div class="metric-card" style="border-top: 4px solid #10B981;"><div class="metric-title">📈 CARD 3 – TOTAL PROFIT</div><div class="metric-value {profit_color}">{format_idr(sim_stats['net_profit'])} <span style="font-size:0.8rem; color:#10B981;">(Sim)</span></div><div class="metric-sub">Sim ROI: <b>{sim_stats['roi']:.2f}%</b><br/>Actual: <b>{act_profit_label}</b></div></div>""", unsafe_allow_html=True)
    with cols[3]:
        ci_low, ci_high = sim_stats["wilson_ci_95"]
        st.markdown(f"""<div class="metric-card" style="border-top: 4px solid #A78BFA;"><div class="metric-title">🎯 CARD 4 – WIN RATE</div><div class="metric-value accent-purple">{sim_stats['win_rate']:.2f}%</div><div class="metric-sub"><b>{sim_stats['win']}</b>W / <b>{sim_stats['lose']}</b>L / <b>{sim_stats['void']}</b>V / <b>{sim_stats['pending']}</b>P<br/>Wilson 95% CI: [{ci_low:.1f}%, {ci_high:.1f}%]</div></div>""", unsafe_allow_html=True)
    with cols[4]:
        major_badge = ("⚠️ LOW SAMPLE SIZE" if major_stats["settled_matches"] < MIN_SAMPLE_SIZE_RELIABLE else "✅ SAMPLE OK")
        st.markdown(f"""<div class="metric-card" style="border-top: 4px solid #EC4899;"><div class="metric-title">🏆 CARD 5 – MAJOR PERFORMANCE</div><div class="metric-value">{major_stats['win_rate']:.2f}% WR</div><div class="metric-sub">Profit (Sim): <b>{format_idr(major_stats['simulated_profit'])}</b> | ROI: <b>{major_stats['simulated_roi']:.2f}%</b><br/>Sampel: <b>{major_stats['settled_matches']}</b> settled ({major_badge})</div></div>""", unsafe_allow_html=True)
    st.write("")
    with st.expander("📊 Detail Statistik Kuantitatif, Break-Even, EV, & Klasifikasi Liga (Major / Minor / Unknown)", expanded=True):
        tab_sim, tab_act, tab_tier = st.tabs(["A. SIMULATED PERFORMANCE (Odds 1.80)", "B. ACTUAL ODDS PERFORMANCE", "C. Klasifikasi Liga (MAJOR / MINOR / UNKNOWN)"])
        with tab_sim:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Break-Even Win Rate", f"{sim_stats['break_even_win_rate']:.2f}%" if sim_stats["break_even_win_rate"] else "N/A")
            c2.metric("Expected Value (EV / Match)", format_idr(int(sim_stats["expected_value_per_match"])) if sim_stats["expected_value_per_match"] is not None else "N/A")
            c3.metric("Maximum Drawdown", format_idr(sim_stats["max_drawdown"]))
            c4.metric("Profit Factor", f"{sim_stats['profit_factor']}" if sim_stats["profit_factor"] != float("inf") else "∞")
            c5, c6, c7, c8 = st.columns(4)
            c5.metric("Longest Winning Streak", f"{sim_stats['longest_winning_streak']} Match")
            c6.metric("Longest Losing Streak", f"{sim_stats['longest_losing_streak']} Match")
            c7.metric("Wilson 95% CI", f"{sim_stats['wilson_ci_95'][0]:.2f}% – {sim_stats['wilson_ci_95'][1]:.2f}%")
            c8.metric("Status Ukuran Sampel", sim_stats["sample_size_warning"])
        with tab_act:
            if not act_stats["available"]:
                st.warning("ACTUAL ODDS: NOT AVAILABLE — Belum ada kandidat pertandingan yang memiliki data odds aktual dari provider saat entry.")
            else:
                a1, a2, a3, a4 = st.columns(4)
                a1.metric("Settled Matches (Actual Odds)", act_stats["settled_matches"])
                a2.metric("Average Entry Odds", f"{act_stats['average_odds']:.3f}" if act_stats["average_odds"] else "N/A")
                a3.metric("Break-Even WR (Actual)", f"{act_stats['break_even_win_rate']:.2f}%" if act_stats["break_even_win_rate"] else "N/A")
                a4.metric("Actual Net Profit", format_idr(act_stats["net_profit"]))
        with tab_tier:
            tier_rows = []
            for tier_key in ("MAJOR", "MINOR", "UNKNOWN"):
                t_info = stats["by_league_tier"][tier_key]
                tier_rows.append({"Kategori Liga": tier_key, "Total Match": t_info["total_matches"], "Settled": t_info["settled_matches"], "WIN": t_info["win"], "LOSE": t_info["lose"], "VOID": t_info["void"], "PENDING": t_info["pending"], "Win Rate (%)": f"{t_info['win_rate']:.2f}%", "Profit Simulasi": format_idr(t_info["simulated_profit"]), "ROI Simulasi (%)": f"{t_info['simulated_roi']:.2f}%", "Profit Aktual": format_idr(t_info["actual_profit"]) if t_info["actual_available"] else "NOT AVAILABLE", "Validitas Sampel": t_info["sample_status"]})
            df_tier_tab = pd.DataFrame(tier_rows)
            styled_tier = df_tier_tab.style.set_properties(**{"background-color": "#1A2436", "color": "#E2E8F0"}).map(color_profit_vivid, subset=["Profit Simulasi", "Profit Aktual"]).map(color_win_rate_vivid, subset=["Win Rate (%)"]).map(color_roi, subset=["ROI Simulasi (%)"]).set_table_styles([{"selector": "th", "props": [("background-color", "#1E3A5F"), ("color", "white"), ("font-weight", "800")]}])
            st.dataframe(styled_tier, use_container_width=True, hide_index=True)
    st.markdown("""<div class="section-card section-card-green"><h3 style="margin:0; border:none; padding:0;">📈 Visualisasi Performa & Distribusi</h3><p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.85rem;">Grafik profit, win rate, dan distribusi entry — semua sudah dark + berwarna.</p></div>""", unsafe_allow_html=True)
    if len(all_records) == 0:
        st.info("NO LIVE MATCH FOUND / BELUM ADA DATA HISTORIS — Grafik akan ditampilkan otomatis setelah terdapat data pertandingan yang tercatat.")
    else:
        g_col1, g_col2, g_col3 = st.columns(3)
        with g_col1:
            status_counts = {"WIN": sim_stats["win"], "LOSE": sim_stats["lose"], "VOID": sim_stats["void"], "PENDING": sim_stats["pending"], "REVIEW": sim_stats["unverified"]}
            non_zero_status = {k: v for k, v in status_counts.items() if v > 0}
            if non_zero_status:
                fig_donut = px.pie(names=list(non_zero_status.keys()), values=list(non_zero_status.values()), hole=0.55, title="Distribusi Status Pertandingan", color=list(non_zero_status.keys()), color_discrete_map={"WIN": "#00C853", "LOSE": "#FF5252", "VOID": "#64748B", "PENDING": "#FFAB00", "REVIEW": "#FF6D00"})
                st.plotly_chart(style_fig(fig_donut), use_container_width=True)
        day_summaries = list(reversed(stats["by_trading_day"]))
        settled_days = [d for d in day_summaries if d["settled_matches"] > 0]
        with g_col2:
            if settled_days:
                df_days = pd.DataFrame(settled_days)
                fig_daily = px.bar(df_days, x="trading_day", y="simulated_profit", title="Grafik Profit Harian (Simulasi IDR)", labels={"trading_day": "Trading Day (Cut-off 12:00 WITA)", "simulated_profit": "Net Profit (IDR)"}, color="simulated_profit", color_continuous_scale=["#FF5252", "#FFAB00", "#00C853"])
                st.plotly_chart(style_fig(fig_daily), use_container_width=True)
        with g_col3:
            if settled_days:
                df_days = pd.DataFrame(settled_days)
                df_days["cumulative_profit"] = df_days["simulated_profit"].cumsum()
                fig_cum = px.line(df_days, x="trading_day", y="cumulative_profit", markers=True, title="Grafik Cumulative Profit (Simulasi IDR)", labels={"trading_day": "Trading Day", "cumulative_profit": "Cumulative Profit (IDR)"}, color_discrete_sequence=["#00E676"])
                st.plotly_chart(style_fig(fig_cum), use_container_width=True)
        g_col4, g_col5, g_col6 = st.columns(3)
        with g_col4:
            tier_list = [stats["by_league_tier"]["MAJOR"], stats["by_league_tier"]["MINOR"], stats["by_league_tier"]["UNKNOWN"]]
            active_tiers = [t for t in tier_list if t["total_matches"] > 0]
            if active_tiers:
                df_tier = pd.DataFrame(active_tiers)
                fig_tier = px.bar(df_tier, x="tier", y=["win", "lose"], barmode="group", title="Performa Major vs Minor vs Unknown", labels={"tier": "Klasifikasi Liga", "value": "Jumlah Pertandingan"}, color_discrete_sequence=["#00C853", "#FF5252"])
                st.plotly_chart(style_fig(fig_tier), use_container_width=True)
        with g_col5:
            actual_settled = [r for r in all_records if r.get("odds_entry") is not None and r.get("result") in ("WIN", "LOSE")]
            if len(actual_settled) >= 2:
                df_odds = pd.DataFrame(actual_settled)
                df_odds["is_win"] = (df_odds["result"] == "WIN").astype(int) * 100.0
                fig_odds = px.histogram(df_odds, x="odds_entry", y="is_win", histfunc="avg", nbins=8, title="Win Rate (%) Berdasarkan Odds Aktual", labels={"odds_entry": "Odds Entry", "is_win": "Win Rate (%)"})
                st.plotly_chart(style_fig(fig_odds), use_container_width=True)
            else:
                st.caption("Data odds aktual belum cukup untuk grafik Win Rate berdasarkan odds.")
        with g_col6:
            entry_mins = [int(r["minute_detected"]) for r in all_records if r.get("minute_detected") is not None]
            if entry_mins:
                df_min = pd.DataFrame({"minute_detected": entry_mins})
                fig_min = px.histogram(df_min, x="minute_detected", nbins=7, title="Distribusi Menit Entry (60'–66')", labels={"minute_detected": "Menit Deteksi Entry"}, color_discrete_sequence=["#40C4FF"])
                fig_min.update_layout(bargap=0.2)
                st.plotly_chart(style_fig(fig_min), use_container_width=True)
    st.markdown("""<div class="section-card"><h3 style="margin:0; border:none; padding:0;">🔥 Insight Trading Day</h3><p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.85rem;">Ringkasan cepat sebelum masuk ke tabel detail.</p></div>""", unsafe_allow_html=True)
    if stats["by_trading_day"]:
        days_for_insight = [d for d in stats["by_trading_day"] if d["settled_matches"] > 0]
        if days_for_insight:
            best_day = max(days_for_insight, key=lambda x: x["simulated_profit"])
            worst_day = min(days_for_insight, key=lambda x: x["simulated_profit"])
            avg_profit = sum(d["simulated_profit"] for d in days_for_insight) / len(days_for_insight)
            i1, i2, i3 = st.columns(3)
            with i1:
                st.markdown(f"""<div class="insight-card" style="border-top: 4px solid #00C853;"><div class="insight-label">🏆 Hari Terbaik</div><div class="insight-value" style="color:#00E676;">{best_day['trading_day']}</div><div class="insight-sub">{format_idr(best_day['simulated_profit'])} • {best_day['summary_text']} • WR {best_day['win_rate']:.1f}%</div></div>""", unsafe_allow_html=True)
            with i2:
                st.markdown(f"""<div class="insight-card" style="border-top: 4px solid #FF5252;"><div class="insight-label">📉 Hari Terburuk</div><div class="insight-value" style="color:#FF5252;">{worst_day['trading_day']}</div><div class="insight-sub">{format_idr(worst_day['simulated_profit'])} • {worst_day['summary_text']} • WR {worst_day['win_rate']:.1f}%</div></div>""", unsafe_allow_html=True)
            with i3:
                avg_color = "#00E676" if avg_profit >= 0 else "#FF5252"
                st.markdown(f"""<div class="insight-card" style="border-top: 4px solid #FFAB00;"><div class="insight-label">📊 Rata-rata Profit / Hari</div><div class="insight-value" style="color:{avg_color};">{format_idr(int(avg_profit))}</div><div class="insight-sub">Dari {len(days_for_insight)} hari settled • Total {format_idr(sim_stats['net_profit'])}</div></div>""", unsafe_allow_html=True)
    st.markdown("""<div class="section-card section-card-blue"><h3 style="margin:0; border:none; padding:0;">🗓️ Ringkasan Partisi Harian (Cut-Off 12:00 WITA)</h3><p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.85rem;">Hijau neon = untung besar, Merah terang = rugi, Kuning emas = win rate sedang.</p></div>""", unsafe_allow_html=True)
    if not stats["by_trading_day"]:
        st.caption("Belum ada riwayat trading day di database.")
    else:
        df_td = pd.DataFrame([{"Trading Day": d["trading_day"], "Rekor (W-L)": d["summary_text"], "Total Match": d["total_matches"], "Settled": d["settled_matches"], "VOID": d["void"], "PENDING": d["pending"], "Win Rate": f"{d['win_rate']:.2f}%", "Net Profit (Simulasi)": format_idr(d["simulated_profit"]), "ROI (Simulasi)": f"{d['simulated_roi']:.2f}%", "Net Profit (Aktual)": format_idr(d["actual_profit"]) if d["actual_profit"] is not None else "NOT AVAILABLE"} for d in stats["by_trading_day"]])
        styled_td = df_td.style.set_properties(**{"background-color": "#1A2436", "color": "#FFFFFF", "font-weight": "600"}).map(color_profit_vivid, subset=["Net Profit (Simulasi)", "Net Profit (Aktual)"]).map(color_win_rate_vivid, subset=["Win Rate"]).map(color_roi, subset=["ROI (Simulasi)"]).map(color_rekor, subset=["Rekor (W-L)"]).set_table_styles([{"selector": "th", "props": [("background-color", "#1E3A5F"), ("color", "white"), ("font-weight", "800")]}])
        st.dataframe(styled_td, use_container_width=True, hide_index=True)
    st.markdown("""<div class="section-card section-card-pink"><h3 style="margin:0; border:none; padding:0;">📋 Daftar Pertandingan (20 Terbaru Sesuai Filter)</h3><p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.85rem;">Sekarang pakai st.html — warna pill-nya pasti muncul, tidak jadi teks putih lagi.</p></div>""", unsafe_allow_html=True)
    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
        status_filter = st.selectbox("Filter Kategori / Status:", options=["Semua", "LIVE", "WIN", "LOSE", "PENDING", "VOID", "REVIEW", "MAJOR", "MINOR"], index=0)
    with f_col2:
        available_days = ["Semua"] + [d["trading_day"] for d in stats["by_trading_day"]]
        day_filter = st.selectbox("Filter Trading Day:", options=available_days, index=0)
    filtered_records: List[Dict[str, Any]] = []
    for rec in all_records:
        if day_filter != "Semua" and rec.get("trading_day") != day_filter:
            continue
        res = str(rec.get("result") or "PENDING").upper()
        m_status = str(rec.get("match_status") or "").upper()
        s_status = str(rec.get("settlement_status") or "PENDING").upper()
        l_cat = str(rec.get("league_category") or ("MAJOR" if rec.get("is_major") else "UNKNOWN")).upper()
        if status_filter == "LIVE" and m_status not in ("FIRST HALF", "SECOND HALF", "HALFTIME", "LIVE", "EXTRA TIME", "PENALTIES"):
            continue
        elif status_filter == "WIN" and res != "WIN":
            continue
        elif status_filter == "LOSE" and res != "LOSE":
            continue
        elif status_filter == "PENDING" and res != "PENDING":
            continue
        elif status_filter == "VOID" and res != "VOID":
            continue
        elif status_filter == "REVIEW" and (s_status != "REVIEW" and res != "DATA UNVERIFIED"):
            continue
        elif status_filter == "MAJOR" and l_cat != "MAJOR":
            continue
        elif status_filter == "MINOR" and l_cat != "MINOR":
            continue
        filtered_records.append(rec)
    top_20 = filtered_records[:20]
    if not top_20:
        st.warning("NO LIVE MATCH FOUND — Tidak ada pertandingan yang cocok dengan filter saat ini.")
    else:
        table_rows = []
        for idx, rec in enumerate(top_20, start=1):
            res = str(rec.get("result") or "PENDING").upper()
            m_status = str(rec.get("match_status") or "")
            is_live_now = m_status in ("First Half", "Second Half", "Halftime", "Live", "Extra Time", "Penalties") and res == "PENDING"
            display_status = "LIVE" if is_live_now else ("REVIEW" if rec.get("settlement_status") == "REVIEW" else res)
            badge_tier = "MAJOR" if rec.get("is_major") else str(rec.get("league_category") or "UNKNOWN")
            odds_disp = f"{rec.get('odds_entry', SIMULATED_ODDS):.2f} (Actual)" if rec.get("odds_entry") is not None else f"{SIMULATED_ODDS:.2f} (Sim)"
            pnl_val = rec.get("actual_profit") if rec.get("odds_entry") is not None else rec.get("simulated_profit", 0)
            act_label = rec.get("activity_label", "NORMAL")
            table_rows.append({"No": idx, "Match ID": rec.get("match_id"), "Match": f"{rec.get('home_team')} vs {rec.get('away_team')}", "League": rec.get("league"), "Badge": badge_tier, "Activity": act_label, "Min Entry": f"{rec.get('minute_detected')}'", "Entry Score": rec.get("score_at_entry"), "Entry Odds": odds_disp, "Current Score": rec.get("current_score"), "Final Score": rec.get("final_score") or "-", "Result": display_status, "Profit": format_idr(int(pnl_val or 0)) if res in ("WIN", "LOSE", "VOID") else "Rp0 (Pending)", "Trading Day": rec.get("trading_day")})
        try:
            st.html(render_match_table_html(table_rows))
        except Exception:
            import streamlit.components.v1 as components
            components.html(render_match_table_html(table_rows), height=700, scrolling=True)
        st.markdown("""<div class="section-card section-card-green"><h3 style="margin:0; border:none; padding:0;">🔍 Audit Trail & Penjelasan Hasil Pertandingan</h3><p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.85rem;">Pilih satu pertandingan untuk melihat bukti entry, settlement, dan verifikasinya.</p></div>""", unsafe_allow_html=True)
        match_options = {f"[{r.get('trading_day')}] {r.get('home_team')} vs {r.get('away_team')} (ID: {r.get('match_id')})": r for r in top_20}
        selected_label = st.selectbox("Pilih Pertandingan untuk Audit Mendalam:", options=list(match_options.keys()))
        if selected_label:
            sel_rec = match_options[selected_label]
            audit_info = audit_result(sel_rec)
            st.markdown(f"**Penjelasan Audit Otomatis:** {audit_info['explanation']}")
            if not audit_info["audit_passed"]:
                st.error(f"Temuan Audit: {', '.join(audit_info['issues'])}")
            a_col1, a_col2, a_col3 = st.columns(3)
            with a_col1:
                st.markdown(f"""<div class="audit-card-blue"><b style="color:#40C4FF;">🔵 1. Identitas & Waktu Entry</b><br><br><span>Match ID: <b>{sel_rec.get('match_id')}</b></span><br><span>League: <b>{sel_rec.get('league_slug')} ({sel_rec.get('league_category')})</b></span><br><span>Activity: <b>{sel_rec.get('activity_label', 'NORMAL')}</b></span><br><span>Entry UTC: <b>{sel_rec.get('detected_at_utc')}</b></span><br><span>Entry WITA: <b>{sel_rec.get('detected_at_wita')}</b></span><br><span>Trading Day: <b>{sel_rec.get('trading_day')}</b></span></div>""", unsafe_allow_html=True)
            with a_col2:
                st.markdown(f"""<div class="audit-card-gold"><b style="color:#FFD54F;">🟡 2. Parameter Entry & Settlement</b><br><br><span>Menit Entry: <b>{sel_rec.get('minute_detected')}'</b></span><br><span>Skor Entry: <b>{sel_rec.get('score_at_entry')}</b></span><br><span>Odds Aktual: <b>{sel_rec.get('odds_entry') or 'NOT AVAILABLE'}</b></span><br><span>Sumber Odds: <b>{sel_rec.get('odds_source')}</b></span><br><span>Status Match: <b>{sel_rec.get('match_status')}</b></span><br><span>Settlement: <b>{sel_rec.get('settlement_status')} ({sel_rec.get('result')})</b></span></div>""", unsafe_allow_html=True)
            with a_col3:
                act_p2 = sel_rec.get("actual_profit")
                st.markdown(f"""<div class="audit-card-green"><b style="color:#69F0AE;">🟢 3. Profit & Verifikasi</b><br><br><span>Stake: <b>{format_idr(int(sel_rec.get('stake') or DEFAULT_STAKE))}</b></span><br><span>Profit Sim: <b>{format_idr(int(sel_rec.get('simulated_profit') or 0))}</b></span><br><span>Profit Aktual: <b>{format_idr(int(act_p2)) if act_p2 is not None else 'NOT AVAILABLE'}</b></span><br><span>Sumber Data: <b>{sel_rec.get('source')}</b></span><br><span>Verifikasi: <b>{sel_rec.get('verification_status')}</b></span><br><span>Terakhir Diverifikasi: <b>{sel_rec.get('last_verified_at')}</b></span></div>""", unsafe_allow_html=True)
            s_col1, s_col2 = st.columns(2)
            with s_col1:
                st.markdown("**Riwayat Snapshot Skor Berkala:**")
                snaps = sel_rec.get("snapshots") or []
                if snaps:
                    st.dataframe(style_dark_table(pd.DataFrame(snaps)), use_container_width=True, hide_index=True)
                else:
                    st.caption("Tidak ada snapshot.")
            with s_col2:
                st.markdown("**Bukti Event Gol / Perubahan Skor:**")
                g_events = sel_rec.get("goal_events") or []
                if g_events:
                    st.dataframe(style_dark_table(pd.DataFrame(g_events)), use_container_width=True, hide_index=True)
                else:
                    st.caption("Belum ada event gol tercatat.")
            revs = sel_rec.get("revision_history") or []
            if revs:
                st.markdown("**Riwayat Perubahan / Koreksi Resmi Provider (Revision History):**")
                st.dataframe(style_dark_table(pd.DataFrame(revs)), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    render_dashboard()
