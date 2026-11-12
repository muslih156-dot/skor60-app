import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from data_loader import load_matches_from_old_repo
from statistics import calculate_stats

st.set_page_config(page_title="Trading Bola Menit 60", layout="wide", page_icon="⚽")

# --- CSS biar cakep kayak dulu ---
st.markdown("""
<style>
    .metric-card { background:#0f172a; padding:15px; border-radius:12px; color:white; }
    .stMetric { background:#f8fafc; padding:15px; border-radius:12px; border:1px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ Trading Bola Menit 60 - Dashboard")
st.caption("Data live dari repo lama skor60 | Update otomatis | WITA")

matches = load_matches_from_old_repo()
if not matches:
    st.warning("Data belum ke-load. Cek data_loader.py")
    st.stop()

df = pd.DataFrame(matches)

# Normalisasi nama kolom biar aman
if "profit" not in df.columns and "pnl" in df.columns:
    df["profit"] = df["pnl"]
if "result" not in df.columns and "settlement" in df.columns:
    df["result"] = df["settlement"]
if "profit" not in df.columns:
    df["profit"] = 0
df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0)
df["cumulative_profit"] = df["profit"].cumsum()

stats = calculate_stats(matches)

# --- FILTER ATAS ---
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    leagues = ["Semua Liga"] + sorted(df["league"].dropna().unique().tolist()) if "league" in df.columns else ["Semua Liga"]
    pilih_liga = st.selectbox("Filter Liga", leagues)
with col_f2:
    results = ["Semua Hasil"] + sorted(df["result"].dropna().unique().tolist()) if "result" in df.columns else ["Semua Hasil"]
    pilih_result = st.selectbox("Filter Hasil", results)
with col_f3:
    pilih_day = st.selectbox("Trading Day", ["Semua"] + sorted(df["trading_day"].dropna().unique().tolist())[::-1][:30] if "trading_day" in df.columns else ["Semua"])

df_f = df.copy()
if pilih_liga != "Semua Liga" and "league" in df.columns:
    df_f = df_f[df_f["league"] == pilih_liga]
if pilih_result != "Semua Hasil" and "result" in df.columns:
    df_f = df_f[df_f["result"] == pilih_result]
if pilih_day != "Semua" and "trading_day" in df.columns:
    df_f = df_f[df_f["trading_day"] == pilih_day]

# --- KPI ---
c1, c2, c3, c4, c5 = st.columns(5)
total = len(df_f)
wins = len(df_f[df_f["result"] == "WIN"]) if "result" in df_f.columns else 0
win_rate = (wins / total * 100) if total > 0 else 0
total_profit = df_f["profit"].sum()
total_stake = total * 50000
roi = (total_profit / total_stake * 100) if total_stake > 0 else 0
max_dd = df_f["cumulative_profit"].min() if total > 0 else 0

c1.metric("Total Match", total)
c2.metric("Win", wins)
c3.metric("Win Rate", f"{win_rate:.1f}%")
c4.metric("ROI", f"{roi:.2f}%")
c5.metric("Total Profit", f"Rp {total_profit:,.0f}")

st.divider()

# --- TABS KAYAK DULU ---
tab1, tab2, tab3 = st.tabs(["📈 Grafik", "📊 Per Liga", "📋 Riwayat Lengkap"])

with tab1:
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("Profit Curve (Kumulatif)")
        df_f_sorted = df_f.copy()
        df_f_sorted["cumulative"] = df_f_sorted["profit"].cumsum()
        fig = px.area(df_f_sorted, y="cumulative", title="Profit Kumulatif", color_discrete_sequence=["#22c55e"])
        st.plotly_chart(fig, use_container_width=True)
    with col_g2:
        st.subheader("Profit Per Match")
        fig2 = px.bar(df_f, y="profit", title="Profit Tiap Match", color="profit", color_continuous_scale="RdYlGn")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Drawdown / Profit Berjalan")
    fig3 = px.line(df_f, y="cumulative_profit", title="Equity Curve")
    st.plotly_chart(fig3, use_container_width=True)

with tab2:
    if "league" in df_f.columns:
        per_liga = df_f.groupby("league").agg(total=("profit", "count"), profit=("profit", "sum"), win_rate=("result", lambda x: (x=="WIN").mean()*100)).reset_index().sort_values("profit", ascending=False)
        st.dataframe(per_liga, use_container_width=True)
        fig_liga = px.bar(per_liga, x="league", y="profit", color="profit", title="Profit Per Liga", color_continuous_scale="Viridis")
        st.plotly_chart(fig_liga, use_container_width=True)
    else:
        st.info("Kolom league tidak ada")

    if "activity_label" in df_f.columns:
        st.subheader("Per Activity Label")
        per_act = df_f.groupby("activity_label").agg(total=("profit", "count"), profit=("profit", "sum")).reset_index()
        st.dataframe(per_act, use_container_width=True)

with tab3:
    st.subheader(f"Riwayat Trading - {len(df_f)} Match")
    # Pilih kolom yang penting aja biar nggak kepanjangan kayak tadi
    cols_show = [c for c in ["trading_day","kickoff_wita","home_team","away_team","league","market","minute_detected","score_at_entry","result","profit"] if c in df_f.columns]
    if cols_show:
        st.dataframe(df_f[cols_show].sort_values("trading_day", ascending=False) if "trading_day" in df_f.columns else df_f[cols_show], use_container_width=True, height=500)
    else:
        st.dataframe(df_f, use_container_width=True)

    st.download_button("⬇️ Download CSV", df_f.to_csv(index=False), "trading_menit60.csv", "text/csv")

st.caption(f"Total Profit: Rp {total_profit:,.0f} | Max Drawdown: Rp {max_dd:,.0f} | Data dari muslih156-dot/skor60")
