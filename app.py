import streamlit as st
import pandas as pd
import datetime
from indicators import calculate_indicators
from coin_gecko import fetch_ohlcv_coin_gecko

st.set_page_config(layout="wide")
st.title("📊 Crypto Multi-Indicator Dashboard")

# 🔝 Top 20 kriptopár USDC ellenében
crypto_options = [
    "BTC-USDC", "ETH-USDC", "SOL-USDC", "ADA-USDC", "XRP-USDC", "AVAX-USDC", "DOGE-USDC", "SHIB-USDC",
    "DOT-USDC", "MATIC-USDC", "LINK-USDC", "NEAR-USDC", "TRX-USDC", "UNI-USDC", "AR-USDC", "ATOM-USDC",
    "VRA-USDC", "VIRTUAL-USDC", "ROUTE-USDC", "LTO-USDC"
]
selected_label = st.selectbox("Válassz kriptopárt (USDC ellenében)", crypto_options)

# ⛏️ coin_id pl. 'bitcoin' a CoinGecko API-hoz
symbol_to_id = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "ADA": "cardano", "XRP": "ripple",
    "AVAX": "avalanche-2", "DOGE": "dogecoin", "SHIB": "shiba-inu", "DOT": "polkadot",
    "MATIC": "matic-network", "LINK": "chainlink", "NEAR": "near", "TRX": "tron",
    "UNI": "uniswap", "AR": "arweave", "ATOM": "cosmos", "VRA": "verasity", "VIRTUAL": "virtual-meta",
    "ROUTE": "router-protocol", "LTO": "lto-network"
}

symbol = selected_label.split("-")[0]
coin_id = symbol_to_id.get(symbol)

if coin_id is None:
    st.error("❌ Ismeretlen kriptopár.")
    st.stop()

with st.spinner("Adatok betöltése..."):
    df, used_currency = fetch_ohlcv_coin_gecko(coin_id)

if df is None or df.empty:
    st.error("❌ Adatok nem érhetők el a kiválasztott kriptopárhoz.")
    st.stop()

# ✅ Módosított főcím a tényleges valutával
st.markdown(f"#### Aktuális árfolyam ({symbol}-{used_currency.upper()})")

df_ind = calculate_indicators(df)

price_col = 'Close'

st.line_chart(df_ind[price_col])

st.subheader("📈 Technikai indikátorok")
st.line_chart(df_ind[['RSI', 'Stoch']])
st.area_chart(df_ind['Drawdown'])

st.subheader("📊 Buy / Sell Score (0–8)")
st.line_chart(df_ind[['Buy_Score', 'Sell_Score']])

st.subheader("📋 Legfrissebb adatok")
st.dataframe(df_ind.tail(30))
