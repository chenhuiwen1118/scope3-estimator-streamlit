#!/usr/bin/env python3
"""
為台灣政府採購資料標註 GHG Protocol 類別
"""

import sys
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# 加入 src 路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from classification.ghg_classifier import GHGCategoryClassifier

DATA_DIR = PROJECT_ROOT / "data" / "training_data"

def main():
    print("=" * 70)
    print("  為台灣政府採購資料標註 GHG Protocol 類別")
    print("=" * 70)

    # 讀取處理後的資料
    input_file = DATA_DIR / "processed" / "taiwan_govt_procurement_2024_h2.csv"

    if not input_file.exists():
        print(f"\n❌ 找不到輸入檔案: {input_file}")
        sys.exit(1)

    print(f"\n📥 讀取資料: {input_file.name}")
    df = pd.read_csv(input_file, encoding='utf-8-sig')
    print(f"   總筆數: {len(df):,} 筆")

    # 初始化分類器
    print(f"\n🔧 初始化 GHGCategoryClassifier...")
    classifier = GHGCategoryClassifier()

    # 進行分類
    print(f"\n🏷️  開始標註 GHG category...")

    results = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="標註進度"):
        # 使用標案名稱和金額進行分類
        case_name = str(row['case_name'])
        amount = row['award_price_num']

        # 調用分類器
        classification = classifier.classify(
            item_name=case_name,
            amount=amount,
            return_confidence=True
        )

        # 記錄結果
        results.append({
            **row.to_dict(),
            'ghg_category': classification['ghg_category'],
            'ghg_confidence': classification['confidence'],
            'ghg_method': classification['method'],
            'ghg_reasoning': classification['reasoning'],
            'is_fixed_asset': classification['is_fixed_asset']
        })

    # 建立結果 DataFrame
    results_df = pd.DataFrame(results)

    # 統計分析
    print(f"\n📊 GHG 分類統計:")

    # 各 Category 分布
    print(f"\n   Category 分布:")
    cat_counts = results_df['ghg_category'].value_counts()
    for cat, count in cat_counts.items():
        pct = count / len(results_df) * 100
        print(f"      Category {cat}: {count:,} 筆 ({pct:.1f}%)")

    # 分類方法分布
    print(f"\n   分類方法分布:")
    method_counts = results_df['ghg_method'].value_counts()
    for method, count in method_counts.items():
        pct = count / len(results_df) * 100
        print(f"      {method}: {count:,} 筆 ({pct:.1f}%)")

    # 平均信心度
    avg_confidence = results_df['ghg_confidence'].mean()
    print(f"\n   平均信心度: {avg_confidence:.3f}")

    # 按採購性質統計
    print(f"\n   各採購性質的 Category 分布:")
    for attr in results_df['procurement_attr'].unique():
        attr_df = results_df[results_df['procurement_attr'] == attr]
        cat_dist = attr_df['ghg_category'].value_counts()
        print(f"\n      {attr} ({len(attr_df)} 筆):")
        for cat, count in cat_dist.items():
            pct = count / len(attr_df) * 100
            print(f"         Category {cat}: {count} 筆 ({pct:.1f}%)")

    # 儲存標註結果
    output_file = DATA_DIR / "annotated" / "taiwan_govt_procurement_2024_h2_annotated.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    results_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 儲存標註結果: {output_file.name}")

    # 顯示分類範例
    print(f"\n📋 分類範例:")

    # Category 1 範例
    cat1_samples = results_df[results_df['ghg_category'] == 1].head(3)
    print(f"\n   Category 1 範例 (購買商品/服務):")
    for idx, row in cat1_samples.iterrows():
        print(f"\n      [{idx+1}] {row['org_name']}")
        print(f"          {row['case_name'][:60]}...")
        print(f"          金額: ${row['award_price_num']:,.0f}")
        print(f"          方法: {row['ghg_method']} | 信心度: {row['ghg_confidence']:.2f}")
        print(f"          理由: {row['ghg_reasoning'][:70]}...")

    # Category 2 範例
    cat2_samples = results_df[results_df['ghg_category'] == 2].head(3)
    print(f"\n   Category 2 範例 (資本財):")
    for idx, row in cat2_samples.iterrows():
        print(f"\n      [{idx+1}] {row['org_name']}")
        print(f"          {row['case_name'][:60]}...")
        print(f"          金額: ${row['award_price_num']:,.0f}")
        print(f"          方法: {row['ghg_method']} | 信心度: {row['ghg_confidence']:.2f}")
        print(f"          理由: {row['ghg_reasoning'][:70]}...")

    print("\n" + "=" * 70)
    print("  ✅ 標註完成！")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  程序被用戶中斷")
    except Exception as e:
        print(f"\n\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
