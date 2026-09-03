#!/usr/bin/env python3
"""
測試台灣採購資料與排放係數的配對成功率
重點：驗證 Tier 1 (台灣本地係數) 的使用率
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from tqdm import tqdm

# 加入 src 路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from retrieval.cascade_retriever import CascadeRetriever

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "training_data" / "annotated"

def main():
    print("=" * 80)
    print("  🧪 台灣採購資料與排放係數配對成功率測試")
    print("=" * 80)
    print("\n📌 測試重點：驗證 Tier 1 (台灣本地排放係數) 使用率")
    print("   預期：Tier 1 使用率應顯著高於國際資料測試的 7.5%\n")

    # 初始化檢索器
    print("🔧 初始化三層級聯檢索器...")
    retriever = CascadeRetriever()

    # 顯示資料庫統計
    stats = retriever.get_stats()
    print("\n📊 排放係數資料庫統計:")
    for tier_name, tier_stats in stats.items():
        if tier_stats:
            count = tier_stats.get('total_records', 'N/A')
            print(f"   {tier_name}: {count:,} 筆")

    # 讀取台灣採購資料
    print("\n📥 讀取台灣採購資料...")
    tw_file = DATA_DIR / "taiwan_govt_procurement_2024_h2_annotated.csv"

    if not tw_file.exists():
        print(f"❌ 找不到檔案: {tw_file}")
        sys.exit(1)

    tw_df = pd.read_csv(tw_file, encoding='utf-8-sig')
    print(f"   台灣政府採購: {len(tw_df):,} 筆")

    # 抽樣測試（避免太慢）
    sample_size = 500  # 測試 500 筆
    print(f"\n🎲 隨機抽樣測試（{sample_size} 筆）...")

    test_samples = tw_df.sample(n=min(sample_size, len(tw_df)), random_state=42)
    print(f"   測試樣本數: {len(test_samples):,} 筆")

    # 分層統計
    print(f"\n📈 測試樣本分布:")
    print(f"   Category 1: {(test_samples['ghg_category'] == 1).sum()} 筆")
    print(f"   Category 2: {(test_samples['ghg_category'] == 2).sum()} 筆")

    print(f"\n   採購性質分布:")
    for attr, count in test_samples['procurement_attr'].value_counts().items():
        pct = count / len(test_samples) * 100
        print(f"      {attr}: {count} 筆 ({pct:.1f}%)")

    # 進行配對測試
    print(f"\n🔍 開始配對測試...")
    print(f"   配對門檻: Tier 1 >= 0.8 | Tier 2 >= 0.7 | Tier 3 >= 0.6")
    print()

    results = []

    for idx, row in tqdm(test_samples.iterrows(), total=len(test_samples), desc="配對進度"):
        description = str(row['case_name'])  # 使用標案名稱

        # 使用瀑布式檢索器進行配對
        try:
            match_result = retriever.search(query=description, top_k=3)

            if match_result['success']:
                best_match = match_result['best_match']
                results.append({
                    'org_name': row['org_name'],
                    'case_name': description[:80],
                    'procurement_attr': row['procurement_attr'],
                    'amount': row['award_price_num'],
                    'ghg_category': row['ghg_category'],
                    'matched': True,
                    'tier': match_result['tier_name'],
                    'similarity': best_match['similarity'],
                    'ef_name': best_match.get('name') or best_match.get('product_name', 'Unknown'),
                    'ef_value': best_match['emission_factor'],
                    'ef_unit': best_match.get('unit') or best_match.get('unit_standard', ''),
                })
            else:
                results.append({
                    'org_name': row['org_name'],
                    'case_name': description[:80],
                    'procurement_attr': row['procurement_attr'],
                    'amount': row['award_price_num'],
                    'ghg_category': row['ghg_category'],
                    'matched': False,
                    'tier': None,
                    'similarity': 0.0,
                    'ef_name': None,
                    'ef_value': None,
                    'ef_unit': None,
                })
        except Exception as e:
            print(f"\n   ⚠️  配對錯誤 [{idx}]: {e}")
            results.append({
                'org_name': row['org_name'],
                'case_name': description[:80],
                'procurement_attr': row['procurement_attr'],
                'amount': row['award_price_num'],
                'ghg_category': row['ghg_category'],
                'matched': False,
                'tier': 'ERROR',
                'similarity': 0.0,
                'ef_name': str(e),
                'ef_value': None,
                'ef_unit': None,
            })

    # 建立結果 DataFrame
    results_df = pd.DataFrame(results)

    # 統計分析
    print("\n" + "=" * 80)
    print("  📊 配對成功率統計")
    print("=" * 80)

    total = len(results_df)
    matched = results_df['matched'].sum()
    match_rate = matched / total * 100

    print(f"\n✅ 整體配對成功率: {matched}/{total} = {match_rate:.1f}%")

    # 按 Tier 統計
    print(f"\n📊 各層級配對分布:")
    tier_counts = results_df[results_df['matched']]['tier'].value_counts()
    for tier, count in tier_counts.items():
        pct = count / matched * 100 if matched > 0 else 0
        print(f"   {tier}: {count} 筆 ({pct:.1f}%)")

    # 重點：Tier 1 使用率
    tier1_count = tier_counts.get('Tier 1 - 台灣本地資料庫', 0)
    tier1_rate = tier1_count / matched * 100 if matched > 0 else 0
    print(f"\n🎯 Tier 1 (台灣本地) 使用率: {tier1_count}/{matched} = {tier1_rate:.1f}%")
    print(f"   對比國際資料測試: 7.5% → {tier1_rate:.1f}%")
    if tier1_rate > 7.5:
        improvement = tier1_rate - 7.5
        print(f"   ✅ 提升 {improvement:.1f} 個百分點！")
    else:
        print(f"   ⚠️  未見明顯提升")

    # 按採購性質統計
    print(f"\n🏭 各採購性質配對成功率:")
    for attr in results_df['procurement_attr'].unique():
        attr_df = results_df[results_df['procurement_attr'] == attr]
        attr_matched = attr_df['matched'].sum()
        attr_rate = attr_matched / len(attr_df) * 100 if len(attr_df) > 0 else 0
        print(f"   {attr}: {attr_matched}/{len(attr_df)} = {attr_rate:.1f}%")

        # 各性質的 Tier 分布
        if attr_matched > 0:
            attr_tier_counts = attr_df[attr_df['matched']]['tier'].value_counts()
            for tier, count in attr_tier_counts.items():
                tier_pct = count / attr_matched * 100
                print(f"      └─ {tier}: {count} 筆 ({tier_pct:.1f}%)")

    # 按 GHG Category 統計
    print(f"\n📦 各 Category 配對成功率:")
    for cat in sorted(results_df['ghg_category'].dropna().unique()):
        cat_df = results_df[results_df['ghg_category'] == cat]
        cat_matched = cat_df['matched'].sum()
        cat_rate = cat_matched / len(cat_df) * 100 if len(cat_df) > 0 else 0
        print(f"   Category {int(cat)}: {cat_matched}/{len(cat_df)} = {cat_rate:.1f}%")

    # 相似度分析
    matched_df = results_df[results_df['matched']]
    if len(matched_df) > 0:
        print(f"\n📈 相似度分布:")
        print(f"   平均相似度: {matched_df['similarity'].mean():.3f}")
        print(f"   中位數: {matched_df['similarity'].median():.3f}")
        print(f"   最小值: {matched_df['similarity'].min():.3f}")
        print(f"   最大值: {matched_df['similarity'].max():.3f}")

        # 相似度區間分布
        print(f"\n   相似度區間分布:")
        bins = [0, 0.6, 0.7, 0.8, 0.9, 1.0]
        labels = ['<0.6', '0.6-0.7', '0.7-0.8', '0.8-0.9', '0.9-1.0']
        matched_df['similarity_bin'] = pd.cut(matched_df['similarity'], bins=bins, labels=labels)
        bin_counts = matched_df['similarity_bin'].value_counts().sort_index()
        for bin_label, count in bin_counts.items():
            pct = count / len(matched_df) * 100
            print(f"      {bin_label}: {count} 筆 ({pct:.1f}%)")

    # 失敗案例分析
    unmatched_df = results_df[~results_df['matched']]
    if len(unmatched_df) > 0:
        print(f"\n❌ 配對失敗案例分析 ({len(unmatched_df)} 筆):")
        print(f"\n   典型失敗案例（前 10 筆）:")
        for idx, row in unmatched_df.head(10).iterrows():
            print(f"\n   [{idx}] {row['org_name']}")
            print(f"      {row['case_name']}")
            print(f"      性質: {row['procurement_attr']} | 金額: ${row['amount']:,.0f}")

    # Tier 1 成功配對案例展示
    tier1_df = results_df[results_df['tier'] == 'Tier 1 - 台灣本地資料庫']
    if len(tier1_df) > 0:
        print(f"\n🇹🇼 Tier 1 (台灣本地) 成功配對案例（前 10 筆）:")
        for idx, row in tier1_df.head(10).iterrows():
            print(f"\n   [{idx}] {row['org_name']}")
            print(f"      {row['case_name']}")
            print(f"      → 排放係數: {row['ef_name']}")
            print(f"      → 係數值: {row['ef_value']} {row['ef_unit']}")
            print(f"      → 相似度: {row['similarity']:.3f}")

    # 儲存詳細結果
    output_file = PROJECT_ROOT / "data" / "training_data" / "review" / "taiwan_emission_matching_test_20260129.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 詳細結果已儲存: {output_file.name}")

    # 總結
    print("\n" + "=" * 80)
    print("  🎯 測試總結")
    print("=" * 80)

    if match_rate >= 90:
        emoji = "🎉"
        verdict = "優秀！"
    elif match_rate >= 75:
        emoji = "✅"
        verdict = "良好"
    elif match_rate >= 60:
        emoji = "⚠️"
        verdict = "尚可，需優化"
    else:
        emoji = "❌"
        verdict = "不佳，需大幅改進"

    print(f"\n{emoji} 配對成功率: {match_rate:.1f}% - {verdict}")
    print(f"   測試樣本: {total:,} 筆")
    print(f"   成功配對: {matched:,} 筆")
    print(f"   配對失敗: {total - matched:,} 筆")

    print(f"\n🇹🇼 Tier 1 (台灣本地) 使用分析:")
    print(f"   使用率: {tier1_rate:.1f}%")
    if tier1_rate < 20:
        print(f"   ⚠️  Tier 1 使用率偏低")
        print(f"   建議: 擴充台灣本地排放係數資料庫涵蓋範圍")
    elif tier1_rate < 40:
        print(f"   ✅ Tier 1 使用率合理")
    else:
        print(f"   🎉 Tier 1 使用率優秀！")

    if match_rate < 90:
        print(f"\n💡 改進建議:")
        if tier_counts.get('Tier 3 - EEIO 模型', 0) / matched > 0.5:
            print(f"   1. Tier 3 使用率過高 ({tier_counts.get('Tier 3 - EEIO 模型', 0) / matched * 100:.1f}%)")
            print(f"      → 擴充 Tier 1 和 Tier 2 資料庫涵蓋範圍")
        if matched_df['similarity'].mean() < 0.75:
            print(f"   2. 平均相似度偏低 ({matched_df['similarity'].mean():.3f})")
            print(f"      → 改進 Embedding 模型或增加同義詞/翻譯")
        if len(unmatched_df) > total * 0.15:
            print(f"   3. 失敗率偏高 ({len(unmatched_df) / total * 100:.1f}%)")
            print(f"      → 降低配對門檻或擴充產業覆蓋")

    print("\n" + "=" * 80)
    print("  ✅ 測試完成！")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  測試被用戶中斷")
    except Exception as e:
        print(f"\n\n❌ 測試錯誤: {e}")
        import traceback
        traceback.print_exc()
