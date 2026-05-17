import sqlite3
from pathlib import Path
db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)
for tbl in ["products","clients","stock_in","stock_out","payments"]:
    cnt = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"{tbl}: {cnt}건")
conn.close()
