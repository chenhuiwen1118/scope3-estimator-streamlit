#!/usr/bin/env python3
"""
快速測試檢索器是否正常運作
"""

import sys
from pathlib import Path

# 加入 src 路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from retrieval.cascade_retriever import CascadeRetriever

print("=" * 80)
print("🧪 檢索器快速測試")
print("=" * 80)

# 初始化檢索器
print("\n正在初始化檢索器...")
retriever = CascadeRetriever()

# 取得統計資訊
print("\n📊 資料庫統計:")
stats = retriever.get_stats()

for tier_name, tier_stats in stats.items():
    if tier_stats:
        print(f"\n{tier_name.upper()}:")
        print(f"   總記錄數: {tier_stats['total_records']:,}")
        if 'sources' in tier_stats:
            print(f"   資料來源數: {len(tier_stats['sources'])}")
        if 'scope3_categories' in tier_stats:
            print(f"   Scope 3 類別: {len(tier_stats['scope3_categories'])} 類")

# 測試查詢
test_queries = [
    "購買牛肉",
    "電力消耗",
    "商務航空旅行",
    "塑膠包裝材料"
]

for query in test_queries:
    print(f"\n{'=' * 80}")
    print(f"🔍 查詢: {query}")
    print("=" * 80)

    results = retriever.search(
        query=query,
        top_k=3
    )

    if results['success'] and results['matches']:
        print(f"\n✅ 找到 {len(results['matches'])} 個匹配")
        print(f"使用 Tier: {results['tier']} ({results.get('tier_name', '')})")
        if results.get('warning'):
            print(f"⚠️  {results['warning']}")

        for i, match in enumerate(results['matches'], 1):
            print(f"\n   {i}. {match['name'][:60]}")
            print(f"      排放係數: {match['emission_factor']:.4f} kg CO2e/{match.get('unit', 'unknown')}")
            print(f"      來源: {match['source']}")
            if 'scope3_category' in match:
                print(f"      Scope 3: Category {match['scope3_category']}")
            print(f"      相似度: {match['similarity']:.4f}")
    else:
        print(f"\n❌ 無符合門檻的結果")

print("\n" + "=" * 80)
print("✅ 測試完成")
print("=" * 80)
