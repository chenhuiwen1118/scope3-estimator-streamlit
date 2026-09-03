#!/usr/bin/env python3
"""
準備 Tier 2 國際資料庫的 RAG 檢索資料 v2.0
整合多個資料來源到支援 Scope 3 分類的統一格式

更新內容:
- 支援 Scope 3 分類 (Category 1-15)
- 新增 Defra UK 2025 和 EPA Supply Chain
- 擴展 schema 包含分項排放與元資料
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from typing import Dict, List

# 路徑設定
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "emission_factors" / "tier2_international"
OUTPUT_DIR = DATA_DIR

print("=" * 80)
print("🔧 Tier 2 國際資料庫預處理 v2.0 (支援 Scope 3)")
print("=" * 80)


def load_agribalyse() -> pd.DataFrame:
    """載入 AGRIBALYSE 食品排放資料"""
    print("\n📦 載入 AGRIBALYSE...")

    # 載入三個檔案
    bio = pd.read_csv(DATA_DIR / "AGRIBALYSE3.1.1_bio.csv")
    conv = pd.read_csv(DATA_DIR / "AGRIBALYSE3.1.1_conv_janv24.csv")
    prod = pd.read_csv(DATA_DIR / "AGRIBALYSE3.1.1_produits.csv")

    # 合併
    df = pd.concat([bio, conv, prod], ignore_index=True)

    # 標準化欄位到新 schema
    df = df.rename(columns={
        'LCI Name': 'category_name_en',
        'kg CO2e': 'emission_factor'
    })

    # 建立新 schema 欄位
    records = []
    for idx, row in df.iterrows():
        record = {
            'emission_factor_id': f"AGRIBALYSE_{idx:06d}",
            'source_database': 'AGRIBALYSE',
            'category_code': str(row['category_name_en'])[:50].upper().replace(' ', '_'),
            'category_name_en': row['category_name_en'],
            'category_name_zh': '',
            'activity_type_en': 'Food & Agriculture',
            'activity_type_zh': '食品與農業',
            'scope3_category': '1',  # 採購商品
            'unit': 'kg CO2e/kg',
            'emission_factor': row['emission_factor'],
            'co2_emission': None,
            'ch4_emission': None,
            'n2o_emission': None,
            'geographic_scope': 'FR',
            'year': 2024,
            'tier_level': 2,
            'data_quality': 'High',
            'gwp_version': 'AR5',
            'source_url': 'https://agribalyse.ademe.fr/',
            'license': 'Open Data',
            'notes': 'French LCA database for food and agriculture'
        }
        records.append(record)

    df = pd.DataFrame(records)
    print(f"   ✓ 載入 {len(df)} 筆記錄")
    return df


def load_idemat() -> pd.DataFrame:
    """載入 Idemat 材料排放資料"""
    print("\n📦 載入 Idemat...")

    df = pd.read_csv(DATA_DIR / "IdematDynamic241.csv")

    records = []
    for idx, row in df.iterrows():
        # 根據 category 判斷 scope3_category
        category = str(row.get('heading', '')).lower()
        if 'end-of-life' in category:
            scope3 = '5'  # 廢棄物
        elif 'fuel' in category or 'electricity' in category:
            scope3 = '3'  # 能源
        else:
            scope3 = '1'  # 採購商品

        record = {
            'emission_factor_id': f"IDEMAT_{idx:06d}",
            'source_database': 'Idemat',
            'category_code': str(row['Process'])[:50].upper().replace(' ', '_'),
            'category_name_en': row['Process'],
            'category_name_zh': '',
            'activity_type_en': row.get('heading', 'Materials'),
            'activity_type_zh': '',
            'scope3_category': scope3,
            'unit': f"kg CO2e/{row.get('Unit', 'kg')}",
            'emission_factor': row['kgCO2e'],
            'co2_emission': None,
            'ch4_emission': None,
            'n2o_emission': None,
            'geographic_scope': 'EU',
            'year': 2024,
            'tier_level': 2,
            'data_quality': 'High',
            'gwp_version': 'AR5',
            'source_url': 'https://www.ecocostsvalue.com/idemat/',
            'license': 'Academic use',
            'notes': 'Delft University materials database'
        }
        records.append(record)

    df = pd.DataFrame(records)
    print(f"   ✓ 載入 {len(df)} 筆記錄")
    return df


def load_big_climate_db() -> pd.DataFrame:
    """載入 Big Climate Database"""
    print("\n📦 載入 Big Climate Database...")

    df = pd.read_csv(DATA_DIR / "The_Big_Climate_Database_version_1_1_download_english.csv")

    records = []
    for idx, row in df.iterrows():
        record = {
            'emission_factor_id': f"BIGCLIMATE_{idx:06d}",
            'source_database': 'Big Climate DB',
            'category_code': str(row['Product'])[:50].upper().replace(' ', '_'),
            'category_name_en': row['Product'],
            'category_name_zh': '',
            'activity_type_en': row.get('Category', 'Consumer Goods'),
            'activity_type_zh': '',
            'scope3_category': '1',
            'unit': 'kg CO2e/kg',
            'emission_factor': row['Total kg CO2e/kg'],
            'co2_emission': None,
            'ch4_emission': None,
            'n2o_emission': None,
            'geographic_scope': 'DK',
            'year': 2022,
            'tier_level': 2,
            'data_quality': 'Medium',
            'gwp_version': 'AR5',
            'source_url': 'https://www.bigclimatevatabase.com/',
            'license': 'Open Data',
            'notes': 'Danish consumer products database'
        }
        records.append(record)

    df = pd.DataFrame(records)
    print(f"   ✓ 載入 {len(df)} 筆記錄")
    return df


def load_footprint_calc() -> pd.DataFrame:
    """載入 FootprintCalc 資料"""
    print("\n📦 載入 FootprintCalc...")

    df = pd.read_csv(DATA_DIR / "FootprintCalc1.2-1.csv")

    records = []
    for idx, row in df.iterrows():
        record = {
            'emission_factor_id': f"FOOTPRINT_{idx:06d}",
            'source_database': 'FootprintCalc',
            'category_code': str(row['Impact factor'])[:50].upper().replace(' ', '_'),
            'category_name_en': row['Impact factor'],
            'category_name_zh': '',
            'activity_type_en': 'Materials & Chemicals',
            'activity_type_zh': '材料與化學品',
            'scope3_category': '1',
            'unit': f"kg CO2e/{row.get('Unit', 'kg')}",
            'emission_factor': row['Carbon footprint (kg CO2e)'],
            'co2_emission': None,
            'ch4_emission': None,
            'n2o_emission': None,
            'geographic_scope': 'Global',
            'year': 2023,
            'tier_level': 2,
            'data_quality': 'Medium',
            'gwp_version': 'AR5',
            'source_url': '',
            'license': 'Check source',
            'notes': 'General materials footprint calculator'
        }
        records.append(record)

    df = pd.DataFrame(records)
    print(f"   ✓ 載入 {len(df)} 筆記錄")
    return df


def load_defra_uk() -> pd.DataFrame:
    """載入 Defra UK 2025 資料（如果存在）"""
    print("\n📦 載入 Defra UK 2025...")

    # 這裡可以添加直接從 Excel 讀取的邏輯
    # 目前先從已整合的資料中篩選
    print("   ⚠️  Defra UK 資料需從整合檔案中取得")
    return pd.DataFrame()


def load_epa_supply_chain() -> pd.DataFrame:
    """載入 EPA Supply Chain 資料（如果存在）"""
    print("\n📦 載入 EPA Supply Chain...")

    print("   ⚠️  EPA Supply Chain 資料需從整合檔案中取得")
    return pd.DataFrame()


def create_search_text(row: pd.Series) -> str:
    """
    為每筆記錄創建搜尋文本（用於向量檢索）
    結合產品名稱、類別、來源等資訊
    """
    parts = [
        str(row['category_name_en']),
        str(row.get('category_name_zh', '')) if pd.notna(row.get('category_name_zh')) else '',
        str(row['activity_type_en']),
        str(row.get('activity_type_zh', '')) if pd.notna(row.get('activity_type_zh')) else '',
        f"Scope 3 Category {row['scope3_category']}",
        str(row['source_database']),
        str(row.get('unit', ''))
    ]

    # 移除空值
    parts = [p for p in parts if p and p != 'nan' and p.strip()]

    return ' '.join(parts)


def main():
    """主流程"""

    # 載入各資料來源
    dfs = []

    try:
        dfs.append(load_agribalyse())
    except Exception as e:
        print(f"   ⚠️  載入 AGRIBALYSE 失敗: {e}")

    try:
        dfs.append(load_idemat())
    except Exception as e:
        print(f"   ⚠️  載入 Idemat 失敗: {e}")

    try:
        dfs.append(load_big_climate_db())
    except Exception as e:
        print(f"   ⚠️  載入 Big Climate DB 失敗: {e}")

    try:
        dfs.append(load_footprint_calc())
    except Exception as e:
        print(f"   ⚠️  載入 FootprintCalc 失敗: {e}")

    # 合併所有資料
    print("\n🔗 合併資料...")
    df = pd.concat(dfs, ignore_index=True)
    print(f"   ✓ 合併後總計: {len(df)} 筆記錄")

    # 資料清理
    print("\n🧹 資料清理...")

    # 移除缺失值
    initial_count = len(df)
    df = df.dropna(subset=['category_name_en', 'emission_factor'])
    print(f"   ✓ 移除缺失值: {initial_count} → {len(df)}")

    # 確保 emission_factor 是數值
    df['emission_factor'] = pd.to_numeric(df['emission_factor'], errors='coerce')
    df = df.dropna(subset=['emission_factor'])
    print(f"   ✓ 確保數值格式: {len(df)} 筆")

    # 移除負值和零值
    df = df[df['emission_factor'] > 0]
    print(f"   ✓ 移除非正值: {len(df)} 筆")

    # 移除異常值 (> 10,000 kg CO2e)
    df = df[df['emission_factor'] < 10000]
    print(f"   ✓ 移除異常值: {len(df)} 筆")

    # 創建搜尋文本
    print("\n📝 創建搜尋文本...")
    df['search_text'] = df.apply(create_search_text, axis=1)
    print(f"   ✓ 完成")

    # 統計資訊
    print("\n📊 資料統計:")
    print(f"   總記錄數: {len(df):,}")
    print(f"   資料來源分布:")
    for source, count in df['source_database'].value_counts().items():
        print(f"      - {source}: {count:,}")
    print(f"   Scope 3 類別分布:")
    for cat, count in df['scope3_category'].value_counts().items():
        print(f"      - Category {cat}: {count:,}")

    # 儲存統一格式資料
    output_file = OUTPUT_DIR / "tier2_unified.csv"
    print(f"\n💾 儲存統一格式資料: {output_file.name}")
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"   ✓ 已儲存 {len(df):,} 筆記錄")

    # 儲存元資料（不含 search_text，減少檔案大小）
    metadata = df.drop(columns=['search_text'])
    metadata_file = OUTPUT_DIR / "tier2_metadata.csv"
    print(f"\n💾 儲存元資料: {metadata_file.name}")
    metadata.to_csv(metadata_file, index=False, encoding='utf-8-sig')
    print(f"   ✓ 已儲存元資料")

    # 範例資料
    print("\n📋 範例資料 (前 5 筆):")
    sample_cols = ['category_name_en', 'scope3_category', 'emission_factor', 'unit', 'source_database']
    print(df[sample_cols].head().to_string(index=False))

    print("\n" + "=" * 80)
    print("✅ Tier 2 資料預處理完成！")
    print("=" * 80)
    print("\n💡 提示:")
    print("   - 若已執行 migrate_tier2_to_scope3_schema.py，請使用已升級的資料")
    print("   - 執行 build_tier2_embeddings.py 建立向量索引")


if __name__ == "__main__":
    main()
