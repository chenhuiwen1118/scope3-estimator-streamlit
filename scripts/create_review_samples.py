#!/usr/bin/env python3
"""
建立人工審核樣本集

從 Singapore 和 San Francisco 資料集中抽取代表性樣本進行人工審核
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "training_data"

print("=" * 70)
print("  建立人工審核樣本集")
print("=" * 70)

# 讀取兩個資料集
print("\n📥 讀取標註資料...")
sg_file = DATA_DIR / "annotated" / "singapore_annotated_20260129.csv"
sf_file = DATA_DIR / "annotated" / "sf_2020_2024_annotated_20260129.csv"

sg_df = pd.read_csv(sg_file, low_memory=False)
sf_df = pd.read_csv(sf_file, low_memory=False)

print(f"   Singapore: {len(sg_df):,} 筆")
print(f"   San Francisco: {len(sf_df):,} 筆")

# 篩選已成功標註的記錄
sg_annotated = sg_df[sg_df['ghg_category'].notna()].copy()
sf_annotated = sf_df[sf_df['ghg_category'].notna()].copy()

print(f"\n   Singapore 已標註: {len(sg_annotated):,} 筆")
print(f"   SF 已標註: {len(sf_annotated):,} 筆")

# ============================================================================
# 抽樣策略：分層隨機抽樣 (Stratified Random Sampling)
# ============================================================================

def stratified_sample(df, n_samples, source_name):
    """分層抽樣：按 Category 和信心度分層"""

    print(f"\n🎲 {source_name} 分層抽樣...")

    samples = []

    # 按 Category 分層
    for category in [1, 2]:
        cat_df = df[df['ghg_category'] == category].copy()

        if len(cat_df) == 0:
            continue

        # 該 Category 應抽取的樣本數（按比例）
        cat_ratio = len(cat_df) / len(df)
        cat_samples = max(5, int(n_samples * cat_ratio))  # 至少 5 筆

        # 進一步按信心度分層
        cat_df['confidence_bin'] = pd.cut(
            cat_df['ghg_confidence'],
            bins=[0, 0.6, 0.7, 0.8, 0.9, 1.0],
            labels=['<60%', '60-70%', '70-80%', '80-90%', '90-100%']
        )

        # 從每個信心度區間抽樣
        for conf_bin in cat_df['confidence_bin'].unique():
            conf_df = cat_df[cat_df['confidence_bin'] == conf_bin]

            # 該區間應抽取的樣本數
            conf_ratio = len(conf_df) / len(cat_df)
            conf_samples = max(1, int(cat_samples * conf_ratio))
            conf_samples = min(conf_samples, len(conf_df))

            # 隨機抽樣
            sample = conf_df.sample(n=conf_samples, random_state=42)
            samples.append(sample)

            print(f"   Category {category}, {conf_bin}: {conf_samples} 筆")

    result = pd.concat(samples, ignore_index=True)

    # 如果超過目標數量，隨機移除多餘的
    if len(result) > n_samples:
        result = result.sample(n=n_samples, random_state=42)

    # 如果不足目標數量，補充隨機樣本
    if len(result) < n_samples:
        remaining = n_samples - len(result)
        extra = df[~df.index.isin(result.index)].sample(n=remaining, random_state=42)
        result = pd.concat([result, extra], ignore_index=True)

    print(f"   總計: {len(result)} 筆")
    return result

# 從 Singapore 抽取 50 筆
sg_samples = stratified_sample(sg_annotated, 50, "Singapore")

# 從 San Francisco 抽取 50 筆
sf_samples = stratified_sample(sf_annotated, 50, "San Francisco")

# ============================================================================
# 標準化欄位，建立統一審核格式
# ============================================================================

print("\n🔧 標準化審核欄位...")

def prepare_review_format(df, source):
    """準備審核格式"""
    review_df = pd.DataFrame()

    review_df['review_id'] = range(1, len(df) + 1)
    review_df['source'] = source
    review_df['description'] = df['description'].values
    review_df['amount'] = df['amount'].values
    review_df['currency'] = df['currency'].values if 'currency' in df.columns else source.split()[0]
    review_df['organization'] = df.get('organization', '').values
    review_df['supplier'] = df.get('supplier', '').values

    # 自動標註結果
    review_df['auto_category'] = df['ghg_category'].values
    review_df['auto_confidence'] = df['ghg_confidence'].values
    review_df['auto_method'] = df['ghg_method'].values
    review_df['auto_reasoning'] = df['ghg_reasoning'].values
    review_df['auto_is_fixed_asset'] = df['is_fixed_asset'].values

    # 人工審核欄位（待填）
    review_df['human_category'] = ''
    review_df['human_reasoning'] = ''
    review_df['is_correct'] = ''
    review_df['notes'] = ''

    return review_df

sg_review = prepare_review_format(sg_samples, 'Singapore')
sf_review = prepare_review_format(sf_samples, 'San Francisco')

# 合併
review_df = pd.concat([sg_review, sf_review], ignore_index=True)
review_df['review_id'] = range(1, len(review_df) + 1)

# 隨機打亂順序（避免審核者偏見）
review_df = review_df.sample(frac=1, random_state=42).reset_index(drop=True)
review_df['review_id'] = range(1, len(review_df) + 1)

print(f"   總審核樣本: {len(review_df)} 筆")

# ============================================================================
# 儲存審核檔案
# ============================================================================

print("\n💾 儲存審核檔案...")

review_dir = DATA_DIR / "review"
review_dir.mkdir(exist_ok=True)

# 儲存為 CSV
review_file = review_dir / f"review_samples_{datetime.now().strftime('%Y%m%d')}.csv"
review_df.to_csv(review_file, index=False, encoding='utf-8-sig')
print(f"   ✅ {review_file.name}")

# 建立簡化版（只顯示關鍵欄位，方便審核）
simplified_df = review_df[[
    'review_id', 'source', 'description', 'amount', 'currency',
    'auto_category', 'auto_confidence', 'auto_reasoning',
    'human_category', 'human_reasoning', 'is_correct', 'notes'
]].copy()

simplified_file = review_dir / f"review_samples_simplified_{datetime.now().strftime('%Y%m%d')}.csv"
simplified_df.to_csv(simplified_file, index=False, encoding='utf-8-sig')
print(f"   ✅ {review_file.name} (簡化版)")

# ============================================================================
# 統計報告
# ============================================================================

print("\n📊 樣本統計:")

print("\n來源分布:")
print(review_df['source'].value_counts())

print("\n自動標註 Category 分布:")
print(review_df['auto_category'].value_counts())

print("\n信心度分布:")
confidence_bins = pd.cut(
    review_df['auto_confidence'],
    bins=[0, 0.6, 0.7, 0.8, 0.9, 1.0],
    labels=['<60%', '60-70%', '70-80%', '80-90%', '90-100%']
)
print(confidence_bins.value_counts().sort_index())

print("\n金額統計:")
print(f"   平均: ${review_df['amount'].mean():,.2f}")
print(f"   中位數: ${review_df['amount'].median():,.2f}")
print(f"   最大: ${review_df['amount'].max():,.2f}")
print(f"   最小: ${review_df['amount'].min():,.2f}")

print("\n判斷方法分布:")
print(review_df['auto_method'].value_counts())

print("\n" + "=" * 70)
print("  ✅ 審核樣本建立完成！")
print("=" * 70)

print(f"\n📂 輸出檔案:")
print(f"   完整版: {review_file}")
print(f"   簡化版: {simplified_file}")

print("\n📋 下一步:")
print("   1. 開啟審核檔案 (CSV 可用 Excel/Google Sheets 開啟)")
print("   2. 填寫 human_category 欄位 (1 或 2)")
print("   3. 填寫 human_reasoning 欄位（判斷理由）")
print("   4. 填寫 is_correct 欄位 (TRUE/FALSE)")
print("   5. 選填 notes 欄位（額外備註）")
print("   6. 儲存後執行 analyze_review_results.py 分析準確度")
