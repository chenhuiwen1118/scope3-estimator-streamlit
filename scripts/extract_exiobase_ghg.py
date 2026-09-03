#!/usr/bin/env python3
"""
提取 EXIOBASE MRIO 資料庫的 GHG 排放係數
特別針對台灣 (TW) 與英國 (GB)
"""

import pandas as pd
import numpy as np
from pathlib import Path

# 設定路徑
EXIOBASE_DIR = Path("/mnt/c/Users/yjchang/USEEIO/import_emission_factors/data/IOT_2022_pxp/IOT_2022_pxp")
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "emission_factors" / "tier3_eeio"

# GWP 值 (AR5 - 100 year)
GWP_AR5 = {
    'CO2': 1,
    'CH4': 28,
    'N2O': 265
}


def load_exiobase_data():
    """
    載入 EXIOBASE 資料
    """
    print("📂 載入 EXIOBASE 資料...")

    # 讀取產品分類
    products_file = EXIOBASE_DIR / "products.txt"
    products = pd.read_csv(products_file, sep='\t')
    print(f"   ✓ 載入 {len(products)} 個產品分類")

    # 讀取環境延伸矩陣 F
    f_file = EXIOBASE_DIR / "satellite" / "F.txt"
    print(f"   📊 讀取 F.txt ({f_file.stat().st_size / 1024 / 1024:.1f} MB)...")

    # 只讀取前幾行來確認結構
    f_preview = pd.read_csv(f_file, sep='\t', nrows=5, index_col=0)
    print(f"   ✓ F 矩陣結構: {len(f_preview.index)} rows × {len(f_preview.columns)} cols (preview)")

    return products, f_file


def extract_ghg_for_country(f_file, products, country_code):
    """
    提取特定國家的 GHG 排放係數

    Args:
        f_file: F.txt 檔案路徑
        products: 產品分類 DataFrame
        country_code: 國家代碼 (如 'TW', 'GB')

    Returns:
        DataFrame: 包含各產品的 GHG 排放係數
    """
    print(f"\n🔍 提取 {country_code} 的 GHG 排放係數...")

    # 讀取完整的 F 矩陣（這可能需要一些時間）
    print("   ⏳ 讀取完整 F 矩陣（可能需要 1-2 分鐘）...")
    F = pd.read_csv(f_file, sep='\t', index_col=0, header=[0, 1])
    print(f"   ✓ 完整 F 矩陣: {F.shape[0]} rows × {F.shape[1]} cols")

    # 篩選 GHG 排放指標
    ghg_indicators = [
        'CO2 - combustion - air',
        'CH4 - combustion - air',
        'N2O - combustion - air'
    ]

    # 檢查指標是否存在
    available_indicators = [ind for ind in ghg_indicators if ind in F.index]
    print(f"   ✓ 找到 {len(available_indicators)}/{len(ghg_indicators)} 個 GHG 指標")

    if not available_indicators:
        print(f"   ❌ 錯誤: 找不到 GHG 指標")
        return None

    # 提取 GHG 資料
    ghg_data = F.loc[available_indicators]

    # 提取特定國家的列
    country_cols = [col for col in ghg_data.columns if col[0] == country_code]

    if not country_cols:
        print(f"   ❌ 錯誤: 找不到國家代碼 {country_code}")
        return None

    print(f"   ✓ 找到 {len(country_cols)} 個 {country_code} 的產品列")

    # 提取資料
    country_ghg = ghg_data[country_cols]

    # 重新整理資料格式
    result = []
    for i, product in products.iterrows():
        if i >= len(country_cols):
            break

        col = country_cols[i]
        row_data = {
            'Country': country_code,
            'Product_Number': product['Number'],
            'Product_Name': product['Name'],
            'Product_Code': product['CodeTxt']
        }

        # 提取各 GHG 排放值
        for indicator in available_indicators:
            ghg_type = indicator.split(' - ')[0]  # 提取 CO2, CH4, N2O
            value = country_ghg.loc[indicator, col]
            row_data[f'{ghg_type}_kg'] = value

        # 計算 CO2e (使用 GWP AR5)
        co2e = 0
        if 'CO2_kg' in row_data:
            co2e += row_data['CO2_kg'] * GWP_AR5['CO2']
        if 'CH4_kg' in row_data:
            co2e += row_data['CH4_kg'] * GWP_AR5['CH4']
        if 'N2O_kg' in row_data:
            co2e += row_data['N2O_kg'] * GWP_AR5['N2O']

        row_data['Total_CO2e_kg'] = co2e
        result.append(row_data)

    result_df = pd.DataFrame(result)
    print(f"   ✓ 完成提取 {len(result_df)} 個產品的排放係數")

    return result_df


def main():
    """
    主程式
    """
    print("=" * 60)
    print("🌍 EXIOBASE GHG 排放係數提取工具")
    print("=" * 60)

    # 載入資料
    products, f_file = load_exiobase_data()

    # 提取台灣 (TW)
    print("\n" + "=" * 60)
    tw_ghg = extract_ghg_for_country(f_file, products, 'TW')

    if tw_ghg is not None:
        # 儲存台灣資料
        output_file = OUTPUT_DIR / "EXIOBASE_TW_2022_GHG.csv"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        tw_ghg.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n   💾 已儲存: {output_file}")
        print(f"   📊 檔案大小: {output_file.stat().st_size / 1024:.1f} KB")

        # 顯示摘要統計
        print("\n   📈 台灣排放係數摘要:")
        print(f"      平均 CO2e: {tw_ghg['Total_CO2e_kg'].mean():.2f} kg CO2e")
        print(f"      最小值: {tw_ghg['Total_CO2e_kg'].min():.2f} kg CO2e")
        print(f"      最大值: {tw_ghg['Total_CO2e_kg'].max():.2f} kg CO2e")
        print(f"\n      前 5 高排放產品:")
        top5 = tw_ghg.nlargest(5, 'Total_CO2e_kg')[['Product_Name', 'Total_CO2e_kg']]
        for idx, row in top5.iterrows():
            print(f"        {idx+1}. {row['Product_Name']}: {row['Total_CO2e_kg']:.2f} kg CO2e")

    # 提取英國 (GB)
    print("\n" + "=" * 60)
    gb_ghg = extract_ghg_for_country(f_file, products, 'GB')

    if gb_ghg is not None:
        # 儲存英國資料
        output_file = OUTPUT_DIR / "EXIOBASE_GB_2022_GHG.csv"
        gb_ghg.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n   💾 已儲存: {output_file}")
        print(f"   📊 檔案大小: {output_file.stat().st_size / 1024:.1f} KB")

        # 顯示摘要統計
        print("\n   📈 英國排放係數摘要:")
        print(f"      平均 CO2e: {gb_ghg['Total_CO2e_kg'].mean():.2f} kg CO2e")
        print(f"      最小值: {gb_ghg['Total_CO2e_kg'].min():.2f} kg CO2e")
        print(f"      最大值: {gb_ghg['Total_CO2e_kg'].max():.2f} kg CO2e")

    print("\n" + "=" * 60)
    print("✅ 完成！")
    print("=" * 60)

    if tw_ghg is not None or gb_ghg is not None:
        print("\n📋 下一步:")
        print("  1. 檢視生成的 CSV 檔案")
        print("  2. 更新 tier3_eeio/README.md")
        print("  3. 整合到 RAG 檢索系統")
        print("  4. 測試與驗證")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
