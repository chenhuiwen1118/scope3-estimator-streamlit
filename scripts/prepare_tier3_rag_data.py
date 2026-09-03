#!/usr/bin/env python3
"""
準備 Tier 3 EEIO 資料供 RAG 檢索使用
將 EXIOBASE 多國資料轉換為統一格式，並添加中文翻譯與同義詞
"""

import pandas as pd
from pathlib import Path
import json

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data" / "emission_factors" / "tier3_eeio"
OUTPUT_FILE = DATA_DIR / "tier3_eeio_unified.csv"

# 國家清單
COUNTRIES = {
    'TW': '台灣',
    'GB': '英國',
    'JP': '日本',
    'CN': '中國',
    'KR': '韓國',
    'US': '美國'
}

# 載入產品翻譯字典
TRANSLATIONS_FILE = DATA_DIR / "product_translations.json"

def load_translations():
    """載入產品翻譯字典"""
    if TRANSLATIONS_FILE.exists():
        with open(TRANSLATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

PRODUCT_TRANSLATIONS = load_translations()

# 備用基本翻譯（若 JSON 檔案不存在）
if not PRODUCT_TRANSLATIONS:
    PRODUCT_TRANSLATIONS = {
        'Paddy rice': {
            'zh': '稻米',
            'synonyms': ['水稻', '稻穀', 'rice', 'paddy'],
            'category': '農業'
        },
    'Wheat': {
        'zh': '小麥',
        'synonyms': ['麵粉', 'wheat', 'flour'],
        'category': '農業'
    },
    'Cereal grains nec': {
        'zh': '其他穀物',
        'synonyms': ['穀物', 'grains', 'cereals', '雜糧'],
        'category': '農業'
    },
    'Vegetables, fruit, nuts': {
        'zh': '蔬菜水果堅果',
        'synonyms': ['蔬果', 'vegetables', 'fruits', 'nuts', '農產品'],
        'category': '農業'
    },
    'Oil seeds': {
        'zh': '油料作物',
        'synonyms': ['油籽', 'oilseeds', '大豆', 'soybean'],
        'category': '農業'
    },
    'Cattle': {
        'zh': '牛',
        'synonyms': ['肉牛', 'cattle', 'beef', '牛肉'],
        'category': '畜牧業'
    },
    'Pigs': {
        'zh': '豬',
        'synonyms': ['豬肉', 'pigs', 'pork'],
        'category': '畜牧業'
    },
    'Poultry': {
        'zh': '家禽',
        'synonyms': ['雞', '禽類', 'chicken', 'poultry'],
        'category': '畜牧業'
    },
    'Raw milk': {
        'zh': '鮮乳',
        'synonyms': ['牛奶', 'milk', '乳品'],
        'category': '畜牧業'
    },
    'Fish and other fishing products; services incidental of fishing (05)': {
        'zh': '漁業產品',
        'synonyms': ['魚類', 'fish', '海鮮', 'seafood', '水產'],
        'category': '漁業'
    },
    'Electricity by coal': {
        'zh': '燃煤發電',
        'synonyms': ['煤電', 'coal power', '火力發電'],
        'category': '電力'
    },
    'Electricity by gas': {
        'zh': '天然氣發電',
        'synonyms': ['氣電', 'gas power', '燃氣發電'],
        'category': '電力'
    },
    'Electricity by nuclear': {
        'zh': '核能發電',
        'synonyms': ['核電', 'nuclear power'],
        'category': '電力'
    },
    'Electricity by hydro': {
        'zh': '水力發電',
        'synonyms': ['水電', 'hydro power'],
        'category': '電力'
    },
    'Electricity by wind': {
        'zh': '風力發電',
        'synonyms': ['風電', 'wind power'],
        'category': '電力'
    },
    'Electricity by solar photovoltaic': {
        'zh': '太陽能發電',
        'synonyms': ['太陽能', 'solar power', 'PV'],
        'category': '電力'
    },
    'Computer, Electronic and optical products': {
        'zh': '電腦與電子產品',
        'synonyms': ['電子產品', 'electronics', '電腦', 'computer', '光學產品'],
        'category': '製造業'
    },
    'Electrical machinery and apparatus n.e.c.': {
        'zh': '電機設備',
        'synonyms': ['電機', 'electrical machinery', '電氣設備'],
        'category': '製造業'
    },
    'Machinery and equipment n.e.c.': {
        'zh': '機械設備',
        'synonyms': ['機械', 'machinery', '設備'],
        'category': '製造業'
    },
    'Motor vehicles, trailers and semi-trailers': {
        'zh': '汽車',
        'synonyms': ['車輛', 'vehicles', 'automobile', '轎車'],
        'category': '製造業'
    },
    'Textiles (13-14)': {
        'zh': '紡織品',
        'synonyms': ['紡織', 'textiles', '布料'],
        'category': '製造業'
    },
    'Wearing apparel; furs (18)': {
        'zh': '服飾',
        'synonyms': ['服裝', 'apparel', '衣服', 'clothing'],
        'category': '製造業'
    },
    'Chemicals and chemical products': {
        'zh': '化學產品',
        'synonyms': ['化工', 'chemicals', '化學品'],
        'category': '製造業'
    },
    'Pharmaceuticals, medicinal chemical and botanical products': {
        'zh': '藥品',
        'synonyms': ['醫藥', 'pharmaceuticals', '藥物'],
        'category': '製造業'
    },
    'Rubber and plastic products': {
        'zh': '塑橡膠製品',
        'synonyms': ['塑膠', 'plastic', '橡膠', 'rubber'],
        'category': '製造業'
    },
    'Basic iron and steel and of ferro-alloys and first products thereof': {
        'zh': '鋼鐵',
        'synonyms': ['鐵', 'steel', 'iron', '鋼材'],
        'category': '製造業'
    },
    'Fabricated metal products': {
        'zh': '金屬製品',
        'synonyms': ['金屬', 'metal products'],
        'category': '製造業'
    },
    'Construction work': {
        'zh': '建築工程',
        'synonyms': ['建築', 'construction', '營建', '工程'],
        'category': '建築業'
    },
    'Wholesale trade and commission trade services, except of motor vehicles and motorcycles': {
        'zh': '批發貿易',
        'synonyms': ['批發', 'wholesale', '貿易'],
        'category': '商業'
    },
    'Retail trade services, except of motor vehicles and motorcycles; repair services': {
        'zh': '零售貿易',
        'synonyms': ['零售', 'retail', '商店'],
        'category': '商業'
    },
    'Hotel and restaurant services': {
        'zh': '旅館餐飲',
        'synonyms': ['飯店', 'hotel', '餐廳', 'restaurant', '餐飲'],
        'category': '服務業'
    },
    'Food and beverage serving services': {
        'zh': '餐飲服務',
        'synonyms': ['餐飲', 'food service', '餐廳', '飲食'],
        'category': '服務業'
    },
    'Land transport; transport via pipelines': {
        'zh': '陸運',
        'synonyms': ['陸路運輸', 'land transport', '公路運輸'],
        'category': '運輸業'
    },
    'Water transport services': {
        'zh': '水運',
        'synonyms': ['海運', 'shipping', '航運'],
        'category': '運輸業'
    },
    'Air transport services': {
        'zh': '空運',
        'synonyms': ['航空', 'air transport', '飛機'],
        'category': '運輸業'
    },
    'Post and telecommunication services': {
        'zh': '郵政電信',
        'synonyms': ['郵政', 'post', '電信', 'telecom'],
        'category': '服務業'
    },
    'Financial intermediation services, except insurance and pension funding services': {
        'zh': '金融服務',
        'synonyms': ['金融', 'finance', '銀行', 'banking'],
        'category': '服務業'
    },
    'Real estate services': {
        'zh': '不動產服務',
        'synonyms': ['房地產', 'real estate', '地產'],
        'category': '服務業'
    },
    'Computer and related services': {
        'zh': '電腦相關服務',
        'synonyms': ['IT服務', 'computer service', '資訊服務'],
        'category': '服務業'
    },
    'Research and development services': {
        'zh': '研發服務',
        'synonyms': ['研發', 'R&D', 'research'],
        'category': '服務業'
    },
    'Public administration and defence services; compulsory social security services': {
        'zh': '公共行政',
        'synonyms': ['政府', 'government', '公部門'],
        'category': '公共服務'
    },
    'Education services': {
        'zh': '教育服務',
        'synonyms': ['教育', 'education', '學校'],
        'category': '公共服務'
    },
    'Health and social work services': {
        'zh': '醫療社福',
        'synonyms': ['醫療', 'healthcare', '健康', '社會服務'],
        'category': '公共服務'
    },
    'Textiles waste for treatment: incineration': {
        'zh': '紡織廢棄物焚化',
        'synonyms': ['紡織廢棄物', 'textile waste', '廢棄物處理'],
        'category': '廢棄物處理'
    },
    'Plastic waste for treatment: incineration': {
        'zh': '塑膠廢棄物焚化',
        'synonyms': ['塑膠廢棄物', 'plastic waste', '廢塑膠'],
        'category': '廢棄物處理'
    },
}


def get_search_text(product_name: str, country_code: str) -> str:
    """
    為產品生成富語意的搜尋文本

    Args:
        product_name: 英文產品名稱
        country_code: 國家代碼

    Returns:
        包含中英文、同義詞、類別的搜尋文本
    """
    country_name = COUNTRIES.get(country_code, country_code)

    # 檢查是否有翻譯
    if product_name in PRODUCT_TRANSLATIONS:
        trans = PRODUCT_TRANSLATIONS[product_name]
        zh_name = trans['zh']
        synonyms = ' '.join(trans['synonyms'])
        category = trans['category']

        # 組合搜尋文本: 中文 英文 同義詞 類別 國家
        search_text = f"{zh_name} {product_name} {synonyms} {category} {country_name}"
    else:
        # 無翻譯時，使用英文名稱
        search_text = f"{product_name} {country_name}"

    return search_text


def prepare_unified_data():
    """
    準備統一格式的 Tier 3 EEIO 資料
    """
    print("=" * 70)
    print("🔧 準備 Tier 3 EEIO RAG 資料")
    print("=" * 70)

    all_records = []

    for country_code, country_name in COUNTRIES.items():
        print(f"\n📂 處理 {country_name} ({country_code})...")

        # 讀取該國資料
        file_path = DATA_DIR / f"EXIOBASE_{country_code}_2022_GHG_intensity.csv"

        if not file_path.exists():
            print(f"   ⚠️  檔案不存在: {file_path.name}")
            continue

        df = pd.read_csv(file_path)
        print(f"   ✓ 載入 {len(df)} 筆記錄")

        # 轉換每一筆記錄
        for _, row in df.iterrows():
            # 生成搜尋文本
            search_text = get_search_text(row['Product_Name'], country_code)

            record = {
                'source': 'EXIOBASE',
                'country': country_code,
                'country_name': country_name,
                'product_id': row['Product_Number'],
                'product_name': row['Product_Name'],
                'product_code': row['Product_Code'],
                'search_text': search_text,
                'emission_factor_per_meur': row['Total_CO2e_kg_per_MEUR'],
                'co2_per_meur': row['CO2_kg_per_MEUR'],
                'ch4_per_meur': row['CH4_kg_per_MEUR'],
                'n2o_per_meur': row['N2O_kg_per_MEUR'],
                'output_meur': row['Output_MEUR'],
                'unit': 'kg CO2e/M.EUR',
                'base_year': 2022,
                'gwp_version': 'AR5',
                'data_quality': 'Medium',  # EEIO 為中等品質
                'tier': 3
            }

            all_records.append(record)

    # 建立統一資料框
    unified_df = pd.DataFrame(all_records)

    # 儲存
    unified_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')

    print("\n" + "=" * 70)
    print("✅ 完成！")
    print("=" * 70)
    print(f"\n📊 統計資訊:")
    print(f"   總記錄數: {len(unified_df)}")
    print(f"   國家數: {unified_df['country'].nunique()}")
    print(f"   產品類別數: {unified_df['product_id'].nunique()}")
    print(f"\n💾 輸出檔案: {OUTPUT_FILE.name}")
    print(f"   檔案大小: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")

    # 顯示各國統計
    print(f"\n📈 各國記錄數:")
    country_counts = unified_df.groupby(['country', 'country_name']).size()
    for (code, name), count in country_counts.items():
        print(f"   {code} ({name}): {count} 筆")

    # 顯示翻譯涵蓋率
    translated_count = sum(1 for name in unified_df['product_name'].unique()
                          if name in PRODUCT_TRANSLATIONS)
    total_products = unified_df['product_name'].nunique()
    print(f"\n🌐 翻譯涵蓋率:")
    print(f"   已翻譯: {translated_count}/{total_products} ({translated_count/total_products*100:.1f}%)")

    # 顯示範例
    print(f"\n📋 資料範例（前 3 筆）:")
    print(unified_df[['country_name', 'product_name', 'search_text', 'emission_factor_per_meur']].head(3).to_string(index=False))

    print(f"\n✨ 下一步:")
    print(f"   1. 執行 build_tier3_embeddings.py 生成向量")
    print(f"   2. 建立 Tier3EEIORetriever 檢索類別")
    print(f"   3. 整合到主檢索系統")


if __name__ == "__main__":
    try:
        prepare_unified_data()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
