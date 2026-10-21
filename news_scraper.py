import requests
import xml.etree.ElementTree as ET
from datetime import datetime

def get_economic_calendar():
    events = []
    try:
        # Menyedut Kalendar ForexFactory secara live (XML Awam)
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            
            for item in root.findall('event'):
                currency = item.find('country').text
                
                # TAPISAN: Hanya ambil kalendar ekonomi Amerika Syarikat (USD)
                if currency == "USD":
                    impact = item.find('impact').text
                    title = item.find('title').text
                    time = item.find('time').text
                    date = item.find('date').text
                    forecast = item.find('forecast').text if item.find('forecast') is not None else "N/A"
                    previous = item.find('previous').text if item.find('previous') is not None else "N/A"
                    
                    events.append({
                        "date": date,
                        "time": time,
                        "currency": currency,
                        "impact": impact,
                        "event": title,
                        "forecast": forecast,
                        "previous": previous
                    })
    except Exception as e:
        print(f"[!] Ralat Kalendar XML: {e}")
        
    return events

def get_news_sentiment_analysis(events):
    # Cari berita AS berimpak tinggi
    high_impact_usd = [e for e in events if e.get('impact') == 'High']
    
    if not high_impact_usd:
        return {
            "sentiment": "NEUTRAL",
            "usd_bias": "RANGING",
            "xau_impact": "MIXED / TECHNICAL",
            "summary": "Tiada data makro AS berimpak tinggi dijadualkan. XAUUSD dijangka bergerak mengikut teknikal tulen. Pasaran selamat untuk entry di zon Pending Order (SBR/RBS)."
        }
    
    # Analisis Sentimen Asas berasaskan Kata Kunci
    event_names = ", ".join([e['event'] for e in high_impact_usd])
    
    hawkish_keywords = ['CPI', 'NFP', 'GDP', 'Retail Sales', 'PMI', 'Fed', 'Powell', 'Interest Rate', 'Employment']
    is_hawkish = any(k.lower() in event_names.lower() for k in hawkish_keywords)
    
    if is_hawkish:
        return {
            "sentiment": "HIGH VOLATILITY",
            "usd_bias": "POTENTIAL HAWKISH (STRONG USD)",
            "xau_impact": "SELL PRESSURE",
            "summary": f"Awas: Pasaran menanti data kritikal AS ({event_names}). Jika data sebenar melebihi ramalan (Forecast), USD akan mengukuh dan menekan XAUUSD ke bawah. Elakkan sebarang entry 15 minit sebelum dan selepas berita dikeluarkan!"
        }
    else:
        return {
            "sentiment": "MODERATE VOLATILITY",
            "usd_bias": "POTENTIAL DOVISH (WEAK USD)",
            "xau_impact": "BUY PRESSURE",
            "summary": f"Perhatian: Data AS ({event_names}) bakal dikeluarkan. Jika data tersasar atau lemah, ia akan melemahkan USD dan memberi ruang untuk XAUUSD meroket ke atas."
        }