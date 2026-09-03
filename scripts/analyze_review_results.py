#!/usr/bin/env python3
"""
分析人工審核結果

計算自動標註準確率，分析錯誤模式，提供改進建議
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "training_data" / "review"

print("=" * 70)
print("  人工審核結果分析")
print("=" * 70)

# 讀取審核結果
print("\n📥 讀取審核結果...")

# 嘗試尋找最新的審核檔案
review_files = list(DATA_DIR.glob("review_samples_*_reviewed.csv"))
if not review_files:
    # 如果沒有 _reviewed 檔案，嘗試原始檔案
    review_files = list(DATA_DIR.glob("review_samples_simplified_*.csv"))

if not review_files:
    print("❌ 找不到審核檔案！")
    print(f"   請將審核完成的檔案放在: {DATA_DIR}")
    sys.exit(1)

# 使用最新的檔案
review_file = sorted(review_files)[-1]
print(f"   使用檔案: {review_file.name}")

df = pd.read_csv(review_file, encoding='utf-8-sig')
print(f"   總記錄數: {len(df)}")

# 檢查必要欄位
required_cols = ['human_category', 'is_correct']
missing_cols = [col for col in required_cols if col not in df.columns]

if missing_cols:
    print(f"\n❌ 缺少必要欄位: {missing_cols}")
    print("   請確保已填寫 human_category 和 is_correct 欄位")
    sys.exit(1)

# 檢查完成度
completed = df['human_category'].notna().sum()
total = len(df)
completion_rate = completed / total * 100

print(f"\n📊 審核完成度: {completed}/{total} ({completion_rate:.1f}%)")

if completed < total:
    print(f"   ⚠️  尚有 {total - completed} 筆未完成審核")
    print("   以下分析僅基於已完成的 {completed} 筆")

# 篩選已完成的審核
df_completed = df[df['human_category'].notna()].copy()

# 轉換類型
df_completed['auto_category'] = df_completed['auto_category'].astype(int)
df_completed['human_category'] = df_completed['human_category'].astype(int)

# 計算 is_correct（如果未填寫）
if df_completed['is_correct'].isna().any():
    print("\n🔄 自動計算 is_correct 欄位...")
    df_completed['is_correct'] = (
        df_completed['auto_category'] == df_completed['human_category']
    )

# 確保 is_correct 是布林值
df_completed['is_correct'] = df_completed['is_correct'].map({
    True: True, 'TRUE': True, 'true': True, 'True': True, 1: True, '1': True,
    False: False, 'FALSE': False, 'false': False, 'False': False, 0: False, '0': False
})

# ============================================================================
# 整體準確率
# ============================================================================

print("\n" + "=" * 70)
print("  整體準確率")
print("=" * 70)

accuracy = df_completed['is_correct'].sum() / len(df_completed) * 100
correct_count = df_completed['is_correct'].sum()
total_count = len(df_completed)

print(f"\n✅ 自動標註準確率: {accuracy:.1f}% ({correct_count}/{total_count})")

if accuracy >= 90:
    print("   🎉 優秀！自動標註效能良好")
elif accuracy >= 80:
    print("   👍 良好！仍有改進空間")
elif accuracy >= 70:
    print("   ⚠️  尚可，需要改進")
else:
    print("   ❌ 較低，需要重大改進")

# ============================================================================
# 按 Category 分析
# ============================================================================

print("\n" + "=" * 70)
print("  按 Category 分析")
print("=" * 70)

for cat in [1, 2]:
    cat_df = df_completed[df_completed['human_category'] == cat]

    if len(cat_df) == 0:
        print(f"\nCategory {cat}: 無資料")
        continue

    cat_correct = cat_df['is_correct'].sum()
    cat_total = len(cat_df)
    cat_accuracy = cat_correct / cat_total * 100

    print(f"\n📊 Category {cat}:")
    print(f"   樣本數: {cat_total}")
    print(f"   正確數: {cat_correct}")
    print(f"   準確率: {cat_accuracy:.1f}%")

    # 誤判情況
    cat_wrong = cat_df[~cat_df['is_correct']]
    if len(cat_wrong) > 0:
        print(f"   ❌ 誤判: {len(cat_wrong)} 筆")
        print(f"      → 誤判為 Category {3-cat} 的案例")

# ============================================================================
# 按信心度分析
# ============================================================================

print("\n" + "=" * 70)
print("  按信心度分析")
print("=" * 70)

df_completed['confidence_bin'] = pd.cut(
    df_completed['auto_confidence'],
    bins=[0, 0.6, 0.7, 0.8, 0.9, 1.0],
    labels=['<60%', '60-70%', '70-80%', '80-90%', '90-100%']
)

for conf_bin in ['<60%', '60-70%', '70-80%', '80-90%', '90-100%']:
    conf_df = df_completed[df_completed['confidence_bin'] == conf_bin]

    if len(conf_df) == 0:
        continue

    conf_correct = conf_df['is_correct'].sum()
    conf_total = len(conf_df)
    conf_accuracy = conf_correct / conf_total * 100

    print(f"\n🎯 信心度 {conf_bin}:")
    print(f"   樣本數: {conf_total}")
    print(f"   準確率: {conf_accuracy:.1f}%")

# ============================================================================
# 按資料來源分析
# ============================================================================

print("\n" + "=" * 70)
print("  按資料來源分析")
print("=" * 70)

for source in df_completed['source'].unique():
    source_df = df_completed[df_completed['source'] == source]
    source_correct = source_df['is_correct'].sum()
    source_total = len(source_df)
    source_accuracy = source_correct / source_total * 100

    print(f"\n📍 {source}:")
    print(f"   樣本數: {source_total}")
    print(f"   準確率: {source_accuracy:.1f}%")

# ============================================================================
# 按金額範圍分析
# ============================================================================

print("\n" + "=" * 70)
print("  按金額範圍分析")
print("=" * 70)

df_completed['amount_bin'] = pd.cut(
    df_completed['amount'],
    bins=[0, 1000, 10000, 30000, 100000, float('inf')],
    labels=['<$1K', '$1K-10K', '$10K-30K', '$30K-100K', '>$100K']
)

for amount_bin in ['<$1K', '$1K-10K', '$10K-30K', '$30K-100K', '>$100K']:
    amount_df = df_completed[df_completed['amount_bin'] == amount_bin]

    if len(amount_df) == 0:
        continue

    amount_correct = amount_df['is_correct'].sum()
    amount_total = len(amount_df)
    amount_accuracy = amount_correct / amount_total * 100

    print(f"\n💰 {amount_bin}:")
    print(f"   樣本數: {amount_total}")
    print(f"   準確率: {amount_accuracy:.1f}%")

# ============================================================================
# 混淆矩陣
# ============================================================================

print("\n" + "=" * 70)
print("  混淆矩陣 (Confusion Matrix)")
print("=" * 70)

from collections import defaultdict

confusion = defaultdict(int)
for _, row in df_completed.iterrows():
    confusion[(row['auto_category'], row['human_category'])] += 1

print("\n                  人工判斷")
print("              Category 1  Category 2")
print(f"自動  Category 1    {confusion[(1, 1)]:3d}         {confusion[(1, 2)]:3d}")
print(f"標註  Category 2    {confusion[(2, 1)]:3d}         {confusion[(2, 2)]:3d}")

# ============================================================================
# 常見錯誤案例
# ============================================================================

print("\n" + "=" * 70)
print("  常見錯誤案例")
print("=" * 70)

wrong_df = df_completed[~df_completed['is_correct']].copy()

if len(wrong_df) > 0:
    print(f"\n總錯誤數: {len(wrong_df)}")

    # 誤判為 Category 1 的案例（實際是 Category 2）
    false_cat1 = wrong_df[
        (wrong_df['auto_category'] == 1) & (wrong_df['human_category'] == 2)
    ]

    if len(false_cat1) > 0:
        print(f"\n❌ 誤判為 Category 1（實際為 Category 2）: {len(false_cat1)} 筆")
        print("   典型案例（前 3 筆）:")
        for idx, row in false_cat1.head(3).iterrows():
            print(f"   - [{row['review_id']}] {row['description'][:60]}...")
            print(f"     金額: ${row['amount']:,.0f} {row['currency']}")
            print(f"     人工理由: {row.get('human_reasoning', 'N/A')[:80]}")

    # 誤判為 Category 2 的案例（實際是 Category 1）
    false_cat2 = wrong_df[
        (wrong_df['auto_category'] == 2) & (wrong_df['human_category'] == 1)
    ]

    if len(false_cat2) > 0:
        print(f"\n❌ 誤判為 Category 2（實際為 Category 1）: {len(false_cat2)} 筆")
        print("   典型案例（前 3 筆）:")
        for idx, row in false_cat2.head(3).iterrows():
            print(f"   - [{row['review_id']}] {row['description'][:60]}...")
            print(f"     金額: ${row['amount']:,.0f} {row['currency']}")
            print(f"     人工理由: {row.get('human_reasoning', 'N/A')[:80]}")

else:
    print("\n🎉 沒有錯誤！所有自動標註都正確！")

# ============================================================================
# 改進建議
# ============================================================================

print("\n" + "=" * 70)
print("  改進建議")
print("=" * 70)

recommendations = []

# 建議 1: 金額門檻
if len(false_cat2) > 0:
    avg_false_cat2_amount = false_cat2['amount'].mean()
    print(f"\n💡 建議 1: 調整金額門檻")
    print(f"   目前門檻: $30,000")
    print(f"   誤判為 Cat 2 的平均金額: ${avg_false_cat2_amount:,.0f}")
    if avg_false_cat2_amount < 50000:
        print(f"   建議: 考慮提高門檻至 $50,000 或 $75,000")
    recommendations.append("調整金額門檻")

# 建議 2: 關鍵字規則
print(f"\n💡 建議 2: 加強關鍵字匹配")
print(f"   目前方法: 主要依賴 amount_threshold (100%)")
print(f"   建議: 增加關鍵字規則庫，提高 keyword method 使用率")
recommendations.append("加強關鍵字規則")

# 建議 3: 服務合約判斷
service_keywords = ['service', 'services', 'consulting', 'training', 'audit', 'legal']
if len(false_cat2) > 0:
    service_errors = false_cat2[
        false_cat2['description'].str.lower().str.contains('|'.join(service_keywords), na=False)
    ]
    if len(service_errors) > 0:
        print(f"\n💡 建議 3: 改進服務合約判斷")
        print(f"   發現 {len(service_errors)} 筆服務類誤判為 Category 2")
        print(f"   建議: 添加服務類別專用規則（優先判為 Category 1）")
        recommendations.append("改進服務合約判斷")

# 建議 4: 人工審核擴大
if completed < 1000:
    print(f"\n💡 建議 4: 擴大人工審核規模")
    print(f"   目前審核: {completed} 筆")
    print(f"   建議: 擴大至 1,000-2,000 筆建立 Gold Standard")
    recommendations.append("擴大人工審核至 1,000+ 筆")

# ============================================================================
# 儲存分析報告
# ============================================================================

print("\n" + "=" * 70)
print("  儲存分析報告")
print("=" * 70)

report_file = DATA_DIR / f"review_analysis_{datetime.now().strftime('%Y%m%d')}.txt"

with open(report_file, 'w', encoding='utf-8') as f:
    f.write("=" * 70 + "\n")
    f.write("  人工審核結果分析報告\n")
    f.write("=" * 70 + "\n")
    f.write(f"\n分析日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    f.write(f"審核檔案: {review_file.name}\n")
    f.write(f"\n整體準確率: {accuracy:.1f}% ({correct_count}/{total_count})\n")
    f.write(f"\n按 Category 準確率:\n")
    for cat in [1, 2]:
        cat_df = df_completed[df_completed['human_category'] == cat]
        if len(cat_df) > 0:
            cat_accuracy = cat_df['is_correct'].sum() / len(cat_df) * 100
            f.write(f"  Category {cat}: {cat_accuracy:.1f}% ({len(cat_df)} 筆)\n")

    f.write(f"\n改進建議:\n")
    for i, rec in enumerate(recommendations, 1):
        f.write(f"  {i}. {rec}\n")

print(f"\n✅ 分析報告已儲存: {report_file.name}")

print("\n" + "=" * 70)
print("  ✅ 分析完成！")
print("=" * 70)
