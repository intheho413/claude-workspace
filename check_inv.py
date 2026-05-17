import sqlite3
from pathlib import Path
db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)
rows = conn.execute("""
SELECT p.name, COALESCE(SUM(s.remaining_qty),0) as q
FROM products p LEFT JOIN stock_in s ON p.id=s.product_id
GROUP BY p.id ORDER BY q ASC
""").fetchall()
for r in rows:
    low = " [재고부족]" if r[1] < 2 else ""
    print(f"  {r[0]}: {int(r[1])}개{low}")
conn.close()
