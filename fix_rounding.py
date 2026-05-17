# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)

# 블루 벨벳 마스크 ×2 레코드 확인 (벨리셀의원, 힐세리온 의원)
rows = conn.execute("""
    SELECT o.id, c.name, o.quantity, o.supply_amount, o.vat_amount, o.total_amount,
           o.fifo_purchase_price, o.margin_amount, o.margin_rate
    FROM stock_out o
    JOIN clients c ON o.client_id=c.id
    JOIN products p ON o.product_id=p.id
    WHERE p.name='블루 벨벳 마스크' AND o.quantity=2
""").fetchall()

print("수정 전:")
for r in rows:
    print(f"  id={r[0]} | {r[1]} | qty={r[2]} | supply={r[3]:,} | vat={r[4]:,} | total={r[5]:,} | fifo={r[6]:,} | margin={r[7]:,} | rate={r[8]:.2f}%")

print()
for r in rows:
    oid = r[0]
    # 스프레드시트 기준: 205,425원 (= 102,712.5 × 2, 소수점 절사)
    new_supply = 205425
    new_vat    = round(new_supply * 0.1)       # 20,543
    new_total  = new_supply + new_vat           # 225,968
    fifo_cost  = r[6] * r[2]                   # fifo단가 × 수량
    new_margin = new_supply - fifo_cost
    new_rate   = (new_margin / new_supply * 100) if new_supply > 0 else 0

    conn.execute("""
        UPDATE stock_out
        SET supply_amount=?, vat_amount=?, total_amount=?, margin_amount=?, margin_rate=?
        WHERE id=?
    """, (new_supply, new_vat, new_total, new_margin, new_rate, oid))
    print(f"수정: id={oid} | supply {r[3]:,} → {new_supply:,} | vat {r[4]:,} → {new_vat:,} | total {r[5]:,} → {new_total:,}")

conn.commit()

# 최종 공급가 합계 확인
total = conn.execute("SELECT SUM(supply_amount) FROM stock_out WHERE type='출고'").fetchone()[0]
print(f"\n최종 전체 공급가 합계: {total:,}원 ← 목표 12,931,599원과 {'✓ 일치' if total==12931599 else f'✗ 차이={total-12931599:+}'}")

conn.close()
