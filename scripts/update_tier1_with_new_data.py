#!/usr/bin/env python3
"""
整合新增的台灣本地排放係數資料到 Tier 1
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# 加入 src 路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.embedding import EmbeddingEngine

TIER1_DIR = PROJECT_ROOT / "data" / "emission_factors" / "tier1_local"

def standardize_unit(unit_str: str) -> str:
    """標準化單位"""
    unit_mapping = {
        '公斤(kg)': 'kg',
        '公斤': 'kg',
        'kg': 'kg',
        '立方公尺(m3)': 'm3',
        '立方公尺': 'm3',
        'm3': 'm3',
        '平方公尺(m2)': 'm2',
        '平方公尺': 'm2',
        'm2': 'm2',
        '度(kwh)': 'kwh',
        'kwh': 'kwh',
        '片': 'piece',
        '張': 'piece',
        '公升': 'liter',
        '升': 'liter',
        'L': 'liter',
    }

    unit_clean = unit_str.strip()
    return unit_mapping.get(unit_clean, unit_clean)


def main():
    print("=" * 80)
    print("  整合新增台灣本地排放係數資料")
    print("=" * 80)

    # 讀取現有資料
    print("\n📥 讀取現有 Tier 1 資料...")
    existing_file = TIER1_DIR / "tier1_unified.csv"
    existing_df = pd.read_csv(existing_file, encoding='utf-8-sig')
    print(f"   現有資料: {len(existing_df):,} 筆")

    # 讀取新增資料
    print("\n📥 讀取新增「碳足跡排放係數.csv」...")
    new_file = TIER1_DIR / "碳足跡排放係數.csv"
    new_df = pd.read_csv(new_file, encoding='utf-8-sig')
    print(f"   新增資料: {len(new_df):,} 筆")

    # 顯示新資料範例
    print(f"\n   新增資料範例:")
    for idx, row in new_df.head(5).iterrows():
        print(f"      {row['name']}: {row['coe']} {row['unit']}")

    # 檢查重複
    print(f"\n🔍 檢查重複項目...")
    existing_names = set(existing_df['name'].str.lower().str.strip())
    new_names = set(new_df['name'].str.lower().str.strip())

    duplicates = existing_names & new_names
    print(f"   重複項目: {len(duplicates)} 筆")

    if len(duplicates) > 0:
        print(f"   前 10 個重複項目:")
        for i, name in enumerate(list(duplicates)[:10], 1):
            print(f"      {i}. {name}")

    # 轉換新資料為統一格式
    print(f"\n🔧 轉換新資料為統一格式...")

    unified_records = []

    for idx, row in new_df.iterrows():
        # 檢查是否已存在（精確比對）
        name_lower = str(row['name']).lower().strip()
        if name_lower in existing_names:
            continue  # 跳過重複項目

        # 標準化單位
        unit_std = standardize_unit(str(row['unit']))

        # 建立搜尋文字
        search_text = f"{row['name']} {unit_std} 台灣 {row['departmentname']}"

        record = {
            'name': str(row['name']).strip(),
            'emission_factor': float(row['coe']),
            'unit_standard': unit_std,
            'unit_original': str(row['unit']),
            'source': 'Taiwan EPA/MOE',
            'region': 'TW',
            'category': 'Taiwan Local',
            'base_year': int(row['announcementyear']),
            'source_dept': str(row['departmentname']),
            'tier': 1,
            'search_text': search_text
        }

        unified_records.append(record)

    new_unified_df = pd.DataFrame(unified_records)
    print(f"   轉換完成: {len(new_unified_df):,} 筆新資料（排除 {len(duplicates)} 筆重複）")

    # 合併資料
    print(f"\n🔗 合併資料...")
    combined_df = pd.concat([existing_df, new_unified_df], ignore_index=True)
    print(f"   合併後總筆數: {len(combined_df):,} 筆")

    # 儲存備份
    print(f"\n💾 儲存備份...")
    backup_file = TIER1_DIR / "tier1_unified_backup_20260129.csv"
    existing_df.to_csv(backup_file, index=False, encoding='utf-8-sig')
    print(f"   備份已儲存: {backup_file.name}")

    # 儲存更新後的資料
    print(f"\n💾 儲存更新後的 tier1_unified.csv...")
    combined_df.to_csv(existing_file, index=False, encoding='utf-8-sig')
    print(f"   更新完成: {existing_file.name}")

    # 統計分析
    print(f"\n📊 資料統計:")
    print(f"   總筆數: {len(combined_df):,}")
    print(f"   來源分布:")
    source_counts = combined_df['source_dept'].value_counts().head(10)
    for dept, count in source_counts.items():
        print(f"      {dept}: {count:,} 筆")

    print(f"\n   單位分布:")
    unit_counts = combined_df['unit_standard'].value_counts().head(10)
    for unit, count in unit_counts.items():
        print(f"      {unit}: {count:,} 筆")

    # 重新生成 embeddings
    print(f"\n🔧 重新生成 Tier 1 embeddings...")
    print(f"   初始化 Embedding 引擎...")
    embedding_engine = EmbeddingEngine(
        model_name="paraphrase-multilingual-MiniLM-L12-v2",
        device="auto"
    )

    print(f"   生成 {len(combined_df):,} 筆資料的 embeddings...")
    texts = combined_df['search_text'].tolist()
    embeddings = embedding_engine.encode(texts, batch_size=128, show_progress=True)

    # 儲存 embeddings
    embeddings_file = TIER1_DIR / "tier1_embeddings.npy"
    np.save(embeddings_file, embeddings)
    print(f"   ✓ Embeddings 已儲存: {embeddings_file.name}")
    print(f"   ✓ 向量維度: {embeddings.shape}")

    # 儲存 metadata
    metadata_file = TIER1_DIR / "tier1_metadata.csv"
    combined_df.to_csv(metadata_file, index=False, encoding='utf-8-sig')
    print(f"   ✓ Metadata 已儲存: {metadata_file.name}")

    print("\n" + "=" * 80)
    print("  ✅ Tier 1 資料更新完成")
    print("=" * 80)

    print(f"\n📝 摘要:")
    print(f"   原有資料: {len(existing_df):,} 筆")
    print(f"   新增資料: {len(new_unified_df):,} 筆")
    print(f"   重複排除: {len(duplicates):,} 筆")
    print(f"   更新後總計: {len(combined_df):,} 筆")

    print(f"\n🎯 新增資料涵蓋領域:")
    new_names_sample = new_unified_df['name'].head(20).tolist()
    for i, name in enumerate(new_names_sample, 1):
        print(f"   {i}. {name}")

    print(f"\n   ...等 {len(new_unified_df):,} 筆新資料")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  程序被用戶中斷")
    except Exception as e:
        print(f"\n\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
