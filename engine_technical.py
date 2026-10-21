import pandas as pd
import numpy as np

# 1. Formula EMA (Sama seperti TradingView ta.ema)
def calculate_ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

# 2. Formula RSI Wilder's Smoothing (Sama seperti TradingView ta.rsi)
def calculate_rsi(series, length=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # TradingView menggunakan Wilder's Moving Average (RMA) untuk RSI
    avg_gain = gain.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, min_periods=length, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def run_technical_engine(df):
    try:
        # Gunakan 100 bar terkini supaya pengiraan RSI & EMA cukup matang
        recent_df = df.copy().tail(100).reset_index(drop=True)
        
        if len(recent_df) < 50:
            return {"name": "Teknikal", "signal": "NEUTRAL", "pct": 50, "reason": "Data tak cukup (min 50 lilin)"}

        # Kira indikator menggunakan formula native (Tak perlu pandas-ta)
        recent_df['EMA20'] = calculate_ema(recent_df['close'], 20)
        recent_df['EMA50'] = calculate_ema(recent_df['close'], 50)
        recent_df['RSI14'] = calculate_rsi(recent_df['close'], 14)

        # Pengiraan HEIKIN-ASHI (Sama seperti Pine Script ticker.heikinashi)
        ha_df = recent_df.copy()
        ha_df['HA_Close'] = (recent_df['open'] + recent_df['high'] + recent_df['low'] + recent_df['close']) / 4
        
        ha_df['HA_Open'] = 0.0 # Placeholder
        ha_df.loc[0, 'HA_Open'] = (recent_df.loc[0, 'open'] + recent_df.loc[0, 'close']) / 2
        for i in range(1, len(ha_df)):
            ha_df.loc[i, 'HA_Open'] = (ha_df.loc[i-1, 'HA_Open'] + ha_df.loc[i-1, 'HA_Close']) / 2

        # Semak trend Heikin-Ashi terkini
        ha_bullish = ha_df['HA_Close'].iloc[-1] > ha_df['HA_Open'].iloc[-1]

        # Ambil nilai terakhir untuk semakan syarat signal
        close = recent_df['close'].iloc[-1]
        ema20 = recent_df['EMA20'].iloc[-1]
        ema50 = recent_df['EMA50'].iloc[-1]
        rsi14 = recent_df['RSI14'].iloc[-1]

        # LOGIK SIGNAL MIRRORING (Sama 100% dengan Pine Script)
        buy_cond = (close > ema20) and (ema20 > ema50) and (rsi14 < 70) and ha_bullish
        sell_cond = (close < ema20) and (ema20 < ema50) and (rsi14 > 30) and not ha_bullish

        # Tentukan Kekuatan Momentum (Untuk papan pemuka)
        momentum_score = 50
        if buy_cond:
            signal = "BUY"
            momentum_score = 75 + int((70 - rsi14) / 2) if pd.notna(rsi14) else 75
        elif sell_cond:
            signal = "SELL"
            momentum_score = 75 + int((rsi14 - 30) / 2) if pd.notna(rsi14) else 75
        else:
            signal = "NEUTRAL"
            momentum_score = 50
            if close > ema20 and ha_bullish:
                momentum_score = 60
            elif close < ema20 and not ha_bullish:
                momentum_score = 40

        momentum_score = max(0, min(100, momentum_score))
        pct_strength = momentum_score if signal in ["BUY", "SELL"] else 50

        # Elakkan isu rsi14 = NaN pada permulaan log
        rsi_display = rsi14 if pd.notna(rsi14) else 50.0

        return {
            "name": "Teknikal",
            "signal": signal,
            "pct": pct_strength,
            "reason": f"M15: EMA20={ema20:.2f}, EMA50={ema50:.2f}, RSI={rsi_display:.1f}, HA={'Bull' if ha_bullish else 'Bear'}"
        }

    except Exception as e:
        print(f"[!] Ralat Enjin Teknikal: {e}")
        return {"name": "Teknikal", "signal": "NEUTRAL", "pct": 50, "reason": "Ralat pengiraan teknikal"}