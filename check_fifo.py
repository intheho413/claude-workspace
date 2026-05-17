# -*- coding: utf-8 -*-
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
db = r'C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db'
conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

print("=== 페이셜 클렌저 FIFO 상태 ===")
prod = conn.execute("SELECT id, name, purchase_price FROM products WHERE name LIKE '%클렌저%'").fetchall()
for p in prod:
    print(f"\n제품: {p['name']} | id={p['id']} | 제품관리 공급가={p['purchase_price']:,}원")
    lots = conn.execute(
        'SELECT id, date, quantity, remaining_qty, purchase_price FROM stock_in WHERE product_id=? ORDER BY date ASC',
        (p['id'],)
    ).fetchall()
    print(f"  입고 lots ({len(lots)}건):")
    total_remain = 0
    for lot in lots:
        status = "★ 잔여있음" if lot['remaining_qty'] > 0 else "소진"
        print(f"    lot#{lot['id']} | {lot['date']} | 입고={lot['quantity']}개 | 잔여={lot['remaining_qty']}개 | 단가={lot['purchase_price']:,}원  [{status}]")
        total_remain += lot['remaining_qty']
    print(f"  총 가용재고: {total_remain}개")

print("\n=== FIFO 시뮬레이션 (새 입고 87,150원 5개 추가 가정) ===")
# 현재 잔여 lots
p = conn.execute("SELECT id FROM products WHERE name LIKE '%페이셜%클렌저%'").fetchone()
if p:
    pid = p['id']
    lots = conn.execute(
        'SELECT remaining_qty, purchase_price FROM stock_in WHERE product_id=? AND remaining_qty>0 ORDER BY date ASC',
        (pid,)
    ).fetchall()
    # 87,150짜리 5개 가상 추가
    sim_lots = [(lot['remaining_qty'], lot['purchase_price']) for lot in lots] + [(5, 87150)]
    print("  가상 재고 (기존 + 신규 87,150×5):")
    for qty, price in sim_lots:
        print(f"    잔여={qty}개 @ {price:,}원")
    # 3개 판매 시뮬
    for sell_qty in [3, 10]:
        total_cost, remaining, used = 0, sell_qty, []
        for qty, price in sim_lots:
            if remaining <= 0: break
            use = min(remaining, qty)
            total_cost += use * price
            used.append(f"{use}개@{price:,}")
            remaining -= use
        if remaining > 0:
            print(f"\n  {sell_qty}개 판매 → 재고 부족")
        else:
            avg = total_cost // sell_qty
            print(f"\n  {sell_qty}개 판매 → FIFO 사용: {' + '.join(used)} | 평균공급가={avg:,}원")

conn.close()
