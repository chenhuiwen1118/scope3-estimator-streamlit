#!/usr/bin/env python3
"""
Tier 2 資料庫升級腳本 - 遷移到 Scope 3 Schema

將現有 6,949 筆資料升級到支援 Scope 3 分類的新 schema
並整合新收集的 Defra UK 2025 和 EPA Supply Chain 資料
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
TIER2_DIR = PROJECT_ROOT / "data" / "emission_factors" / "tier2_international"
NEW_DATA_DIR = Path(__file__).parent.parent.parent / "data"

print("=" * 80)
print("🔄 Tier 2 資料庫升級 - 遷移到 Scope 3 Schema")
print("=" * 80)

# ============================================================
# 1. 載入現有資料
# ============================================================

print("\n【步驟 1】載入現有資料...")

old_tier2 = pd.read_csv(TIER2_DIR / "tier2_unified.csv")
print(f"✓ 現有 Tier 2: {len(old_tier2):,} 筆")

# ============================================================
# 2. 建立 Scope 3 分類映射規則
# ============================================================

print("\n【步驟 2】建立 Scope 3 分類映射...")

# 根據 category 和 source 推斷 scope3_category
def infer_scope3_category(row):
    """推斷 Scope 3 類別"""
    category = str(row.get('category', '')).lower()
    source = str(row.get('source', '')).lower()
    name = str(row.get('name', '')).lower()

    # Category 1: 採購的商品與服務
    if any(kw in category for kw in ['food', 'agriculture', 'material', 'chemical', 'metal', 'plastic',
                                       'textile', 'paper', 'wood', 'glass', 'ceramic']):
        return '1'

    # Category 3: 燃料與能源相關活動
    if any(kw in category for kw in ['fuel', 'electricity', 'energy', 'heat']):
        return '3'

    # Category 4: 上游運輸
    if 'transport' in category and 'upstream' in name:
        return '4'

    # Category 5: 營運廢棄物
    if 'end-of-life' in category or 'waste' in name:
        return '5'

    # Category 9: 下游運輸
    if 'transport' in category and 'downstream' in name:
        return '9'

    # Category 12: 產品終結處理
    if 'end-of-life' in category:
        return '12'

    # 預設: Category 1 (最常見)
    return '1'

old_tier2['scope3_category'] = old_tier2.apply(infer_scope3_category, axis=1)

# ============================================================
# 3. 轉換到新 Schema
# ============================================================

print("\n【步驟 3】轉換到新 Schema...")

def migrate_to_new_schema(df, prefix='LEGACY'):
    """將舊資料轉換為新 schema"""
    records = []

    for idx, row in df.iterrows():
        # 建立唯一 ID
        source_clean = str(row['source']).upper().replace(' ', '_').replace('-', '_')
        emission_factor_id = f"{prefix}_{source_clean}_{idx:06d}"

        # 建立 category_code
        category_code = str(row.get('name', ''))[:50].upper().replace(' ', '_').replace(',', '').replace('(', '').replace(')', '')

        record = {
            'emission_factor_id': emission_factor_id,
            'source_database': row['source'],
            'category_code': category_code,
            'category_name_en': row['name'],
            'category_name_zh': '',  # 待翻譯
            'activity_type_en': row.get('category', ''),
            'activity_type_zh': '',  # 待翻譯
            'scope3_category': row.get('scope3_category', '1'),
            'unit': f"kg CO2e/{row.get('unit', 'kg')}",
            'emission_factor': row['emission_factor'],
            'co2_emission': None,  # 舊資料無分項
            'ch4_emission': None,
            'n2o_emission': None,
            'geographic_scope': row.get('region', 'Global'),
            'year': int(row.get('base_year', 2024)),
            'tier_level': 2,
            'data_quality': 'Medium',  # 預設中等品質
            'gwp_version': 'AR5',  # 預設 AR5
            'source_url': '',
            'license': 'Check source database',
            'notes': f"Migrated from {row['source']}"
        }

        records.append(record)

    return pd.DataFrame(records)

migrated_df = migrate_to_new_schema(old_tier2)
print(f"✓ 已遷移: {len(migrated_df):,} 筆")

# ============================================================
# 4. 載入新收集的資料
# ============================================================

print("\n【步驟 4】載入新收集的資料...")

# 檢查新資料是否存在
new_data_file = NEW_DATA_DIR / "processed" / "integrated" / "tier2_full_20260129.csv"

if new_data_file.exists():
    new_data = pd.read_csv(new_data_file)
    # 移除 BOM
    if new_data.columns[0].startswith('\ufeff'):
        new_data.columns = [new_data.columns[0].replace('\ufeff', '')] + list(new_data.columns[1:])

    print(f"✓ 新資料: {len(new_data):,} 筆")
    print(f"   - Defra UK 2025: {len(new_data[new_data['source_database'] == 'Defra UK 2025']):,} 筆")
    print(f"   - EPA Supply Chain: {len(new_data[new_data['source_database'] == 'EPA Supply Chain GHG Emission Factors v1.3.0']):,} 筆")
else:
    print("⚠️  未找到新資料檔案")
    new_data = pd.DataFrame()

# ============================================================
# 5. 整合所有資料
# ============================================================

print("\n【步驟 5】整合資料...")

if not new_data.empty:
    # 確保欄位一致
    all_columns = [
        'emission_factor_id', 'source_database', 'category_code',
        'category_name_en', 'category_name_zh', 'activity_type_en', 'activity_type_zh',
        'scope3_category', 'unit', 'emission_factor',
        'co2_emission', 'ch4_emission', 'n2o_emission',
        'geographic_scope', 'year', 'tier_level', 'data_quality',
        'gwp_version', 'source_url', 'license', 'notes'
    ]

    # 確保兩個 DataFrame 都有所有欄位
    for col in all_columns:
        if col not in migrated_df.columns:
            migrated_df[col] = None
        if col not in new_data.columns:
            new_data[col] = None

    # 選擇欄位並合併
    migrated_df = migrated_df[all_columns]
    new_data = new_data[all_columns]

    integrated_df = pd.concat([migrated_df, new_data], ignore_index=True)
else:
    integrated_df = migrated_df

print(f"✓ 整合後總計: {len(integrated_df):,} 筆")

# ============================================================
# 6. 資料統計
# ============================================================

print("\n【步驟 6】資料統計...")

print(f"\n資料來源分布:")
for source, count in integrated_df['source_database'].value_counts().head(10).items():
    print(f"  {source}: {count:,} 筆")

print(f"\nScope 3 類別分布:")
for cat, count in integrated_df['scope3_category'].value_counts().sort_index().items():
    print(f"  Category {cat}: {count:,} 筆")

print(f"\n地理範圍分布:")
for region, count in integrated_df['geographic_scope'].value_counts().head(10).items():
    print(f"  {region}: {count:,} 筆")

# ============================================================
# 7. 建立搜尋文本（用於 RAG）
# ============================================================

print("\n【步驟 7】建立搜尋文本...")

def create_search_text(row):
    """建立用於向量檢索的文本"""
    parts = [
        str(row['category_name_en']),
        str(row['category_name_zh']) if pd.notna(row['category_name_zh']) and row['category_name_zh'] else '',
        str(row['activity_type_en']),
        str(row['activity_type_zh']) if pd.notna(row['activity_type_zh']) and row['activity_type_zh'] else '',
        f"Scope 3 Category {row['scope3_category']}",
        str(row['source_database']),
        str(row['unit'])
    ]

    # 移除空值
    parts = [p for p in parts if p and p != 'nan' and p.strip()]

    return ' '.join(parts)

integrated_df['search_text'] = integrated_df.apply(create_search_text, axis=1)
print("✓ 搜尋文本建立完成")

# ============================================================
# 8. 儲存結果
# ============================================================

print("\n【步驟 8】儲存結果...")

# 備份舊檔案
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
if (TIER2_DIR / "tier2_unified.csv").exists():
    backup_file = TIER2_DIR / f"tier2_unified_backup_{timestamp}.csv"
    old_tier2.to_csv(backup_file, index=False, encoding='utf-8')
    print(f"✓ 備份舊檔案: {backup_file.name}")

# 儲存新的統一檔案
output_file = TIER2_DIR / "tier2_unified.csv"
integrated_df.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"✓ 儲存: {output_file.name} ({len(integrated_df):,} 筆)")

# 儲存元資料（不含 search_text）
metadata = integrated_df.drop(columns=['search_text'])
metadata_file = TIER2_DIR / "tier2_metadata.csv"
metadata.to_csv(metadata_file, index=False, encoding='utf-8-sig')
print(f"✓ 儲存: {metadata_file.name}")

# 儲存 Scope 3 分類映射表
scope3_summary = integrated_df.groupby('scope3_category').agg({
    'emission_factor_id': 'count',
    'source_database': lambda x: ', '.join(x.unique()[:3])
}).reset_index()
scope3_summary.columns = ['scope3_category', 'count', 'sample_sources']

scope3_file = TIER2_DIR / "tier2_scope3_summary.csv"
scope3_summary.to_csv(scope3_file, index=False, encoding='utf-8-sig')
print(f"✓ 儲存: {scope3_file.name}")

# 範例資料
print("\n【範例資料】(前 5 筆):")
sample_cols = ['category_name_en', 'scope3_category', 'emission_factor', 'unit', 'source_database']
print(integrated_df[sample_cols].head(10).to_string(index=False))

print("\n" + "=" * 80)
print("✅ Tier 2 資料庫升級完成！")
print("=" * 80)
print(f"\n📊 摘要:")
print(f"  - 舊資料遷移: 6,949 筆")
print(f"  - 新資料整合: {len(new_data) if not new_data.empty else 0:,} 筆")
print(f"  - 總計: {len(integrated_df):,} 筆")
print(f"  - 支援 Scope 3 類別: {integrated_df['scope3_category'].nunique()} 類")
print(f"\n📁 輸出檔案:")
print(f"  - {output_file}")
print(f"  - {metadata_file}")
print(f"  - {scope3_file}")
print(f"\n⚠️  待辦事項:")
print(f"  1. 執行 build_tier2_embeddings.py 重建向量索引")
print(f"  2. 補充中文翻譯 (category_name_zh, activity_type_zh)")
print(f"  3. 精煉 Scope 3 分類映射（目前為自動推斷）")
