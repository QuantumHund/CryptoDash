import streamlit as st
import yfinance as yf
import pandas as pd
import ta
import altair as alt

st.set_page_config(layout="wide")
st.title("📊 Crypto Multi-Indicator Dashboard (USDC pairs)")

# Lista a kiválasztható kripto párokról (USDC ellenében, Yahoo Finance kompatibilis formátumban)
token_list = [
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "ADA-USD", "SOL-USD", "DOGE-USD",
    "DOT-USD", "MATIC-USD", "LTC-USD", "LINK-USD", "SHIB-USD", "AVAX-USD", "UNI-USD",
    "AR-USD", "ATOM-USD", "VRA-USD", "VIRTUAL-USD", "ROUTE-USD", "LTO-USD"
]

selected_token = st.selectbox("Válassz kriptopárt (USDC ellenében)", token_list, index=0)

@st.cache_data(ttl=300)
def fetch_data(ticker, period="6mo", interval="1d"):
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty:
            st.warning(f"⚠️ Nem érkeztek adatok a {ticker} tickerhez.")
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        st.error(f"Adatlekérés hiba a {ticker} esetén: {e}")
        return pd.DataFrame()

df = fetch_data(selected_token)

if df.empty:
    st.error("❌ Adatok nem érhetők el a kiválasztott kriptopárhoz.")
    st.stop()

price_col = None
for col in ['Adj Close', 'Close']:
    if col in df.columns:
        price_col = col
        break

if price_col is None:
    st.error("❌ Nem található 'Close' vagy 'Adj Close' árfolyam oszlop.")
    st.stop()

try:
    # RSI
    rsi = ta.momentum.RSIIndicator(df[price_col], window=14).rsi()
    # SMA 21 és EMA 34 a MWhalekiller sávhoz
    sma21 = df[price_col].rolling(window=21).mean()
    ema34 = df[price_col].ewm(span=34, adjust=False).mean()
    
    # MWhalekiller band feltétele (bullish ha close > sma21 és ema34)
    bullish_band = (df[price_col] > sma21) & (df[price_col] > ema34)
    
    # On-Balance Volume (OBV)
    obv = ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
    
    # Stochastic Oscillator
    stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df[price_col]).stoch()
    
    # Bollinger Bands
    bollinger = ta.volatility.BollingerBands(df[price_col])
    bb_upper = bollinger.bollinger_hband()
    bb_lower = bollinger.bollinger_lband()
    
    # MACD
    macd = ta.trend.MACD(df[price_col])
    macd_line = macd.macd()
    macd_signal = macd.macd_signal()
    
except Exception as e:
    st.error(f"Hiba az indikátorok számításakor: {e}")
    st.stop()

# Egyszerű scoring példa (lehet tovább finomítani)
score = 0
score += int(rsi < 30)
score += int(rsi > 70)
score += int(bullish_band)
score += int(macd_line > macd_signal)
score += int(df[price_col].iloc[-1] < bb_lower.iloc[-1])
score += int(df[price_col].iloc[-1] > bb_upper.iloc[-1])
score += int(stoch.iloc[-1] < 20)
score += int(stoch.iloc[-1] > 80)

st.subheader(f"📈 {selected_token} Árfolyam és indikátorok")

# Árfolyam chart
st.line_chart(df[price_col])

# RSI chart háttérszínnel (piros a túlvettséghez, zöld a túlértékesítéshez)
rsi_df = pd.DataFrame({'RSI': rsi})
rsi_chart = alt.Chart(rsi_df.reset_index()).mark_line().encode(
    x='Date:T',
    y='RSI:Q'
)

rsi_bg = alt.Chart(rsi_df.reset_index()).mark_rect().encode(
    x='Date:T',
    y=alt.value(0),
    y2=alt.value(100),
    color=alt.condition(
        (alt.datum.RSI > 70),
        alt.value('red'),
        alt.condition((alt.datum.RSI < 30), alt.value('green'), alt.value('transparent'))
    )
)

st.altair_chart(rsi_bg + rsi_chart, use_container_width=True)

# OBV chart
st.subheader("OBV (On-Balance Volume)")
st.line_chart(obv)

# MWhalekiller band indikátor szöveg (short)
st.markdown("""
**MWhalekiller Support/Resistance Band**  
- Ha árfolyam a 21 SMA és 34 EMA fölött zár, bullish jelzés  
- Ha árfolyam ezek alatt, bearish jelzés  
""")

st.markdown(f"**Jelenlegi állapot:** {'Bullish' if bullish_band.iloc[-1] else 'Bearish'}")

