#!/usr/bin/env python3
"""
測試 GHG Category 分類器
"""

import sys
from pathlib import Path

# 加入 src 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from classification.ghg_classifier import GHGCategoryClassifier


def print_result(item_desc, result):
    """印出分類結果"""
    print(f"\n{'='*70}")
    print(f"項目：{item_desc}")
    print(f"{'='*70}")
    print(f"GHG 類別：Category {result['ghg_category']}")
    print(f"信心度：{result['confidence']:.0%}")
    print(f"判斷方法：{result['method']}")
    print(f"是否固定資產：{result['is_fixed_asset']}")
    print(f"判斷理由：{result['reasoning']}")
    print(f"建議：{result['recommendation']}")


def main():
    """測試主函數"""
    print("="*70)
    print("  GHG Protocol Category 分類器測試")
    print("="*70)

    # 初始化分類器
    classifier = GHGCategoryClassifier()

    # 測試案例
    test_cases = [
        {
            'description': '案例 1：有會計科目 - 機械設備',
            'item_name': '工業用機器',
            'accounting_subject': '機械設備',
            'amount': 500000
        },
        {
            'description': '案例 2：有會計科目 - 辦公用品',
            'item_name': '影印紙',
            'accounting_subject': '文具用品',
            'amount': 5000
        },
        {
            'description': '案例 3：無會計科目，但有關鍵字 - 車輛',
            'item_name': '購買貨車',
            'amount': 800000
        },
        {
            'description': '案例 4：無會計科目，但有關鍵字 - 文具',
            'item_name': '購買辦公室文具',
            'amount': 3000
        },
        {
            'description': '案例 5：模糊案例 - 電腦（高金額）',
            'item_name': '購買電腦設備',
            'amount': 50000,
            'useful_life': 5
        },
        {
            'description': '案例 6：模糊案例 - 電腦（低金額）',
            'item_name': '購買電腦週邊',
            'amount': 5000
        },
        {
            'description': '案例 7：財物分類匹配 - 運輸設備',
            'item_name': '堆高機',
            'amount': 300000
        },
        {
            'description': '案例 8：折舊費用（應排除）',
            'item_name': '機械設備折舊',
            'accounting_subject': '折舊費用',
            'amount': 100000
        },
        {
            'description': '案例 9：資本支出代碼',
            'item_name': '購買新廠房設備',
            'accounting_subject_code': '1600'
        },
        {
            'description': '案例 10：原物料採購',
            'item_name': '鋼材採購',
            'accounting_subject_code': '5101',
            'amount': 200000
        }
    ]

    # 執行測試
    for test_case in test_cases:
        result = classifier.classify(
            item_name=test_case['item_name'],
            accounting_subject=test_case.get('accounting_subject'),
            accounting_subject_code=test_case.get('accounting_subject_code'),
            amount=test_case.get('amount'),
            useful_life=test_case.get('useful_life')
        )

        print_result(test_case['description'], result)

    # 統計測試結果
    print("\n" + "="*70)
    print("  測試摘要")
    print("="*70)

    results = [
        classifier.classify(
            item_name=tc['item_name'],
            accounting_subject=tc.get('accounting_subject'),
            accounting_subject_code=tc.get('accounting_subject_code'),
            amount=tc.get('amount'),
            useful_life=tc.get('useful_life')
        )
        for tc in test_cases
    ]

    cat1_count = sum(1 for r in results if r['ghg_category'] == 1)
    cat2_count = sum(1 for r in results if r['ghg_category'] == 2)
    exclude_count = sum(1 for r in results if r['ghg_category'] == 'exclude')
    unknown_count = sum(1 for r in results if r['ghg_category'] == 'unknown')

    print(f"\n總測試案例數：{len(test_cases)}")
    print(f"  Category 1（購買商品）：{cat1_count} 個")
    print(f"  Category 2（資本財）：{cat2_count} 個")
    print(f"  排除（非現金支出）：{exclude_count} 個")
    print(f"  無法判斷：{unknown_count} 個")

    avg_confidence = sum(r['confidence'] for r in results) / len(results)
    print(f"\n平均信心度：{avg_confidence:.0%}")

    # 方法統計
    method_counts = {}
    for r in results:
        method = r['method']
        method_counts[method] = method_counts.get(method, 0) + 1

    print("\n判斷方法統計：")
    for method, count in method_counts.items():
        print(f"  {method}: {count} 個")

    print("\n" + "="*70)
    print("  ✅ 測試完成！")
    print("="*70)


if __name__ == "__main__":
    main()
