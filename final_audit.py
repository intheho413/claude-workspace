# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)

print("=" * 70)
print("최종 검수 결과")
print("=" * 70)

# 1. 거래처 이름 검증
print("\n[1] 거래처 목록 검증")
expected_clients = {
    "세라미크 강남":      ("루트스퀘어", 0.17),
    "벨리셀의원":         ("루트스퀘어", 0.17),
    "온리프 성형외과":    ("비네트워크", 0.10),
    "리진의원":           ("비네트워크", 0.10),
    "셀린의원 수원망포":  ("루트스퀘어", 0.17),
    "데이뷰 안양점":      ("더데이랩스", 0.20),
    "셀린의원 연신내점":  ("루트스퀘어", 0.17),
    "셀린의원 명동점":    ("루트스퀘어", 0.17),
    "셀린의원 하남미사점":("루트스퀘어", 0.17),
    "데이뷰 명동점":      ("더데이랩스", 0.20),
    "힐세리온 의원":      ("비네트워크", 0.17),
    "셀린의원 청주점":    ("루트스퀘어", 0.17),
    "데이뷰 광주상무점":  ("더데이랩스", 0.20),
    "셀린의원 다산점":    ("루트스퀘어", 0.17),
    "셀린의원 수원점":    ("루트스퀘어", 0.17),
    "셀린의원 홍대점":    ("루트스퀘어", 0.17),
    "셀렌의원 명동점":    ("루트스퀘어", 0.17),
}
db_clients = {r[1]: (r[2], r[3]) for r in conn.execute("SELECT id, name, category, discount_rate FROM clients ORDER BY id")}
ok = True
for name, (cat, disc) in expected_clients.items():
    if name in db_clients:
        db_cat, db_disc = db_clients[name]
        disc_ok = abs(db_disc - disc) < 0.001
        if disc_ok:
            print(f"  ✓ {name} (할인율 {db_disc:.0%})")
        else:
            print(f"  ✗ {name} 할인율 오류: 기대={disc:.0%} 실제={db_disc:.0%}")
            ok = False
    else:
        print(f"  ✗ '{name}' 없음")
        ok = False

if ok:
    print("  → 거래처 데이터 모두 정상 ✓")

# 2. 출고 공급가 검증 (스프레드시트 기준)
print("\n[2] 거래처별 출고 공급가 합계 검증")
sheet_totals = {
    "세라미크 강남":       1288285,
    "벨리셀의원":          1660249,
    "온리프 성형외과":     735300,
    "리진의원":            735300,
    "셀린의원 수원망포":   166000,
    "데이뷰 안양점":       1620800,
    "셀린의원 연신내점":   495925,
    "셀린의원 명동점":     1542970,
    "셀린의원 하남미사점": 468950,
    "데이뷰 명동점":       127600,
    "힐세리온 의원":       513770,
    "셀린의원 청주점":     671885,
    "데이뷰 광주상무점":   1190200,
    "셀린의원 다산점":     650305,
    "셀린의원 수원점":     254810,
    "셀린의원 홍대점":     527880,
    "셀렌의원 명동점":     281370,
}
db_totals = {r[0]: r[1] for r in conn.execute("""
    SELECT c.name, SUM(o.supply_amount)
    FROM stock_out o JOIN clients c ON o.client_id=c.id
    WHERE o.type='출고' GROUP BY c.name
""")}

grand_sheet = 0
grand_db = 0
all_ok = True
for name, s_amt in sheet_totals.items():
    db_amt = db_totals.get(name, 0)
    diff = db_amt - s_amt
    grand_sheet += s_amt
    grand_db += db_amt
    if abs(diff) <= 1:
        print(f"  ✓ {name}: ₩{s_amt:,}")
    else:
        print(f"  ✗ {name}: 시트={s_amt:,} / DB={db_amt:,} | 차이={diff:+,}")
        all_ok = False

print(f"\n  전체 합계: 시트={grand_sheet:,} / DB={grand_db:,} | 차이={grand_db-grand_sheet:+,}")
if all_ok:
    print("  → 전체 공급가 데이터 정상 (1원 반올림 차이 무시) ✓")

# 3. 셀린의원 명동점 상세
print("\n[3] 셀린의원 명동점 상세 검증")
rows = conn.execute("""
    SELECT o.date, p.name, o.quantity, o.supply_amount
    FROM stock_out o JOIN products p ON o.product_id=p.id
    WHERE o.client_id=8 ORDER BY o.date, o.id
""").fetchall()
total = sum(r[3] for r in rows)
print(f"  총 {len(rows)}건 | 공급가 합계: ₩{total:,} ← 스프레드시트 ₩1,542,970 {'✓' if total==1542970 else '✗'}")

# 4. 재고 현황
print("\n[4] 현재 재고 현황")
stocks = conn.execute("""
    SELECT p.name, COALESCE(SUM(s.remaining_qty),0) as 재고
    FROM products p
    LEFT JOIN stock_in s ON p.id=s.product_id
    GROUP BY p.id ORDER BY p.name
""").fetchall()
for s in stocks:
    warn = " ⚠ 재고 부족" if s[1] < 2 else ""
    print(f"  {s[0]}: {int(s[1])}개{warn}")

print("\n" + "=" * 70)
print("검수 완료")
print("=" * 70)
conn.close()
