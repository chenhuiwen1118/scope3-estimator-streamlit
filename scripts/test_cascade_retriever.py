#!/usr/bin/env python3
"""
測試三層級聯檢索器
"""

import sys
from pathlib import Path

# 加入 src 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from retrieval.cascade_retriever import CascadeRetriever


def main():
    print("=" * 70)
    print("🧪 三層級聯檢索器測試")
    print("=" * 70)

    # 初始化
    retriever = CascadeRetriever()

    # 顯示統計
    print("\n📊 資料庫統計:")
    stats = retriever.get_stats()
    for tier_name, tier_stats in stats.items():
        if tier_stats:
            print(f"\n   {tier_name.upper()}:")
            print(f"      記錄數: {tier_stats.get('total_records', 'N/A')}")

    # 測試查詢
    test_queries = [
        ("購買塑膠袋", "應該命中 Tier 1 (台灣本地)"),
        ("紙箱包裝", "應該命中 Tier 1 (台灣本地)"),
        ("牛肉採購", "應該命中 Tier 2 (國際產業)"),
        ("鋼材", "應該命中 Tier 2 (國際產業)"),
        ("購買軟體服務", "應該命中 Tier 3 (EEIO 模型)"),
        ("購買電腦設備", "可能命中多層"),
        ("不存在的產品XYZ123", "應該無結果")
    ]

    for query, expected in test_queries:
        print(f"\n" + "=" * 70)
        print(f"🔍 測試查詢: {query}")
        print(f"   預期: {expected}")
        print("=" * 70)

        result = retriever.search(query=query, top_k=3)

        if result['success']:
            print(f"\n✅ 成功")
            print(f"   層級: {result['tier_name']}")
            print(f"   訊息: {result['message']}")
            print(f"   找到 {len(result['matches'])} 個匹配")

            if result.get('warning'):
                print(f"\n⚠️  警告:")
                for line in result['warning'].split('\n'):
                    if line.strip():
                        print(f"   {line}")

            print(f"\n📋 最佳匹配:")
            best = result['best_match']
            if 'name' in best:
                name = best['name']
            elif 'product_name' in best:
                name = best['product_name']
            else:
                name = "Unknown"

            print(f"   名稱: {name[:60]}")
            print(f"   排放係數: {best['emission_factor']:.4f}")

            if 'unit' in best:
                print(f"   單位: {best['unit']}")
            elif 'unit_standard' in best:
                print(f"   單位: {best['unit_standard']}")

            print(f"   相似度: {best['similarity']:.4f}")

            if len(result['matches']) > 1:
                print(f"\n   其他候選:")
                for i, match in enumerate(result['matches'][1:], 2):
                    match_name = match.get('name') or match.get('product_name', 'Unknown')
                    print(f"      {i}. {match_name[:50]}... (相似度: {match['similarity']:.4f})")
        else:
            print(f"\n❌ 失敗")
            print(f"   訊息: {result['message']}")

    print(f"\n" + "=" * 70)
    print("✅ 測試完成！")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
