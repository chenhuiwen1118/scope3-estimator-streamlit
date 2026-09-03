#!/usr/bin/env python3
"""
建立 Tier 1 台灣環保署資料的 Embedding 向量
使用 Sentence Transformers 進行向量化
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# 加入 src 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.embedding import EmbeddingEngine

# 路徑設定
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "emission_factors" / "tier1_local"
INPUT_FILE = DATA_DIR / "tier1_unified.csv"
OUTPUT_EMBEDDINGS = DATA_DIR / "tier1_embeddings.npy"
OUTPUT_METADATA = DATA_DIR / "tier1_metadata.csv"

print("=" * 70)
print("🚀 Tier 1 Embedding 向量生成")
print("=" * 70)


def main():
    """主流程"""

    # 1. 載入資料
    print(f"\n📂 載入資料: {INPUT_FILE.name}")
    df = pd.read_csv(INPUT_FILE)
    print(f"   ✓ 載入 {len(df)} 筆記錄")

    # 2. 準備文本
    print("\n📝 準備搜尋文本...")
    texts = df['search_text'].tolist()
    print(f"   ✓ {len(texts)} 個文本")

    # 範例文本
    print("\n📋 範例文本 (前 5 個):")
    for i, text in enumerate(texts[:5], 1):
        print(f"   {i}. {text[:80]}...")

    # 3. 初始化 Embedding 引擎
    print("\n🔧 初始化 Embedding 引擎...")
    engine = EmbeddingEngine(
        model_name="paraphrase-multilingual-MiniLM-L12-v2",
        device="auto"  # 自動選擇 GPU/CPU
    )
    print(f"   ✓ 模型: {engine.model_name}")
    print(f"   ✓ 設備: {engine.device}")

    # 4. 生成 Embedding
    print("\n⚡ 生成 Embedding 向量...")
    print("   (這應該很快...)")

    embeddings = engine.encode(
        texts,
        batch_size=32,
        show_progress=True,
        normalize=True  # 歸一化以便計算 cosine similarity
    )

    print(f"\n   ✓ 向量矩陣形狀: {embeddings.shape}")
    print(f"   ✓ 向量維度: {embeddings.shape[1]}")
    print(f"   ✓ 記憶體使用: {embeddings.nbytes / 1024 / 1024:.2f} MB")

    # 5. 儲存 Embedding 向量
    print(f"\n💾 儲存 Embedding 向量: {OUTPUT_EMBEDDINGS.name}")
    np.save(OUTPUT_EMBEDDINGS, embeddings)
    print(f"   ✓ 已儲存 (檔案大小: {OUTPUT_EMBEDDINGS.stat().st_size / 1024 / 1024:.2f} MB)")

    # 6. 儲存元資料（不含 search_text，減少檔案大小）
    print(f"\n💾 儲存元資料: {OUTPUT_METADATA.name}")
    metadata = df.drop(columns=['search_text'])
    metadata.to_csv(OUTPUT_METADATA, index=False, encoding='utf-8')
    print(f"   ✓ 已儲存 (檔案大小: {OUTPUT_METADATA.stat().st_size / 1024:.2f} KB)")

    # 7. 驗證向量品質
    print("\n🔍 驗證向量品質...")

    # 測試幾個相似度
    test_pairs = [
        (0, 1),   # 前兩個
        (0, 10),  # 距離較遠
        (0, 50)   # 距離更遠
    ]

    from utils.similarity import cosine_similarity

    print("   相似度測試:")
    for i, j in test_pairs:
        if j < len(embeddings):
            sim = cosine_similarity(embeddings[i], embeddings[j])
            name_i = df.iloc[i]['name'][:30]
            name_j = df.iloc[j]['name'][:30]
            print(f"      [{i}] {name_i}... vs")
            print(f"      [{j}] {name_j}...")
            print(f"      → 相似度: {sim:.4f}")

    # 8. 統計資訊
    print("\n📊 最終統計:")
    print(f"   總記錄數: {len(df)}")
    print(f"   Embedding 向量數: {embeddings.shape[0]}")
    print(f"   向量維度: {embeddings.shape[1]}")
    print(f"   年度分布:")
    for year, count in df['base_year'].value_counts().head(5).items():
        print(f"      - {int(year)}: {count}")

    print("\n" + "=" * 70)
    print("✅ Tier 1 Embedding 向量生成完成！")
    print("=" * 70)
    print(f"\n📦 生成檔案:")
    print(f"   1. {OUTPUT_EMBEDDINGS}")
    print(f"   2. {OUTPUT_METADATA}")


if __name__ == "__main__":
    main()
