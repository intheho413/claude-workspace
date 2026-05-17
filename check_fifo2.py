# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=== 현재 재고 상태 ===")
lots = [
    (8, 77000, "lot#1 (2025-11-28)"),
    (1,     0, "lot#16 (2025-12-29, 0원)"),
]

print("FIFO 순서:")
for qty, price, label in lots:
    print(f"  {label} : {qty}개 @ {price:,}원")

print("\n=== 출고 수량별 FIFO 계산 시뮬레이션 ===")
for sell_qty in [3, 8, 9]:
    remaining = sell_qty
    total_cost = 0
    used = []
    for qty, price, label in lots:
        if remaining <= 0:
            break
        use = min(remaining, qty)
        total_cost += use * price
        used.append(f"{use}개@{price:,}")
        remaining -= use

    avg = total_cost // sell_qty
    print(f"\n  {sell_qty}개 출고:")
    print(f"    FIFO 소비: {' + '.join(used)}")
    print(f"    총 원가: {total_cost:,}원 / 평균 공급가액: {avg:,}원/개")
    납품단가 = 126000 * 0.83  # 예: 17% 할인
    margin = int(납품단가) * sell_qty - avg * sell_qty
    rate = margin / (int(납품단가) * sell_qty) * 100
    print(f"    납품단가 {int(납품단가):,}원 기준 → 마진: {margin:,}원 / 마진율: {rate:.1f}%")

print("\n=== 기존 재고 소진 후, 87,150원 입고 시 ===")
lots2 = [(5, 87150, "신규lot (87,150원)")]
for sell_qty in [3, 5]:
    remaining = sell_qty
    total_cost = 0
    used = []
    for qty, price, label in lots2:
        if remaining <= 0: break
        use = min(remaining, qty)
        total_cost += use * price
        used.append(f"{use}개@{price:,}")
        remaining -= use
    avg = total_cost // sell_qty
    margin = int(납품단가) * sell_qty - avg * sell_qty
    rate = margin / (int(납품단가) * sell_qty) * 100
    print(f"\n  {sell_qty}개 출고: FIFO={' + '.join(used)} | 평균공급가={avg:,} | 마진율={rate:.1f}%")
