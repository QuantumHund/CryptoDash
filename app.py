import streamlit as st
import pandas as pd
import numpy as np
import requests
import ta
import altair as alt

st.set_page_config(layout="wide")
st.title("📊 Crypto Multi-Indicator Dashboard (USDC pairs)")

# --- Top 20 coinok CoinGecko ID szerint ---
coin_options = {
    "BTC-USDC": "bitcoin",
    "ETH-USDC": "ethereum",
    "SOL-USDC": "solana",
    "XRP-USDC": "ripple",
    "ADA-USDC": "cardano",
    "AVAX-USDC": "avalanche-2",
    "MATIC-USDC": "matic-network",
    "DOT-USDC": "polkadot",
    "TRX-USDC": "tron",
    "DOGE-USDC": "dogecoin",
    "LINK-USDC": "chainlink",
    "LTC-USDC": "litecoin",
    "OP-USDC": "optimism",
    "ARB-USDC": "arbitrum",
    "ATOM-USDC": "cosmos",
    "VRA-USDC": "verasity",
    "VIRTUAL-USDC": "virtual-dao",
    "ROUTE-USDC": "route",
    "LTO-USDC": "lto-network"
}

selected_label = st.selectbox("Válassz kriptopárt (USDC ellenében)", list(coin_options.keys()))
coin_id = coin_options[selected_label]

# --- Adatlekérés CoinGecko-ról, fallback USD-re ---
@st.cache_data(ttl=600)
def fetch_ohlcv_coin_gecko(coin_id, days=180):
    for vs_currency in ["usdc", "usd"]:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": vs_currency, "days": days, "interval": "daily"}
        resp = requests.get(url, params=params)

        if resp.status_code == 200:
            data = resp.json()
            prices = data.get("prices", [])
            volumes = data.get("total_volumes", [])

            if not prices or not volumes:
                continue

            df = pd.DataFrame(prices, columns=["timestamp", "Close"])
            df["Volume"] = [v[1] for v in volumes]
            df["Date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.date
            df.set_index("Date", inplace=True)
            df.drop(columns=["timestamp"], inplace=True)
            df["Open"] = df["Close"]
            df["High"] = df["Close"]
            df["Low"] = df["Close"]
            return df[["Open", "High", "Low", "Close", "Volume"]]

        elif resp.status_code == 400 and vs_currency == "usdc":
            continue  # próbálja USD-vel
    return pd.DataFrame()

df = fetch_ohlcv_coin_gecko(coin_id)

if df.empty:
    st.error(f"❌ Adatok nem érhetők el a kiválasztott kriptopárhoz.")
    st.stop()

# --- Indikátorok számítása ---
try:
    df["Drawdown"] = (df["Close"] / df["Close"].cummax()) - 1
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=14).rsi()
    df["SMA50"] = df["Close"].rolling(window=50).mean()
    df["SMA200"] = df["Close"].rolling(window=200).mean()
    macd = ta.trend.MACD(df["Close"])
    df["MACD"] = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    stoch = ta.momentum.StochasticOscillator(df["High"], df["Low"], df["Close"])
    df["Stoch"] = stoch.stoch()
    df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()

    # MWhalekiller indikátor: Bullish ha Close > SMA21 és EMA34
    df["EMA34"] = df["Close"].ewm(span=34).mean()
    df["SMA21"] = df["Close"].rolling(window=21).mean()
    df["WhaleSupport"] = ((df["Close"] > df["EMA34"]) & (df["Close"] > df["SMA21"])).astype(int)
except Exception as e:
    st.error(f"Hiba az indikátor számításakor: {e}")
    st.stop()

# --- Scoring ---
df["Buy_Score"] = (
    ((df["RSI"] < 30).astype(int)) +
    ((df["Drawdown"] < -0.10).astype(int)) +
    ((df["MACD"] > df["MACD_signal"]).astype(int)) +
    ((df["SMA50"] > df["SMA200"]).astype(int)) +
    ((df["Close"] < df["SMA21"]).astype(int)) +  # whale band alatt nincs
    ((df["Stoch"] < 20).astype(int)) +
    ((df["OBV"] > df["OBV"].rolling(window=14).mean()).astype(int)) +
    (df["WhaleSupport"])
)

df["Sell_Score"] = (
    ((df["RSI"] > 70).astype(int)) +
    ((df["Drawdown"] > -0.01).astype(int)) +
    ((df["MACD"] < df["MACD_signal"]).astype(int)) +
    ((df["SMA50"] < df["SMA200"]).astype(int)) +
    ((df["Close"] > df["SMA21"]).astype(int)) +
    ((df["Stoch"] > 80).astype(int)) +
    ((df["OBV"] < df["OBV"].rolling(window=14).mean()).astype(int)) +
    (~(df["WhaleSupport"].astype(bool))).astype(int)
)

# --- Chartok ---
st.subheader(f"📈 Árfolyam ({selected_label})")
st.line_chart(df["Close"])

st.subheader("📉 RSI (zöld háttér: oversold, piros: overbought)")
rsi_color = ["#e6f4ea" if r < 30 else "#fcebea" if r > 70 else "white" for r in df["RSI"]]
rsi_df = pd.DataFrame({"Date": df.index, "RSI": df["RSI"], "Color": rsi_color})
rsi_chart = alt.Chart(rsi_df).mark_line().encode(
    x='Date:T', y='RSI:Q', tooltip=["Date:T", "RSI:Q"]
).properties(height=200)
st.altair_chart(rsi_chart, use_container_width=True)

st.subheader("🟢 Buy & 🔴 Sell Score (0–8)")
score_df = df.reset_index()[["Date", "Buy_Score", "Sell_Score"]].melt(
    id_vars="Date", var_name="Signal", value_name="Score"
)
color_scale = alt.Scale(domain=["Buy_Score", "Sell_Score"], range=["green", "red"])
score_chart = alt.Chart(score_df).mark_line().encode(
    x="Date:T", y="Score:Q", color=alt.Color("Signal:N", scale=color_scale),
    tooltip=["Date:T", "Signal:N", "Score:Q"]
).interactive()
st.altair_chart(score_chart, use_container_width=True)

# --- OBV chart külön ---
st.subheader("📊 On-Balance Volume (OBV)")
st.line_chart(df["OBV"])

# --- Részletes tábla ---
st.subheader("📋 Részletes adat (utolsó 30 nap)")
st.dataframe(df.tail(30))
