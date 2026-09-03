#!/usr/bin/env python3
"""
解析台灣政府電子採購網 XML 決標資料，轉換為 CSV 格式
"""

import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import sys

PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "training_data" / "raw" / "taiwan_procurement"
OUTPUT_DIR = PROJECT_ROOT / "data" / "training_data" / "processed"

def parse_xml_file(xml_file: Path) -> list:
    """解析單個 XML 檔案"""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        records = []

        for tender in root.findall('TENDER'):
            # 提取關鍵欄位
            record = {
                'org_name': tender.findtext('TENDER_ORG_NAME', ''),
                'org_addr': tender.findtext('TENDER_ORG_ADDR', ''),
                'case_no': tender.findtext('TENDER_CASE_NO', ''),
                'case_name': tender.findtext('TENDER_NAME', ''),
                'procurement_attr': tender.findtext('PROCUREMENT_ATTR', ''),  # 工程類/財物類/勞務類
                'procurement_type': tender.findtext('PROCUREMENT_TYPE', ''),
                'award_way': tender.findtext('TENDER_AWARD_WAY', ''),
                'award_price': tender.findtext('TENDER_AWARD_PRICE', ''),
                'award_date': tender.findtext('AWARD_DATE', ''),
                'award_notice_date': tender.findtext('AWARD_NOTICE_DATE', ''),
                'contact_person': tender.findtext('CONTACT_PERSON', ''),
                'contact_tel': tender.findtext('TENDER_TEL', ''),
                'source_file': xml_file.name
            }

            # 提取得標廠商資訊（如果有）
            bidder_list = tender.find('BIDDER_LIST')
            if bidder_list is not None:
                record['bidder_name'] = bidder_list.findtext('BIDDER_SUPP_NAME', '')
                record['bidder_addr'] = bidder_list.findtext('BIDDER_SUPP_ADDR', '')

            records.append(record)

        return records

    except ET.ParseError as e:
        print(f"  ⚠️  XML 解析錯誤 [{xml_file.name}]: {e}")
        return []
    except Exception as e:
        print(f"  ⚠️  其他錯誤 [{xml_file.name}]: {e}")
        return []


def main():
    print("=" * 70)
    print("  解析台灣政府電子採購網 XML 決標資料")
    print("=" * 70)

    # 尋找所有 XML 檔案
    xml_files = sorted(RAW_DIR.glob("award_*.xml"))

    if not xml_files:
        print(f"\n❌ 找不到 XML 檔案: {RAW_DIR}")
        sys.exit(1)

    print(f"\n📥 找到 {len(xml_files)} 個 XML 檔案")
    print(f"   範圍: {xml_files[0].name} ~ {xml_files[-1].name}\n")

    # 解析所有檔案
    all_records = []

    for xml_file in tqdm(xml_files, desc="解析進度"):
        records = parse_xml_file(xml_file)
        all_records.extend(records)

    print(f"\n✅ 解析完成: {len(all_records):,} 筆記錄")

    if len(all_records) == 0:
        print("❌ 沒有解析到任何資料")
        sys.exit(1)

    # 轉換為 DataFrame
    df = pd.DataFrame(all_records)

    # 資料清理
    print(f"\n🔧 資料清理...")

    # 轉換金額為數字
    df['award_price_num'] = pd.to_numeric(df['award_price'], errors='coerce')

    # 移除金額為空或 0 的記錄
    before_count = len(df)
    df = df[df['award_price_num'] > 0].copy()
    removed = before_count - len(df)
    print(f"   移除無效金額記錄: {removed} 筆")

    # 移除標案名稱為空的記錄
    before_count = len(df)
    df = df[df['case_name'].str.strip() != ''].copy()
    removed = before_count - len(df)
    print(f"   移除無標案名稱記錄: {removed} 筆")

    print(f"\n📊 最終資料筆數: {len(df):,} 筆")

    # 統計分析
    print(f"\n📈 資料統計:")
    print(f"   採購性質分布:")
    attr_counts = df['procurement_attr'].value_counts()
    for attr, count in attr_counts.items():
        pct = count / len(df) * 100
        print(f"      {attr}: {count:,} 筆 ({pct:.1f}%)")

    print(f"\n   金額統計:")
    print(f"      總決標金額: ${df['award_price_num'].sum():,.0f} 元")
    print(f"      平均金額: ${df['award_price_num'].mean():,.0f} 元")
    print(f"      中位數: ${df['award_price_num'].median():,.0f} 元")
    print(f"      最大值: ${df['award_price_num'].max():,.0f} 元")
    print(f"      最小值: ${df['award_price_num'].min():,.0f} 元")

    print(f"\n   前 10 大機關:")
    org_counts = df['org_name'].value_counts().head(10)
    for org, count in org_counts.items():
        print(f"      {org}: {count} 筆")

    # 儲存為 CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "taiwan_govt_procurement_2024_h2.csv"

    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 儲存結果: {output_file.name}")

    # 顯示範例
    print(f"\n📋 資料範例（前 5 筆）:")
    sample_cols = ['org_name', 'case_name', 'procurement_attr', 'award_price_num']
    for idx, row in df[sample_cols].head(5).iterrows():
        print(f"\n   [{idx+1}] {row['org_name']}")
        print(f"       {row['case_name'][:60]}{'...' if len(row['case_name']) > 60 else ''}")
        print(f"       類別: {row['procurement_attr']} | 金額: ${row['award_price_num']:,.0f}")

    print("\n" + "=" * 70)
    print("  ✅ 解析完成！")
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
