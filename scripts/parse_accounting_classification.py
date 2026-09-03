#!/usr/bin/env python3
"""
解析政府「財物標準分類」XML 資料
建立固定資產判定對照表
"""

import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
import json

# 路徑設定
DATA_DIR = Path(__file__).parent.parent / "data" / "reference_data" / "accounting_classification"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "reference_data"

# XML 檔案配置
XML_FILES = {
    'machinery': {
        'file': 'machinery.xml',
        'tag': 'machinery',
        'category': '機械及設備',
        'is_fixed_asset': True,
        'ghg_category': 2,  # 通常為資本財
        'description': '機械設備通常為固定資產，屬於 Category 2'
    },
    'transportation': {
        'file': 'transportation.xml',
        'tag': 'Transportation',
        'category': '交通及運輸設備',
        'is_fixed_asset': True,
        'ghg_category': 2,  # 資本財
        'description': '車輛、運輸設備通常為固定資產，屬於 Category 2'
    },
    # 以下為 Cloudflare 保護，暫時手動定義
    'land': {
        'category': '土地及改良物',
        'is_fixed_asset': True,
        'ghg_category': 2,
        'description': '土地與土地改良物為固定資產，屬於 Category 2'
    },
    'building': {
        'category': '建築物',
        'is_fixed_asset': True,
        'ghg_category': 2,
        'description': '建築物為固定資產，屬於 Category 2'
    },
    'miscellaneous': {
        'category': '雜項設備',
        'is_fixed_asset': True,
        'ghg_category': 2,
        'description': '雜項設備（如家具、冷氣設備等）通常為固定資產'
    },
    'nonconsumables': {
        'category': '非消耗品',
        'is_fixed_asset': False,  # 視金額而定
        'ghg_category': '1 or 2',
        'description': '非消耗品需視金額與使用年限判斷，可能屬於 Category 1 或 2'
    },
    'consumables': {
        'category': '消耗品',
        'is_fixed_asset': False,
        'ghg_category': 1,
        'description': '消耗品不列為固定資產，屬於 Category 1'
    }
}


