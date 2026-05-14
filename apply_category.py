import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "cosmetics.db"
conn = sqlite3.connect(DB_PATH)

conn.execute("UPDATE clients SET category='더데이랩스' WHERE ROUND(discount_rate,2)=0.20")
conn.execute("UPDATE clients SET category='루트스퀘어' WHERE ROUND(discount_rate,2)=0.17")
conn.execute("UPDATE clients SET category='개인병원A'  WHERE ROUND(discount_rate,2)=0.15")
conn.execute("UPDATE clients SET category='개인병원B'  WHERE ROUND(discount_rate,2)=0.10")
conn.commit()

rows = conn.execute("SELECT name, category, ROUND(discount_rate*100,1) FROM clients ORDER BY category, name").fetchall()
print(f"{'대분류':12} | {'할인율':5} | 거래처명")
print("-" * 40)
for r in rows:
    print(f"{r[1]:12} | {r[2]}% | {r[0]}")

conn.close()
print("\nOK: 대분류 일괄 적용 완료")
