#!/usr/bin/env python3
"""
準備 Tier 2 國際資料庫的 RAG 檢索資料
整合多個資料來源到統一格式
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

print("=" * 70)
print("🔧 Tier 2 國際資料庫預處理")
print("=" * 70)


def load_agribalyse() -> pd.DataFrame:
    """載入 AGRIBALYSE 食品排放資料"""
    print("\n📦 載入 AGRIBALYSE...")

    # 載入三個檔案
    bio = pd.read_csv(DATA_DIR / "AGRIBALYSE3.1.1_bio.csv")
    conv = pd.read_csv(DATA_DIR / "AGRIBALYSE3.1.1_conv_janv24.csv")
    prod = pd.read_csv(DATA_DIR / "AGRIBALYSE3.1.1_produits.csv")

    # 合併
    df = pd.concat([bio, conv, prod], ignore_index=True)

    # 標準化欄位
    df = df.rename(columns={
        'LCI Name': 'name',
        'kg CO2e': 'emission_factor'
    })

    # 篩選必要欄位
    df = df[['name', 'emission_factor']].copy()

    # 添加元資料
    df['unit'] = 'kg'
    df['source'] = 'AGRIBALYSE'
    df['category'] = 'Food & Agriculture'
    df['region'] = 'FR'  # French database
    df['base_year'] = 2024

    print(f"   ✓ 載入 {len(df)} 筆記錄")
    return df


def load_idemat() -> pd.DataFrame:
    """載入 Idemat 材料排放資料"""
    print("\n📦 載入 Idemat...")

    df = pd.read_csv(DATA_DIR / "IdematDynamic241.csv")

    # 標準化欄位
    df = df.rename(columns={
        'Process': 'name',
        'kgCO2e': 'emission_factor',
        'Unit': 'unit',
        'heading': 'category'
    })

    # 篩選必要欄位
    df = df[['name', 'emission_factor', 'unit', 'category']].copy()

    # 添加元資料
    df['source'] = 'Idemat'
    df['region'] = 'EU'
    df['base_year'] = 2024

    print(f"   ✓ 載入 {len(df)} 筆記錄")
    return df


def load_big_climate_db() -> pd.DataFrame:
    """載入 Big Climate Database"""
    print("\n📦 載入 Big Climate Database...")

    df = pd.read_csv(DATA_DIR / "The_Big_Climate_Database_version_1_1_download_english.csv")

    # 標準化欄位
    df = df.rename(columns={
        'Product': 'name',
        'Total kg CO2e/kg': 'emission_factor',
        'Category': 'category'
    })

    # 篩選必要欄位
    df = df[['name', 'emission_factor', 'category']].copy()

    # 添加元資料
    df['unit'] = 'kg'
    df['source'] = 'Big Climate DB'
    df['region'] = 'DK'  # Danish database
    df['base_year'] = 2022

    print(f"   ✓ 載入 {len(df)} 筆記錄")
    return df


def load_footprint_calc() -> pd.DataFrame:
    """載入 FootprintCalc 資料"""
    print("\n📦 載入 FootprintCalc...")

    df = pd.read_csv(DATA_DIR / "FootprintCalc1.2-1.csv")

    # 標準化欄位
    df = df.rename(columns={
        'Impact factor': 'name',
        'Carbon footprint (kg CO2e)': 'emission_factor',
        'Unit': 'unit'
    })

    # 篩選必要欄位
    df = df[['name', 'emission_factor', 'unit']].copy()

    # 添加元資料
    df['source'] = 'FootprintCalc'
    df['category'] = 'Materials & Chemicals'
    df['region'] = 'Global'
    df['base_year'] = 2023

    print(f"   ✓ 載入 {len(df)} 筆記錄")
    return df


def create_search_text(row: pd.Series) -> str:
    """
    為每筆記錄創建搜尋文本
    結合產品名稱、類別、來源等資訊
    """
    parts = [
        str(row['name']),
        str(row.get('category', '')),
        str(row['source']),
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
    df = df.dropna(subset=['name', 'emission_factor'])
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

    # 填充缺失的 category
    df['category'] = df['category'].fillna('General')

    # 添加 tier 標記
    df['tier'] = 2

    # 創建搜尋文本
    print("\n📝 創建搜尋文本...")
    df['search_text'] = df.apply(create_search_text, axis=1)
    print(f"   ✓ 完成")

    # 統計資訊
    print("\n📊 資料統計:")
    print(f"   總記錄數: {len(df)}")
    print(f"   資料來源分布:")
    for source, count in df['source'].value_counts().items():
        print(f"      - {source}: {count}")
    print(f"   類別分布:")
    for cat, count in df['category'].value_counts().head(10).items():
        print(f"      - {cat}: {count}")

    # 儲存統一格式資料
    output_file = OUTPUT_DIR / "tier2_unified.csv"
    print(f"\n💾 儲存統一格式資料: {output_file.name}")
    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f"   ✓ 已儲存 {len(df)} 筆記錄")

    # 儲存元資料（不含 search_text，減少檔案大小）
    metadata = df.drop(columns=['search_text'])
    metadata_file = OUTPUT_DIR / "tier2_metadata.csv"
    print(f"\n💾 儲存元資料: {metadata_file.name}")
    metadata.to_csv(metadata_file, index=False, encoding='utf-8')
    print(f"   ✓ 已儲存元資料")

    # 範例資料
    print("\n📋 範例資料 (前 5 筆):")
    print(df[['name', 'emission_factor', 'unit', 'source', 'category']].head().to_string(index=False))

    print("\n" + "=" * 70)
    print("✅ Tier 2 資料預處理完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
