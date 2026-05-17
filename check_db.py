import sqlite3
from pathlib import Path
db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)
print("=== 테이블별 레코드 수 ===")
for t in ["products","clients","stock_in","stock_out","payments"]:
    n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t}: {n}건")

print("\n=== 매출 요약 ===")
r = conn.execute("SELECT COUNT(*), COALESCE(SUM(total_amount),0), COALESCE(SUM(margin_amount),0) FROM stock_out WHERE type='출고'").fetchone()
print(f"  출고: {r[0]}건 / 총매출: {r[1]:,.0f}원 / 총마진: {r[2]:,.0f}원")

print("\n=== 거래처별 미수금 TOP5 ===")
rows = conn.execute("""
SELECT c.name, COALESCE(SUM(o.total_amount),0)-COALESCE(SUM(p.amount),0) as recv
FROM clients c
LEFT JOIN stock_out o ON c.id=o.client_id AND o.type='출고'
LEFT JOIN payments p ON c.id=p.client_id
GROUP BY c.id HAVING recv>0 ORDER BY recv DESC LIMIT 5
""").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]:,.0f}원")

print("\n=== 제품별 현재고 ===")
rows = conn.execute("""
SELECT p.name, COALESCE(SUM(s.remaining_qty),0) as q
FROM products p LEFT JOIN stock_in s ON p.id=s.product_id
GROUP BY p.id ORDER BY q ASC
""").fetchall()
for r in rows:
    flag = " ⚠" if r[1] < 2 else ""
    print(f"  {r[0]}: {int(r[1])}개{flag}")
conn.close()
