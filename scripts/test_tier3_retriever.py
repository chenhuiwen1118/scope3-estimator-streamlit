#!/usr/bin/env python3
"""
測試 Tier 3 EEIO 檢索器
"""

import sys
from pathlib import Path

# 加入 src 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from retrieval.tier3_eeio import Tier3EEIORetriever


def main():
    print("=" * 70)
    print("🧪 Tier 3 EEIO 檢索器測試")
    print("=" * 70)

    # 初始化
    retriever = Tier3EEIORetriever()

    # 顯示統計
    stats = retriever.get_stats()
    print(f"\n📊 資料庫統計:")
    print(f"   總記錄數: {stats['total_records']}")
    print(f"   國家數: {len(stats['countries'])}")
    print(f"   國家: {', '.join(stats['countries'])}")
    print(f"   Embedding 維度: {stats['embedding_dimension']}")

    # 測試查詢
    test_queries = [
        ("購買電腦設備", 300000, "TWD"),
        ("餐廳用餐", 50000, "TWD"),
        ("電力費用", 100000, "TWD"),
        ("鋼鐵材料", 200000, "TWD"),
        ("塑膠製品", 150000, "TWD")
    ]

    for query, amount, currency in test_queries:
        print(f"\n" + "=" * 70)
        print(f"🔍 查詢: {query} ({currency} {amount:,})")
        print("=" * 70)

        result = retriever.search_with_emissions(
            query=query,
            amount=amount,
            currency=currency,
            country_priority="TW",
            top_k=3,
            threshold=0.60
        )

        if result['success']:
            best = result['best_match']
            print(f"\n✅ 找到匹配")
            print(f"   最佳匹配: {best['country_name']} - {best['product_name']}")
            print(f"   排放係數: {best['emission_factor']:,.0f} kg CO2e/M.EUR")
            print(f"   相似度: {best['similarity']:.4f}")
            print(f"   優先國家: {'✓' if best['is_priority_country'] else '✗'}")
            print(f"   計算排放量: {result['emissions']:,.2f} kg CO2e")

            print(f"\n   其他候選:")
            for i, match in enumerate(result['matches'][1:], 2):
                priority_mark = '✓' if match['is_priority_country'] else '✗'
                print(f"      {i}. [{priority_mark}] {match['country_name']} - {match['product_name']} (相似度: {match['similarity']:.4f})")
        else:
            print(f"\n❌ {result['message']}")

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
