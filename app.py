import streamlit as st
import pandas as pd
from indicators import calculate_indicators
from coin_gecko import fetch_ohlcv_coin_gecko

st.set_page_config(layout="wide")
st.title("📊 Crypto Multi-Indicator Dashboard")

crypto_options = [
    "BTC-USDC", "ETH-USDC", "SOL-USDC", "ADA-USDC", "XRP-USDC", "AVAX-USDC", "DOGE-USDC", "SHIB-USDC",
    "DOT-USDC", "MATIC-USDC", "LINK-USDC", "NEAR-USDC", "TRX-USDC", "UNI-USDC",
    "AR-USDC", "ATOM-USDC", "VRA-USDC", "VIRTUAL-USDC", "ROUTE-USDC", "LTO-USDC"
]

symbol_to_id = {
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "ADA": "cardano", "XRP": "ripple",
    "AVAX": "avalanche-2", "DOGE": "dogecoin", "SHIB": "shiba-inu", "DOT": "polkadot",
    "MATIC": "matic-network", "LINK": "chainlink", "NEAR": "near", "TRX": "tron",
    "UNI": "uniswap", "AR": "arweave", "ATOM": "cosmos", "VRA": "verasity",
    "VIRTUAL": "virtual-meta", "ROUTE": "router-protocol", "LTO": "lto-network"
}

selected = st.selectbox("Válassz kriptopárt (USDC ellenében)", crypto_options)
symbol = selected.split("-")[0]
coin_id = symbol_to_id.get(symbol)

if not coin_id:
    st.error("❌ Ismeretlen kriptopár.")
    st.stop()

with st.spinner("🔄 Adatok betöltése..."):
    df, used_currency = fetch_ohlcv_coin_gecko(coin_id, currency="usd")  # csak usd-t használunk

if df is None or df.empty:
    st.error(f"❌ Adatok nem érhetők el a kiválasztott {symbol}-USD párosra.")
    if st.button("Újrapróbálkozás"):
        st.experimental_rerun()
    st.stop()

df_ind = calculate_indicators(df)

st.markdown(f"#### Aktuális árfolyam ({symbol}-{used_currency.upper()})")
st.line_chart(df_ind['Close'])

st.subheader("📉 Drawdown")
st.area_chart(df_ind['Drawdown'])

st.subheader("📈 RSI & Stochastic")
st.line_chart(df_ind[['RSI', 'Stoch']])

st.subheader("📊 Buy / Sell Score (0–8)")
st.line_chart(df_ind[['Buy_Score', 'Sell_Score']])

st.subheader("📋 Legfrissebb adatok")
st.dataframe(df_ind.tail(30))
