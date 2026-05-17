# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)

# 1. 데이뷰 안양점 블루 벨벳 마스크 (id=35) 롤백: 원래 198,000원 (20% 할인, 99,000×2)
fifo_unit = conn.execute("SELECT fifo_purchase_price FROM stock_out WHERE id=35").fetchone()[0]
fifo_cost = fifo_unit * 2
supply35  = 198000   # 원래 정상값 (99,000 × 2)
vat35     = round(supply35 * 0.1)
total35   = supply35 + vat35
margin35  = supply35 - fifo_cost
rate35    = (margin35 / supply35 * 100) if supply35 > 0 else 0
conn.execute("UPDATE stock_out SET supply_amount=?,vat_amount=?,total_amount=?,margin_amount=?,margin_rate=? WHERE id=35",
             (supply35, vat35, total35, margin35, rate35))
print(f"id=35 데이뷰 안양점 롤백: supply={supply35:,} | vat={vat35:,} | total={total35:,}")

# 2. 벨리셀의원(id=20) / 힐세리온(id=45) 블루 벨벳 마스크 ×2 정확히 수정
# 스프레드시트: 205,425원 (= 102,712.5 × 2, 단가가 소수점이라 합계로 맞춤)
for oid in [20, 45]:
    row = conn.execute("SELECT quantity, fifo_purchase_price, client_id FROM stock_out WHERE id=?", (oid,)).fetchone()
    qty, fifo_unit, cid = row
    fifo_cost = fifo_unit * qty
    new_supply = 205425
    new_vat    = round(new_supply * 0.1)
    new_total  = new_supply + new_vat
    new_margin = new_supply - fifo_cost
    new_rate   = (new_margin / new_supply * 100) if new_supply > 0 else 0
    conn.execute("UPDATE stock_out SET supply_amount=?,vat_amount=?,total_amount=?,margin_amount=?,margin_rate=? WHERE id=?",
                 (new_supply, new_vat, new_total, new_margin, new_rate, oid))
    client = conn.execute("SELECT name FROM clients WHERE id=?", (cid,)).fetchone()[0]
    print(f"id={oid} {client} 수정: supply={new_supply:,} | vat={new_vat:,} | total={new_total:,}")

conn.commit()

# 최종 확인
total_supply = conn.execute("SELECT SUM(supply_amount) FROM stock_out WHERE type='출고'").fetchone()[0]
print(f"\n최종 전체 공급가 합계: {total_supply:,}원 ← 목표 12,931,599원 {'✓' if total_supply==12931599 else f'✗ 차이={total_supply-12931599:+}'}")

# 거래처별 재확인
print("\n[거래처별 공급가 최종 확인]")
sheet_totals = {
    "세라미크 강남": 1288285, "벨리셀의원": 1660249, "온리프 성형외과": 735300,
    "리진의원": 735300, "셀린의원 수원망포": 166000, "데이뷰 안양점": 1620800,
    "셀린의원 연신내점": 495925, "셀린의원 명동점": 1542970, "셀린의원 하남미사점": 468950,
    "데이뷰 명동점": 127600, "힐세리온 의원": 513770, "셀린의원 청주점": 671885,
    "데이뷰 광주상무점": 1190200, "셀린의원 다산점": 650305, "셀린의원 수원점": 254810,
    "셀린의원 홍대점": 527880, "셀렌의원 명동점": 281370,
}
db_map = dict(conn.execute("""
    SELECT c.name, SUM(o.supply_amount)
    FROM stock_out o JOIN clients c ON o.client_id=c.id
    WHERE o.type='출고' GROUP BY c.name
""").fetchall())

all_ok = True
for name, s_amt in sheet_totals.items():
    db_amt = db_map.get(name, 0)
    diff = db_amt - s_amt
    if abs(diff) > 0:
        print(f"  ✗ {name}: 시트={s_amt:,} / DB={db_amt:,} | 차이={diff:+}")
        all_ok = False
    else:
        print(f"  ✓ {name}: ₩{s_amt:,}")
if all_ok:
    print("  → 전체 일치 ✓")

conn.close()
