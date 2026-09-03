#!/usr/bin/env python3
"""
生成 Tier 3 EEIO 資料的 Embedding 向量
使用 sentence-transformers 進行向量化
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# 加入 src 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.embedding import EmbeddingEngine

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data" / "emission_factors" / "tier3_eeio"
INPUT_FILE = DATA_DIR / "tier3_eeio_unified.csv"
OUTPUT_FILE = DATA_DIR / "tier3_eeio_embeddings.npy"
METADATA_FILE = DATA_DIR / "tier3_eeio_metadata.csv"


def build_embeddings():
    """
    生成 Tier 3 EEIO 資料的向量
    """
    print("=" * 70)
    print("🚀 生成 Tier 3 EEIO Embedding 向量")
    print("=" * 70)

    # 1. 載入資料
    print(f"\n📂 載入資料: {INPUT_FILE.name}")
    df = pd.read_csv(INPUT_FILE)
    print(f"   ✓ 載入 {len(df)} 筆記錄")

    # 檢查 search_text 欄位
    if 'search_text' not in df.columns:
        print("   ❌ 錯誤: 找不到 'search_text' 欄位")
        return

    # 2. 初始化 Embedding 引擎
    print(f"\n🤖 初始化 Embedding 引擎...")
    try:
        engine = EmbeddingEngine(
            model_name="paraphrase-multilingual-MiniLM-L12-v2",
            device="auto"
        )
        print(f"   ✓ 模型載入成功")
        print(f"   ✓ Embedding 維度: {engine.get_dimension()}")
    except Exception as e:
        print(f"   ❌ 模型載入失敗: {e}")
        return

    # 3. 批次向量化
    print(f"\n🔄 開始向量化...")
    texts = df['search_text'].tolist()

    try:
        embeddings = engine.encode(
            texts,
            batch_size=32,
            show_progress=True,
            convert_to_numpy=True,
            normalize=True  # 正規化向量（用於餘弦相似度）
        )
        print(f"   ✓ 向量化完成")
        print(f"   ✓ 向量矩陣形狀: {embeddings.shape}")
    except Exception as e:
        print(f"   ❌ 向量化失敗: {e}")
        return

    # 4. 儲存向量
    print(f"\n💾 儲存向量...")
    np.save(OUTPUT_FILE, embeddings)
    print(f"   ✓ 已儲存: {OUTPUT_FILE.name}")
    print(f"   📊 檔案大小: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.2f} MB")

    # 5. 儲存元資料（輕量版，用於快速載入）
    print(f"\n💾 儲存元資料...")
    metadata_cols = [
        'source', 'country', 'country_name', 'product_id', 'product_name',
        'product_code', 'emission_factor_per_meur', 'unit', 'base_year',
        'tier'
    ]
    metadata_df = df[metadata_cols].copy()
    metadata_df.to_csv(METADATA_FILE, index=False, encoding='utf-8-sig')
    print(f"   ✓ 已儲存: {METADATA_FILE.name}")
    print(f"   📊 檔案大小: {METADATA_FILE.stat().st_size / 1024:.1f} KB")

    # 6. 驗證向量品質
    print(f"\n🔍 驗證向量品質...")

    # 計算向量範數
    norms = np.linalg.norm(embeddings, axis=1)
    print(f"   向量範數統計:")
    print(f"      平均: {norms.mean():.4f}")
    print(f"      最小: {norms.min():.4f}")
    print(f"      最大: {norms.max():.4f}")

    # 測試相似度計算
    print(f"\n   測試相似度計算:")
    test_pairs = [
        (0, 1),    # 稻米 vs 小麥
        (0, 200),  # 台灣稻米 vs 英國稻米
        (0, 100),  # 稻米 vs 某個工業產品（應該不相似）
    ]

    for idx1, idx2 in test_pairs:
        if idx2 < len(embeddings):
            sim = np.dot(embeddings[idx1], embeddings[idx2])
            name1 = df.iloc[idx1]['product_name']
            name2 = df.iloc[idx2]['product_name']
            country1 = df.iloc[idx1]['country']
            country2 = df.iloc[idx2]['country']
            print(f"      {country1}-{name1} ↔ {country2}-{name2}: {sim:.4f}")

    # 7. 完成
    print("\n" + "=" * 70)
    print("✅ 完成！")
    print("=" * 70)

    print(f"\n📁 生成的檔案:")
    print(f"   1. {OUTPUT_FILE.name} ({OUTPUT_FILE.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"   2. {METADATA_FILE.name} ({METADATA_FILE.stat().st_size / 1024:.1f} KB)")

    print(f"\n✨ 下一步:")
    print(f"   1. 建立 Tier3EEIORetriever 檢索類別")
    print(f"   2. 整合到主檢索系統")
    print(f"   3. 測試檢索準確性")


if __name__ == "__main__":
    try:
        build_embeddings()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
