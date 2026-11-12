import json
import os
import statistics as stats_module
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from zoneinfo import ZoneInfo

# --- 1. LOAD DATA DARI REPO LAMA (SUDAH DIREVISI) ---
try:
    from data_loader import load_matches_from_old_repo
except Exception:
    load_matches_from_old_repo = None

# --- 2. CONFIG DENGAN CADANGAN BIAR NGGAK ERROR LAGI ---
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

WITA_TZ = ZoneInfo(TIMEZONE_NAME)
UTC_TZ = timezone.utc

# --- 3. DATABASE / SETTLEMENT / STATISTICS DENGAN CADANGAN ---
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
        return {"label": record.get("activity_label", "NORMAL"), "is_win": record.get("result") == "WIN", "is_loss": record.get("result") == "LOSS"}

try:
    from statistics import compute_full_dashboard_statistics
except Exception:
    def compute_full_dashboard_statistics(records):
        # Hitungan cadangan kalau statistics.py beda versi
        total = len(records)
        wins = sum(1 for r in records if r.get("result") == "WIN")
        losses = sum(1 for r in records if r.get("result") == "LOSS")
        voids = sum(1 for r in records if r.get("result") in ("VOID", "NO_RESULT"))
        profit = sum(float(r.get("profit", 0) or 0) for r in records)
        stake = total * DEFAULT_STAKE
        win_rate = (wins / total * 100) if total else 0
        roi = (profit / stake * 100) if stake else 0
        # Per market
        win_by_market = {}
        profit_by_market = {}
        win_by_label = {}
        profit_by_label = {}
        profit_by_trading_day = {}
        win_by_trading_day = {}
        profit_by_market_hour = {}
        win_by_market_hour = {}
        for r in records:
            m = r.get("market", "Unknown")
            lab = r.get("activity_label", "NORMAL")
            day = r.get("trading_day", "Unknown")
            hour = str(r.get("market_hour", r.get("minute_detected", 0)))
            profit_by_market[m] = profit_by_market.get(m, 0) + float(r.get("profit", 0) or 0)
            profit_by_label[lab] = profit_by_label.get(lab, 0) + float(r.get("profit", 0) or 0)
            profit_by_trading_day[day] = profit_by_trading_day.get(day, 0) + float(r.get("profit", 0) or 0)
            if r.get("result") == "WIN":
                win_by_market[m] = win_by_market.get(m, 0) + 1
                win_by_label[lab] = win_by_label.get(lab, 0) + 1
                win_by_trading_day[day] = win_by_trading_day.get(day, 0) + 1
        return {
            "total_matches": total, "total_stake": stake, "total_wins": wins,
            "total_losses": losses, "total_voids": voids, "total_no_result": 0,
            "win_rate": win_rate, "roi": roi, "expected_value": roi,
            "profit": profit, "net_profit": profit, "total_profit": profit,
            "total_gain": sum(float(r.get("profit", 0) or 0) for r in records if float(r.get("profit", 0) or 0) > 0),
            "total_loss": sum(float(r.get("profit", 0) or 0) for r in records if float(r.get("profit", 0) or 0) < 0),
            "total_earnings": profit,
            "win_by_market": win_by_market, "profit_by_market": profit_by_market,
            "win_by_label": win_by_label, "profit_by_label": profit_by_label,
            "filtered_profit": profit, "filtered_matches": total, "filtered_win_rate": win_rate,
            "filtered_roi": roi, "filtered_expected_value": roi, "filtered_total_stake": stake,
            "profit_by_trading_day": profit_by_trading_day, "win_by_trading_day": win_by_trading_day,
            "profit_by_market_hour": profit_by_market_hour, "win_by_market_hour": win_by_market_hour,
            "profit_by_day_profit": profit_by_trading_day,
        }

if "page" not in st.session_state:
    st.session_state.page = "dashboard"

st.set_page_config(page_title="Trading Bola Menit 60", layout="wide", page_icon="⚽")
st.title("⚽ Trading Bola Menit 60")
st.caption(f"Trading Day • Cut-off 12:00 WITA • Modal {CURRENCY} {DEFAULT_STAKE:,.0f} per Match • Odds Simulasi {SIMULATED_ODDS}")

