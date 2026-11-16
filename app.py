"""
app.py
Dashboard Streamlit Produksi untuk TRADING BOLA MENIT 60 – LAST GOAL SYSTEM.
FULL VERSION - FIX applymap -> map (Pandas baru)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from zoneinfo import ZoneInfo

# =====================================================================
# IMPORT DENGAN CADANGAN
# =====================================================================
try:
    from config import (
        CURRENCY,
        DEFAULT_STAKE,
        MATCHES_JSON_PATH,
        MIN_SAMPLE_SIZE_RELIABLE,
        SIMULATED_ODDS,
        TIMEZONE_NAME,
    )
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
        return {
            "label": record.get("activity_label", "NORMAL"),
            "explanation": "Audit cadangan",
            "audit_passed": True,
            "issues": [],
        }

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
    """Panggil scan ESPN kalau file scanner-nya ada."""
    if _run_scan_from_scanner is None:
        return {"ok": False, "msg": "File scanner.py belum ada / nama fungsinya beda"}
    try:
        result = _run_scan_from_scanner()
        return {"ok": True, "msg": str(result)}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

WITA_TZ = ZoneInfo(TIMEZONE_NAME)

# =====================================================================
# HELPER GRAFIK & TABEL - VERSI BERWARNA
# =====================================================================
def style_fig(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#131A26",
        plot_bgcolor="#131A26",
        font=dict(color="#E2E8F0", size=12),
        title_font=dict(color="#FFFFFF", size=14, family="Arial Black"),
        xaxis=dict(
            gridcolor="#2A3550",
            zerolinecolor="#2A3550",
            tickfont=dict(color="#94A3B8"),
        ),
        yaxis=dict(
            gridcolor="#2A3550",
            zerolinecolor="#2A3550",
            tickfont=dict(color="#94A3B8"),
        ),
        legend=dict(
            bgcolor="#131A26",
            font=dict(color="#E2E8F0"),
        ),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig

def style_dark_table(df):
    """Tabel dasar hitam untuk tabel kecil."""
    return (
        df.style.set_properties(
            **{
                "background-color": "#131A26",
                "color": "#E2E8F0",
                "border-color": "#2A3550",
            }
        ).set_table_styles(
            [
                {
                    "selector": "th",
                    "props": [
                        ("background-color", "#1E293B"),
                        ("color", "white"),
                        ("border-color", "#2A3550"),
                    ],
                },
                {
                    "selector": "td",
                    "props": [("border-color", "#2A3550")],
                },
            ]
        )
    )

def color_profit(val):
    """Buat kolom profit jadi hijau kalau untung, merah kalau rugi."""
    try:
        is_neg = str(val).strip().startswith("-")
        if is_neg:
            return "background-color: #3F1D1D; color: #FCA5A5; font-weight: 700;"
        if "Rp0" in str(val):
            return "background-color: #131A26; color: #94A3B8;"
        return "background-color: #123325; color: #6EE7B7; font-weight: 700;"
    except Exception:
        return ""

def color_win_rate(val):
    """Win rate tinggi = hijau, sedang = kuning, rendah = merah."""
    try:
        num = float(str(val).replace("%", ""))
        if num >= 65:
            return "background-color: #123325; color: #6EE7B7; font-weight: 700;"
        if num >= 55:
            return "background-color: #3A2E12; color: #FCD34D; font-weight: 700;"
        return "background-color: #3F1D1D; color: #FCA5A5; font-weight: 700;"
    except Exception:
        return ""

st.set_page_config(
    page_title="TRADING BOLA MENIT 60 – LAST GOAL SYSTEM",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================================
# CSS PREMIUM - ATAS BERWARNA, BAWAH JUGA BERWARNA
# =====================================================================
st.markdown(
    """
