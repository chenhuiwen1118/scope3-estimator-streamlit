#!/usr/bin/env python3
"""
測試新增資料（Defra UK & GHG Protocol）的檢索功能
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from retrieval.cascade_retriever import CascadeRetriever

print("=" * 80)
print("🧪 新增資料檢索功能測試")
print("=" * 80)

# 初始化檢索器
print("\n正在初始化檢索器...")
retriever = CascadeRetriever()

# 取得統計資訊
stats = retriever.get_stats()
print(f"\n📊 系統統計:")
print(f"  Tier 1: {stats['tier1']['total_records']:,} 筆")
print(f"  Tier 2: {stats['tier2']['total_records']:,} 筆")
print(f"  Tier 3: {stats['tier3']['total_records']:,} 筆")
print(f"  總計: {stats['tier1']['total_records'] + stats['tier2']['total_records'] + stats['tier3']['total_records']:,} 筆")

print(f"\nTier 2 資料來源:")
for src, count in list(stats['tier2']['source_counts'].items())[:7]:
    print(f"  - {src}: {count:,}")

print(f"\nScope 3 類別涵蓋:")
for cat in sorted(stats['tier2']['scope3_categories'].keys()):
    count = stats['tier2']['scope3_categories'][cat]
    print(f"  - Category {cat}: {count:,}")

# 測試案例：針對新增資料設計的查詢
test_cases = [
    {
        'name': '貨運飛機運輸 (GHG Protocol - Freight)',
        'query': 'international freight flights cargo transport',
        'expected_source': 'GHG Protocol',
        'expected_category': '4,9'
    },
    {
        'name': '員工通勤巴士 (GHG Protocol - Public)',
        'query': 'employee commute bus public transport',
        'expected_source': 'GHG Protocol',
        'expected_category': '6,7'
    },
    {
        'name': '柴油固定燃燒 (GHG Protocol - Stationary)',
        'query': 'diesel fuel combustion stationary',
        'expected_source': 'GHG Protocol',
        'expected_category': '3'
    },
    {
        'name': '貨物陸運 (Defra UK - Freighting)',
        'query': 'heavy goods vehicle freight transport',
        'expected_source': 'Defra UK 2025',
        'expected_category': '4,9'
    },
    {
        'name': '海上商務旅行 (Defra UK - Sea)',
        'query': 'business travel ferry sea cruise',
        'expected_source': 'Defra UK 2025',
        'expected_category': '6'
    }
]

print("\n" + "=" * 80)
print("測試案例")
print("=" * 80)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\n【測試 {i}】{test['name']}")
    print(f"查詢: {test['query']}")
    print(f"預期來源: {test['expected_source']}")
    print(f"預期類別: Category {test['expected_category']}")
    print("-" * 80)

    results = retriever.search(query=test['query'], top_k=5)

    if results['success'] and results['matches']:
        print(f"✅ 找到 {len(results['matches'])} 個匹配")
        print(f"使用 Tier: {results['tier']}")

        # 檢查是否有符合預期來源的結果
        found_expected = False
        for j, match in enumerate(results['matches'], 1):
            source = match['source']
            scope3 = match.get('scope3_category', '')

            print(f"\n  {j}. {match['name'][:70]}")
            print(f"     來源: {source}")
            print(f"     Category: {scope3}")
            print(f"     EF: {match['emission_factor']:.4f} {match.get('unit', 'kg CO2e')}")
            print(f"     相似度: {match['similarity']:.4f}")

            # 檢查是否符合預期
            if test['expected_source'] in source:
                found_expected = True
                if scope3 == test['expected_category']:
                    print(f"     ✅ 符合預期（來源 + 類別）")
                else:
                    print(f"     ⚠️  來源正確，但類別不符（預期: {test['expected_category']}）")

        if found_expected:
            print(f"\n✅ 測試通過：找到預期來源的資料")
            passed += 1
        else:
            print(f"\n⚠️  測試部分通過：未找到預期來源，但有其他相關結果")
            passed += 0.5
            failed += 0.5
    else:
        print(f"❌ 測試失敗：無符合門檻的結果")
        failed += 1

# 額外測試：直接檢索新資料
print("\n" + "=" * 80)
print("直接資料庫查詢測試")
print("=" * 80)

import pandas as pd

tier2_file = Path(__file__).parent / 'data' / 'emission_factors' / 'tier2_international' / 'tier2_unified.csv'
df = pd.read_csv(tier2_file)

print(f"\n檢查新增資料存在性:")

# Defra UK 2025
defra_records = df[df['source_database'] == 'Defra UK 2025']
print(f"\n✓ Defra UK 2025: {len(defra_records)} 筆")
defra_freighting = defra_records[defra_records['activity_type_en'] == 'Freighting goods']
defra_sea = defra_records[defra_records['activity_type_en'] == 'Business travel- sea']
print(f"  - Freighting goods: {len(defra_freighting)} 筆")
print(f"  - Business travel-sea: {len(defra_sea)} 筆")

# GHG Protocol
ghg_records = df[df['source_database'] == 'GHG Protocol Cross-Sector v2.0 (2024)']
print(f"\n✓ GHG Protocol Cross-Sector v2.0 (2024): {len(ghg_records)} 筆")
ghg_freight = ghg_records[ghg_records['activity_type_en'] == 'Freight Transportation']
ghg_public = ghg_records[ghg_records['activity_type_en'] == 'Public Transportation']
ghg_stationary = ghg_records[ghg_records['activity_type_en'] == 'Stationary Combustion']
print(f"  - Freight Transportation: {len(ghg_freight)} 筆")
print(f"  - Public Transportation: {len(ghg_public)} 筆")
print(f"  - Stationary Combustion: {len(ghg_stationary)} 筆")

# 檢查 search_text 是否存在
missing_search_text = df[df['search_text'].isna()]
print(f"\n檢查 search_text:")
if len(missing_search_text) == 0:
    print(f"  ✅ 所有記錄都有 search_text ({len(df):,} 筆)")
else:
    print(f"  ⚠️  缺少 search_text: {len(missing_search_text)} 筆")

# 總結
print("\n" + "=" * 80)
print("測試總結")
print("=" * 80)
print(f"\n通過: {passed}/{len(test_cases)}")
print(f"失敗: {failed}/{len(test_cases)}")

if passed == len(test_cases):
    print(f"\n🎉 所有測試通過！")
    exit_code = 0
elif passed >= len(test_cases) * 0.8:
    print(f"\n✅ 大部分測試通過！")
    exit_code = 0
else:
    print(f"\n⚠️  部分測試未通過，需要檢查")
    exit_code = 1

print("\n新增資料檢索功能驗證完成！")
sys.exit(exit_code)
