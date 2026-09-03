#!/usr/bin/env python3
"""
測試系統是否能完全離線運作
Test if the system can run completely offline
"""

import os
import sys
from pathlib import Path

# 強制離線模式
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

# 加入 src 路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_offline_mode():
    """測試離線模式"""

    print("=" * 70)
    print("🔒 測試系統離線運作能力")
    print("=" * 70)

    # 1. 測試環境變數
    print("\n📋 步驟 1: 檢查環境變數")
    print(f"   HF_HUB_OFFLINE: {os.environ.get('HF_HUB_OFFLINE', 'Not set')}")
    print(f"   TRANSFORMERS_OFFLINE: {os.environ.get('TRANSFORMERS_OFFLINE', 'Not set')}")

    # 2. 測試模型載入
    print("\n📋 步驟 2: 測試模型載入（離線模式）")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        print("   ✅ 模型載入成功（未訪問網路）")
    except Exception as e:
        print(f"   ❌ 模型載入失敗: {e}")
        print("\n   💡 可能需要先下載模型，請在有網路時執行：")
        print("      python3 -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')\"")
        return False

    # 3. 測試 EmbeddingEngine
    print("\n📋 步驟 3: 測試 EmbeddingEngine")
    try:
        from utils.embedding import EmbeddingEngine
        engine = EmbeddingEngine()
        print("   ✅ EmbeddingEngine 初始化成功")
    except Exception as e:
        print(f"   ❌ EmbeddingEngine 初始化失敗: {e}")
        return False

    # 4. 測試編碼
    print("\n📋 步驟 4: 測試文本編碼")
    try:
        test_texts = ["購買筆記型電腦", "Laptop Computer"]
        embeddings = engine.encode(test_texts)
        print(f"   ✅ 編碼成功，shape: {embeddings.shape}")
    except Exception as e:
        print(f"   ❌ 編碼失敗: {e}")
        return False

    # 5. 測試檢索器
    print("\n📋 步驟 5: 測試 CascadeRetriever")
    try:
        from retrieval.cascade_retriever import CascadeRetriever
        retriever = CascadeRetriever()
        print("   ✅ CascadeRetriever 初始化成功")
    except Exception as e:
        print(f"   ❌ CascadeRetriever 初始化失敗: {e}")
        return False

    # 6. 測試查詢
    print("\n📋 步驟 6: 測試查詢功能")
    try:
        result = retriever.search("購買塑膠袋", top_k=3)
        if result['success']:
            print(f"   ✅ 查詢成功")
            print(f"      層級: {result['tier_name']}")
            print(f"      最佳匹配: {result['best_match'].get('name', 'N/A')[:50]}")
            print(f"      相似度: {result['best_match']['similarity']:.4f}")
        else:
            print(f"   ⚠️  查詢無結果: {result['message']}")
    except Exception as e:
        print(f"   ❌ 查詢失敗: {e}")
        return False

    # 完成
    print("\n" + "=" * 70)
    print("✅ 所有測試通過！系統可完全離線運作")
    print("=" * 70)

    return True

if __name__ == "__main__":
    success = test_offline_mode()
    sys.exit(0 if success else 1)
