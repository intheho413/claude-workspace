import sqlite3
from pathlib import Path
conn = sqlite3.connect(Path("data/cosmetics.db"))
cur = conn.execute("UPDATE products SET min_stock=2 WHERE name LIKE '%PHA물톡스%' OR name LIKE '%물톡스%'")
conn.commit()
rows = conn.execute("SELECT name, min_stock FROM products ORDER BY name").fetchall()
for r in rows:
    print(f"{r[0]:30} | 최소재고: {r[1]}")
conn.close()
