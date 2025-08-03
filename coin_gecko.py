import requests
import pandas as pd

def fetch_ohlcv_coin_gecko(coin_id: str, currency: str = "usd", days: int = 180):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": currency, "days": days, "interval": "daily"}
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()

        df = pd.DataFrame(data['prices'], columns=['timestamp', 'Close'])
        df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('Date', inplace=True)
        df.drop('timestamp', axis=1, inplace=True)

        df['Volume'] = pd.DataFrame(data['total_volumes'])[1].values
        df['High'] = df['Close'] * 1.01  # dummy értékek, ha nincs külön adat
        df['Low'] = df['Close'] * 0.99

        return df, currency
    except Exception:
        return None, None
