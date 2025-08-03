import pandas as pd
import ta

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    price_col = 'Close'

    df['Drawdown'] = (df[price_col] / df[price_col].cummax()) - 1
    df['RSI'] = ta.momentum.RSIIndicator(df[price_col], window=14).rsi()
    df['SMA50'] = df[price_col].rolling(window=50).mean()
    df['SMA200'] = df[price_col].rolling(window=200).mean()

    macd = ta.trend.MACD(df[price_col])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()

    boll = ta.volatility.BollingerBands(df[price_col])
    df['BB_upper'] = boll.bollinger_hband()
    df['BB_lower'] = boll.bollinger_lband()

    stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df[price_col])
    df['Stoch'] = stoch.stoch()

    # OBV kézi számítás (nem minden API adja)
    df['OBV'] = (df['Volume'] * ((df[price_col] > df[price_col].shift()).astype(int) - 
                                 (df[price_col] < df[price_col].shift()).astype(int))).cumsum()

    # VIX placeholder (konstans érték)
    df['VIX_level'] = 15

    df['Buy_Score'] = (
        (df['RSI'] < 30).astype(int) +
        (df['Drawdown'] < -0.10).astype(int) +
        (df['MACD'] > df['MACD_signal']).astype(int) +
        (df['SMA50'] > df['SMA200']).astype(int) +
        (df[price_col] < df['BB_lower']).astype(int) +
        (df['Stoch'] < 20).astype(int) +
        (df['OBV'] > df['OBV'].rolling(14).mean()).astype(int) +
        (df['VIX_level'] < 15).astype(int)
    )

    df['Sell_Score'] = (
        (df['RSI'] > 70).astype(int) +
        (df['Drawdown'] > -0.01).astype(int) +
        (df['MACD'] < df['MACD_signal']).astype(int) +
        (df['SMA50'] < df['SMA200']).astype(int) +
        (df[price_col] > df['BB_upper']).astype(int) +
        (df['Stoch'] > 80).astype(int) +
        (df['OBV'] < df['OBV'].rolling(14).mean()).astype(int) +
        (df['VIX_level'] > 20).astype(int)
    )

    return df
