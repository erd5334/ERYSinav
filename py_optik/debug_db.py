import sqlite3
import os

db_path = 'testcevaplari.db3'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cur.fetchall()
    print(f"Tables: {tables}")
    for table in tables:
        cur.execute(f"PRAGMA table_info({table[0]})")
        print(f"Table {table[0]} Schema: {cur.fetchall()}")
else:
    print("Database not found")
