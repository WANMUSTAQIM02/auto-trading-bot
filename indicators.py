import pandas as pd

from engine_technical import run_technical_engine
from engine_fundamental import run_fundamental_engine
from engine_sentiment import get_all_timeframe_biases, run_sentiment_engine
from engine_volatility import run_orderblock_volatility_engine

def run_multi_timeframe_analysis(df_m15, news_events=[]):
    try:
        if 'time' in df_m15.columns:
            df_m15['time'] = pd.to_datetime(df_m15['time'])
            df_m15.set_index('time', inplace=True)
        
        close_price = df_m15['close'].iloc[-1]
        
        # Jalankan 4 Modul Fail Enjin Secara Serentak
        tf_biases = get_all_timeframe_biases()
        eng1_tech = run_technical_engine(df_m15)
        eng2_fund = run_fundamental_engine(news_events)
        eng3_sent = run_sentiment_engine(tf_biases)
        eng4_vol  = run_orderblock_volatility_engine(df_m15)

        # Pengiraan Konsensus Menyeluruh Daripada 4 Enjin
        total_pct = int((eng1_tech['pct'] + eng2_fund['pct'] + eng3_sent['pct'] + eng4_vol['pct']) / 4)
        overall_signal = eng1_tech['signal'] if eng1_tech['signal'] != "NEUTRAL" else eng3_sent['signal']

        # Profil Trader Asas Signal
        scalp_signal = eng1_tech['signal']
        intraday_signal = overall_signal
        swing_signal = eng3_sent['signal']

        # --- LOGIK KIRAAN INSTANT ENTRY (MARKET EXECUTION) ---
        atr = eng4_vol.get('atr', 2.0)

        # Fungsi Pengiraan Stop Loss & Take Profit berasaskan Harga Semasa
        def calc_trade(sig, risk_multi):
            ent = close_price # <-- Masuk harga semasa secara INSTANT
            if sig == "BUY":
                sl = ent - (atr * risk_multi)
                tp = ent + (atr * risk_multi * 2) # Risk Reward 1:2
            elif sig == "SELL":
                sl = ent + (atr * risk_multi)
                tp = ent - (atr * risk_multi * 2)
            else:
                sl = ent - (atr * risk_multi)
                tp = ent + (atr * risk_multi * 2)
            return round(ent, 2), round(sl, 2), round(tp, 2)

        # Hasilkan Koordinat Entry, SL, TP (Margin risiko berbeza ikut gaya trader)
        scalp_entry, scalp_sl, scalp_tp = calc_trade(scalp_signal, 1.2)   # Scalp: SL Ketat
        intra_entry, intra_sl, intra_tp = calc_trade(intraday_signal, 2.5) # Intraday: SL Sederhana
        swing_entry, swing_sl, swing_tp = calc_trade(swing_signal, 5.0)    # Swing: SL Longgar

        return {
            "status": "success",
            "h4_trend": tf_biases.get("4h", "NEUTRAL"),
            "m15_rsi": eng1_tech['pct'],
            "momentum_status": "Active Confluence",
            "buy_count": 10, "sell_count": 5, "neutral_count": 5,
            "consensus": {
                "overall_signal": overall_signal,
                "overall_pct": total_pct,
                "engine1": eng1_tech,
                "engine2": eng2_fund,
                "engine3": eng3_sent,
                "engine4": eng4_vol,
            },
            # HANTAR KEPADA UI: Beli/Jual pada harga semasa
            "scalp": {"signal": scalp_signal, "entry": scalp_entry, "sl": scalp_sl, "tp": scalp_tp},
            "intraday": {"signal": intraday_signal, "entry": intra_entry, "sl": intra_sl, "tp": intra_tp},
            "swing": {"signal": swing_signal, "entry": swing_entry, "sl": swing_sl, "tp": swing_tp},
            "signal": intraday_signal,
            "entry": intra_entry,
            "sl": intra_sl,
            "tp1": round(intra_entry + (atr * 2.5) if intraday_signal == "BUY" else intra_entry - (atr * 2.5), 2),
            "tp2": round(intra_entry + (atr * 3.5) if intraday_signal == "BUY" else intra_entry - (atr * 3.5), 2),
            "tp3": round(intra_entry + (atr * 5.0) if intraday_signal == "BUY" else intra_entry - (atr * 5.0), 2),
            "current_price": round(close_price, 2),
            "reason": f"Sistem Instant Entry Aktif. Masuk pasaran pada harga semasa secara terus.",
            "order_blocks": {"bullish": eng4_vol.get('bullish_ob', 'TIADA ZON'), "bearish": eng4_vol.get('bearish_ob', 'TIADA ZON')},
            "tf_biases": tf_biases
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}