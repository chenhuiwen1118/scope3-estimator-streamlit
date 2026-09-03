#!/usr/bin/env python3
"""
提取 EXIOBASE MRIO 資料庫的 GHG 排放係數（排放強度）- 多國版本
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

# 要提取的國家清單
COUNTRIES = {
    'TW': '台灣',
    'GB': '英國',
    'JP': '日本',
    'CN': '中國',
    'KR': '韓國',
    'US': '美國'
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
    print(f"🔍 提取 {country_code} 的 GHG 排放強度...")

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
    print("=" * 70)
    print("🌍 EXIOBASE GHG 排放強度提取工具 - 多國版本")
    print("   計算: kg CO2e per M.EUR (百萬歐元)")
    print("=" * 70)

    # 載入資料
    products, f_file, x_file = load_exiobase_data()

    # 儲存結果摘要
    summary = []

    # 循環處理所有國家
    for country_code, country_name in COUNTRIES.items():
        print("\n" + "=" * 70)
        print(f"📍 處理 {country_name} ({country_code})")
        print("=" * 70)

        country_ghg = extract_ghg_intensity_for_country(f_file, x_file, products, country_code)

        if country_ghg is not None:
            # 儲存該國資料
            output_file = OUTPUT_DIR / f"EXIOBASE_{country_code}_2022_GHG_intensity.csv"
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            country_ghg.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n   💾 已儲存: {output_file.name}")
            print(f"   📊 檔案大小: {output_file.stat().st_size / 1024:.1f} KB")

            # 計算統計資料
            stats = {
                'Country': country_name,
                'Code': country_code,
                'Mean': country_ghg['Total_CO2e_kg_per_MEUR'].mean(),
                'Median': country_ghg['Total_CO2e_kg_per_MEUR'].median(),
                'Min': country_ghg['Total_CO2e_kg_per_MEUR'].min(),
                'Max': country_ghg['Total_CO2e_kg_per_MEUR'].max()
            }
            summary.append(stats)

            # 顯示摘要統計
            print(f"\n   📈 {country_name}排放強度摘要 (kg CO2e per M.EUR):")
            print(f"      平均: {stats['Mean']:,.2f}")
            print(f"      中位數: {stats['Median']:,.2f}")
            print(f"      最小值: {stats['Min']:,.2f}")
            print(f"      最大值: {stats['Max']:,.2f}")

            print(f"\n      前 3 高排放強度產品:")
            top3 = country_ghg.nlargest(3, 'Total_CO2e_kg_per_MEUR')[['Product_Name', 'Total_CO2e_kg_per_MEUR']]
            for idx, (_, row) in enumerate(top3.iterrows(), 1):
                print(f"        {idx}. {row['Product_Name']}: {row['Total_CO2e_kg_per_MEUR']:,.0f} kg CO2e/M.EUR")
        else:
            print(f"   ⚠️  無法提取 {country_name} 的資料")

    # 顯示各國比較
    print("\n" + "=" * 70)
    print("✅ 完成！")
    print("=" * 70)

    if summary:
        print("\n📊 各國排放強度比較 (平均值, kg CO2e per M.EUR):\n")
        summary_df = pd.DataFrame(summary).sort_values('Mean')

        for _, row in summary_df.iterrows():
            bar_length = int(row['Mean'] / 50000)
            bar = "█" * min(bar_length, 40)
            print(f"   {row['Code']:3s} {row['Country']:6s} │ {bar} {row['Mean']:>12,.0f}")

        print("\n📋 資料說明:")
        print("  - 單位: kg CO2e per M.EUR (百萬歐元)")
        print("  - 基準年: 2022")
        print("  - GWP: AR5 (100-year)")
        print("  - 資料來源: EXIOBASE 3")
        print(f"  - 已提取 {len(summary)} 個國家")

        print("\n📋 生成的檔案:")
        for country_code, country_name in COUNTRIES.items():
            filename = f"EXIOBASE_{country_code}_2022_GHG_intensity.csv"
            filepath = OUTPUT_DIR / filename
            if filepath.exists():
                print(f"  ✓ {filename}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
