#!/usr/bin/env python3
"""
使用改進後的 GHGCategoryClassifier 重新分類審核樣本
"""

import sys
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from classification.ghg_classifier import GHGCategoryClassifier

DATA_DIR = PROJECT_ROOT / "data" / "training_data" / "review"

print("=" * 70)
print("  使用改進後的分類器重新分類審核樣本")
print("=" * 70)

# 讀取原始審核樣本
review_file = DATA_DIR / "review_samples_simplified_20260129.csv"
df = pd.read_csv(review_file, encoding='utf-8-sig')

print(f"\n📥 讀取樣本: {len(df)} 筆")

# 初始化改進後的分類器
print(f"\n🔧 初始化改進後的 GHGCategoryClassifier...")
classifier = GHGCategoryClassifier()

print(f"\n🔍 重新分類...")

new_results = []

for idx, row in df.iterrows():
    description = str(row['description'])
    amount = float(row['amount']) if pd.notna(row['amount']) else None

    # 使用改進後的分類器
    result = classifier.classify(
        item_name=description,
        amount=amount
    )

    new_results.append({
        'review_id': row['review_id'],
        'source': row['source'],
        'description': description,
        'amount': amount,
        'currency': row['currency'],
        'auto_category_new': result['ghg_category'],
        'auto_confidence_new': result['confidence'],
        'auto_method_new': result['method'],
        'auto_reasoning_new': result['reasoning'],
        'auto_category_old': row['auto_category'],
        'auto_confidence_old': row['auto_confidence']
    })

    if (idx + 1) % 20 == 0:
        print(f"   已處理: {idx + 1}/100")

print(f"   已處理: 100/100 ✅")

# 建立對比 DataFrame
comparison_df = pd.DataFrame(new_results)

# 統計變化
changed = (comparison_df['auto_category_new'] != comparison_df['auto_category_old']).sum()
print(f"\n📊 分類變化: {changed} 筆")

# 統計新分類的方法分布
print(f"\n📈 新分類方法分布:")
method_counts = comparison_df['auto_method_new'].value_counts()
for method, count in method_counts.items():
    print(f"   {method}: {count} 筆")

# 統計新分類的 Category 分布
print(f"\n📊 新分類 Category 分布:")
cat_counts = comparison_df['auto_category_new'].value_counts()
for cat, count in cat_counts.items():
    print(f"   Category {cat}: {count} 筆")

# 顯示變化案例
print(f"\n🔄 分類改變的案例 (前 10 筆):")
changed_df = comparison_df[comparison_df['auto_category_new'] != comparison_df['auto_category_old']]

for _, row in changed_df.head(10).iterrows():
    print(f"\n   [{row['review_id']}] {row['description'][:60]}...")
    print(f"      金額: ${row['amount']:,.0f} {row['currency']}")
    print(f"      舊分類: Cat {int(row['auto_category_old'])} | 新分類: Cat {int(row['auto_category_new'])}")
    print(f"      新方法: {row['auto_method_new']}")
    print(f"      理由: {row['auto_reasoning_new'][:80]}")

# 儲存結果
output_file = DATA_DIR / "review_samples_reclassified_20260129.csv"
comparison_df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"\n💾 儲存結果: {output_file.name}")

print("\n" + "=" * 70)
print("  ✅ 重新分類完成！")
print("=" * 70)
