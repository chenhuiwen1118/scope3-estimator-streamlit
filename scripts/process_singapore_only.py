#!/usr/bin/env python3
"""
Singapore 資料集處理腳本（簡化版）

只處理 Singapore 政府採購資料集，避免記憶體問題
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
print("  Singapore 政府採購資料處理")
print("="*70)

# 1. 讀取 Singapore 資料
print("\n📥 讀取 Singapore 資料...")
sg_file = DATA_DIR / "raw" / "kaggle" / "singapore_procurement" / "government-procurement-via-gebiz.csv"

if not sg_file.exists():
    print(f"❌ 找不到檔案: {sg_file}")
    sys.exit(1)

df = pd.read_csv(sg_file, low_memory=False)
print(f"   原始記錄數: {len(df)}")
print(f"   原始欄位: {df.columns.tolist()}")

# 2. 標準化欄位
print("\n🔧 標準化欄位...")
df = df.rename(columns={
    'tender_no.': 'tender_id',
    'tender_description': 'description',
    'agency': 'organization',
    'award_date': 'date',
    'supplier_name': 'supplier',
    'awarded_amt': 'amount'
})

# 3. 清理資料
print("\n🧹 清理資料...")
# 移除空描述
before = len(df)
df = df[df['description'].notna()]
df = df[df['description'].str.len() > 0]
after = len(df)
print(f"   移除 {before - after} 筆空描述")

# 清理文字
df['description'] = df['description'].str.strip()

# 標準化金額
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

# 加入來源
df['source'] = 'kaggle_singapore_govt'
df['currency'] = 'SGD'
df['processed_at'] = datetime.now().isoformat()

print(f"   處理後記錄數: {len(df)}")

# 4. 儲存處理後資料
print("\n💾 儲存處理後資料...")
processed_dir = DATA_DIR / "processed"
processed_dir.mkdir(parents=True, exist_ok=True)

processed_file = processed_dir / "singapore_govt_processed.csv"
df.to_csv(processed_file, index=False, encoding='utf-8')
print(f"   ✅ {processed_file.name}")

# 5. GHG 分類標註
print("\n🏷️  執行 GHG 分類標註...")
print(f"   總記錄數: {len(df)}")

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
    if annotated % 1000 == 0 and annotated > 0:
        print(f"   已標註: {annotated}/{len(df)} ({annotated/len(df)*100:.1f}%)")

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

print(f"\n   標註完成: {annotated}/{len(df)}")
print(f"   錯誤數: {errors}")

# 6. 統計報告
print("\n📊 分類統計:")
print(f"   Category 1: {(df['ghg_category'] == 1).sum()} 筆")
print(f"   Category 2: {(df['ghg_category'] == 2).sum()} 筆")
print(f"   Unknown: {(df['ghg_category'] == 'unknown').sum()} 筆")
print(f"   Exclude: {(df['ghg_category'] == 'exclude').sum()} 筆")

if annotated > 0:
    avg_conf = df['ghg_confidence'].mean()
    print(f"   平均信心度: {avg_conf:.2%}")

# 7. 儲存標註資料
print("\n💾 儲存標註資料...")
annotated_dir = DATA_DIR / "annotated"
annotated_dir.mkdir(parents=True, exist_ok=True)

annotated_file = annotated_dir / f"singapore_annotated_{datetime.now().strftime('%Y%m%d')}.csv"
df.to_csv(annotated_file, index=False, encoding='utf-8')
print(f"   ✅ {annotated_file.name}")

print("\n" + "="*70)
print("  ✅ 處理完成！")
print("="*70)
print(f"\n📊 最終統計:")
print(f"   總記錄數: {len(df)}")
print(f"   已標註: {annotated} ({annotated/len(df)*100:.1f}%)")
print(f"\n💾 輸出檔案:")
print(f"   處理後: {processed_file}")
print(f"   標註後: {annotated_file}")

print("\n下一步: 人工審核高信心度樣本")
