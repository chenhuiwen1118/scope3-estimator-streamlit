#!/usr/bin/env python3
"""
使用合成採購資料測試排放係數配對系統

方法論依據：
- Jain et al. (2023) - Scope 3 LLM 研究
- 金融 NLP 與 ESG NLP 領域的合成資料驗證方法
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
DATA_DIR = PROJECT_ROOT / "data" / "synthetic"

def main():
    print("=" * 80)
    print("  🧪 合成採購資料排放係數配對測試")
    print("=" * 80)
    print("\n📌 測試方法：使用結構化合成資料驗證配對系統")
    print("   參考：Jain et al. (2023) Scope 3 LLM 研究")
    print("   🔧 實驗：Tier 1 門檻調整至 0.7（原 0.8）\n")

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

    # 讀取合成採購資料
    print("\n📥 讀取合成採購資料...")
    en_file = DATA_DIR / "synthetic_procurement_en_1000.csv"
    zh_file = DATA_DIR / "synthetic_procurement_zh_1000.csv"

    if not en_file.exists():
        print(f"❌ 找不到檔案: {en_file}")
        sys.exit(1)

    df_en = pd.read_csv(en_file, encoding='utf-8-sig')
    df_zh = pd.read_csv(zh_file, encoding='utf-8-sig')

    print(f"   英文資料: {len(df_en):,} 筆")
    print(f"   中文資料: {len(df_zh):,} 筆")
    print(f"   總計: {len(df_en) + len(df_zh):,} 筆")

    # 測試英文資料
    print("\n" + "=" * 80)
    print("  📝 測試 1: 英文合成採購資料")
    print("=" * 80)

    results_en = test_dataset(df_en, retriever, "English")

    # 測試中文資料
    print("\n" + "=" * 80)
    print("  📝 測試 2: 中文合成採購資料")
    print("=" * 80)

    results_zh = test_dataset(df_zh, retriever, "Chinese")

    # 合併結果分析
    print("\n" + "=" * 80)
    print("  📊 綜合分析")
    print("=" * 80)

    all_results = pd.concat([results_en, results_zh], ignore_index=True)

    total = len(all_results)
    matched = all_results['matched'].sum()
    match_rate = matched / total * 100

    print(f"\n✅ 整體配對成功率: {matched}/{total} = {match_rate:.1f}%")

    # 按語言統計
    print(f"\n🌐 各語言配對成功率:")
    for lang in ["English", "Chinese"]:
        lang_df = all_results[all_results['language'] == lang]
        lang_matched = lang_df['matched'].sum()
        lang_rate = lang_matched / len(lang_df) * 100
        print(f"   {lang}: {lang_matched}/{len(lang_df)} = {lang_rate:.1f}%")

    # 按 Tier 統計
    matched_df = all_results[all_results['matched']]
    if len(matched_df) > 0:
        print(f"\n📊 各層級配對分布:")
        tier_counts = matched_df['tier'].value_counts()
        for tier, count in tier_counts.items():
            pct = count / matched * 100
            print(f"   {tier}: {count} 筆 ({pct:.1f}%)")

    # 按 Scenario 統計
    print(f"\n🏭 各情境配對成功率:")
    for scenario in all_results['scenario'].unique():
        scenario_df = all_results[all_results['scenario'] == scenario]
        scenario_matched = scenario_df['matched'].sum()
        scenario_rate = scenario_matched / len(scenario_df) * 100
        print(f"   {scenario}: {scenario_matched}/{len(scenario_df)} = {scenario_rate:.1f}%")

    # 按 GHG Category 統計
    print(f"\n📦 各 GHG Category 配對成功率:")
    for cat in sorted(all_results['ghg_category'].unique()):
        cat_df = all_results[all_results['ghg_category'] == cat]
        cat_matched = cat_df['matched'].sum()
        cat_rate = cat_matched / len(cat_df) * 100
        print(f"   Category {int(cat)}: {cat_matched}/{len(cat_df)} = {cat_rate:.1f}%")

    # 相似度分析
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
    unmatched_df = all_results[~all_results['matched']]
    if len(unmatched_df) > 0:
        print(f"\n❌ 配對失敗案例分析 ({len(unmatched_df)} 筆):")

        # 按情境統計失敗率
        print(f"\n   各情境失敗率:")
        for scenario in unmatched_df['scenario'].unique():
            scenario_unmatched = len(unmatched_df[unmatched_df['scenario'] == scenario])
            scenario_total = len(all_results[all_results['scenario'] == scenario])
            fail_rate = scenario_unmatched / scenario_total * 100
            print(f"      {scenario}: {scenario_unmatched}/{scenario_total} ({fail_rate:.1f}%)")

        print(f"\n   典型失敗案例（前 10 筆）:")
        for idx, row in unmatched_df.head(10).iterrows():
            print(f"\n   [{idx}] {row['description']}")
            print(f"      情境: {row['scenario']} | Category: {int(row['ghg_category'])} | 金額: ${row['amount']:,.2f}")

    # 成功案例展示
    print(f"\n✅ 優質配對案例（相似度 > 0.85）:")
    high_quality = matched_df[matched_df['similarity'] > 0.85].head(10)
    for idx, row in high_quality.iterrows():
        print(f"\n   [{idx}] {row['description']}")
        print(f"      → 排放係數: {row['ef_name']}")
        print(f"      → 係數值: {row['ef_value']} {row['ef_unit']}")
        print(f"      → 層級: {row['tier']} | 相似度: {row['similarity']:.3f}")

    # 儲存詳細結果
    output_file = PROJECT_ROOT / "data" / "training_data" / "review" / "synthetic_emission_matching_test_20260129.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    all_results.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 詳細結果已儲存: {output_file.name}")

    # 總結
    print("\n" + "=" * 80)
    print("  🎯 測試總結")
    print("=" * 80)

    if match_rate >= 90:
        emoji = "🎉"
        verdict = "優秀！配對系統運作良好"
    elif match_rate >= 75:
        emoji = "✅"
        verdict = "良好，配對系統可接受"
    elif match_rate >= 60:
        emoji = "⚠️"
        verdict = "尚可，需要優化"
    else:
        emoji = "❌"
        verdict = "不佳，需大幅改進"

    print(f"\n{emoji} 配對成功率: {match_rate:.1f}% - {verdict}")
    print(f"   測試樣本: {total:,} 筆合成採購資料")
    print(f"   成功配對: {matched:,} 筆")
    print(f"   配對失敗: {total - matched:,} 筆")

    print(f"\n📊 資料庫覆蓋率分析:")
    tier1_rate = tier_counts.get('Tier 1 - 台灣本地', 0) / matched * 100 if matched > 0 else 0
    tier2_rate = tier_counts.get('Tier 2 - 國際產業', 0) / matched * 100 if matched > 0 else 0
    tier3_rate = tier_counts.get('Tier 3 - EEIO 模型', 0) / matched * 100 if matched > 0 else 0

    print(f"   Tier 1 (台灣本地): {tier1_rate:.1f}%")
    print(f"   Tier 2 (國際產業): {tier2_rate:.1f}%")
    print(f"   Tier 3 (EEIO 模型): {tier3_rate:.1f}%")

    if tier3_rate > 50:
        print(f"\n   ⚠️  Tier 3 使用率過高 ({tier3_rate:.1f}%)")
        print(f"   建議：擴充 Tier 1 和 Tier 2 資料庫")

    if match_rate < 90:
        print(f"\n💡 改進建議:")
        if len(unmatched_df) > 0:
            top_fail_scenario = unmatched_df['scenario'].value_counts().index[0]
            print(f"   1. 加強「{top_fail_scenario}」情境的排放係數覆蓋")
        if matched_df['similarity'].mean() < 0.75:
            print(f"   2. 平均相似度偏低 ({matched_df['similarity'].mean():.3f})")
            print(f"      → 考慮改進 Embedding 模型或增加同義詞")
        if tier3_rate > 50:
            print(f"   3. 擴充 Tier 1 和 Tier 2 產品級排放係數資料庫")

    print("\n" + "=" * 80)
    print("  ✅ 測試完成！")
    print("=" * 80)


def test_dataset(df: pd.DataFrame, retriever, language: str) -> pd.DataFrame:
    """測試單個資料集"""

    print(f"\n📈 測試樣本分布:")
    print(f"   Category 1: {(df['ghg_category'] == 1).sum()} 筆")
    print(f"   Category 2: {(df['ghg_category'] == 2).sum()} 筆")

    print(f"\n   Scenario 分布:")
    for scenario, count in df['scenario'].value_counts().items():
        pct = count / len(df) * 100
        print(f"      {scenario}: {count} 筆 ({pct:.1f}%)")

    # 進行配對測試
    print(f"\n🔍 開始配對測試...")
    print(f"   配對門檻: Tier 1 >= 0.7 | Tier 2 >= 0.7 | Tier 3 >= 0.6")
    print()

    results = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="配對進度"):
        description = str(row['description'])

        # 使用瀑布式檢索器進行配對
        try:
            match_result = retriever.search(query=description, top_k=3)

            if match_result['success']:
                best_match = match_result['best_match']
                results.append({
                    'description': description,
                    'ghg_category': row['ghg_category'],
                    'scenario': row['scenario'],
                    'industry': row['industry'],
                    'amount': row['amount'],
                    'language': language,
                    'matched': True,
                    'tier': match_result['tier_name'],
                    'similarity': best_match['similarity'],
                    'ef_name': best_match.get('name') or best_match.get('product_name', 'Unknown'),
                    'ef_value': best_match['emission_factor'],
                    'ef_unit': best_match.get('unit') or best_match.get('unit_standard', ''),
                })
            else:
                results.append({
                    'description': description,
                    'ghg_category': row['ghg_category'],
                    'scenario': row['scenario'],
                    'industry': row['industry'],
                    'amount': row['amount'],
                    'language': language,
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
                'description': description,
                'ghg_category': row['ghg_category'],
                'scenario': row['scenario'],
                'industry': row['industry'],
                'amount': row['amount'],
                'language': language,
                'matched': False,
                'tier': 'ERROR',
                'similarity': 0.0,
                'ef_name': str(e),
                'ef_value': None,
                'ef_unit': None,
            })

    results_df = pd.DataFrame(results)

    # 統計分析
    total = len(results_df)
    matched = results_df['matched'].sum()
    match_rate = matched / total * 100

    print(f"\n✅ {language} 配對成功率: {matched}/{total} = {match_rate:.1f}%")

    # 按 Tier 統計
    if matched > 0:
        print(f"\n📊 各層級配對分布:")
        tier_counts = results_df[results_df['matched']]['tier'].value_counts()
        for tier, count in tier_counts.items():
            pct = count / matched * 100
            print(f"   {tier}: {count} 筆 ({pct:.1f}%)")

    return results_df


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  測試被用戶中斷")
    except Exception as e:
        print(f"\n\n❌ 測試錯誤: {e}")
        import traceback
        traceback.print_exc()
