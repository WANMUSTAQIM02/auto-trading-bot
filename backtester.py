import requests
import yfinance as yf
import pandas as pd
import numpy as np

session = requests.Session()
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def run_historical_backtest(symbol="GC=F"):
    try:
        ticker = yf.Ticker(symbol, session=session)
        # Muat turun data 1 tahun penuh pada timeframe 1 Jam (H1) - had maksimum Yahoo Finance yang stabil
        df = ticker.history(period="1y", interval="1h")
        
        if df.empty:
            print("[!] Backtest 1 Tahun: Data H1 kosong daripada yfinance.")
            return {"status": "error", "total": 0, "wins": 0, "losses": 0, "win_rate": "0%", "profit_factor": "0.0", "max_drawdown": "$0", "net_profit": "$0"}
        
        df.reset_index(inplace=True)
        time_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
        df = df.rename(columns={time_col: 'time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        
        # Indikator Trend & ATR Volatiliti H1
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['ATR'] = df['tr'].rolling(window=14).mean()

        trades = []

        # Imbasan Struktur Pasaran 1 Tahun Penuh
        for i in range(200, len(df) - 30):
            row = df.iloc[i]
            close = row['close']
            ema200 = row['EMA_200']
            atr = row['ATR'] if not pd.isna(row['ATR']) else 5.0

            # Swing High / Low H1 untuk Breakout
            prev_high = df.loc[i-15:i-1, 'high'].max()
            prev_low = df.loc[i-15:i-1, 'low'].min()

            # Setup BUY (1 Tahun)
            if close > ema200 and close > prev_high:
                entry = close
                sl_dist = max(8.0, round(atr * 1.5, 2)) # Buffer lebih besar untuk H1
                sl = entry - sl_dist
                tp = entry + (sl_dist * 2.0)            # Nisbah R:R 1:2
                
                hit = "PENDING"
                for j in range(i + 1, min(i + 40, len(df))):
                    f_high = df.loc[j, 'high']
                    f_low = df.loc[j, 'low']
                    
                    if f_low <= sl:
                        hit = "SL"
                        break
                    if f_high >= tp:
                        hit = "TP"
                        break
                        
                if hit != "PENDING":
                    trades.append({"type": "BUY", "result": hit, "pnl": (sl_dist * 2.0) if hit == "TP" else -sl_dist})

            # Setup SELL (1 Tahun)
            elif close < ema200 and close < prev_low:
                entry = close
                sl_dist = max(8.0, round(atr * 1.5, 2))
                sl = entry + sl_dist
                tp = entry - (sl_dist * 2.0)
                
                hit = "PENDING"
                for j in range(i + 1, min(i + 40, len(df))):
                    f_high = df.loc[j, 'high']
                    f_low = df.loc[j, 'low']
                    
                    if f_high >= sl:
                        hit = "SL"
                        break
                    if f_low <= tp:
                        hit = "TP"
                        break
                        
                if hit != "PENDING":
                    trades.append({"type": "SELL", "result": hit, "pnl": (sl_dist * 2.0) if hit == "TP" else -sl_dist})

        total_trades = len(trades)
        if total_trades == 0:
            return {"status": "success", "total": 0, "wins": 0, "losses": 0, "win_rate": "0%", "profit_factor": "0.0", "max_drawdown": "$0", "net_profit": "$0"}

        wins = [t for t in trades if t['result'] == 'TP']
        losses = [t for t in trades if t['result'] == 'SL']

        win_rate_val = (len(wins) / total_trades) * 100
        gross_profit = sum([t['pnl'] for t in wins])
        gross_loss = abs(sum([t['pnl'] for t in losses]))
        
        profit_factor_val = (gross_profit / gross_loss) if gross_loss > 0 else 2.5
        net_profit_val = sum([t['pnl'] for t in trades])

        # Pengiraan Drawdown 1 Tahun
        peak = 0
        max_dd = 0
        running_bal = 0
        for t in trades:
            running_bal += t['pnl']
            if running_bal > peak:
                peak = running_bal
            dd = peak - running_bal
            if dd > max_dd:
                max_dd = dd

        print(f"[*] Backtest 1 Tahun Selesai: {total_trades} trade dijumpai ({win_rate_val:.1f}% Win Rate).")

        return {
            "status": "success",
            "total": total_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": f"{win_rate_val:.1f}%",
            "profit_factor": f"{profit_factor_val:.2f}",
            "max_drawdown": f"${(max_dd * 10):.2f}",
            "net_profit": f"${(net_profit_val * 10):.2f}"
        }
    except Exception as e:
        print(f"[!] Ralat Backtest 1 Tahun: {e}")
        return {"status": "error", "total": 0, "wins": 0, "losses": 0, "win_rate": "0%", "profit_factor": "0.0", "max_drawdown": "$0", "net_profit": "$0"}