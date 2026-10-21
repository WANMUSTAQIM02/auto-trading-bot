import yfinance as yf
import pandas as pd
import requests

session = requests.Session()
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def get_all_timeframe_biases(symbol="GC=F"):
    biases = {
        "1m": "NEUTRAL", "5m": "NEUTRAL", "15m": "NEUTRAL",
        "30m": "NEUTRAL", "1h": "NEUTRAL", "4h": "NEUTRAL",
        "1d": "NEUTRAL", "1w": "NEUTRAL", "1mn": "NEUTRAL"
    }
    try:
        df_15m = yf.download(symbol, period="5d", interval="15m", progress=False, session=session)
        if not df_15m.empty:
            if isinstance(df_15m.columns, pd.MultiIndex):
                df_15m.columns = df_15m.columns.get_level_values(0)
            df_15m = df_15m.rename(columns={'Open':'open', 'High':'high', 'Low':'low', 'Close':'close', 'Volume':'volume'})
            
            df_15m['EMA20'] = df_15m['close'].ewm(span=20, adjust=False).mean()
            biases["15m"] = "BULLISH" if df_15m['close'].iloc[-1] > df_15m['EMA20'].iloc[-1] else "BEARISH"
            
            df_1h = df_15m.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
            if len(df_1h) > 10:
                df_1h['EMA50'] = df_1h['close'].ewm(span=50, adjust=False).mean()
                biases["1h"] = "BULLISH" if df_1h['close'].iloc[-1] > df_1h['EMA50'].iloc[-1] else "BEARISH"
            
            df_4h = df_15m.resample('4h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna()
            if len(df_4h) > 10:
                df_4h['EMA50'] = df_4h['close'].ewm(span=50, adjust=False).mean()
                biases["4h"] = "BULLISH" if df_4h['close'].iloc[-1] > df_4h['EMA50'].iloc[-1] else "BEARISH"

        df_1d = yf.download(symbol, period="6mo", interval="1d", progress=False, session=session)
        if not df_1d.empty:
            if isinstance(df_1d.columns, pd.MultiIndex):
                df_1d.columns = df_1d.columns.get_level_values(0)
            df_1d = df_1d.rename(columns={'Open':'open', 'High':'high', 'Low':'low', 'Close':'close', 'Volume':'volume'})
            df_1d['EMA50'] = df_1d['close'].ewm(span=50, adjust=False).mean()
            biases["1d"] = "BULLISH" if df_1d['close'].iloc[-1] > df_1d['EMA50'].iloc[-1] else "BEARISH"
    except Exception as e:
        print(f"[!] Ralat Biases: {e}")
    return biases

def run_sentiment_engine(tf_biases):
    try:
        bullish_count = sum(1 for tf, b in tf_biases.items() if b == 'BULLISH')
        bearish_count = sum(1 for tf, b in tf_biases.items() if b == 'BEARISH')
        total = len(tf_biases)
        
        if bullish_count > bearish_count:
            signal = "BUY"
            pct = int((bullish_count / total) * 100)
        elif bearish_count > bullish_count:
            signal = "SELL"
            pct = int((bearish_count / total) * 100)
        else:
            signal = "NEUTRAL"
            pct = 50
            
        return {"name": "Sentimen", "signal": signal, "pct": max(pct, 51)}
    except Exception:
        return {"name": "Sentimen", "signal": "NEUTRAL", "pct": 50}