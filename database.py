import sqlite3
from datetime import datetime

DB_NAME = "trading_data.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal TEXT,
            entry REAL,
            sl REAL,
            tp1 REAL,
            tp2 REAL,
            tp3 REAL,
            status TEXT DEFAULT 'ACTIVE',
            tp_hit TEXT DEFAULT '-',
            created_at TIMESTAMP,
            closed_at TIMESTAMP
        )
    ''')
    
    cursor.execute("PRAGMA table_info(signals)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'tp_hit' not in columns:
        cursor.execute("ALTER TABLE signals ADD COLUMN tp1 REAL DEFAULT 0")
        cursor.execute("ALTER TABLE signals ADD COLUMN tp2 REAL DEFAULT 0")
        cursor.execute("ALTER TABLE signals ADD COLUMN tp3 REAL DEFAULT 0")
        cursor.execute("ALTER TABLE signals ADD COLUMN tp_hit TEXT DEFAULT '-'")
        cursor.execute("ALTER TABLE signals ADD COLUMN created_at TIMESTAMP")
        cursor.execute("ALTER TABLE signals ADD COLUMN closed_at TIMESTAMP")
        
    conn.commit()
    conn.close()

def log_signal(signal, entry, sl, tp1, tp2, tp3):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # ANTI-SPAM: Kalau dah ada arah yang sama (contoh: BUY) sedang RUNNING, jangan buka order baru!
    cursor.execute("SELECT id FROM signals WHERE status IN ('ACTIVE', 'RUNNING') AND signal = ?", (signal,))
    if not cursor.fetchone():
        # INSTANT ENTRY: Status terus masuk sebagai RUNNING, bukan ACTIVE/PENDING
        cursor.execute('''
            INSERT INTO signals (signal, entry, sl, tp1, tp2, tp3, status, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, 'RUNNING', ?)
        ''', (signal, float(entry), float(sl), float(tp1), float(tp2), float(tp3), now_str))
        
    conn.commit()
    conn.close()

def update_trade_status(current_price):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, signal, entry, sl, tp1, tp2, tp3, status FROM signals WHERE status IN ('ACTIVE', 'RUNNING')")
    active_trades = cursor.fetchall()
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    current_price = float(current_price)
    
    for trade in active_trades:
        t_id, sig, ent, sl, tp1, tp2, tp3, current_status = trade
        new_status = current_status
        tp_hit = '-'
        closed_time = None
        
        # Fasa 1 (Sekiranya ada rekod lama yang masih ACTIVE tersangkut di pangkalan data)
        if current_status == 'ACTIVE':
            if sig == 'BUY' and current_price <= ent:
                new_status = 'RUNNING'
            elif sig == 'SELL' and current_price >= ent:
                new_status = 'RUNNING'
                
        # Fasa 2: Semak TP/SL untuk order yang RUNNING (Instant Entry terus masuk fasa ini)
        if new_status == 'RUNNING':
            if sig == 'BUY':
                if current_price <= sl:
                    new_status = 'SL'
                    closed_time = now_str
                elif tp3 > 0 and current_price >= tp3:
                    new_status = 'TP'
                    tp_hit = 'TP3'
                    closed_time = now_str
                elif tp2 > 0 and current_price >= tp2:
                    new_status = 'TP'
                    tp_hit = 'TP2'
                    closed_time = now_str
                elif tp1 > 0 and current_price >= tp1:
                    new_status = 'TP'
                    tp_hit = 'TP1'
                    closed_time = now_str
                    
            elif sig == 'SELL':
                if current_price >= sl:
                    new_status = 'SL'
                    closed_time = now_str
                elif tp3 > 0 and current_price <= tp3:
                    new_status = 'TP'
                    tp_hit = 'TP3'
                    closed_time = now_str
                elif tp2 > 0 and current_price <= tp2:
                    new_status = 'TP'
                    tp_hit = 'TP2'
                    closed_time = now_str
                elif tp1 > 0 and current_price <= tp1:
                    new_status = 'TP'
                    tp_hit = 'TP1'
                    closed_time = now_str
                    
        # Kemas kini jika berubah
        if new_status != current_status:
            if new_status in ['TP', 'SL']:
                cursor.execute("UPDATE signals SET status = ?, tp_hit = ?, closed_at = ? WHERE id = ?", (new_status, tp_hit, closed_time, t_id))
            else:
                cursor.execute("UPDATE signals SET status = ? WHERE id = ?", (new_status, t_id))
            
    conn.commit()
    conn.close()

def get_win_rate_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM signals")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM signals WHERE status = 'TP'")
    tp = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM signals WHERE status = 'SL'")
    sl = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM signals WHERE status IN ('ACTIVE', 'RUNNING')")
    active = cursor.fetchone()[0]
    
    rate = f"{(tp / (tp + sl) * 100):.1f}%" if (tp + sl) > 0 else "0.0%"
    
    cursor.execute("SELECT signal, entry, status, tp_hit, created_at, closed_at FROM signals ORDER BY id DESC LIMIT 15")
    recent_raw = cursor.fetchall()
    conn.close()
    
    recent = []
    for r in recent_raw:
        sig, ent, stat, tp_hit, created_at, closed_at = r
        duration_str = "Menunggu..."
        time_str = "Baru"
        
        if created_at:
            try:
                fmt = "%Y-%m-%d %H:%M:%S"
                c_time = datetime.strptime(created_at, fmt)
                time_str = c_time.strftime("%d/%m %H:%M")
                
                if closed_at:
                    x_time = datetime.strptime(closed_at, fmt)
                    delta = x_time - c_time
                    minutes = int(delta.total_seconds() / 60)
                    if minutes < 60:
                        duration_str = f"{minutes} min"
                    else:
                        duration_str = f"{minutes // 60}j {minutes % 60}m"
                else:
                    delta = datetime.now() - c_time
                    minutes = int(delta.total_seconds() / 60)
                    if minutes < 60:
                        duration_str = f"{minutes} min (Aktif)"
                    else:
                        duration_str = f"{minutes // 60}j {minutes % 60}m (Aktif)"
            except Exception:
                pass
        
        recent.append({
            "signal": sig,
            "entry": ent,
            "status": stat,
            "tp_hit": tp_hit,
            "time": time_str,
            "duration": duration_str
        })
        
    return {
        "total": total,
        "tp": tp,
        "sl": sl,
        "active": active,
        "rate": rate,
        "recent": recent
    }