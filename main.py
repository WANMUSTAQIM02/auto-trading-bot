import time
import pandas as pd
from indicators import run_multi_timeframe_analysis

def get_mock_live_data():
    # Simulasi data candlestick M15
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200, freq='15min')
    data = {
        'time': dates,
        'open': [2730 + i*0.1 for i in range(200)],
        'high': [2732 + i*0.1 for i in range(200)],
        'low': [2728 + i*0.1 for i in range(200)],
        'close': [2731 + i*0.1 for i in range(200)],
        'volume': [1000 for _ in range(200)]
    }
    return pd.DataFrame(data)

def main_engine():
    print("[*] Sistem Auto-Trading Multi-TF bermula...")
    
    while True:
        print("\n[*] Menjalankan kitaran imbasan pasaran...")
        
        # 1. Tarik data harga terkini
        df = get_mock_live_data()
        
        # 2. Jalankan analisis Multi-TF
        result = run_multi_timeframe_analysis(df)
        
        if result["status"] == "success":
            print(f" > H4 Trend : {result['h4_trend']}")
            print(f" > M15 RSI  : {result['m15_rsi']}")
            print(f" > Signal   : {result['signal']} ({result['reason']})")
        else:
            print(f" [!] Ralat: {result['message']}")
            
        # Rehat selama 15 minit sebelum imbasan seterusnya
        print("[*] Menunggu kitaran seterusnya dalam 15 minit...")
        time.sleep(900) 

if __name__ == "__main__":
    main_engine()