<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMainBlockContainer"], [data-testid="stHeader"] {
    background: radial-gradient(1200px 600px at 20% 0%, #111B2E 0%, #0A0F1A 45%, #080A10 100%) !important;
    background-color: #0A0F1A !important;
}
[data-testid="stMainBlockContainer"] {
    padding-top: 18px !important;
    max-width: 100% !important;
}
h1, h2, h3, h4, p, span, div, label, li {
    color: #E2E8F0 !important;
}
small, .stCaption, [data-testid="stCaptionContainer"] {
    color: #94A3B8 !important;
}
h3 {
    border-left: 5px solid #10B981 !important;
    padding-left: 12px !important;
}
[data-testid="stExpander"], [data-testid="stTabs"], [data-testid="stSelectbox"], [data-testid="stDataFrame"] {
    background-color: #131A26 !important;
    border: 1px solid #2A3550 !important;
    border-radius: 14px !important;
}
[data-testid="stExpander"] summary, button[data-baseweb="tab"] {
    color: #E2E8F0 !important;
    background-color: #131A26 !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    background-color: #1E293B !important;
    color: #FFFFFF !important;
    border-bottom: 3px solid #10B981 !important;
}
div[data-baseweb="select"] > div, input {
    background-color: #1A2436 !important;
    color: #FFFFFF !important;
    border-color: #2A3550 !important;
}
.stButton > button {
    background: linear-gradient(90deg, #0EA5E9, #10B981) !important;
    color: #FFFFFF !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    box-shadow: 0 4px 18px rgba(16,185,129,0.35) !important;
}
[data-testid="stDataFrame"], [data-testid="stDataFrame"] > div, [data-testid="stDataFrame"] iframe {
    background-color: #131A26 !important;
    color: #E2E8F0 !important;
}
[data-testid="stPlotlyChart"], [data-testid="stPlotlyChart"] > div {
    background-color: #131A26 !important;
    border: 1px solid #2A3550 !important;
    border-radius: 14px !important;
    padding: 8px !important;
    box-shadow: 0 6px 24px rgba(0,0,0,0.35) !important;
}
[data-testid="stAlert"] {
    background-color: #131A26 !important;
    color: #E2E8F0 !important;
    border: 1px solid #2A3550 !important;
    border-left: 5px solid #10B981 !important;
    border-radius: 12px !important;
}
[data-testid="stAlert"] p, [data-testid="stAlert"] span, [data-testid="stAlert"] div {
    color: #E2E8F0 !important;
}
[data-testid="stMetric"] {
    background-color: #131A26 !important;
    border: 1px solid #2A3550 !important;
    border-radius: 14px !important;
    padding: 12px !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
    color: #FFFFFF !important;
}
.section-card {
    background: linear-gradient(90deg, #1A2436 0%, #131A26 100%);
    border: 1px solid #2A3550;
    border-left: 5px solid #F59E0B;
    border-radius: 12px;
    padding: 12px 16px;
    margin: 18px 0 10px 0;
}
.section-card-blue {
    border-left: 5px solid #3B82F6 !important;
}
.section-card-green {
    border-left: 5px solid #10B981 !important;
}
.section-card-pink {
    border-left: 5px solid #EC4899 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(90deg, #0F172A 0%, #1E3A5F 45%, #0F3D33 100%);
        color: #f8fafc;
        padding: 1.4rem 1.8rem;
        border-radius: 16px;
        border-left: 6px solid #10B981;
        border: 1px solid #2A3550;
        box-shadow: 0 8px 30px rgba(0,0,0,0.45);
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background: linear-gradient(180deg, #1A2436 0%, #131A26 100%);
        color: #f8fafc;
        padding: 1.1rem;
        border-radius: 14px;
        border: 1px solid #2A3550;
        height: 100%;
        box-shadow: 0 6px 20px rgba(0,0,0,0.30);
    }
    .metric-title {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94A3B8;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: 1.55rem;
        font-weight: 800;
        color: #ffffff;
    }
    .metric-sub {
        font-size: 0.82rem;
        color: #CBD5E1;
        margin-top: 0.3rem;
    }
    .profit-green { color: #34D399 !important; }
    .profit-red { color: #F87171 !important; }
    .accent-blue { color: #60A5FA !important; }
    .accent-gold { color: #FBBF24 !important; }
    .accent-purple { color: #A78BFA !important; }
    .insight-card {
        background: linear-gradient(180deg, #1A2436 0%, #131A26 100%);
        border: 1px solid #2A3550;
        border-radius: 14px;
        padding: 14px;
        text-align: center;
    }
    .insight-label { font-size: 0.75rem; letter-spacing: 0.08em; color: #94A3B8; text-transform: uppercase; }
    .insight-value { font-size: 1.35rem; font-weight: 800; margin-top: 6px; }
    .insight-sub { font-size: 0.80rem; color: #CBD5E1; margin-top: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    # =============================================================
    # PANEL SCAN
    # =============================================================
    st.markdown("### 🔄 Live Scan ESPN")
    c_scan1, c_scan2, c_scan3 = st.columns([1, 1, 3])
    with c_scan1:
        if st.button("🔄 Scan Sekarang", use_container_width=True):
            with st.spinner("Lagi scan ESPN..."):
                res = _try_run_scan()
                if res["ok"]:
                    st.success(f"Scan berhasil: {res['msg']}")
                else:
                    st.warning(
                        f"Scan belum jalan: {res['msg']} | Masih pakai data lama, tidak error."
                    )
                st.rerun()
    with c_scan2:
        if st.button("🧹 Clear Cache & Reload", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with c_scan3:
        st.caption(
            "Kalau tombol Scan bilang 'scanner.py belum ada', berarti file scanner bapak namanya beda. "
            "Kirim nama file scanner-nya, saya sesuaikan import-nya. Data lama tetap tampil, tidak hilang."
        )

    # =============================================================
    # AMBIL DATA
    # =============================================================
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
        scan_meta = {
            "scan_timestamp_wita": "DARI REPO LAMA skor60",
            "source_status": "LOADED_FROM_OLD_REPO",
            "live_matches_seen": len(all_records),
        }

    # Auto-scan 1x per 15 menit
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

    # =============================================================
    # 1. HEADER UTAMA
    # =============================================================
    st.markdown(
        f"""
        <div class="main-header">
            <h2 style="margin:0; font-weight:800;">⚽ TRADING BOLA MENIT 60 — <span style="color:#34D399;">LAST GOAL SYSTEM</span></h2>
            <p style="margin:6px 0 10px 0; color:#94A3B8;">
                Market: <b style="color:#FBBF24;">OVER 0.5 GOAL AFTER ENTRY (Menit 60'–66', Skor Entry 0-0)</b> |
                Cut-Off Trading Day: <b style="color:#fff;">12:00 WITA</b>
            </p>
            <div style="display:flex; flex-wrap:wrap; gap:18px; font-size:0.86rem;">
                <span>🟢 <b>System Status:</b> {source_status}</span>
                <span>📡 <b>Data Source:</b> ESPN API (All + Multi-League)</span>
                <span>🕒 <b>Last Scan:</b> {last_scan_wita}</span>
                <span>💾 <b>Last DB Update:</b> {last_db_update_str}</span>
                <span>⏰ <b>Current WITA:</b> {now_wita.strftime('%Y-%m-%d %H:%M:%S')}</span>
                <span>⚽ <b>Total Matches:</b> {len(all_records)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        f"🕒 **Panduan Monitoring Jam Aktif (WITA):** {get_peak_hours_label(now_wita)} "
        f"*(Panduan monitoring, bukan jaminan jumlah pertandingan).* "
        f"Pertandingan LIVE terdeteksi pada scan terakhir: **{scan_meta.get('live_matches_seen', 0)}**"
    )

    sim_stats = stats["simulated"]
    act_stats = stats["actual"]
    major_stats = stats["by_league_tier"]["MAJOR"]

    # =============================================================
    # 2. LIMA KARTU UTAMA - ATAS UDAH OK, DIPERTAHANKAN
    # =============================================================
    cols = st.columns(5)

    with cols[0]:
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 4px solid #60A5FA;">
                <div class="metric-title">💰 CARD 1 – MODAL PER MATCH</div>
                <div class="metric-value accent-blue">{format_idr(DEFAULT_STAKE)}</div>
                <div class="metric-sub">Odds Simulasi: <b>{SIMULATED_ODDS:.2f}</b> ({CURRENCY})</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cols[1]:
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 4px solid #F59E0B;">
                <div class="metric-title">📤 CARD 2 – TOTAL MODAL KELUAR</div>
                <div class="metric-value accent-gold">{format_idr(sim_stats['total_stake_settled'])}</div>
                <div class="metric-sub">Settled: <b>{sim_stats['settled_matches']}</b> Match (Excl. Pending/Void)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cols[2]:
        act_profit_label = (
            f"{format_idr(act_stats['net_profit'])} (ROI {act_stats['roi']:.2f}%)"
            if act_stats["available"]
            else "ACTUAL ODDS: NOT AVAILABLE"
        )
        profit_color = "profit-green" if sim_stats['net_profit'] >= 0 else "profit-red"
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 4px solid #10B981;">
                <div class="metric-title">📈 CARD 3 – TOTAL PROFIT</div>
                <div class="metric-value {profit_color}">{format_idr(sim_stats['net_profit'])} <span style="font-size:0.8rem; color:#10B981;">(Sim)</span></div>
                <div class="metric-sub">
                    Sim ROI: <b>{sim_stats['roi']:.2f}%</b><br/>
                    Actual: <b>{act_profit_label}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cols[3]:
        ci_low, ci_high = sim_stats["wilson_ci_95"]
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 4px solid #A78BFA;">
                <div class="metric-title">🎯 CARD 4 – WIN RATE</div>
                <div class="metric-value accent-purple">{sim_stats['win_rate']:.2f}%</div>
                <div class="metric-sub">
                    <b>{sim_stats['win']}</b>W / <b>{sim_stats['lose']}</b>L /
                    <b>{sim_stats['void']}</b>V / <b>{sim_stats['pending']}</b>P<br/>
                    Wilson 95% CI: [{ci_low:.1f}%, {ci_high:.1f}%]
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with cols[4]:
        major_badge = (
            "⚠️ LOW SAMPLE SIZE"
            if major_stats["settled_matches"] < MIN_SAMPLE_SIZE_RELIABLE
            else "✅ SAMPLE OK"
        )
        st.markdown(
            f"""
            <div class="metric-card" style="border-top: 4px solid #EC4899;">
                <div class="metric-title">🏆 CARD 5 – MAJOR PERFORMANCE</div>
                <div class="metric-value">{major_stats['win_rate']:.2f}% WR</div>
                <div class="metric-sub">
                    Profit (Sim): <b>{format_idr(major_stats['simulated_profit'])}</b> | ROI: <b>{major_stats['simulated_roi']:.2f}%</b><br/>
                    Sampel: <b>{major_stats['settled_matches']}</b> settled ({major_badge})
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    # =============================================================
    # 3. DETAIL STATISTIK
    # =============================================================
    with st.expander(
        "📊 Detail Statistik Kuantitatif, Break-Even, EV, & Klasifikasi Liga (Major / Minor / Unknown)",
        expanded=True,
    ):
        tab_sim, tab_act, tab_tier = st.tabs(
            [
                "A. SIMULATED PERFORMANCE (Odds 1.80)",
                "B. ACTUAL ODDS PERFORMANCE",
                "C. Klasifikasi Liga (MAJOR / MINOR / UNKNOWN)",
            ]
        )

        with tab_sim:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(
                "Break-Even Win Rate",
                f"{sim_stats['break_even_win_rate']:.2f}%"
                if sim_stats["break_even_win_rate"]
                else "N/A",
            )
            c2.metric(
                "Expected Value (EV / Match)",
                format_idr(int(sim_stats["expected_value_per_match"]))
                if sim_stats["expected_value_per_match"] is not None
                else "N/A",
            )
            c3.metric("Maximum Drawdown", format_idr(sim_stats["max_drawdown"]))
            c4.metric(
                "Profit Factor",
                f"{sim_stats['profit_factor']}"
                if sim_stats["profit_factor"] != float("inf")
                else "∞",
            )

            c5, c6, c7, c8 = st.columns(4)
            c5.metric(
                "Longest Winning Streak",
                f"{sim_stats['longest_winning_streak']} Match",
            )
            c6.metric(
                "Longest Losing Streak",
                f"{sim_stats['longest_losing_streak']} Match",
            )
            c7.metric(
                "Wilson 95% CI",
                f"{sim_stats['wilson_ci_95'][0]:.2f}% – {sim_stats['wilson_ci_95'][1]:.2f}%",
            )
            c8.metric("Status Ukuran Sampel", sim_stats["sample_size_warning"])

        with tab_act:
            if not act_stats["available"]:
                st.warning(
                    "ACTUAL ODDS: NOT AVAILABLE — Belum ada kandidat pertandingan "
                    "yang memiliki data odds aktual dari provider saat entry."
                )
            else:
                a1, a2, a3, a4 = st.columns(4)
                a1.metric(
                    "Settled Matches (Actual Odds)",
                    act_stats["settled_matches"],
                )
                a2.metric(
                    "Average Entry Odds",
                    f"{act_stats['average_odds']:.3f}"
                    if act_stats["average_odds"]
                    else "N/A",
                )
                a3.metric(
                    "Break-Even WR (Actual)",
                    f"{act_stats['break_even_win_rate']:.2f}%"
                    if act_stats["break_even_win_rate"]
                    else "N/A",
                )
                a4.metric("Actual Net Profit", format_idr(act_stats["net_profit"]))

        with tab_tier:
            tier_rows = []
            for tier_key in ("MAJOR", "MINOR", "UNKNOWN"):
                t_info = stats["by_league_tier"][tier_key]
                tier_rows.append(
                    {
                        "Kategori Liga": tier_key,
                        "Total Match": t_info["total_matches"],
                        "Settled": t_info["settled_matches"],
                        "WIN": t_info["win"],
                        "LOSE": t_info["lose"],
                        "VOID": t_info["void"],
                        "PENDING": t_info["pending"],
                        "Win Rate (%)": f"{t_info['win_rate']:.2f}%",
                        "Profit Simulasi": format_idr(t_info["simulated_profit"]),
                        "ROI Simulasi (%)": f"{t_info['simulated_roi']:.2f}%",
                        "Profit Aktual": format_idr(t_info["actual_profit"])
                        if t_info["actual_available"]
                        else "NOT AVAILABLE",
                        "Validitas Sampel": t_info["sample_status"],
                    }
                )
            df_tier_tab = pd.DataFrame(tier_rows)
            # FIX: applymap -> map (Pandas baru)
            styled_tier = (
                df_tier_tab.style.set_properties(
                    **{
                        "background-color": "#131A26",
                        "color": "#E2E8F0",
                    }
                )
                .map(color_profit, subset=["Profit Simulasi", "Profit Aktual"])
                .map(color_win_rate, subset=["Win Rate (%)"])
                .set_table_styles(
                    [
                        {
                            "selector": "th",
                            "props": [
                                ("background-color", "#1E293B"),
                                ("color", "white"),
                            ],
                        }
                    ]
                )
            )
            st.dataframe(styled_tier, use_container_width=True, hide_index=True)

    # =============================================================
    # 4. GRAFIK
    # =============================================================
    st.markdown(
        """
        <div class="section-card section-card-green">
            <h3 style="margin:0; border:none; padding:0;">📈 Visualisasi Performa & Distribusi</h3>
            <p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.85rem;">Grafik profit, win rate, dan distribusi entry — semua sudah dark + berwarna.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if len(all_records) == 0:
        st.info(
            "NO LIVE MATCH FOUND / BELUM ADA DATA HISTORIS — Grafik akan ditampilkan "
            "otomatis setelah terdapat data pertandingan yang tercatat."
        )
    else:
        g_col1, g_col2, g_col3 = st.columns(3)

        with g_col1:
            status_counts = {
                "WIN": sim_stats["win"],
                "LOSE": sim_stats["lose"],
                "VOID": sim_stats["void"],
                "PENDING": sim_stats["pending"],
                "REVIEW": sim_stats["unverified"],
            }
            non_zero_status = {k: v for k, v in status_counts.items() if v > 0}
            if non_zero_status:
                fig_donut = px.pie(
                    names=list(non_zero_status.keys()),
                    values=list(non_zero_status.values()),
                    hole=0.55,
                    title="Distribusi Status Pertandingan",
                    color=list(non_zero_status.keys()),
                    color_discrete_map={
                        "WIN": "#10B981",
                        "LOSE": "#EF4444",
                        "VOID": "#64748B",
                        "PENDING": "#F59E0B",
                        "REVIEW": "#EA580C",
                    },
                )
                st.plotly_chart(style_fig(fig_donut), use_container_width=True)
            else:
                st.caption("Data belum cukup untuk grafik distribusi status.")

        day_summaries = list(reversed(stats["by_trading_day"]))
        settled_days = [d for d in day_summaries if d["settled_matches"] > 0]

        with g_col2:
            if settled_days:
                df_days = pd.DataFrame(settled_days)
                fig_daily = px.bar(
                    df_days,
                    x="trading_day",
                    y="simulated_profit",
                    title="Grafik Profit Harian (Simulasi IDR)",
                    labels={
                        "trading_day": "Trading Day (Cut-off 12:00 WITA)",
                        "simulated_profit": "Net Profit (IDR)",
                    },
                    color="simulated_profit",
                    color_continuous_scale=["#EF4444", "#F59E0B", "#10B981"],
                )
                st.plotly_chart(style_fig(fig_daily), use_container_width=True)
            else:
                st.caption("Belum ada pertandingan settled untuk grafik profit harian.")

        with g_col3:
            if settled_days:
                df_days = pd.DataFrame(settled_days)
                df_days["cumulative_profit"] = df_days["simulated_profit"].cumsum()
                fig_cum = px.line(
                    df_days,
                    x="trading_day",
                    y="cumulative_profit",
                    markers=True,
                    title="Grafik Cumulative Profit (Simulasi IDR)",
                    labels={
                        "trading_day": "Trading Day",
                        "cumulative_profit": "Cumulative Profit (IDR)",
                    },
                    color_discrete_sequence=["#34D399"],
                )
                st.plotly_chart(style_fig(fig_cum), use_container_width=True)
            else:
                st.caption("Belum ada pertandingan settled untuk grafik cumulative profit.")

        g_col4, g_col5, g_col6 = st.columns(3)

        with g_col4:
            tier_list = [
                stats["by_league_tier"]["MAJOR"],
                stats["by_league_tier"]["MINOR"],
                stats["by_league_tier"]["UNKNOWN"],
            ]
            active_tiers = [t for t in tier_list if t["total_matches"] > 0]
            if active_tiers:
                df_tier = pd.DataFrame(active_tiers)
                fig_tier = px.bar(
                    df_tier,
                    x="tier",
                    y=["win", "lose"],
                    barmode="group",
                    title="Performa Major vs Minor vs Unknown",
                    labels={
                        "tier": "Klasifikasi Liga",
                        "value": "Jumlah Pertandingan",
                    },
                    color_discrete_sequence=["#10B981", "#EF4444"],
                )
                st.plotly_chart(style_fig(fig_tier), use_container_width=True)
            else:
                st.caption("Data belum cukup untuk grafik Major vs Minor.")

        with g_col5:
            actual_settled = [
                r
                for r in all_records
                if r.get("odds_entry") is not None and r.get("result") in ("WIN", "LOSE")
            ]
            if len(actual_settled) >= 2:
                df_odds = pd.DataFrame(actual_settled)
                df_odds["is_win"] = (df_odds["result"] == "WIN").astype(int) * 100.0
                fig_odds = px.histogram(
                    df_odds,
                    x="odds_entry",
                    y="is_win",
                    histfunc="avg",
                    nbins=8,
                    title="Win Rate (%) Berdasarkan Odds Aktual",
                    labels={"odds_entry": "Odds Entry", "is_win": "Win Rate (%)"},
                )
                st.plotly_chart(style_fig(fig_odds), use_container_width=True)
            else:
                st.caption(
                    "Data odds aktual belum cukup untuk grafik Win Rate berdasarkan odds."
                )

        with g_col6:
            entry_mins = [
                int(r["minute_detected"])
                for r in all_records
                if r.get("minute_detected") is not None
            ]
            if entry_mins:
                df_min = pd.DataFrame({"minute_detected": entry_mins})
                fig_min = px.histogram(
                    df_min,
                    x="minute_detected",
                    nbins=7,
                    title="Distribusi Menit Entry (60'–66')",
                    labels={"minute_detected": "Menit Deteksi Entry"},
                    color_discrete_sequence=["#3B82F6"],
                )
                fig_min.update_layout(bargap=0.2)
                st.plotly_chart(style_fig(fig_min), use_container_width=True)
            else:
                st.caption("Data belum cukup untuk grafik distribusi menit entry.")

    # =============================================================
    # 5. INSIGHT BAWAH
    # =============================================================
    st.markdown(
        """
        <div class="section-card">
            <h3 style="margin:0; border:none; padding:0;">🔥 Insight Trading Day</h3>
            <p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.85rem;">Ringkasan cepat sebelum masuk ke tabel detail — hari terbaik / terburuk langsung keliatan warnanya.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if stats["by_trading_day"]:
        days_for_insight = [d for d in stats["by_trading_day"] if d["settled_matches"] > 0]
        if days_for_insight:
            best_day = max(days_for_insight, key=lambda x: x["simulated_profit"])
            worst_day = min(days_for_insight, key=lambda x: x["simulated_profit"])
            avg_profit = sum(d["simulated_profit"] for d in days_for_insight) / len(
                days_for_insight
            )
            i1, i2, i3 = st.columns(3)
            with i1:
                st.markdown(
                    f"""
                    <div class="insight-card" style="border-top: 4px solid #10B981;">
                        <div class="insight-label">🏆 Hari Terbaik</div>
                        <div class="insight-value" style="color:#34D399;">{best_day['trading_day']}</div>
                        <div class="insight-sub">{format_idr(best_day['simulated_profit'])} • {best_day['summary_text']} • WR {best_day['win_rate']:.1f}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with i2:
                st.markdown(
                    f"""
                    <div class="insight-card" style="border-top: 4px solid #EF4444;">
                        <div class="insight-label">📉 Hari Terburuk</div>
                        <div class="insight-value" style="color:#F87171;">{worst_day['trading_day']}</div>
                        <div class="insight-sub">{format_idr(worst_day['simulated_profit'])} • {worst_day['summary_text']} • WR {worst_day['win_rate']:.1f}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with i3:
                avg_color = "#34D399" if avg_profit >= 0 else "#F87171"
                st.markdown(
                    f"""
                    <div class="insight-card" style="border-top: 4px solid #F59E0B;">
                        <div class="insight-label">📊 Rata-rata Profit / Hari</div>
                        <div class="insight-value" style="color:{avg_color};">{format_idr(int(avg_profit))}</div>
                        <div class="insight-sub">Dari {len(days_for_insight)} hari settled • Total {format_idr(sim_stats['net_profit'])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # =============================================================
    # 6. RINGKASAN TRADING DAY - BERWARNA
    # =============================================================
    st.markdown(
        """
        <div class="section-card section-card-blue">
            <h3 style="margin:0; border:none; padding:0;">🗓️ Ringkasan Partisi Harian (Cut-Off 12:00 WITA)</h3>
            <p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.85rem;">Hijau = untung, Merah = rugi, Kuning = win rate sedang.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not stats["by_trading_day"]:
        st.caption("Belum ada riwayat trading day di database.")
    else:
        df_td = pd.DataFrame(
            [
                {
                    "Trading Day": d["trading_day"],
                    "Rekor (W-L)": d["summary_text"],
                    "Total Match": d["total_matches"],
                    "Settled": d["settled_matches"],
                    "VOID": d["void"],
                    "PENDING": d["pending"],
                    "Win Rate": f"{d['win_rate']:.2f}%",
                    "Net Profit (Simulasi)": format_idr(d["simulated_profit"]),
                    "ROI (Simulasi)": f"{d['simulated_roi']:.2f}%",
                    "Net Profit (Aktual)": format_idr(d["actual_profit"])
                    if d["actual_profit"] is not None
                    else "NOT AVAILABLE",
                }
                for d in stats["by_trading_day"]
            ]
        )
        # FIX: applymap -> map
        styled_td = (
            df_td.style.set_properties(
                **{"background-color": "#131A26", "color": "#E2E8F0"}
            )
            .map(color_profit, subset=["Net Profit (Simulasi)", "Net Profit (Aktual)"])
            .map(color_win_rate, subset=["Win Rate"])
            .set_table_styles(
                [
                    {
                        "selector": "th",
                        "props": [
                            ("background-color", "#1E293B"),
                            ("color", "white"),
                        ],
                    }
                ]
            )
        )
        st.dataframe(styled_td, use_container_width=True, hide_index=True)

    # =============================================================
    # 7. TABEL PERTANDINGAN & FILTER
    # =============================================================
    st.markdown(
        """
        <div class="section-card section-card-pink">
            <h3 style="margin:0; border:none; padding:0;">📋 Daftar Pertandingan (20 Terbaru Sesuai Filter)</h3>
            <p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.85rem;">Badge WIN hijau, LOSE merah, LIVE biru, PENDING kuning — profit juga sudah berwarna.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    f_col1, f_col2 = st.columns([2, 1])
    with f_col1:
        status_filter = st.selectbox(
            "Filter Kategori / Status:",
            options=[
                "Semua",
                "LIVE",
                "WIN",
                "LOSE",
                "PENDING",
                "VOID",
                "REVIEW",
                "MAJOR",
                "MINOR",
            ],
            index=0,
        )
    with f_col2:
        available_days = ["Semua"] + [d["trading_day"] for d in stats["by_trading_day"]]
        day_filter = st.selectbox(
            "Filter Trading Day:", options=available_days, index=0
        )

    filtered_records: List[Dict[str, Any]] = []
    for rec in all_records:
        if day_filter != "Semua" and rec.get("trading_day") != day_filter:
            continue

        res = str(rec.get("result") or "PENDING").upper()
        m_status = str(rec.get("match_status") or "").upper()
        s_status = str(rec.get("settlement_status") or "PENDING").upper()
        l_cat = str(
            rec.get("league_category")
            or ("MAJOR" if rec.get("is_major") else "UNKNOWN")
        ).upper()

        if status_filter == "LIVE" and m_status not in (
            "FIRST HALF",
            "SECOND HALF",
            "HALFTIME",
            "LIVE",
            "EXTRA TIME",
            "PENALTIES",
        ):
            continue
        elif status_filter == "WIN" and res != "WIN":
            continue
        elif status_filter == "LOSE" and res != "LOSE":
            continue
        elif status_filter == "PENDING" and res != "PENDING":
            continue
        elif status_filter == "VOID" and res != "VOID":
            continue
        elif status_filter == "REVIEW" and (
            s_status != "REVIEW" and res != "DATA UNVERIFIED"
        ):
            continue
        elif status_filter == "MAJOR" and l_cat != "MAJOR":
            continue
        elif status_filter == "MINOR" and l_cat != "MINOR":
            continue

        filtered_records.append(rec)

    top_20 = filtered_records[:20]

    if not top_20:
        st.warning(
            "NO LIVE MATCH FOUND — Tidak ada pertandingan yang cocok dengan filter saat ini."
        )
    else:
        table_rows = []
        for idx, rec in enumerate(top_20, start=1):
            res = str(rec.get("result") or "PENDING").upper()
            m_status = str(rec.get("match_status") or "")
            is_live_now = m_status in (
                "First Half",
                "Second Half",
                "Halftime",
                "Live",
                "Extra Time",
                "Penalties",
            ) and res == "PENDING"
            display_status = (
                "LIVE"
                if is_live_now
                else (
                    "REVIEW"
                    if rec.get("settlement_status") == "REVIEW"
                    else res
                )
            )

            badge_tier = (
                "MAJOR"
                if rec.get("is_major")
                else str(rec.get("league_category") or "UNKNOWN")
            )
            odds_disp = (
                f"{rec.get('odds_entry', SIMULATED_ODDS):.2f} (Actual)"
                if rec.get("odds_entry") is not None
                else f"{SIMULATED_ODDS:.2f} (Sim)"
            )
            pnl_val = (
                rec.get("actual_profit")
                if rec.get("odds_entry") is not None
                else rec.get("simulated_profit", 0)
            )
            act_label = rec.get("activity_label", "NORMAL")

            table_rows.append(
                {
                    "No": idx,
                    "Match ID": rec.get("match_id"),
                    "Match": f"{rec.get('home_team')} vs {rec.get('away_team')}",
                    "League": rec.get("league"),
                    "Badge": badge_tier,
                    "Activity": act_label,
                    "Min Entry": f"{rec.get('minute_detected')}'",
                    "Entry Score": rec.get("score_at_entry"),
                    "Entry Odds": odds_disp,
                    "Current Score": rec.get("current_score"),
                    "Final Score": rec.get("final_score") or "-",
                    "Result": display_status,
                    "Profit": format_idr(int(pnl_val or 0))
                    if res in ("WIN", "LOSE", "VOID")
                    else "Rp0 (Pending)",
                    "Trading Day": rec.get("trading_day"),
                }
            )

        df_table = pd.DataFrame(table_rows)

        def style_table(row):
            styles = [""] * len(row)
            res_val = str(row["Result"]).upper()
            if res_val == "WIN":
                styles[row.index.get_loc("Result")] = (
                    "background-color: #16a34a; color: white; font-weight: bold;"
                )
            elif res_val == "LOSE":
                styles[row.index.get_loc("Result")] = (
                    "background-color: #dc2626; color: white; font-weight: bold;"
                )
            elif res_val == "LIVE":
                styles[row.index.get_loc("Result")] = (
                    "background-color: #2563eb; color: white; font-weight: bold;"
                )
            elif res_val == "PENDING":
                styles[row.index.get_loc("Result")] = (
                    "background-color: #ca8a04; color: white; font-weight: bold;"
                )
            elif res_val == "VOID":
                styles[row.index.get_loc("Result")] = (
                    "background-color: #64748b; color: white; font-weight: bold;"
                )
            elif res_val in ("REVIEW", "DATA UNVERIFIED"):
                styles[row.index.get_loc("Result")] = (
                    "background-color: #ea580c; color: white; font-weight: bold;"
                )
            act_val = str(row["Activity"]).upper()
            if act_val == "AKTIF":
                styles[row.index.get_loc("Activity")] = (
                    "background-color: #2e7d32; color: white; font-weight: bold;"
                )
            elif act_val == "PASIF":
                styles[row.index.get_loc("Activity")] = (
                    "background-color: #d32f2f; color: white; font-weight: bold;"
                )
            profit_str = str(row["Profit"])
            if profit_str.startswith("-"):
                styles[row.index.get_loc("Profit")] = (
                    "background-color: #3F1D1D; color: #FCA5A5; font-weight: bold;"
                )
            elif profit_str.startswith("Rp") and "Rp0" not in profit_str:
                styles[row.index.get_loc("Profit")] = (
                    "background-color: #123325; color: #6EE7B7; font-weight: bold;"
                )
            if str(row["Badge"]).upper() == "MAJOR":
                styles[row.index.get_loc("Badge")] = (
                    "background-color: #1E3A5F; color: #93C5FD; font-weight: bold;"
                )
            elif str(row["Badge"]).upper() == "MINOR":
                styles[row.index.get_loc("Badge")] = (
                    "background-color: #3A2E12; color: #FCD34D; font-weight: bold;"
                )
            return styles

        styled = (
            df_table.style.apply(style_table, axis=1)
            .set_properties(
                **{"background-color": "#131A26", "color": "#E2E8F0"}
            )
            .set_table_styles(
                [
                    {
                        "selector": "th",
                        "props": [
                            ("background-color", "#1E293B"),
                            ("color", "white"),
                        ],
                    }
                ]
            )
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

        # =========================================================
        # 8. PANEL AUDIT
        # =========================================================
        st.markdown(
            """
            <div class="section-card section-card-green">
                <h3 style="margin:0; border:none; padding:0;">🔍 Audit Trail & Penjelasan Hasil Pertandingan</h3>
                <p style="margin:4px 0 0 0; color:#94A3B8; font-size:0.85rem;">Pilih satu pertandingan untuk melihat bukti entry, settlement, dan verifikasinya.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        match_options = {
            f"[{r.get('trading_day')}] {r.get('home_team')} vs {r.get('away_team')} (ID: {r.get('match_id')})": r
            for r in top_20
        }
        selected_label = st.selectbox(
            "Pilih Pertandingan untuk Audit Mendalam:",
            options=list(match_options.keys()),
        )
        if selected_label:
            sel_rec = match_options[selected_label]
            audit_info = audit_result(sel_rec)

            st.markdown(
                f"**Penjelasan Audit Otomatis:** {audit_info['explanation']}"
            )
            if not audit_info["audit_passed"]:
                st.error(f"Temuan Audit: {', '.join(audit_info['issues'])}")

            a_col1, a_col2, a_col3 = st.columns(3)
            with a_col1:
                st.markdown("**1. Identitas & Waktu Entry**")
                st.write(f"- **Match ID:** `{sel_rec.get('match_id')}`")
                st.write(
                    f"- **League Slug:** `{sel_rec.get('league_slug')}` ({sel_rec.get('league_category')})"
                )
                st.write(
                    f"- **Activity Level:** `{sel_rec.get('activity_label', 'NORMAL')}`"
                )
                st.write(
                    f"- **Waktu Deteksi / Entry (UTC):** `{sel_rec.get('detected_at_utc')}`"
                )
                st.write(
                    f"- **Waktu Deteksi / Entry (WITA):** `{sel_rec.get('detected_at_wita')}`"
                )
                st.write(f"- **Trading Day:** `{sel_rec.get('trading_day')}`")
            with a_col2:
                st.markdown("**2. Parameter Entry & Settlement**")
                st.write(f"- **Menit Entry:** `{sel_rec.get('minute_detected')}'`")
                st.write(f"- **Skor Entry:** `{sel_rec.get('score_at_entry')}`")
                st.write(
                    f"- **Odds Entry Aktual:** `{sel_rec.get('odds_entry') or 'NOT AVAILABLE'}`"
                )
                st.write(f"- **Sumber Odds:** `{sel_rec.get('odds_source')}`")
                st.write(f"- **Status Pertandingan:** `{sel_rec.get('match_status')}`")
                st.write(
                    f"- **Status Settlement:** `{sel_rec.get('settlement_status')}` (`{sel_rec.get('result')}`)"
                )
            with a_col3:
                st.markdown("**3. Perhitungan Profit & Verifikasi**")
                st.write(
                    f"- **Stake:** `{format_idr(int(sel_rec.get('stake') or DEFAULT_STAKE))}`"
                )
                st.write(
                    f"- **Profit Simulasi (1.80):** `{format_idr(int(sel_rec.get('simulated_profit') or 0))}`"
                )
                act_p = sel_rec.get("actual_profit")
                st.write(
                    f"- **Profit Aktual:** `{format_idr(int(act_p)) if act_p is not None else 'NOT AVAILABLE'}`"
                )
                st.write(f"- **Sumber Data:** `{sel_rec.get('source')}`")
                st.write(f"- **Status Verifikasi:** `{sel_rec.get('verification_status')}`")
                st.write(
                    f"- **Terakhir Diverifikasi:** `{sel_rec.get('last_verified_at')}`"
                )

            s_col1, s_col2 = st.columns(2)
            with s_col1:
                st.markdown("**Riwayat Snapshot Skor Berkala:**")
                snaps = sel_rec.get("snapshots") or []
                if snaps:
                    st.dataframe(
                        style_dark_table(pd.DataFrame(snaps)),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("Tidak ada snapshot.")

            with s_col2:
                st.markdown("**Bukti Event Gol / Perubahan Skor:**")
                g_events = sel_rec.get("goal_events") or []
                if g_events:
                    st.dataframe(
                        style_dark_table(pd.DataFrame(g_events)),
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("Belum ada event gol tercatat.")

            revs = sel_rec.get("revision_history") or []
            if revs:
                st.markdown(
                    "**Riwayat Perubahan / Koreksi Resmi Provider (Revision History):**"
                )
                st.dataframe(
                    style_dark_table(pd.DataFrame(revs)),
                    use_container_width=True,
                    hide_index=True,
                )

if __name__ == "__main__":
    render_dashboard()
