#!/usr/bin/env python3
"""
San Francisco 採購資料處理腳本（2020-2024 年）

使用 chunking 方式處理大檔案，篩選 2020-2024 年資料
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# 加入 src 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from classification.ghg_classifier import GHGCategoryClassifier

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "training_data"

print("="*70)
print("  San Francisco 採購資料處理（2020-2024）")
print("="*70)

# 1. 使用 chunking 讀取並篩選資料
print("\n📥 讀取並篩選 2020-2024 年資料...")
sf_file = DATA_DIR / "raw" / "kaggle" / "sf_procurement" / "Purchasing_Commodity_Data.csv"

if not sf_file.exists():
    print(f"❌ 找不到檔案: {sf_file}")
    sys.exit(1)

# 使用 chunking 讀取
chunk_size = 100000
chunks = []
total_processed = 0
filtered_count = 0

print(f"   使用 chunking 讀取（每批 {chunk_size:,} 筆）...")

for i, chunk in enumerate(pd.read_csv(sf_file, chunksize=chunk_size, low_memory=False)):
    total_processed += len(chunk)

    # 篩選 2020-2024 年
    chunk_filtered = chunk[chunk['Fiscal Year'] >= 2020]
    filtered_count += len(chunk_filtered)

    if len(chunk_filtered) > 0:
        chunks.append(chunk_filtered)

    if (i + 1) % 10 == 0:
        print(f"   已處理 {total_processed:,} 筆，篩選出 {filtered_count:,} 筆")

print(f"\n   總處理筆數: {total_processed:,}")
print(f"   篩選後筆數: {filtered_count:,} ({filtered_count/total_processed*100:.1f}%)")

# 合併所有 chunks
print("\n🔀 合併篩選結果...")
df = pd.concat(chunks, ignore_index=True)
print(f"   合併後筆數: {len(df):,}")

# 2. 標準化欄位
print("\n🔧 標準化欄位...")
df = df.rename(columns={
    'Commodity Title': 'description',
    'Encumbered Amount': 'amount',
    'Supplier & Other Non-Supplier Payees': 'supplier',
    'Post Date - Current': 'date',
    'Fiscal Year': 'fiscal_year',
    'Commodity Code': 'commodity_code',
    'Purchasing Department Title': 'organization'
})

# 3. 清理資料
print("\n🧹 清理資料...")

# 移除空描述
before = len(df)
df = df[df['description'].notna()]
df = df[df['description'].str.len() > 0]
after = len(df)
print(f"   移除 {before - after:,} 筆空描述")

# 清理文字
df['description'] = df['description'].str.strip()

# 標準化金額
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

# 移除負金額或零金額
before = len(df)
df = df[df['amount'] > 0]
after = len(df)
print(f"   移除 {before - after:,} 筆無效金額")

# 加入來源
df['source'] = 'kaggle_sf_procurement_2020_2024'
df['currency'] = 'USD'
df['processed_at'] = datetime.now().isoformat()

print(f"   清理後記錄數: {len(df):,}")

# 4. 儲存處理後資料
print("\n💾 儲存處理後資料...")
processed_dir = DATA_DIR / "processed"
processed_dir.mkdir(parents=True, exist_ok=True)

processed_file = processed_dir / "sf_procurement_2020_2024_processed.csv"
df.to_csv(processed_file, index=False, encoding='utf-8')
print(f"   ✅ {processed_file.name}")

# 5. GHG 分類標註
print(f"\n🏷️  執行 GHG 分類標註...")
print(f"   總記錄數: {len(df):,}")

classifier = GHGCategoryClassifier()

# 準備標註欄位
df['ghg_category'] = None
df['ghg_confidence'] = None
df['ghg_method'] = None
df['ghg_reasoning'] = None
df['is_fixed_asset'] = None

annotated = 0
errors = 0

for idx, row in df.iterrows():
    if annotated % 5000 == 0 and annotated > 0:
        print(f"   已標註: {annotated:,}/{len(df):,} ({annotated/len(df)*100:.1f}%)")

    try:
        result = classifier.classify(
            item_name=row['description'],
            amount=row.get('amount', None)
        )

        df.at[idx, 'ghg_category'] = result['ghg_category']
        df.at[idx, 'ghg_confidence'] = result['confidence']
        df.at[idx, 'ghg_method'] = result['method']
        df.at[idx, 'ghg_reasoning'] = result['reasoning']
        df.at[idx, 'is_fixed_asset'] = result['is_fixed_asset']

        annotated += 1
    except Exception as e:
        errors += 1
        if errors < 10:
            print(f"   ⚠️  標註失敗 (idx={idx}): {e}")
        continue

print(f"\n   標註完成: {annotated:,}/{len(df):,}")
print(f"   成功率: {annotated/len(df)*100:.1f}%")
print(f"   錯誤數: {errors:,}")

# 6. 統計報告
print("\n📊 分類統計:")
print(f"   Category 1: {(df['ghg_category'] == 1).sum():,} 筆 ({(df['ghg_category'] == 1).sum()/len(df)*100:.1f}%)")
print(f"   Category 2: {(df['ghg_category'] == 2).sum():,} 筆 ({(df['ghg_category'] == 2).sum()/len(df)*100:.1f}%)")
print(f"   Unknown: {(df['ghg_category'] == 'unknown').sum():,} 筆")
print(f"   Exclude: {(df['ghg_category'] == 'exclude').sum():,} 筆")

if annotated > 0:
    avg_conf = df['ghg_confidence'].mean()
    print(f"   平均信心度: {avg_conf:.2%}")

print("\n💰 金額統計:")
print(f"   平均金額: ${df['amount'].mean():,.2f} USD")
print(f"   中位數金額: ${df['amount'].median():,.2f} USD")
print(f"   最大金額: ${df['amount'].max():,.2f} USD")
print(f"   最小金額: ${df['amount'].min():,.2f} USD")

print("\n📅 年份分布:")
year_counts = df['fiscal_year'].value_counts().sort_index()
for year, count in year_counts.items():
    print(f"   {year}: {count:,} 筆 ({count/len(df)*100:.1f}%)")

# 7. 儲存標註資料
print("\n💾 儲存標註資料...")
annotated_dir = DATA_DIR / "annotated"
annotated_dir.mkdir(parents=True, exist_ok=True)

annotated_file = annotated_dir / f"sf_2020_2024_annotated_{datetime.now().strftime('%Y%m%d')}.csv"
df.to_csv(annotated_file, index=False, encoding='utf-8')
print(f"   ✅ {annotated_file.name}")

print("\n" + "="*70)
print("  ✅ 處理完成！")
print("="*70)
print(f"\n📊 最終統計:")
print(f"   原始資料: {total_processed:,} 筆")
print(f"   篩選後: {filtered_count:,} 筆 ({filtered_count/total_processed*100:.1f}%)")
print(f"   清理後: {len(df):,} 筆")
print(f"   已標註: {annotated:,} 筆 ({annotated/len(df)*100:.1f}%)")

print(f"\n💾 輸出檔案:")
print(f"   處理後: {processed_file}")
print(f"   標註後: {annotated_file}")

print("\n🎯 資料收集進度:")
singapore_count = 32554  # 已完成
sf_count = annotated
total_annotated = singapore_count + sf_count
phase1_target = 15000

print(f"   Singapore: {singapore_count:,} 筆")
print(f"   San Francisco (2020-2024): {sf_count:,} 筆")
print(f"   總計: {total_annotated:,} 筆")
print(f"   Phase 1 目標: {phase1_target:,} 筆")
print(f"   達成率: {total_annotated/phase1_target*100:.1f}%")

print("\n下一步: 合併兩個資料集，進行人工審核")
