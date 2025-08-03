import streamlit as st
import pandas as pd
import numpy as np
import requests
import ta
import altair as alt
from datetime import datetime

st.set_page_config(layout="wide")
st.title("📊 Crypto Multi-Indicator Dashboard (USDC párok)")

# CoinGecko coin id-k és ticker mapping USDC párokra (mainly spot market)
coins_usdc = {
    "bitcoin": "BTC-USDC",
    "ethereum": "ETH-USDC",
    "binancecoin": "BNB-USDC",
    "ripple": "XRP-USDC",
    "cardano": "ADA-USDC",
    "dogecoin": "DOGE-USDC",
    "polkadot": "DOT-USDC",
    "solana": "SOL-USDC",
    "litecoin": "LTC-USDC",
    "chainlink": "LINK-USDC",
    "stellar": "XLM-USDC",
    "uniswap": "UNI-USDC",
    "vechain": "VET-USDC",
    "tron": "TRX-USDC",
    # Extra párjaid
    "arweave": "AR-USDC",
    "cosmos": "ATOM-USDC",
    "verasity": "VRA-USDC",
    "virtuality": "VIRTUAL-USDC",
    "routerprotocol": "ROUTE-USDC",
    "lto-network": "LTO-USDC",
}

def fetch_ohlcv_coin_gecko(coin_id, days=180):
    """
    Lekéri a napi OHLCV adatokat CoinGecko API-val.
    Visszatér DataFrame-mel, index dátum, oszlopok: Open, High, Low, Close, Volume
    """
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usdc", "days": days, "interval": "daily"}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        st.error(f"Adatlekérés hiba: {resp.status_code} a {coin_id} esetén")
        return pd.DataFrame()
    data = resp.json()

    # Az adatok listák: [[timestamp, value], ...]
    prices = data.get("prices", [])
    market_caps = data.get("market_caps", [])
    total_volumes = data.get("total_volumes", [])

    if not prices or not total_volumes:
        st.warning("Nincs elegendő adat a kiválasztott kriptopárhoz.")
        return pd.DataFrame()

    # A CoinGecko csak árakat és volumeneket ad (árfolyam napi záró ár körül, OHLC nem biztos)
    # OHLC nincs közvetlenül, de approximáljuk:
    # Átlagárból -> Open, High, Low nem lesz pontos, így egyszerűsítve Close lesz az ár, Open=Low=High=Close
    df = pd.DataFrame(prices, columns=["timestamp", "Close"])
    df["Volume"] = [v[1] for v in total_volumes]
    df["Date"] = pd.to_datetime(df["timestamp"], unit="ms").dt.date
    df.set_index("Date", inplace=True)
    df.drop(columns=["timestamp"], inplace=True)
    # Egyszerű OHLC: Close ár, Open=High=Low=Close
    df["Open"] = df["Close"]
    df["High"] = df["Close"]
    df["Low"] = df["Close"]

    # Átrendezzük az oszlopokat a ta könyvtárhoz
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    return df

# Dropdown - választható coinok
selected_coin_name = st.selectbox("Válassz kriptopárt (USDC ellenében)", list(coins_usdc.values()))

# Lekérjük a coin_id-t a kiválasztott ticker alapján
coin_id = None
for k, v in coins_usdc.items():
    if v == selected_coin_name:
        coin_id = k
        break

if coin_id is None:
    st.error("Hibás kriptopár kiválasztás.")
    st.stop()

df = fetch_ohlcv_coin_gecko(coin_id)

if df.empty:
    st.error("❌ Adatok nem érhetők el a kiválasztott kriptopárhoz.")
    st.stop()

price_col = "Close"

# Indikátorok számítása
try:
    df['RSI'] = ta.momentum.RSIIndicator(df[price_col], window=14).rsi()
    df['SMA21'] = df[price_col].rolling(window=21).mean()
    df['EMA34'] = df[price_col].ewm(span=34, adjust=False).mean()
    df['EMA200'] = df[price_col].ewm(span=200, adjust=False).mean()
    df['SMA200'] = df[price_col].rolling(window=200).mean()

    macd = ta.trend.MACD(df[price_col])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()

    bollinger = ta.volatility.BollingerBands(df[price_col])
    df['BB_upper'] = bollinger.bollinger_hband()
    df['BB_lower'] = bollinger.bollinger_lband()

    stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df[price_col])
    df['Stoch'] = stoch.stoch()

    # OBV manuális számítása (nem része a CoinGecko adatoknak)
    df['OBV'] = (np.sign(df[price_col].diff()) * df['Volume']).fillna(0).cumsum()

except Exception as e:
    st.error(f"Hiba az indikátorok számításakor: {e}")
    st.stop()

# Whalekiller support/resistance band (EMA34, SMA21)
df['Band_bull'] = (df[price_col] > df['EMA34']) & (df[price_col] > df['SMA21'])

# Buy/Sell score 8 faktor alapján:
# 1. RSI oversold (<30) vételi jel, overbought (>70) eladási jel
# 2. MACD > MACD_signal vétel, fordított eladás
# 3. Bollinger Lower Band alatt vétel, felső sáv felett eladás
# 4. Stoch < 20 vétel, > 80 eladás
# 5. OBV pozitív trend vétel, negatív eladás (pl. OBV jelenlegi magasabb mint 10 napja)
# 6. SMA21 > EMA34 bullish, fordított bearish
# 7. EMA200 > SMA200 bullish hosszú távon, fordított bearish
# 8. Whalekiller band zárás felett vétel, alatta eladás

df['OBV_diff'] = df['OBV'] - df['OBV'].shift(10)
df['Buy_Score'] = (
    (df['RSI'] < 30).astype(int) +
    (df['MACD'] > df['MACD_signal']).astype(int) +
    (df[price_col] < df['BB_lower']).astype(int) +
    (df['Stoch'] < 20).astype(int) +
    (df['OBV_diff'] > 0).astype(int) +
    (df['SMA21'] > df['EMA34']).astype(int) +
    (df['EMA200'] > df['SMA200']).astype(int) +
    (df['Band_bull']).astype(int)
)

df['Sell_Score'] = (
    (df['RSI'] > 70).astype(int) +
    (df['MACD'] < df['MACD_signal']).astype(int) +
    (df[price_col] > df['BB_upper']).astype(int) +
    (df['Stoch'] > 80).astype(int) +
    (df['OBV_diff'] < 0).astype(int) +
    (df['SMA21'] < df['EMA34']).astype(int) +
    (df['EMA200'] < df['SMA200']).astype(int) +
    (~df['Band_bull']).astype(int)
)

# Megjelenítés

st.subheader(f"📉 {selected_coin_name} Árfolyam (Close)")
st.line_chart(df[price_col])

st.subheader("📈 RSI (színezett háttérrel az oversold/overbought szinteknél)")
def rsi_chart(df):
    base = alt.Chart(df.reset_index()).encode(x='Date:T')
    line = base.mark_line(color='blue').encode(y='RSI:Q')

    band_overs
