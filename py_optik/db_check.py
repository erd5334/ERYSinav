import sqlite3
import os

db_path = 'testcevaplari.db3'
if not os.path.exists(db_path):
    print(f"HATA: {db_path} bulunamadı!")
else:
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        print(f"Tablolar: {tables}")
        for table in tables:
            t_name = table[0]
            cur.execute(f"PRAGMA table_info({t_name});")
            cols = cur.fetchall()
            print(f"  {t_name} Sütunları: {[c[1] for c in cols]}")
        conn.close()
    except Exception as e:
        print(f"Hata: {e}")
