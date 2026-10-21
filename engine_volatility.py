import numpy as np
import pandas as pd

def run_orderblock_volatility_engine(df):
    try:
        # Analisis 100 lilin terakhir untuk nampak zon struktur yang jelas
        recent_df = df.tail(100).copy().reset_index(drop=True)
        current_price = recent_df['close'].iloc[-1]
        
        bullish_ob_str = "TIADA ZON"
        bearish_ob_str = "TIADA ZON"
        demand_zone = current_price
        supply_zone = current_price
        ob_score = 50
        
        # 1. RBR / DBR (BULLISH OB / DEMAND ZONE)
        for i in range(len(recent_df) - 3, 2, -1):
            if recent_df.loc[i, 'close'] < recent_df.loc[i, 'open']: # Bearish candle (Base)
                if recent_df.loc[i+1, 'close'] > recent_df.loc[i, 'high'] and recent_df.loc[i+2, 'close'] > recent_df.loc[i+1, 'close']: # Rally
                    bullish_ob_str = f"${recent_df.loc[i, 'low']:.2f} - ${recent_df.loc[i, 'high']:.2f}"
                    demand_zone = recent_df.loc[i, 'high'] # Entry pada bucu atas base
                    ob_score = 75
                    break
                    
        # 2. DBD / RBD (BEARISH OB / SUPPLY ZONE)
        for i in range(len(recent_df) - 3, 2, -1):
            if recent_df.loc[i, 'close'] > recent_df.loc[i, 'open']: # Bullish candle (Base)
                if recent_df.loc[i+1, 'close'] < recent_df.loc[i, 'low'] and recent_df.loc[i+2, 'close'] < recent_df.loc[i+1, 'close']: # Drop
                    bearish_ob_str = f"${recent_df.loc[i, 'low']:.2f} - ${recent_df.loc[i, 'high']:.2f}"
                    supply_zone = recent_df.loc[i, 'low'] # Entry pada bucu bawah base
                    ob_score = 75
                    break

        # 3. RBS & SBR (Resistance Become Support & Support Become Resistance)
        # Cari Swing High (Resistance) dan Swing Low (Support)
        recent_df['swing_high'] = recent_df['high'] == recent_df['high'].rolling(window=9, center=True).max()
        recent_df['swing_low'] = recent_df['low'] == recent_df['low'].rolling(window=9, center=True).min()
        
        resistances = recent_df[recent_df['swing_high']]['high'].tolist()
        supports = recent_df[recent_df['swing_low']]['low'].tolist()
        
        # RBS: Resistance lama yang dah dipecahkan, sekarang duduk BAWAH harga semasa
        rbs_levels = [r for r in resistances if r < current_price]
        best_rbs = max(rbs_levels) if rbs_levels else demand_zone
        
        # SBR: Support lama yang dah dipecahkan, sekarang duduk ATAS harga semasa
        sbr_levels = [s for s in supports if s > current_price]
        best_sbr = min(sbr_levels) if sbr_levels else supply_zone
        
        # Tentukan Entry Limit Terbaik
        # BUY mestilah harga BAWAH harga semasa (pilih paling selamat antara RBS atau Demand)
        best_buy_entry = min(best_rbs, demand_zone, current_price - 0.5) 
        
        # SELL mestilah harga ATAS harga semasa (pilih paling selamat antara SBR atau Supply)
        best_sell_entry = max(best_sbr, supply_zone, current_price + 0.5)

        # Kira volatiliti ATR (Average True Range) untuk pengurusan risiko
        tr = np.maximum(recent_df['high'] - recent_df['low'], np.maximum(abs(recent_df['high'] - recent_df['close'].shift(1)), abs(recent_df['low'] - recent_df['close'].shift(1))))
        atr = tr.rolling(window=14).mean().iloc[-1]
        volatility_status = "BULLISH" if ob_score >= 75 else "NEUTRAL"

        return {
            "name": "Zon SnD & SnR",
            "signal": volatility_status,
            "pct": ob_score,
            "bullish_ob": bullish_ob_str,
            "bearish_ob": bearish_ob_str,
            "best_buy_entry": best_buy_entry,
            "best_sell_entry": best_sell_entry,
            "atr": atr
        }
    except Exception as e:
        print(f"[!] Ralat SnD/SnR: {e}")
        return {"name": "Zon SnD & SnR", "signal": "NEUTRAL", "pct": 50, "bullish_ob": "TIADA DATA", "bearish_ob": "TIADA DATA", "best_buy_entry": 0, "best_sell_entry": 0, "atr": 2.0}