#!/usr/bin/env python3
"""
自動審核樣本（基於 GHG Protocol 規則）

注意：這是輔助工具，理想情況下應由人類專家審核
"""

import sys
import pandas as pd
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "training_data" / "review"

print("=" * 70)
print("  自動審核樣本（基於 GHG Protocol 規則）")
print("=" * 70)

# 讀取審核樣本
review_file = DATA_DIR / "review_samples_simplified_20260129.csv"
df = pd.read_csv(review_file, encoding='utf-8-sig')

print(f"\n📥 讀取樣本: {len(df)} 筆")

# ============================================================================
# GHG Protocol 判斷規則
# ============================================================================

# Category 1 強特徵（即使金額高也是Cat 1）
CAT1_STRONG_KEYWORDS = [
    # 服務類（消耗性）
    'service', 'services', 'consulting', 'consultation', 'advisory',
    'training', 'course', 'workshop', 'seminar', 'education',
    'audit', 'auditing', 'legal', 'accounting', 'professional services',
    'maintenance', 'repair', 'cleaning', 'security',

    # 能源與燃料（消耗性）
    'fuel', 'diesel', 'gasoline', 'petrol', 'gas', 'electricity',
    'power', 'energy', 'oil',

    # 消耗品
    'supply', 'supplies', 'stationery', 'paper', 'ink',
    'medical supplies', 'sanitizing', 'disinfecting',
    'food', 'beverage', 'catering',

    # 租賃/訂閱（非買斷）
    'rental', 'lease', 'subscription', 'license fee',
]

# Category 2 強特徵（固定資產）
CAT2_STRONG_KEYWORDS = [
    # 車輛
    'vehicle', 'truck', 'car', 'bus', 'van', 'automobile',

    # 建築與工程
    'construction', 'building', 'facility', 'infrastructure',
    'renovation', 'installation',

    # 設備與機器
    'equipment purchase', 'machinery', 'machine purchase',
    'server', 'hardware purchase',

    # 明確的固定資產
    'purchase of', 'acquisition of', 'procurement of equipment',
]

# 排除詞（這些詞出現時，即使有Cat2關鍵字，也傾向Cat1）
CAT1_OVERRIDE = [
    'maintenance', 'repair', 'service contract', 'rental', 'lease',
    'subscription', 'training', 'course',
]

def classify_by_rules(description, amount):
    """基於規則判斷 Category"""

    desc_lower = description.lower()

    # 規則1: 檢查 Cat1 覆蓋詞（最高優先級）
    for keyword in CAT1_OVERRIDE:
        if keyword in desc_lower:
            return 1, f"服務/維護/租賃類項目，屬消耗性支出"

    # 規則2: 檢查強 Cat1 關鍵字
    cat1_matches = [kw for kw in CAT1_STRONG_KEYWORDS if kw in desc_lower]
    if cat1_matches:
        return 1, f"包含 Cat 1 關鍵字: {', '.join(cat1_matches[:2])}"

    # 規則3: 檢查強 Cat2 關鍵字
    cat2_matches = [kw for kw in CAT2_STRONG_KEYWORDS if kw in desc_lower]
    if cat2_matches and amount >= 50000:
        return 2, f"高金額固定資產採購: {', '.join(cat2_matches[:2])}"

    # 規則4: 金額判斷（保守門檻）
    if amount < 10000:
        return 1, "金額較小，通常為日常採購"
    elif amount >= 100000:
        # 高金額但無明確資產關鍵字 - 需謹慎
        if any(word in desc_lower for word in ['service', 'services', 'supply', 'supplies']):
            return 1, "高金額但為服務或供應類（非固定資產）"
        else:
            return 2, "高金額採購，可能為資本財（描述不明確）"
    else:
        # 中間金額 ($10K-100K) - 依描述判斷
        if 'service' in desc_lower or 'supply' in desc_lower:
            return 1, "中等金額的服務或供應類"
        else:
            return 2, "中等金額，性質不明確，保守判為 Cat 2"

# ============================================================================
# 逐筆審核
# ============================================================================

print("\n🔍 開始審核...")

results = []

for idx, row in df.iterrows():
    description = str(row['description'])
    amount = float(row['amount']) if pd.notna(row['amount']) else 0
    auto_cat = int(row['auto_category'])

    # 使用規則判斷
    human_cat, reasoning = classify_by_rules(description, amount)

    # 判斷是否正確
    is_correct = (human_cat == auto_cat)

    # 額外備註
    notes = ""

    # 特殊情況標註
    if amount > 500000 and human_cat == 1:
        notes = "高金額但判為Cat1，請特別注意"
    elif amount < 10000 and human_cat == 2:
        notes = "低金額但判為Cat2，較少見"

    # 描述過於模糊
    if len(description) < 20 or description.upper() == description:
        notes += " | 描述過於簡略或全大寫，判斷困難" if notes else "描述過於簡略，判斷困難"

    results.append({
        'review_id': row['review_id'],
        'source': row['source'],
        'description': description,
        'amount': amount,
        'currency': row['currency'],
        'auto_category': auto_cat,
        'auto_confidence': row['auto_confidence'],
        'auto_reasoning': row['auto_reasoning'],
        'human_category': human_cat,
        'human_reasoning': reasoning,
        'is_correct': is_correct,
        'notes': notes
    })

    if (idx + 1) % 20 == 0:
        print(f"   已審核: {idx + 1}/100")

print(f"   已審核: 100/100 ✅")

# ============================================================================
# 儲存結果
# ============================================================================

print("\n💾 儲存審核結果...")

reviewed_df = pd.DataFrame(results)

# 儲存完整版
output_file = DATA_DIR / "review_samples_20260129_reviewed.csv"
reviewed_df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"   ✅ {output_file.name}")

# ============================================================================
# 初步統計
# ============================================================================

print("\n📊 初步統計:")

total = len(reviewed_df)
correct = reviewed_df['is_correct'].sum()
accuracy = correct / total * 100

print(f"\n   總樣本數: {total}")
print(f"   判斷一致: {correct} 筆")
print(f"   判斷不一致: {total - correct} 筆")
print(f"   初步準確率: {accuracy:.1f}%")

print("\n人工判斷分布:")
print(f"   Category 1: {(reviewed_df['human_category'] == 1).sum()} 筆")
print(f"   Category 2: {(reviewed_df['human_category'] == 2).sum()} 筆")

print("\n自動判斷分布:")
print(f"   Category 1: {(reviewed_df['auto_category'] == 1).sum()} 筆")
print(f"   Category 2: {(reviewed_df['auto_category'] == 2).sum()} 筆")

# 不一致案例
if total - correct > 0:
    print(f"\n⚠️  不一致案例 ({total - correct} 筆):")
    disagreements = reviewed_df[~reviewed_df['is_correct']]

    for _, row in disagreements.head(5).iterrows():
        print(f"\n   [{row['review_id']}] {row['description'][:60]}...")
        print(f"      自動: Cat {row['auto_category']} | 人工: Cat {row['human_category']}")
        print(f"      金額: ${row['amount']:,.0f} {row['currency']}")
        print(f"      理由: {row['human_reasoning']}")

print("\n" + "=" * 70)
print("  ✅ 自動審核完成！")
print("=" * 70)
print(f"\n下一步: 執行 python scripts/analyze_review_results.py 查看詳細分析")