def render_dashboard() -> None:
    # --- LOAD DARI REPO LAMA DULU, BARU FALLBACK LOKAL ---
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

    scan_timestamp = scan_meta.get("scan_timestamp_wita", "-")
    scan_status = scan_meta.get("source_status", "-")
    live_seen = scan_meta.get("live_matches_seen", "-")
    scan_teams = scan_meta.get("live_matches_seen_teams", scan_meta.get("live_teams", []))
    scan_teams_str = ", ".join(scan_teams) if isinstance(scan_teams, list) and scan_teams else "-"

    last_db_update_str = "DARI REPO LAMA skor60 (via data_loader.py)"

    sidebar = st.sidebar
    with sidebar:
        st.markdown("### 🎛️ Pengaturan Tampilan")
        selected_trading_day = st.selectbox("Filter Trading Day", ["Semua Hari Trading"] + sorted({r.get("trading_day", "-") for r in all_records}, reverse=True))
        selected_league = st.selectbox("Filter Liga", ["Semua Liga"] + sorted({r.get("league", "-") for r in all_records}))
        selected_market = st.selectbox("Filter Market", ["Semua Market"] + sorted({r.get("market", "-") for r in all_records}))
        filter_mode = st.radio("Tampilan Statistik", ["Ringkasan Full", "Filter Berdasarkan Aktivitas Menit 60", "Semua"], index=0)
        if filter_mode == "Semua":
            activity_filter = ["ACTIVE_NORMAL"]
        elif filter_mode == "Filter Berdasarkan Aktivitas Menit 60":
            activity_filter = ["ACTIVE_NORMAL", "ACTIVE_PASSIVE"]
        else:
            activity_filter = ["ACTIVE_NORMAL", "ACTIVE_PASSIVE", "NO_STATS_DATA"]
        st.markdown("---")
        st.markdown("### ⏱️ Metadata Scan Terakhir")
        st.markdown(f"- **Timestamp Scan (WITA):** {scan_timestamp}")
        st.markdown(f"- **Status Sumber:** {scan_status}")
        st.markdown(f"- **Pertandingan Live Terlihat:** {live_seen}")
        st.markdown(f"- **Tim Live:** {scan_teams_str}")
        st.markdown(f"- **Terakhir Database Diperbarui:** {last_db_update_str}")

    def filter_matches(records, trading_day, league, market):
        filtered = []
        for r in records:
            if trading_day != "Semua Hari Trading" and r.get("trading_day") != trading_day:
                continue
            if league != "Semua Liga" and r.get("league") != league:
                continue
            if market != "Semua Market" and r.get("market") != market:
                continue
            filtered.append(r)
        return filtered

    filtered_records = filter_matches(all_records, selected_trading_day, selected_league, selected_market)
    stats = compute_full_dashboard_statistics(filtered_records)

    if activity_filter == ["ACTIVE_NORMAL"]:
        display_records = [r for r in filtered_records if r.get("activity_label") == "NORMAL"]
    elif activity_filter == ["ACTIVE_NORMAL", "ACTIVE_PASSIVE"]:
        display_records = [r for r in filtered_records if r.get("activity_label") in ("NORMAL", "PASIF")]
    else:
        display_records = filtered_records

    stats_filtered = compute_full_dashboard_statistics(display_records)
    filtered_profit = stats_filtered.get("filtered_profit", stats_filtered.get("profit", 0))
    filtered_matches = stats_filtered.get("filtered_matches", stats_filtered.get("total_matches", 0))
    filtered_win_rate = stats_filtered.get("filtered_win_rate", stats_filtered.get("win_rate", 0))
    filtered_roi = stats_filtered.get("filtered_roi", stats_filtered.get("roi", 0))
    filtered_ev = stats_filtered.get("filtered_expected_value", stats_filtered.get("expected_value", 0))
    filtered_total_stake = stats_filtered.get("filtered_total_stake", stats_filtered.get("total_stake", 0))

    total_matches = stats.get("total_matches", 0)
    total_stake = stats.get("total_stake", 0)
    total_wins = stats.get("total_wins", 0)
    total_losses = stats.get("total_losses", 0)
    total_voids = stats.get("total_voids", 0)
    total_no_result = stats.get("total_no_result", 0)
    win_rate = stats.get("win_rate", 0)
    roi = stats.get("roi", 0)
    expected_value = stats.get("expected_value", 0)
    total_profit = stats.get("profit", stats.get("net_profit", 0))

    st.header("📊 Ringkasan Utama")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Pertandingan", f"{total_matches}")
    with col2:
        st.metric("Win Rate", f"{win_rate:.2f}%")
    with col3:
        st.metric("ROI", f"{roi:.2f}%")
    with col4:
        st.metric("Total Profit", f"{CURRENCY} {total_profit:,.0f}")
    with col5:
        st.metric("Total Stake", f"{CURRENCY} {total_stake:,.0f}")

    st.markdown(f"**Win:** {total_wins} | **Loss:** {total_losses} | **Void:** {total_voids} | **No Result:** {total_no_result}")

    st.header("📊 Statistik Filter")
    fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns(5)
    with fcol1:
        st.metric("Filtered Matches", f"{filtered_matches}")
    with fcol2:
        st.metric("Filtered Win Rate", f"{filtered_win_rate:.2f}%")
    with fcol3:
        st.metric("Filtered ROI", f"{filtered_roi:.2f}%")
    with fcol4:
        st.metric("Filtered Profit", f"{CURRENCY} {filtered_profit:,.0f}")
    with fcol5:
        st.metric("Filtered Total Stake", f"{CURRENCY} {filtered_total_stake:,.0f}")

    st.markdown("### 📊 Win Rate & Profit Per Market")
    win_by_market = stats.get("win_by_market", {})
    profit_by_market = stats.get("profit_by_market", {})
    if win_by_market or profit_by_market:
        market_df = pd.DataFrame([
            {"Market": m, "Win": win_by_market.get(m, 0), "Profit": profit_by_market.get(m, 0)}
            for m in sorted(set(win_by_market) | set(profit_by_market))
        ])
        st.dataframe(market_df, use_container_width=True)
        fig_market = px.bar(market_df, x="Market", y="Profit", color="Profit", title="Profit per Market", color_continuous_scale="RdYlGn")
        st.plotly_chart(fig_market, use_container_width=True)
    else:
        st.info("Belum ada data per market.")

    st.markdown("### 📊 Win Rate & Profit Per Label Aktivitas")
    win_by_label = stats.get("win_by_label", {})
    profit_by_label = stats.get("profit_by_label", {})
    if win_by_label or profit_by_label:
        label_df = pd.DataFrame([
            {"Label": l, "Win": win_by_label.get(l, 0), "Profit": profit_by_label.get(l, 0)}
            for l in sorted(set(win_by_label) | set(profit_by_label))
        ])
        st.dataframe(label_df, use_container_width=True)
        fig_label = px.bar(label_df, x="Label", y="Profit", color="Profit", title="Profit per Label Aktivitas", color_continuous_scale="Viridis")
        st.plotly_chart(fig_label, use_container_width=True)

    st.markdown("### 📊 Profit per Trading Day")
    profit_by_day = stats.get("profit_by_trading_day", stats.get("profit_by_day_profit", {}))
    if profit_by_day:
        day_df = pd.DataFrame([{"Trading Day": d, "Profit": p} for d, p in sorted(profit_by_day.items())])
        fig_day = px.bar(day_df, x="Trading Day", y="Profit", color="Profit", title="Profit per Trading Day", color_continuous_scale="RdYlGn")
        st.plotly_chart(fig_day, use_container_width=True)
        st.dataframe(day_df, use_container_width=True)

    st.markdown("### 📊 Profit per Market Hour")
    profit_by_hour = stats.get("profit_by_market_hour", {})
    if profit_by_hour:
        hour_df = pd.DataFrame([{"Market Hour": h, "Profit": p} for h, p in sorted(profit_by_hour.items(), key=lambda x: str(x[0]))])
        fig_hour = px.line(hour_df, x="Market Hour", y="Profit", markers=True, title="Profit per Market Hour")
        st.plotly_chart(fig_hour, use_container_width=True)

    st.markdown("### 📈 Profit Kumulatif")
    if display_records:
        df_cum = pd.DataFrame(display_records)
        if "profit" in df_cum.columns:
            df_cum["profit"] = pd.to_numeric(df_cum["profit"], errors="coerce").fillna(0)
            df_cum["cumulative"] = df_cum["profit"].cumsum()
            fig_cum = px.area(df_cum, y="cumulative", title="Profit Kumulatif", color_discrete_sequence=["#22c55e"])
            st.plotly_chart(fig_cum, use_container_width=True)

    st.markdown("### 📋 20 Pertandingan Terbaru")
    if display_records:
        recent = sorted(display_records, key=lambda x: str(x.get("trading_day", "")), reverse=True)[:20]
        recent_df = pd.DataFrame([{
            "Trading Day": r.get("trading_day", "-"),
            "Home": r.get("home_team", "-"),
            "Away": r.get("away_team", "-"),
            "Liga": r.get("league", "-"),
            "Market": r.get("market", "-"),
            "Menit": r.get("minute_detected", "-"),
            "Skor Entry": r.get("score_at_entry", "-"),
            "Hasil": r.get("result", "-"),
            "Profit": r.get("profit", 0),
            "Label": r.get("activity_label", "-"),
        } for r in recent])
        st.dataframe(recent_df, use_container_width=True)

    st.markdown("### 🔍 Detail Audit (Contoh 10 Terakhir)")
    if display_records:
        for r in display_records[-10:]:
            try:
                audit = audit_result(r)
            except Exception as e:
                audit = {"label": "ERROR", "error": str(e)}
            with st.expander(f"{r.get('home_team','?')} vs {r.get('away_team','?')} - {r.get('result','?')} - Profit {r.get('profit',0)}"):
                st.json(audit)
                st.json({k: r.get(k) for k in ["match_id","league","market","trading_day","minute_detected","score_at_entry","activity_label"]})

    st.markdown("---")
    st.caption(f"Data dari repo lama muslih156-dot/skor60 via data_loader.py | Total Profit: {CURRENCY} {total_profit:,.0f}")

if st.session_state.page == "dashboard":
    render_dashboard()
else:
    render_dashboard()
