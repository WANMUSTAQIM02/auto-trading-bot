def run_fundamental_engine(news_events):
    try:
        high_impact = [e for e in news_events if e.get('impact') == 'High']
        if len(high_impact) > 0:
            return {"name": "Fundamental", "signal": "NEUTRAL", "pct": 65}
        return {"name": "Fundamental", "signal": "BUY", "pct": 75}
    except Exception:
        return {"name": "Fundamental", "signal": "NEUTRAL", "pct": 60}