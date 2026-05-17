import sqlite3
from pathlib import Path
db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
print("DB exists:", db.exists(), "size:", db.stat().st_size if db.exists() else 0)
conn = sqlite3.connect(db)
for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    tname = row[0]
    cols = conn.execute(f"PRAGMA table_info({tname})").fetchall()
    print(f"--- {tname} ---")
    for c in cols:
        print(f"  {c[1]} {c[2]}")
conn.close()
