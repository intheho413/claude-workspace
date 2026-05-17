# -*- coding: utf-8 -*-
import sqlite3
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

db = Path(r"C:\Users\inho4\OneDrive\바탕 화면\claude\2.TheSC-MSO 사이트\data\cosmetics.db")
conn = sqlite3.connect(db)

print("=== DB 데이터 수정 ===\n")

# 1. 거래처 이름 및 할인율 수정
fixes = [
    # (id, 수정 내용, 기존값, 신규값)
    (1, "이름", "세라미크의원 강남", "세라미크 강남"),
    (1, "카테고리", "더데이랩스", "루트스퀘어"),
    (1, "할인율", 0.20, 0.17),
    (2, "카테고리", "더데이랩스", "루트스퀘어"),
    (2, "할인율", 0.20, 0.17),
    (3, "이름", "온리프성형외과", "온리프 성형외과"),
]

# 거래처 이름 수정
conn.execute("UPDATE clients SET name='세라미크 강남', category='루트스퀘어', discount_rate=0.17 WHERE id=1")
print("✓ id=1 세라미크의원 강남 → 세라미크 강남 / 카테고리: 더데이랩스 → 루트스퀘어 / 할인율: 20% → 17%")

conn.execute("UPDATE clients SET category='루트스퀘어', discount_rate=0.17 WHERE id=2")
print("✓ id=2 벨리셀의원 카테고리: 더데이랩스 → 루트스퀘어 / 할인율: 20% → 17%")

conn.execute("UPDATE clients SET name='온리프 성형외과' WHERE id=3")
print("✓ id=3 온리프성형외과 → 온리프 성형외과")

# 2. stock_out의 discount_rate도 수정 (id=1 거래처 출고분: 0.17로)
r1 = conn.execute("UPDATE stock_out SET discount_rate=0.17 WHERE client_id=1 AND discount_rate!=0.17").rowcount
print(f"✓ stock_out id=1(세라미크 강남) 할인율 수정: {r1}건")

r2 = conn.execute("UPDATE stock_out SET discount_rate=0.17 WHERE client_id=2 AND discount_rate!=0.17").rowcount
print(f"✓ stock_out id=2(벨리셀의원) 할인율 수정: {r2}건")

conn.commit()

# 3. 검증 출력
print("\n=== 수정 결과 검증 ===")
clients = conn.execute("SELECT id, name, category, discount_rate FROM clients ORDER BY id").fetchall()
for c in clients:
    print(f"  id={c[0]} | {c[1]} | {c[2]} | 할인율={c[3]:.0%}")

# 4. 셀린의원 명동점 최종 확인
print("\n=== 셀린의원 명동점 출고 현황 (공급가 기준) ===")
rows = conn.execute("""
    SELECT o.date, p.name, o.quantity, o.supply_amount, o.total_amount
    FROM stock_out o
    JOIN products p ON o.product_id=p.id
    WHERE o.client_id=8
    ORDER BY o.date, o.id
""").fetchall()
s_total = 0
for r in rows:
    print(f"  {r[0]} | {r[1]} | ×{r[2]} | 공급가={r[3]:,} | 총액(VAT포함)={r[4]:,}")
    s_total += r[3]
print(f"\n  공급가 합계: {s_total:,}원 ← 스프레드시트 합계 ₩1,542,970원과 {'✓ 일치' if s_total==1542970 else '✗ 불일치'}")

# 5. 전체 거래처별 공급가 합계
print("\n=== 전체 거래처별 공급가 합계 (스프레드시트 기준) ===")
sheet_totals = {
    "세라미크 강남": 1288285,
    "벨리셀의원": 1660249,
    "온리프 성형외과": 735300,
    "리진의원": 735300,
    "셀린의원 수원망포": 166000,
    "데이뷰 안양점": 1620800,
    "셀린의원 연신내점": 495925,
    "셀린의원 명동점": 1542970,
    "셀린의원 하남미사점": 468950,
    "데이뷰 명동점": 127600,
    "힐세리온 의원": 513770,
    "셀린의원 청주점": 671885,
    "데이뷰 광주상무점": 1190200,
    "셀렌의원 명동점": 281370,
}
db_totals = conn.execute("""
    SELECT c.name, SUM(o.supply_amount)
    FROM stock_out o JOIN clients c ON o.client_id=c.id
    WHERE o.type='출고'
    GROUP BY c.id, c.name
""").fetchall()
db_map = dict(db_totals)

for name, s_amt in sheet_totals.items():
    db_amt = db_map.get(name, 0)
    diff = db_amt - s_amt
    status = "✓" if abs(diff) <= 1 else f"✗ 차이={diff:+,}"
    print(f"  {name}: 시트={s_amt:,} / DB={db_amt:,} {status}")

conn.close()
print("\n=== 데이터 수정 완료 ===")
