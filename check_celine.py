# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)

# 셀린의원 명동점 (id=8) 출고 내역
print('=== 셀린의원 명동점 (id=8) 출고 내역 ===')
rows = conn.execute("""
    SELECT so.id, so.date, p.name, so.quantity, so.discount_rate,
           so.supply_amount, so.vat_amount, so.total_amount, so.note
    FROM stock_out so
    JOIN products p ON so.product_id = p.id
    WHERE so.client_id = 8
    ORDER BY so.date, so.id
""").fetchall()

total_supply = 0
total_vat = 0
total_amount = 0
for r in rows:
    s = r[5] if r[5] else 0
    v = r[6] if r[6] else 0
    t = r[7] if r[7] else 0
    print(f"  id={r[0]} | {r[1]} | {r[2]} | qty={r[3]} | disc={r[4]}% | supply={s:,} | vat={v:,} | total={t:,} | note={r[8]}")
    total_supply += s
    total_vat += v
    total_amount += t

print(f"\n  공급가 합계: {total_supply:,}원")
print(f"  VAT 합계:   {total_vat:,}원")
print(f"  총액 합계:  {total_amount:,}원")

# 셀렌의원 명동점 (id=17)도 있음 - 확인
print('\n=== 셀렌의원 명동점 (id=17) 출고 내역 ===')
rows17 = conn.execute("""
    SELECT so.id, so.date, p.name, so.quantity, so.discount_rate,
           so.supply_amount, so.vat_amount, so.total_amount, so.note
    FROM stock_out so
    JOIN products p ON so.product_id = p.id
    WHERE so.client_id = 17
    ORDER BY so.date, so.id
""").fetchall()

t17 = 0
for r in rows17:
    t = r[7] if r[7] else 0
    print(f"  id={r[0]} | {r[1]} | {r[2]} | qty={r[3]} | total={t:,}")
    t17 += t
print(f"  총액 합계: {t17:,}원")

# products 테이블도 확인
print('\n=== 제품 목록 ===')
products = conn.execute("SELECT id, name, list_price, supply_price FROM products ORDER BY id").fetchall()
for p in products:
    print(f"  id={p[0]} | {p[1]} | 정가={p[2]:,} | 공급가={p[3]:,}")

conn.close()
