#!/usr/bin/env python3
"""
準備 Tier 1 台灣環保署資料的 RAG 檢索資料
整理台灣本地排放係數到統一格式
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import re

# 路徑設定
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "emission_factors" / "tier1_local"
INPUT_FILE = DATA_DIR / "TWMOEPA_Preview_Data.csv"
OUTPUT_DIR = DATA_DIR

print("=" * 70)
print("🔧 Tier 1 台灣環保署資料預處理")
print("=" * 70)


def clean_unit(unit_str: str) -> str:
    """
    清理單位字串
    從「公斤(kg)」→「kg」
    從「張」→「piece」
    """
    if pd.isna(unit_str):
        return "unknown"

    # 提取括號內的英文單位
    match = re.search(r'\(([a-zA-Z0-9]+)\)', unit_str)
    if match:
        return match.group(1).lower()

    # 處理中文單位
    unit_map = {
        '張': 'piece',
        '個': 'piece',
        '支': 'piece',
        '件': 'piece',
        '噸': 'ton',
        '公噸': 'ton',
        '度': 'kWh',
        '千瓦小時': 'kWh'
    }

    for zh, en in unit_map.items():
        if zh in unit_str:
            return en

    return unit_str.strip()


def create_search_text(row: pd.Series) -> str:
    """
    為每筆記錄創建搜尋文本
    結合產品名稱、單位等資訊
    """
    parts = [
        str(row['name']),
        str(row.get('unit_clean', '')),
        "台灣",
        "環保署"
    ]

    # 移除空值
    parts = [p for p in parts if p and p != 'nan' and p.strip()]

    return ' '.join(parts)


def main():
    """主流程"""

    # 1. 載入資料
    print(f"\n📂 載入資料: {INPUT_FILE.name}")
    df = pd.read_csv(INPUT_FILE)
    print(f"   ✓ 載入 {len(df)} 筆記錄")

    # 2. 資料清理
    print("\n🧹 資料清理...")

    # 移除缺失值
    initial_count = len(df)
    df = df.dropna(subset=['name', 'kg CO2e'])
    print(f"   ✓ 移除缺失值: {initial_count} → {len(df)}")

    # 確保 emission_factor 是數值
    df = df.rename(columns={'kg CO2e': 'emission_factor'})
    df['emission_factor'] = pd.to_numeric(df['emission_factor'], errors='coerce')
    df = df.dropna(subset=['emission_factor'])
    print(f"   ✓ 確保數值格式: {len(df)} 筆")

    # 移除負值和零值
    df = df[df['emission_factor'] > 0]
    print(f"   ✓ 移除非正值: {len(df)} 筆")

    # 清理單位
    df['unit_clean'] = df['unit'].apply(clean_unit)
    print(f"   ✓ 清理單位格式")

    # 3. 標準化欄位
    print("\n📝 標準化欄位...")

    df = df.rename(columns={
        'announcementyear': 'base_year',
        'departmentname': 'source_dept'
    })

    # 添加元資料
    df['source'] = 'Taiwan EPA'
    df['region'] = 'TW'
    df['tier'] = 1
    df['category'] = 'Taiwan Local'

    # 4. 創建搜尋文本
    print("\n📝 創建搜尋文本...")
    df['search_text'] = df.apply(create_search_text, axis=1)
    print(f"   ✓ 完成")

    # 5. 統計資訊
    print("\n📊 資料統計:")
    print(f"   總記錄數: {len(df)}")
    print(f"   年度分布:")
    for year, count in df['base_year'].value_counts().items():
        print(f"      - {int(year)}: {count}")
    print(f"   單位分布 (前 10):")
    for unit, count in df['unit_clean'].value_counts().head(10).items():
        print(f"      - {unit}: {count}")

    # 6. 儲存統一格式資料
    output_file = OUTPUT_DIR / "tier1_unified.csv"
    print(f"\n💾 儲存統一格式資料: {output_file.name}")

    # 選擇欄位並重新排序
    output_columns = [
        'name', 'emission_factor', 'unit_clean', 'unit',
        'source', 'region', 'category', 'base_year',
        'source_dept', 'tier', 'search_text'
    ]
    df_output = df[output_columns].copy()
    df_output = df_output.rename(columns={'unit_clean': 'unit_standard', 'unit': 'unit_original'})

    df_output.to_csv(output_file, index=False, encoding='utf-8')
    print(f"   ✓ 已儲存 {len(df_output)} 筆記錄")

    # 7. 儲存元資料（不含 search_text，減少檔案大小）
    metadata = df_output.drop(columns=['search_text'])
    metadata_file = OUTPUT_DIR / "tier1_metadata.csv"
    print(f"\n💾 儲存元資料: {metadata_file.name}")
    metadata.to_csv(metadata_file, index=False, encoding='utf-8')
    print(f"   ✓ 已儲存元資料")

    # 8. 範例資料
    print("\n📋 範例資料 (前 10 筆):")
    print(df_output[['name', 'emission_factor', 'unit_standard', 'base_year']].head(10).to_string(index=False))

    print("\n" + "=" * 70)
    print("✅ Tier 1 資料預處理完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
