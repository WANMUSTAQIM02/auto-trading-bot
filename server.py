import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import yfinance as yf
from database import init_db, log_signal, update_trade_status, get_win_rate_stats
from indicators import run_multi_timeframe_analysis
from news_scraper import get_economic_calendar, get_news_sentiment_analysis
from backtester import run_historical_backtest

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Kembali kepada simbol stabil yfinance untuk mengelakkan ralat 404
SYMBOL = "GC=F"

session = requests.Session()
session.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

latest_status = {
    "status": "waiting",
    "current_price": "0.00",
    "h4_trend": "NEUTRAL",
    "m15_rsi": 0.0,
    "buy_count": 0,
    "sell_count": 0,
    "neutral_count": 0,
    "b_pct": 33,
    "n_pct": 34,
    "s_pct": 33,
    "gauge_status": "Neutral",
    "signal": "WAIT",
    "entry": 0.0,
    "sl": 0.0,
    "tp1": 0.0,
    "tp2": 0.0,
    "tp3": 0.0,
    "consensus": {
        "overall_signal": "WAIT",
        "overall_pct": "0%",
        "engines": [
            {"id": 1, "name": "Teknikal", "signal": "WAIT", "pct_str": "0%"},
            {"id": 2, "name": "Fundamental", "signal": "WAIT", "pct_str": "0%"},
            {"id": 3, "name": "Sentimen", "signal": "WAIT", "pct_str": "0%"},
            {"id": 4, "name": "Volatiliti & OB", "signal": "WAIT", "pct_str": "0%"}
        ]
    },
    "scalp": {"signal": "WAIT", "entry": 0.0, "sl": 0.0, "tp": 0.0},
    "intraday": {"signal": "WAIT", "entry": 0.0, "sl": 0.0, "tp": 0.0},
    "swing": {"signal": "WAIT", "entry": 0.0, "sl": 0.0, "tp": 0.0},
    "reason": "Memuat analisis pasaran sebenar...",
    "sessions": {"tokyo": "CLOSED", "london": "CLOSED", "new_york": "CLOSED"},
    "tf_matrix": {
        "1m": "NEUTRAL", "5m": "NEUTRAL", "15m": "NEUTRAL",
        "30m": "NEUTRAL", "1h": "NEUTRAL", "4h": "NEUTRAL",
        "1d": "NEUTRAL", "1w": "NEUTRAL", "1mn": "NEUTRAL"
    },
    "order_blocks": {"bullish": "TIADA ZON", "bearish": "TIADA ZON"},
    "win_rate": {"total": 0, "tp": 0, "sl": 0, "active": 0, "rate": "0%", "recent": []},
    "backtest": {"total": 0, "wins": 0, "losses": 0, "win_rate": "0%", "profit_factor": "0.0", "max_drawdown": "$0", "net_profit": "$0"},
    "news_calendar": [],
    "news_analysis": {
        "sentiment": "NEUTRAL",
        "usd_bias": "MEMUATKAN...",
        "xau_impact": "MEMUATKAN...",
        "summary": "Menyedut data kalendar makro AS terkini..."
    },
    "last_updated": "Baru sahaja bermula"
}

def check_market_sessions():
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour
    return {
        "tokyo": "OPEN" if 0 <= hour < 9 else "CLOSED",
        "london": "OPEN" if 8 <= hour < 16 else "CLOSED",
        "new_york": "OPEN" if 13 <= hour < 21 else "CLOSED"
    }

def get_real_live_data():
    try:
        ticker = yf.Ticker(SYMBOL, session=session)
        df = ticker.history(period="5d", interval="15m")
        if df.empty:
            return None
        df.reset_index(inplace=True)
        time_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
        df = df.rename(columns={time_col: 'time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        return df[['time', 'open', 'high', 'low', 'close', 'volume']]
    except Exception as e:
        print(f"[!] Ralat Data Live yfinance: {e}")
        return None

async def background_trading_engine():
    global latest_status
    init_db()
    print("[*] Menjalankan Analisis Backtest Sejarah 1 Tahun Penuh...")
    backtest_results = run_historical_backtest(SYMBOL)
    print("[*] Backtest Selesai!")
    
    while True:
        calendar_events = get_economic_calendar()
        sentiment_data = get_news_sentiment_analysis(calendar_events)
        sessions = check_market_sessions()
        df = get_real_live_data()
        
        if df is not None:
            result = run_multi_timeframe_analysis(df, calendar_events)
            
            if result.get("status") == "success":
                current_price = result["current_price"]
                update_trade_status(current_price)
                
                if result["signal"] != "WAIT":
                    log_signal(result["signal"], result["entry"], result["sl"], result["tp1"], result["tp2"], result["tp3"])
                
                win_stats = get_win_rate_stats()
                
                total_t = result["buy_count"] + result["sell_count"] + result["neutral_count"]
                total_t = total_t if total_t > 0 else 1
                b_pct = int((result["buy_count"] / total_t) * 100)
                n_pct = int((result["neutral_count"] / total_t) * 100)
                s_pct = 100 - b_pct - n_pct
                
                c_data = result.get("consensus", {})
                e1 = c_data.get("engine1", {"name": "Teknikal", "signal": "NEUTRAL", "pct": 50})
                e2 = c_data.get("engine2", {"name": "Fundamental", "signal": "NEUTRAL", "pct": 50})
                e3 = c_data.get("engine3", {"name": "Sentimen", "signal": "NEUTRAL", "pct": 50})
                e4 = c_data.get("engine4", {"name": "Zon SnD & SnR", "signal": "NEUTRAL", "pct": 50})

                engines_list = [
                    {"id": 1, "name": "Teknikal", "signal": e1.get("signal", "NEUTRAL"), "pct_str": f"{e1.get('pct', 50)}%"},
                    {"id": 2, "name": "Fundamental", "signal": e2.get("signal", "NEUTRAL"), "pct_str": f"{e2.get('pct', 50)}%"},
                    {"id": 3, "name": "Sentimen", "signal": e3.get("signal", "NEUTRAL"), "pct_str": f"{e3.get('pct', 50)}%"},
                    {"id": 4, "name": "Zon SnD & SnR", "signal": e4.get("signal", "NEUTRAL"), "pct_str": f"{e4.get('pct', 50)}%"}
                ]

                latest_status = {
                    "status": "success",
                    "current_price": f"{current_price:.2f}",
                    "h4_trend": result["h4_trend"],
                    "m15_rsi": result["m15_rsi"],
                    "buy_count": result["buy_count"],
                    "sell_count": result["sell_count"],
                    "neutral_count": result["neutral_count"],
                    "b_pct": b_pct,
                    "n_pct": n_pct,
                    "s_pct": s_pct,
                    "gauge_status": result["momentum_status"],
                    "signal": result["signal"],
                    "entry": result["entry"],
                    "sl": result["sl"],
                    "tp1": result["tp1"],
                    "tp2": result["tp2"],
                    "tp3": result["tp3"],
                    "consensus": {
                        "overall_signal": c_data.get("overall_signal", "NEUTRAL"),
                        "overall_pct": f"{c_data.get('overall_pct', 50)}%",
                        "engines": engines_list
                    },
                    "scalp": result["scalp"],
                    "intraday": result["intraday"],
                    "swing": result["swing"],
                    "reason": result["reason"],
                    "sessions": sessions,
                    "tf_matrix": result["tf_biases"],
                    "order_blocks": result["order_blocks"],
                    "win_rate": win_stats,
                    "backtest": backtest_results,
                    "news_calendar": calendar_events,
                    "news_analysis": sentiment_data,
                    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_trading_engine())

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "index.html", {"data": latest_status})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)