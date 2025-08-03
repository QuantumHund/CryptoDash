import streamlit as st
import pandas as pd
import numpy as np
import requests
import ta
import datetime
import altair as alt

st.set_page_config(layout="wide")
st.title("\U0001F4CA Crypto Multi-Indicator Dashboard")

# Coin list (top + extras)
coin_options = {
    "BTC-USDC": "bitcoin",
    "ETH-USDC": "ethereum",
    "BNB-USDC": "binancecoin",
    "SOL-USDC": "solana",
    "XRP-USDC": "ripple",
    "DOGE-USDC": "dogecoin",
    "ADA-USDC": "cardano",
    "AVAX-USDC": "avalanche-2",
    "MATIC-USDC": "matic-network",
    "DOT-USDC": "polkadot",
    "SHIB-USDC": "shiba-inu",
    "LINK-USDC": "chainlink",
    "NEAR-USDC": "near",
    "APT-USDC": "aptos",
    "AR-USDC": "arweave",
    "ATOM-USDC": "cosmos",
    "VRA-USDC": "verasity",
    "VIRTUAL-USDC": "virtual",
    "ROUTE-USDC": "route",
    "LTO-USDC": "lto-network"
}

selected_label = st.selectbox("Válassz kriptopárt (USDC ellenében)", list(coin_options.keys()))
coin_id = coin_options[selected_label]

@st.cache_data(ttl=3600)
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
            return df[["Open", "High", "Low", "Close", "Volume"]], vs_currency.upper()
    return pd.DataFrame(), "N/A"

df, used_currency = fetch_ohlcv_coin_gecko(coin_id)

if df.empty:
    st.error("\u274c Adatok nem érhetők el a kiválasztott kriptopárhoz.")
    st.stop()

price_col = "Close"
df["Drawdown"] = (df[price_col] / df[price_col].cummax()) - 1

df["RSI"] = ta.momentum.RSIIndicator(df[price_col], window=14).rsi()
df["SMA50"] = df[price_col].rolling(window=50).mean()
df["SMA200"] = df[price_col].rolling(window=200).mean()

macd = ta.trend.MACD(df[price_col])
df["MACD"] = macd.macd()
df["MACD_signal"] = macd.macd_signal()

boll = ta.volatility.BollingerBands(df[price_col])
df["BB_upper"] = boll.bollinger_hband()
df["BB_lower"] = boll.bollinger_lband()

stoch = ta.momentum.StochasticOscillator(df["High"], df["Low"], df[price_col])
df["Stoch"] = stoch.stoch()

df["OBV"] = (np.sign(df["Close"].diff()) * df["Volume"]).fillna(0).cumsum()

# Dummy whalekiller band
df["EMA34"] = df[price_col].ewm(span=34).mean()
df["SMA21"] = df[price_col].rolling(window=21).mean()
df["Band"] = np.where((df[price_col] > df["EMA34"]) & (df[price_col] > df["SMA21"]), 1,
                np.where((df[price_col] < df["EMA34"]) & (df[price_col] < df["SMA21"]), -1, 0))

# VIX surrogate (placeholder)
df["VIX"] = df["Close"].pct_change().rolling(5).std() * 100

# Score system
score_cols = [
    (df["RSI"] < 30).astype(int),
    (df["Drawdown"] < -0.10).astype(int),
    (df["MACD"] > df["MACD_signal"]).astype(int),
    (df["SMA50"] > df["SMA200"]).astype(int),
    (df[price_col] < df["BB_lower"]).astype(int),
    (df["Stoch"] < 20).astype(int),
    (df["Band"] == 1).astype(int),
    (df["VIX"] < 15).astype(int)
]

df["Buy_Score"] = sum(score_cols)

score_cols_sell = [
    (df["RSI"] > 70).astype(int),
    (df["Drawdown"] > -0.01).astype(int),
    (df["MACD"] < df["MACD_signal"]).astype(int),
    (df["SMA50"] < df["SMA200"]).astype(int),
    (df[price_col] > df["BB_upper"]).astype(int),
    (df["Stoch"] > 80).astype(int),
    (df["Band"] == -1).astype(int),
    (df["VIX"] > 20).astype(int)
]

df["Sell_Score"] = sum(score_cols_sell)

# Display
st.subheader(f"\U0001F4C8 Árfolyam ({selected_label.replace('USDC', used_currency)})")
st.line_chart(df[price_col])

st.subheader("\U0001F4C9 RSI + háttér")
rsi_chart = alt.Chart(df.reset_index()).mark_line().encode(
    x='Date:T', y='RSI:Q', tooltip=['Date:T', 'RSI:Q']
).interactive()

bands = alt.Chart(df.reset_index()).mark_rect(opacity=0.15).encode(
    x='Date:T',
    x2='Date:T',
    color=alt.condition(
        alt.datum.RSI > 70, alt.value('red'),
        alt.condition(alt.datum.RSI < 30, alt.value('green'), alt.value('transparent'))
    )
)
st.altair_chart(bands + rsi_chart, use_container_width=True)

st.subheader("\U0001F4C8 OBV")
st.line_chart(df['OBV'])

st.subheader("\U0001F4CA Buy/Sell Score")
df_score = df.reset_index()[["Date", "Buy_Score", "Sell_Score"]]
df_score = df_score.melt(id_vars='Date', var_name='Signal', value_name='Score')
color_scale = alt.Scale(domain=['Buy_Score', 'Sell_Score'], range=['green', 'red'])
score_chart = alt.Chart(df_score).mark_line().encode(
    x='Date:T', y='Score:Q', color=alt.Color('Signal:N', scale=color_scale), tooltip=['Date:T', 'Signal:N', 'Score:Q']
).interactive()
st.altair_chart(score_chart, use_container_width=True)

st.subheader("\U0001F5D2️ Részletes adatok")
st.dataframe(df.tail(30))
