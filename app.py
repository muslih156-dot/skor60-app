import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_matches_from_old_repo
from statistics import calculate_stats
from settlement import audit_result

st.set_page_config(page_title="Trading Bola Menit 60", layout="wide")
st.title("⚽ Trading Bola Menit 60 - Dashboard")

matches = load_matches_from_old_repo()

if not matches:
    st.warning("Belum ada data. Data masih ada di repo lama skor60, cek koneksi atau username di data_loader.py")
    st.stop()

df = pd.DataFrame(matches)
stats = calculate_stats(matches)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Match", stats.get("total", 0))
col2.metric("Win Rate", f"{stats.get('win_rate', 0):.1f}%")
col3.metric("ROI", f"{stats.get('roi', 0):.2f}%")
col4.metric("Total Profit", f"{stats.get('total_profit', 0):,.0f}")

st.subheader("Riwayat Trading")
st.dataframe(df, use_container_width=True)

if len(df) > 0 and "profit" in df.columns:
    fig = px.line(df, y="profit", title="Profit Curve")
    st.plotly_chart(fig, use_container_width=True)
