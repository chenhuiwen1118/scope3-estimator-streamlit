#!/usr/bin/env python3
"""
比較分類結果與人工審核結果，計算準確度
"""

import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "training_data" / "review"

print("=" * 70)
print("  分類準確度分析")
print("=" * 70)

# 讀取人工審核結果（ground truth）
reviewed_file = DATA_DIR / "review_samples_20260129_reviewed.csv"
reviewed_df = pd.read_csv(reviewed_file, encoding='utf-8-sig')

# 讀取自動分類結果
reclassified_file = DATA_DIR / "review_samples_reclassified_20260129.csv"
reclassified_df = pd.read_csv(reclassified_file, encoding='utf-8-sig')

# 合併資料
merged = reviewed_df.merge(
    reclassified_df[['review_id', 'auto_category_new', 'auto_confidence_new', 'auto_method_new', 'auto_reasoning_new']],
    on='review_id',
    how='inner'
)

print(f"\n📊 資料統計:")
print(f"   人工審核樣本: {len(reviewed_df)} 筆")
print(f"   自動分類樣本: {len(reclassified_df)} 筆")
print(f"   可比較樣本: {len(merged)} 筆")

# 計算準確度
correct = (merged['human_category'] == merged['auto_category_new']).sum()
accuracy = correct / len(merged) * 100

print(f"\n✅ 整體準確度: {correct}/{len(merged)} = {accuracy:.1f}%")

# 按 Category 計算準確度
print(f"\n📈 各類別準確度:")
for cat in [1, 2]:
    cat_df = merged[merged['human_category'] == cat]
    cat_correct = (cat_df['human_category'] == cat_df['auto_category_new']).sum()
    cat_accuracy = cat_correct / len(cat_df) * 100 if len(cat_df) > 0 else 0
    print(f"   Category {cat}: {cat_correct}/{len(cat_df)} = {cat_accuracy:.1f}%")

# 分類方法分布
print(f"\n🔍 分類方法分布:")
method_counts = merged['auto_method_new'].value_counts()
for method, count in method_counts.items():
    pct = count / len(merged) * 100
    print(f"   {method}: {count} 筆 ({pct:.1f}%)")

# 錯誤案例分析
print(f"\n❌ 錯誤案例分析 ({len(merged) - correct} 筆):")
errors = merged[merged['human_category'] != merged['auto_category_new']].copy()

# 按錯誤類型分組
cat1_to_cat2 = errors[errors['human_category'] == 1]  # False Positive (誤判為資本財)
cat2_to_cat1 = errors[errors['human_category'] == 2]  # False Negative (誤判為購買商品)

print(f"\n   Type 1: 應為 Cat 1，誤判為 Cat 2 (False Positive): {len(cat1_to_cat2)} 筆")
if len(cat1_to_cat2) > 0:
    print(f"   常見原因:")
    reason_counts = cat1_to_cat2['auto_method_new'].value_counts()
    for reason, count in reason_counts.items():
        print(f"      - {reason}: {count} 筆")

    print(f"\n   典型案例:")
    for idx, row in cat1_to_cat2.head(5).iterrows():
        print(f"\n   [{row['review_id']}] {row['description'][:60]}...")
        print(f"      金額: ${row['amount']:,.0f} {row['currency']}")
        print(f"      人工: Cat {int(row['human_category'])} | 自動: Cat {int(row['auto_category_new'])}")
        print(f"      方法: {row['auto_method_new']}")
        print(f"      理由: {row['auto_reasoning_new'][:80]}")

print(f"\n   Type 2: 應為 Cat 2，誤判為 Cat 1 (False Negative): {len(cat2_to_cat1)} 筆")
if len(cat2_to_cat1) > 0:
    print(f"   常見原因:")
    reason_counts = cat2_to_cat1['auto_method_new'].value_counts()
    for reason, count in reason_counts.items():
        print(f"      - {reason}: {count} 筆")

    print(f"\n   典型案例:")
    for idx, row in cat2_to_cat1.head(5).iterrows():
        print(f"\n   [{row['review_id']}] {row['description'][:60]}...")
        print(f"      金額: ${row['amount']:,.0f} {row['currency']}")
        print(f"      人工: Cat {int(row['human_category'])} | 自動: Cat {int(row['auto_category_new'])}")
        print(f"      方法: {row['auto_method_new']}")
        print(f"      理由: {row['auto_reasoning_new'][:80]}")

# 比較改進前後
print(f"\n📊 改進效果比較:")
print(f"   改進前準確度: 71% (29 筆錯誤)")
print(f"   改進後準確度: {accuracy:.1f}% ({len(merged) - correct} 筆錯誤)")
improvement = accuracy - 71
print(f"   改進幅度: {improvement:+.1f} 百分點")

# 輸出詳細錯誤報告
error_report = errors[['review_id', 'description', 'amount', 'currency',
                        'human_category', 'auto_category_new',
                        'auto_method_new', 'auto_reasoning_new']].copy()
error_report.columns = ['ID', '描述', '金額', '幣別', '人工分類', '自動分類', '方法', '理由']

output_file = DATA_DIR / "classification_errors_20260129.csv"
error_report.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n💾 詳細錯誤報告已儲存: {output_file.name}")

print("\n" + "=" * 70)
print(f"  ✅ 分析完成！準確度: {accuracy:.1f}%")
print("=" * 70)