def parse_xml_file(xml_path, tag_name):
    """
    解析 XML 檔案，提取財產名稱
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        items = []
        for item in root.findall(tag_name):
            name_elem = item.find('財產名稱')
            if name_elem is not None and name_elem.text:
                name = name_elem.text.strip()
                if name and name != tag_name:  # 排除頂層標題
                    # 提取其他資訊
                    lei = item.find('類')
                    xiang = item.find('項')
                    mu = item.find('目')
                    jie = item.find('節')

                    code_parts = []
                    if lei is not None and lei.text and lei.text.strip():
                        code_parts.append(lei.text.strip())
                    if xiang is not None and xiang.text and xiang.text.strip():
                        code_parts.append(xiang.text.strip())
                    if mu is not None and mu.text and mu.text.strip():
                        code_parts.append(mu.text.strip())
                    if jie is not None and jie.text and jie.text.strip():
                        code_parts.append(jie.text.strip())

                    code = '-'.join(code_parts) if code_parts else ''

                    items.append({
                        'code': code,
                        'name': name
                    })

        return items
    except ET.ParseError as e:
        print(f"XML 解析錯誤 {xml_path}: {e}")
        return []
    except Exception as e:
        print(f"檔案讀取錯誤 {xml_path}: {e}")
        return []


def build_asset_classification_table():
    """
    建立固定資產分類對照表
    """
    all_items = []

    for key, config in XML_FILES.items():
        print(f"\n處理 {config['category']}...")

        if 'file' in config and 'tag' in config:
            # 解析 XML 檔案
            xml_path = DATA_DIR / config['file']
            if xml_path.exists():
                items = parse_xml_file(xml_path, config['tag'])
                print(f"  從 {config['file']} 解析出 {len(items)} 個項目")

                for item in items:
                    all_items.append({
                        'category': config['category'],
                        'code': item['code'],
                        'name': item['name'],
                        'is_fixed_asset': config['is_fixed_asset'],
                        'ghg_category': config['ghg_category'],
                        'description': config['description']
                    })
            else:
                print(f"  檔案不存在: {xml_path}")
        else:
            # 只有大類別資訊（Cloudflare 保護的檔案）
            all_items.append({
                'category': config['category'],
                'code': '',
                'name': config['category'],
                'is_fixed_asset': config['is_fixed_asset'],
                'ghg_category': config['ghg_category'],
                'description': config['description']
            })
            print(f"  加入大類別：{config['category']}")

    # 轉換為 DataFrame
    df = pd.DataFrame(all_items)

    # 輸出統計
    print(f"\n總計：{len(df)} 個項目")
    print(f"固定資產類：{df['is_fixed_asset'].sum()} 個")
    print(f"非固定資產類：{(~df['is_fixed_asset']).sum()} 個")

    return df


def build_keyword_rules():
    """
    建立關鍵字判斷規則
    基於常見採購項目
    """
    rules = {
        'category_2_keywords': {
            # 絕對屬於 Category 2（資本財）的關鍵字
            'equipment': ['設備', '機器', '機械', '儀器', '裝置'],
            'vehicles': ['車輛', '汽車', '卡車', '貨車', '轎車', '電動車'],
            'furniture': ['家具', '辦公桌', '椅子', '櫃子', '沙發'],
            'property': ['土地', '建築', '廠房', '房屋', '不動產'],
            'it_hardware': ['伺服器', '工作站', '主機', '網路設備', '儲存設備'],
            'description': '這些項目通常金額較高且使用年限超過 2 年，應列為固定資產'
        },
        'category_1_keywords': {
            # 絕對屬於 Category 1（購買商品）的關鍵字
            'office_supplies': ['文具', '紙張', '筆', '墨水', '影印紙'],
            'consumables': ['耗材', '碳粉', '墨水匣', '電池', '燈泡'],
            'raw_materials': ['原料', '材料', '零件', '配件'],
            'services': ['服務', '維修', '保養', '清潔', '顧問'],
            'description': '這些項目為消耗品或服務，不列為固定資產'
        },
        'ambiguous_keywords': {
            # 需要額外判斷（金額、會計科目）的關鍵字
            'computer_related': ['電腦', '筆電', '平板', '螢幕', '印表機'],
            'phone_related': ['手機', '電話', '通訊設備'],
            'appliances': ['冷氣', '冰箱', '飲水機'],
            'description': '這些項目需要根據金額門檻（通常 10,000-50,000 元）與會計科目判斷',
            'threshold_note': '企業通常將金額 >= 10,000-50,000 元且使用年限 > 2 年的項目列為固定資產'
        }
    }

    return rules


def main():
    """主函數"""
    print("=" * 70)
    print("  解析政府「財物標準分類」資料")
    print("=" * 70)

    # 1. 建立分類對照表
    df = build_asset_classification_table()

    # 2. 儲存 CSV
    output_csv = OUTPUT_DIR / "asset_classification_table.csv"
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n✅ 已儲存 CSV: {output_csv}")
    print(f"   共 {len(df)} 筆資料")

    # 3. 建立關鍵字規則
    rules = build_keyword_rules()

    # 4. 儲存 JSON
    output_json = OUTPUT_DIR / "ghg_category_rules.json"
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 已儲存規則: {output_json}")

    # 5. 顯示範例
    print("\n" + "=" * 70)
    print("  Category 2 固定資產範例（機械設備）")
    print("=" * 70)
    machinery_df = df[df['category'] == '機械及設備'].head(10)
    for idx, row in machinery_df.iterrows():
        print(f"  {row['code']:15s} {row['name']}")

    print("\n" + "=" * 70)
    print("  關鍵字規則摘要")
    print("=" * 70)
    print(f"\n🔴 Category 2（資本財）關鍵字數：{sum(len(v) for k, v in rules['category_2_keywords'].items() if isinstance(v, list))} 個")
    print(f"🟢 Category 1（購買商品）關鍵字數：{sum(len(v) for k, v in rules['category_1_keywords'].items() if isinstance(v, list))} 個")
    print(f"🟡 需額外判斷關鍵字數：{sum(len(v) for k, v in rules['ambiguous_keywords'].items() if isinstance(v, list))} 個")

    print("\n" + "=" * 70)
    print("  ✅ 完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
