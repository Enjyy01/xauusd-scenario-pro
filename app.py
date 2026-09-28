import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ============================================================
# KONFIGURASI APLIKASI
# ============================================================
st.set_page_config(
    page_title="XAUUSD Scenario Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 XAUUSD Scenario Pro & Market Terminal")
st.caption("Platform analisis gaya TradingView untuk pemetaan skenario, sinyal, dan pelacakan fundamental.")

# ============================================================
# SIDEBAR: PENGATURAN ANALISIS
# ============================================================
st.sidebar.header("⚙️ Konfigurasi Chart")

# Pilihan Timeframe
timeframe_options = {
    "15 Menit": {"interval": "15m", "period": "60d"},
    "1 Jam": {"interval": "60m", "period": "730d"},
    "4 Jam": {"interval": "1h", "period": "730d"}, # yfinance proxy for 4h is often 1h resampled, we'll stick to 1h 
    "Harian (Daily)": {"interval": "1d", "period": "5y"},
    "Mingguan (Weekly)": {"interval": "1wk", "period": "10y"},
    "Bulanan (Monthly)": {"interval": "1mo", "period": "10y"}
}

selected_tf_label = st.sidebar.selectbox("Pilih Timeframe", list(timeframe_options.keys()), index=3)
tf_config = timeframe_options[selected_tf_label]

st.sidebar.header("📊 Indikator Overlay")
show_sma = st.sidebar.checkbox("SMA (50 & 200)", value=True)
show_ema = st.sidebar.checkbox("EMA (20 & 50)", value=False)
show_bb = st.sidebar.checkbox("Bollinger Bands", value=False)
show_ichimoku = st.sidebar.checkbox("Ichimoku Cloud", value=False)

st.sidebar.header("📉 Indikator Osilator")
show_rsi = st.sidebar.checkbox("RSI (14)", value=True)
show_macd = st.sidebar.checkbox("MACD", value=True)
show_stoch = st.sidebar.checkbox("Stochastic", value=False)

# ============================================================
# SIDEBAR: SCENARIO PLANNER (ENTRY, TP, SL)
# ============================================================
st.sidebar.header("🎯 Pemetaan Skenario")
enable_scenario = st.sidebar.checkbox("Aktifkan Skenario Planner", value=True)

if enable_scenario:
    entry_price = st.sidebar.number_input("Harga Entry", value=0.0, step=1.0, format="%.2f")
    tp_price = st.sidebar.number_input("Take Profit (TP)", value=0.0, step=1.0, format="%.2f")
    sl_price = st.sidebar.number_input("Stop Loss (SL)", value=0.0, step=1.0, format="%.2f")
    
    if entry_price > 0 and tp_price > 0 and sl_price > 0:
        risk = abs(entry_price - sl_price)
        reward = abs(tp_price - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        
        st.sidebar.markdown(f"**Risk/Reward Ratio:** `1 : {rr_ratio:.2f}`")
        if rr_ratio >= 2.0:
            st.sidebar.success("✅ R/R Ratio Ideal (>= 1:2)")
        else:
            st.sidebar.warning("⚠️ R/R Ratio Kurang Optimal (< 1:2)")

# ============================================================
# FUNGSI MENGAMBIL DATA
# ============================================================
@st.cache_data(ttl=900)
def load_data(interval, period):
    # Menggunakan Gold Futures (GC=F) karena paling stabil di Yahoo Finance untuk semua timeframe
    df = yf.download("GC=F", period=period, interval=interval, progress=False)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df.dropna(inplace=True)
    return df

df = load_data(tf_config["interval"], tf_config["period"])

if df.empty:
    st.error("Gagal mengambil data dari server. Silakan coba lagi.")
    st.stop()

# ============================================================
# KALKULASI INDIKATOR (MENGGUNAKAN PANDAS-TA)
# ============================================================
# Overlays
if show_sma:
    df.ta.sma(length=50, append=True)
    df.ta.sma(length=200, append=True)
if show_ema:
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
if show_bb:
    df.ta.bbands(length=20, append=True)
if show_ichimoku:
    df.ta.ichimoku(append=True)

# Oscillators
if show_rsi:
    df.ta.rsi(length=14, append=True)
if show_macd:
    df.ta.macd(append=True)
if show_stoch:
    df.ta.stoch(append=True)

# Sinyal Sederhana (berdasarkan SMA)
if show_sma and 'SMA_50' in df.columns and 'SMA_200' in df.columns:
    df['Trend'] = "SIDEWAYS"
    df.loc[df['Close'] > df['SMA_200'], 'Trend'] = "BULLISH"
    df.loc[df['Close'] < df['SMA_200'], 'Trend'] = "BEARISH"
else:
    df['Trend'] = "ANALISIS TIDAK AKTIF"

# ============================================================
# MEMBANGUN CHART DINAMIS (PLOTLY)
# ============================================================
active_oscillators = []
if show_macd: active_oscillators.append("MACD")
if show_rsi: active_oscillators.append("RSI")
if show_stoch: active_oscillators.append("STOCH")

num_rows = 1 + len(active_oscillators)
row_heights = [0.6] + [0.4 / len(active_oscillators)] * len(active_oscillators) if active_oscillators else [1.0]
subplot_titles = ["Chart Utama (XAUUSD)"] + active_oscillators

fig = make_subplots(
    rows=num_rows, cols=1, shared_xaxes=True,
    row_heights=row_heights, vertical_spacing=0.05,
    subplot_titles=subplot_titles
)

# 1. Main Candlestick Chart
fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="XAUUSD"
), row=1, col=1)

