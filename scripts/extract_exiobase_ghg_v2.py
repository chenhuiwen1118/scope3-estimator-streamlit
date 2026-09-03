#!/usr/bin/env python3
"""
提取 EXIOBASE MRIO 資料庫的 GHG 排放係數（排放強度）
計算方式: 排放係數 = F (排放量 kg) / x (產出 M.EUR)
單位: kg CO2e per M.EUR
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

    # 讀取總產出向量 x
    x_file = EXIOBASE_DIR / "x.txt"
    print(f"   📊 讀取 x.txt (總產出向量)...")

    return products, f_file, x_file


def extract_ghg_intensity_for_country(f_file, x_file, products, country_code):
    """
    提取特定國家的 GHG 排放強度（intensity）

    Args:
        f_file: F.txt 檔案路徑
        x_file: x.txt 檔案路徑（總產出向量）
        products: 產品分類 DataFrame
        country_code: 國家代碼 (如 'TW', 'GB')

    Returns:
        DataFrame: 包含各產品的 GHG 排放強度 (kg per M.EUR)
    """
    print(f"\n🔍 提取 {country_code} 的 GHG 排放強度...")

    # 讀取完整的 F 矩陣
    print("   ⏳ 讀取完整 F 矩陣（排放量，可能需要 1-2 分鐘）...")
    F = pd.read_csv(f_file, sep='\t', index_col=0, header=[0, 1])
    print(f"   ✓ F 矩陣: {F.shape[0]} rows × {F.shape[1]} cols")

    # 讀取總產出向量 x
    print("   ⏳ 讀取 x 向量（總產出）...")
    x = pd.read_csv(x_file, sep='\t')
    print(f"   ✓ x 向量: {x.shape}")

    # 篩選 GHG 排放指標
    ghg_indicators = [
        'CO2 - combustion - air',
        'CH4 - combustion - air',
        'N2O - combustion - air'
    ]

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

    # 提取該國的總產出 (從 x 向量篩選該國資料)
    country_x = x[x['region'] == country_code].copy()
    country_output = country_x['indout'].values
    print(f"   ✓ 提取總產出向量 (M.EUR): {len(country_output)} 個產品")

    # 提取資料並計算排放強度
    country_ghg = ghg_data[country_cols]

    result = []
    for i, product in products.iterrows():
        if i >= len(country_cols):
            break

        col = country_cols[i]
        output_meur = country_output[i]

        row_data = {
            'Country': country_code,
            'Product_Number': product['Number'],
            'Product_Name': product['Name'],
            'Product_Code': product['CodeTxt'],
            'Output_MEUR': output_meur
        }

        # 提取各 GHG 排放量與計算強度
        for indicator in available_indicators:
            ghg_type = indicator.split(' - ')[0]  # CO2, CH4, N2O
            emission_kg = country_ghg.loc[indicator, col]

            # 計算排放強度 (kg per M.EUR)
            if output_meur > 0:
                intensity = emission_kg / output_meur
            else:
                intensity = 0

            row_data[f'{ghg_type}_kg_total'] = emission_kg
            row_data[f'{ghg_type}_kg_per_MEUR'] = intensity

        # 計算 CO2e 強度
        co2e_intensity = 0
        if 'CO2_kg_per_MEUR' in row_data:
            co2e_intensity += row_data['CO2_kg_per_MEUR'] * GWP_AR5['CO2']
        if 'CH4_kg_per_MEUR' in row_data:
            co2e_intensity += row_data['CH4_kg_per_MEUR'] * GWP_AR5['CH4']
        if 'N2O_kg_per_MEUR' in row_data:
            co2e_intensity += row_data['N2O_kg_per_MEUR'] * GWP_AR5['N2O']

        row_data['Total_CO2e_kg_per_MEUR'] = co2e_intensity

        result.append(row_data)

    result_df = pd.DataFrame(result)
    print(f"   ✓ 完成提取 {len(result_df)} 個產品的排放強度")

    return result_df


def main():
    """
    主程式
    """
    print("=" * 60)
    print("🌍 EXIOBASE GHG 排放強度提取工具 v2")
    print("   計算: kg CO2e per M.EUR (百萬歐元)")
    print("=" * 60)

    # 載入資料
    products, f_file, x_file = load_exiobase_data()

    # 提取台灣 (TW)
    print("\n" + "=" * 60)
    tw_ghg = extract_ghg_intensity_for_country(f_file, x_file, products, 'TW')

    if tw_ghg is not None:
        # 儲存台灣資料
        output_file = OUTPUT_DIR / "EXIOBASE_TW_2022_GHG_intensity.csv"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        tw_ghg.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n   💾 已儲存: {output_file}")
        print(f"   📊 檔案大小: {output_file.stat().st_size / 1024:.1f} KB")

        # 顯示摘要統計
        print("\n   📈 台灣排放強度摘要 (kg CO2e per M.EUR):")
        print(f"      平均: {tw_ghg['Total_CO2e_kg_per_MEUR'].mean():.2f}")
        print(f"      中位數: {tw_ghg['Total_CO2e_kg_per_MEUR'].median():.2f}")
        print(f"      最小值: {tw_ghg['Total_CO2e_kg_per_MEUR'].min():.2f}")
        print(f"      最大值: {tw_ghg['Total_CO2e_kg_per_MEUR'].max():.2f}")

        print(f"\n      前 5 高排放強度產品:")
        top5 = tw_ghg.nlargest(5, 'Total_CO2e_kg_per_MEUR')[['Product_Name', 'Total_CO2e_kg_per_MEUR']]
        for idx, row in top5.iterrows():
            print(f"        {idx+1}. {row['Product_Name']}: {row['Total_CO2e_kg_per_MEUR']:.2f} kg CO2e/M.EUR")

        # 換算為 kg CO2e per USD 參考
        eur_to_usd = 1.10  # 2022 平均匯率
        print(f"\n      💡 換算參考 (假設 1 EUR = {eur_to_usd} USD):")
        print(f"         平均: {tw_ghg['Total_CO2e_kg_per_MEUR'].mean() / eur_to_usd:.4f} kg CO2e/USD")

    # 提取英國 (GB)
    print("\n" + "=" * 60)
    gb_ghg = extract_ghg_intensity_for_country(f_file, x_file, products, 'GB')

    if gb_ghg is not None:
        # 儲存英國資料
        output_file = OUTPUT_DIR / "EXIOBASE_GB_2022_GHG_intensity.csv"
        gb_ghg.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n   💾 已儲存: {output_file}")
        print(f"   📊 檔案大小: {output_file.stat().st_size / 1024:.1f} KB")

        # 顯示摘要統計
        print("\n   📈 英國排放強度摘要 (kg CO2e per M.EUR):")
        print(f"      平均: {gb_ghg['Total_CO2e_kg_per_MEUR'].mean():.2f}")
        print(f"      中位數: {gb_ghg['Total_CO2e_kg_per_MEUR'].median():.2f}")
        print(f"      最小值: {gb_ghg['Total_CO2e_kg_per_MEUR'].min():.2f}")
        print(f"      最大值: {gb_ghg['Total_CO2e_kg_per_MEUR'].max():.2f}")

    print("\n" + "=" * 60)
    print("✅ 完成！")
    print("=" * 60)

    if tw_ghg is not None or gb_ghg is not None:
        print("\n📋 資料說明:")
        print("  - 單位: kg CO2e per M.EUR (百萬歐元)")
        print("  - 基準年: 2022")
        print("  - GWP: AR5 (100-year)")
        print("  - 資料來源: EXIOBASE (推測)")
        print("\n📋 下一步:")
        print("  1. 檢視生成的 CSV 檔案")
        print("  2. 建立匯率與通膨調整機制")
        print("  3. 更新 tier3_eeio/README.md")
        print("  4. 整合到 RAG 檢索系統")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
