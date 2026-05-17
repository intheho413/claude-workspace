# -*- coding: utf-8 -*-
import sqlite3, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')

db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

records = conn.execute("""
    SELECT o.id, o.quantity, o.discount_rate, o.fifo_purchase_price,
           COALESCE(NULLIF(p.settlement_price,0), p.sale_price) as base_p
    FROM stock_out o JOIN products p ON o.product_id=p.id
    WHERE o.type='출고'
""").fetchall()

updated = 0
skipped = 0
for r in records:
    oid, qty, disc, fifo, sale_p = r["id"], r["quantity"], r["discount_rate"], r["fifo_purchase_price"], r["base_p"]
    if not sale_p or sale_p <= 0:
        skipped += 1
        continue
    new_납품금액 = int(sale_p * qty * (1 - disc))
    new_공급가액 = (fifo or 0) * qty
    new_margin   = new_납품금액 - new_공급가액
    new_rate     = (new_margin / new_납품금액 * 100) if new_납품금액 > 0 else 0
    conn.execute("""
        UPDATE stock_out SET supply_amount=?, vat_amount=0, total_amount=?,
            margin_amount=?, margin_rate=? WHERE id=?
    """, (new_납품금액, new_납품금액, new_margin, new_rate, oid))
    updated += 1

conn.commit()

# 결과 확인
total_sales = conn.execute("SELECT SUM(total_amount) FROM stock_out WHERE type='출고'").fetchone()[0]
total_supply = conn.execute("SELECT SUM(supply_amount) FROM stock_out WHERE type='출고'").fetchone()[0]
avg_margin = conn.execute("SELECT AVG(margin_rate) FROM stock_out WHERE type='출고'").fetchone()[0]

print(f"재계산 완료: {updated}건 업데이트, {skipped}건 스킵(납품가 미등록)")
print(f"납품금액 합계(VAT포함): {total_sales:,.0f}원")
print(f"supply_amount 합계:     {total_supply:,.0f}원")
print(f"supply == total: {'✓' if total_sales == total_supply else '✗'}")
print(f"평균 마진율: {avg_margin:.1f}%")

# total_amount=0 잔여 확인
zero_cnt = conn.execute("SELECT COUNT(*) FROM stock_out WHERE type='출고' AND total_amount=0").fetchone()[0]
print(f"total_amount=0 잔여: {zero_cnt}건 {'✓' if zero_cnt==0 else '⚠ 확인 필요'}")

conn.close()