# Tambahkan Indikator Overlay
if show_sma and 'SMA_50' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA_50"], name="SMA 50", line=dict(color='orange')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["SMA_200"], name="SMA 200", line=dict(color='red')), row=1, col=1)

if show_ema and 'EMA_20' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA_20"], name="EMA 20", line=dict(color='blue')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["EMA_50"], name="EMA 50", line=dict(color='purple')), row=1, col=1)

if show_bb and 'BBL_20_2.0' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["BBU_20_2.0"], name="BB Upper", line=dict(color='gray', dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["BBL_20_2.0"], name="BB Lower", fill='tonexty', line=dict(color='gray', dash='dot')), row=1, col=1)

# Tambahkan Garis Skenario Planner
if enable_scenario:
    if entry_price > 0:
        fig.add_hline(y=entry_price, line_dash="dash", line_color="blue", annotation_text="Entry", row=1, col=1)
    if tp_price > 0:
        fig.add_hline(y=tp_price, line_dash="dash", line_color="green", annotation_text="Take Profit", row=1, col=1)
    if sl_price > 0:
        fig.add_hline(y=sl_price, line_dash="dash", line_color="red", annotation_text="Stop Loss", row=1, col=1)

# 2. Oscillators
current_row = 2
if show_macd and 'MACD_12_26_9' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["MACD_12_26_9"], name="MACD"), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["MACDs_12_26_9"], name="Signal"), row=current_row, col=1)
    fig.add_trace(go.Bar(x=df.index, y=df["MACDh_12_26_9"], name="Histogram"), row=current_row, col=1)
    current_row += 1

if show_rsi and 'RSI_14' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI_14"], name="RSI 14"), row=current_row, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=current_row, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=current_row, col=1)
    current_row += 1

if show_stoch and 'STOCHk_14_3_3' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df["STOCHk_14_3_3"], name="Stoch %K"), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df["STOCHd_14_3_3"], name="Stoch %D"), row=current_row, col=1)
    fig.add_hline(y=80, line_dash="dot", line_color="red", row=current_row, col=1)
    fig.add_hline(y=20, line_dash="dot", line_color="green", row=current_row, col=1)

# Finalisasi Layout Chart
fig.update_layout(
    height=800 if num_rows > 1 else 600,
    xaxis_rangeslider_visible=False,
    template="plotly_dark", # Tema Gelap gaya TradingView
    margin=dict(l=10, r=10, t=30, b=10),
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

# ============================================================
# PANEL BAWAH: BERITA & FUNDAMENTAL
# ============================================================
st.markdown("---")
col_news, col_fund = st.columns([1.5, 1])

with col_news:
    st.subheader("📰 Berita XAUUSD Terkini")
    try:
        ticker = yf.Ticker("GC=F")
        news = ticker.news
        if news:
            for article in news[:5]:
                st.markdown(f"**[{article['title']}]({article['link']})**")
                date_published = datetime.fromtimestamp(article['providerPublishTime']).strftime('%Y-%m-%d %H:%M')
                st.caption(f"{article['publisher']} - {date_published}")
                st.write("")
        else:
            st.info("Tidak ada berita terbaru yang ditemukan saat ini.")
    except Exception as e:
        st.warning("Gagal memuat berita langsung dari server Yahoo Finance.")

with col_fund:
    st.subheader("🏦 Market Drivers (Korelasi Emas)")
    
    with st.expander("💵 US Dollar Index (DXY)", expanded=True):
        st.write("Korelasi **Negatif**. Jika Dolar AS menguat, harga Emas (XAUUSD) cenderung melemah, dan sebaliknya.")
        
    with st.expander("📈 US Treasury Yields (Obligasi 10 Tahun)"):
        st.write("Korelasi **Negatif**. Emas tidak memberikan bunga (non-yielding asset). Jika *yield* obligasi AS naik, investor lebih memilih obligasi daripada emas.")
        
    with st.expander("🏦 Suku Bunga The Fed (FOMC)"):
        st.write("Suku bunga naik ➡️ Dolar menguat ➡️ Emas berpotensi turun.\n\nSuku bunga turun/ditahan ➡️ Dolar melemah ➡️ Emas berpotensi naik.")
        
    with st.expander("⚔️ Geopolitik & Inflasi"):
        st.write("Emas adalah aset *Safe Haven*. Di tengah perang, ketidakpastian politik global, atau inflasi yang sangat tinggi, permintaan emas akan melonjak tajam.")
