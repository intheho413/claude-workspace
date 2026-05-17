# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)

print("=== payments 테이블 ===")
pays = conn.execute("SELECT * FROM payments").fetchall()
print(f"  결제 건수: {len(pays)}건")
for p in pays:
    print(f"  {p}")

print("\n=== 현재 cosmetics.py 미수금 KPI 쿼리 결과 (JOIN 버전) ===")
v = conn.execute("""
    SELECT COALESCE(SUM(o.supply_amount),0)-COALESCE(SUM(p.amount),0) as v
    FROM stock_out o LEFT JOIN payments p ON p.client_id=o.client_id
    WHERE o.type='출고'
""").fetchone()[0]
print(f"  JOIN 버전: {v:,}원")

print("\n=== 올바른 계산 (서브쿼리) ===")
total_supply = conn.execute("SELECT SUM(supply_amount) FROM stock_out WHERE type='출고'").fetchone()[0]
total_pay    = conn.execute("SELECT COALESCE(SUM(amount),0) FROM payments").fetchone()[0]
print(f"  총 공급가: {total_supply:,}원")
print(f"  총 수금액: {total_pay:,}원")
print(f"  실제 미수금: {total_supply - total_pay:,}원")

print("\n=== 공급가 상세 (스프레드시트 2원 차이 확인) ===")
rows = conn.execute("""
    SELECT c.name, p.name, o.quantity, o.supply_amount
    FROM stock_out o
    JOIN clients c ON o.client_id=c.id
    JOIN products p ON o.product_id=p.id
    WHERE p.name='블루 벨벳 마스크'
    ORDER BY o.date
""").fetchall()
for r in rows:
    print(f"  {r[0]} | {r[1]} ×{r[2]} | 공급가={r[3]:,}")

conn.close()
