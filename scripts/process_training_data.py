#!/usr/bin/env python3
"""
Training Data Processing Script

功能：
1. 解析下載的訓練資料（Kaggle CSV, OCDS JSON）
2. 標準化欄位格式
3. 清理文字資料
4. 使用 GHGCategoryClassifier 自動標註
5. 輸出統一格式的資料集

使用方法：
    python scripts/process_training_data.py
"""

import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import re

# 加入 src 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from classification.ghg_classifier import GHGCategoryClassifier


###############################################################################
# 配置
###############################################################################

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "training_data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ANNOTATED_DIR = DATA_DIR / "annotated"

# 標準化欄位名稱對應
COLUMN_MAPPING = {
    # 描述欄位
    'tender_description': 'description',
    'commodity_description': 'description',
    'item_description': 'description',
    'product_description': 'description',
    'description': 'description',
    'title': 'title',

    # 金額欄位
    'awarded_amt': 'amount',
    'amount': 'amount',
    'value': 'amount',
    'total_amount': 'amount',
    'payment_amount': 'amount',

    # 供應商欄位
    'supplier_name': 'supplier',
    'supplier': 'supplier',
    'vendor': 'supplier',
    'contractor': 'supplier',

    # 日期欄位
    'award_date': 'date',
    'date': 'date',
    'transaction_date': 'date',

    # 分類欄位
    'category': 'original_category',
    'classification': 'original_category',

    # 機關欄位
    'agency': 'organization',
    'department': 'organization',
}


###############################################################################
# 資料清理函數
###############################################################################

def clean_text(text: str) -> str:
    """清理文字資料"""
    if pd.isna(text) or not isinstance(text, str):
        return ""

    # 移除多餘空白
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # 移除特殊字元（保留基本標點）
    # text = re.sub(r'[^\w\s\-.,;:()\[\]\/]', '', text)

    return text


def standardize_amount(amount) -> Optional[float]:
    """標準化金額格式"""
    if pd.isna(amount):
        return None

    if isinstance(amount, str):
        # 移除貨幣符號和逗號
        amount = re.sub(r'[£$€¥,]', '', amount)
        try:
            return float(amount)
        except ValueError:
            return None

    try:
        return float(amount)
    except (ValueError, TypeError):
        return None


def infer_currency(row: pd.Series, source: str) -> str:
    """根據來源推斷貨幣"""
    if 'currency' in row and not pd.isna(row['currency']):
        return row['currency']

    # 根據資料來源推斷
    currency_map = {
        'singapore': 'SGD',
        'san_francisco': 'USD',
        'sf_procurement': 'USD',
        'uk_contracts': 'GBP',
    }

    for key, currency in currency_map.items():
        if key in source.lower():
            return currency

    return 'UNKNOWN'


###############################################################################
# 資料解析函數
###############################################################################

def parse_kaggle_csv(file_path: Path, source_name: str) -> pd.DataFrame:
    """解析 Kaggle CSV 資料"""
    print(f"  📄 解析 {file_path.name}...")

    try:
        df = pd.read_csv(file_path, low_memory=False)
        print(f"     原始記錄數: {len(df)}")
        print(f"     原始欄位: {df.columns.tolist()}")

        # 標準化欄位名稱
        df_renamed = {}
        for col in df.columns:
            col_lower = col.lower().replace(' ', '_')
            if col_lower in COLUMN_MAPPING:
                standard_name = COLUMN_MAPPING[col_lower]
                df_renamed[col] = standard_name

        df = df.rename(columns=df_renamed)

        # 確保有 description 欄位
        if 'description' not in df.columns:
            print(f"     ⚠️  警告: 找不到 description 欄位")
            # 嘗試從其他欄位推斷
            for col in df.columns:
                if 'desc' in col.lower() or 'item' in col.lower():
                    df['description'] = df[col]
                    print(f"     使用 {col} 作為 description")
                    break

        # 加入來源資訊
        df['source'] = source_name
        df['source_file'] = file_path.name

        return df

    except Exception as e:
        print(f"     ❌ 解析失敗: {e}")
        return pd.DataFrame()


def parse_ocds_jsonl(file_path: Path, source_name: str) -> pd.DataFrame:
    """解析 OCDS JSONL 資料"""
    print(f"  📄 解析 {file_path.name}...")

    records = []
    line_count = 0
    error_count = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1

                # 每 10000 筆顯示進度
                if line_count % 10000 == 0:
                    print(f"     處理 {line_count} 筆記錄...")

                try:
                    data = json.loads(line)

                    # 提取 tender 資訊
                    if 'tender' not in data:
                        continue

                    tender = data['tender']

                    # 提取 items（最重要）
                    if 'items' in tender and tender['items']:
                        for item in tender['items']:
                            record = {
                                'ocid': data.get('ocid', ''),
                                'tender_id': tender.get('id', ''),
                                'title': tender.get('title', ''),
                                'description': item.get('description', ''),
                                'tender_description': tender.get('description', ''),
                                'original_category': None,
                                'classification_scheme': None,
                                'classification_code': None,
                                'classification_description': None,
                                'quantity': item.get('quantity', None),
                                'unit': None,
                                'amount': None,
                                'currency': None,
                                'organization': None,
                                'date': tender.get('tenderPeriod', {}).get('startDate', None),
                                'source': source_name,
                                'source_file': file_path.name,
                            }

                            # 提取分類資訊
                            if 'classification' in item:
                                classification = item['classification']
                                record['classification_scheme'] = classification.get('scheme', None)
                                record['classification_code'] = classification.get('id', None)
                                record['classification_description'] = classification.get('description', None)

                            # 提取單位資訊
                            if 'unit' in item:
                                unit_info = item['unit']
                                record['unit'] = unit_info.get('name', None)

                                # 提取單價
                                if 'value' in unit_info:
                                    value = unit_info['value']
                                    record['amount'] = value.get('amount', None)
                                    record['currency'] = value.get('currency', None)

                            # 若 item 沒有金額，使用 tender 總金額
                            if record['amount'] is None and 'value' in tender:
                                value = tender['value']
                                record['amount'] = value.get('amount', None)
                                record['currency'] = value.get('currency', None)

                            records.append(record)

                    # 若沒有 items，至少保留 tender 層級資訊
                    elif 'description' in tender or 'title' in tender:
                        record = {
                            'ocid': data.get('ocid', ''),
                            'tender_id': tender.get('id', ''),
                            'title': tender.get('title', ''),
                            'description': tender.get('description', ''),
                            'tender_description': None,
                            'original_category': None,
                            'classification_scheme': None,
                            'classification_code': None,
                            'classification_description': None,
                            'quantity': None,
                            'unit': None,
                            'amount': None,
                            'currency': None,
                            'organization': None,
                            'date': tender.get('tenderPeriod', {}).get('startDate', None),
                            'source': source_name,
                            'source_file': file_path.name,
                        }

                        if 'value' in tender:
                            value = tender['value']
                            record['amount'] = value.get('amount', None)
                            record['currency'] = value.get('currency', None)

                        records.append(record)

                except json.JSONDecodeError:
                    error_count += 1
                    continue
                except Exception as e:
                    error_count += 1
                    if error_count < 10:  # 只顯示前 10 個錯誤
                        print(f"     ⚠️  處理第 {line_count} 筆時發生錯誤: {e}")
                    continue

        print(f"     原始記錄數: {line_count}")
        print(f"     提取記錄數: {len(records)}")
        print(f"     錯誤數: {error_count}")

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        return df

    except Exception as e:
        print(f"     ❌ 解析失敗: {e}")
        return pd.DataFrame()


###############################################################################
# 資料標準化與清理
###############################################################################

def standardize_dataset(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """標準化資料集格式"""
    print(f"\n  🔧 標準化 {source_name}...")

    if df.empty:
        return df

    # 清理描述文字
    if 'description' in df.columns:
        df['description'] = df['description'].apply(clean_text)

    if 'title' in df.columns:
        df['title'] = df['title'].apply(clean_text)

    # 標準化金額
    if 'amount' in df.columns:
        df['amount'] = df['amount'].apply(standardize_amount)

    # 推斷貨幣
    if 'currency' not in df.columns or df['currency'].isna().all():
        df['currency'] = df.apply(lambda row: infer_currency(row, source_name), axis=1)

    # 移除空描述的記錄
    if 'description' in df.columns:
        before_count = len(df)
        df = df[df['description'].str.len() > 0]
        after_count = len(df)
        if before_count > after_count:
            print(f"     移除 {before_count - after_count} 筆空描述記錄")

    # 加入處理時間戳記
    df['processed_at'] = datetime.now().isoformat()

    print(f"     處理後記錄數: {len(df)}")

    return df


###############################################################################
# GHG 分類標註
###############################################################################

def annotate_with_ghg_classifier(df: pd.DataFrame) -> pd.DataFrame:
    """使用 GHGCategoryClassifier 標註資料"""
    print(f"\n  🏷️  GHG 分類標註...")

    if df.empty:
        return df

    # 初始化分類器
    classifier = GHGCategoryClassifier()

    # 準備標註結果欄位
    df['ghg_category'] = None
    df['ghg_confidence'] = None
    df['ghg_method'] = None
    df['ghg_reasoning'] = None
    df['is_fixed_asset'] = None

    total = len(df)
    annotated = 0

    print(f"     總記錄數: {total}")

    for idx, row in df.iterrows():
        # 每 1000 筆顯示進度
        if annotated % 1000 == 0 and annotated > 0:
            print(f"     已標註: {annotated}/{total} ({annotated/total*100:.1f}%)")

        # 準備分類器輸入
        item_name = row.get('description', '')
        if not item_name:
            item_name = row.get('title', '')

        amount = row.get('amount', None)

        # 執行分類
        try:
            result = classifier.classify(
                item_name=item_name,
                amount=amount
            )

            df.at[idx, 'ghg_category'] = result['ghg_category']
            df.at[idx, 'ghg_confidence'] = result['confidence']
            df.at[idx, 'ghg_method'] = result['method']
            df.at[idx, 'ghg_reasoning'] = result['reasoning']
            df.at[idx, 'is_fixed_asset'] = result['is_fixed_asset']

            annotated += 1

        except Exception as e:
            print(f"     ⚠️  標註失敗 (idx={idx}): {e}")
            continue

    print(f"     標註完成: {annotated}/{total}")

    # 統計
    if annotated > 0:
        print(f"\n     📊 分類統計:")
        print(f"        Category 1: {(df['ghg_category'] == 1).sum()} 筆")
        print(f"        Category 2: {(df['ghg_category'] == 2).sum()} 筆")
        print(f"        Unknown: {(df['ghg_category'] == 'unknown').sum()} 筆")
        print(f"        Exclude: {(df['ghg_category'] == 'exclude').sum()} 筆")
        print(f"        平均信心度: {df['ghg_confidence'].mean():.2%}")

    return df


###############################################################################
# 主程式
###############################################################################

def process_all_datasets():
    """處理所有下載的資料集"""
    print("="*70)
    print("  Training Data Processing Script")
    print("="*70)

    # 確保輸出目錄存在
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)

    all_datasets = []

    # 1. 處理 Kaggle 資料集
    print("\n📦 處理 Kaggle 資料集...")

    kaggle_dir = RAW_DIR / "kaggle"
    if kaggle_dir.exists():
        # Singapore Government Procurement
        sg_dir = kaggle_dir / "singapore_procurement"
        if sg_dir.exists():
            for csv_file in sg_dir.glob("*.csv"):
                df = parse_kaggle_csv(csv_file, "kaggle_singapore_govt")
                if not df.empty:
                    df = standardize_dataset(df, "kaggle_singapore_govt")
                    all_datasets.append(('singapore_govt', df))

        # San Francisco Procurement
        sf_dir = kaggle_dir / "sf_procurement"
        if sf_dir.exists():
            for csv_file in sf_dir.glob("*.csv"):
                df = parse_kaggle_csv(csv_file, "kaggle_sf_procurement")
                if not df.empty:
                    df = standardize_dataset(df, "kaggle_sf_procurement")
                    all_datasets.append(('sf_procurement', df))

        # 其他 Kaggle 資料集
        for subdir in kaggle_dir.iterdir():
            if subdir.is_dir() and subdir.name not in ['singapore_procurement', 'sf_procurement']:
                for csv_file in subdir.glob("*.csv"):
                    df = parse_kaggle_csv(csv_file, f"kaggle_{subdir.name}")
                    if not df.empty:
                        df = standardize_dataset(df, f"kaggle_{subdir.name}")
                        all_datasets.append((subdir.name, df))

    # 2. 處理 OCDS 資料集
    print("\n🌍 處理 OCDS 資料集...")

    ocds_dir = RAW_DIR / "ocds"
    if ocds_dir.exists():
        for jsonl_file in ocds_dir.glob("*.jsonl"):
            year = jsonl_file.stem
            df = parse_ocds_jsonl(jsonl_file, f"ocds_uk_{year}")
            if not df.empty:
                df = standardize_dataset(df, f"ocds_uk_{year}")
                all_datasets.append((f'ocds_uk_{year}', df))

    # 3. 合併所有資料集
    if not all_datasets:
        print("\n❌ 沒有找到任何資料集！")
        print("   請先執行 download_training_data.sh 下載資料")
        return

    print(f"\n📊 找到 {len(all_datasets)} 個資料集")

    # 儲存個別處理後的資料集
    print("\n💾 儲存處理後的資料集...")
    for name, df in all_datasets:
        output_file = PROCESSED_DIR / f"{name}_processed.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"   ✅ {output_file.name} ({len(df)} records)")

    # 合併所有資料集
    print("\n🔀 合併所有資料集...")
    combined_df = pd.concat([df for _, df in all_datasets], ignore_index=True)
    print(f"   總記錄數: {len(combined_df)}")

    # 儲存合併後的資料集
    combined_file = PROCESSED_DIR / "combined_all_sources.csv"
    combined_df.to_csv(combined_file, index=False, encoding='utf-8')
    print(f"   ✅ {combined_file.name}")

    # 4. GHG 分類標註
    print("\n🏷️  執行 GHG 分類標註...")
    annotated_df = annotate_with_ghg_classifier(combined_df.copy())

    # 儲存標註後的資料集
    annotated_file = ANNOTATED_DIR / f"annotated_{datetime.now().strftime('%Y%m%d')}.csv"
    annotated_df.to_csv(annotated_file, index=False, encoding='utf-8')
    print(f"\n   ✅ {annotated_file.name}")

    # 5. 產生統計報告
    print("\n" + "="*70)
    print("  處理完成！統計報告")
    print("="*70)

    print(f"\n📊 資料集統計:")
    print(f"   總記錄數: {len(combined_df)}")
    print(f"   資料來源數: {combined_df['source'].nunique()}")
    print(f"   有金額資訊: {combined_df['amount'].notna().sum()} ({combined_df['amount'].notna().sum()/len(combined_df)*100:.1f}%)")

    print(f"\n🏷️  GHG 分類統計:")
    print(f"   Category 1: {(annotated_df['ghg_category'] == 1).sum()}")
    print(f"   Category 2: {(annotated_df['ghg_category'] == 2).sum()}")
    print(f"   Unknown: {(annotated_df['ghg_category'] == 'unknown').sum()}")
    print(f"   Exclude: {(annotated_df['ghg_category'] == 'exclude').sum()}")
    print(f"   平均信心度: {annotated_df['ghg_confidence'].mean():.2%}")

    print(f"\n💾 輸出檔案:")
    print(f"   處理後資料: {PROCESSED_DIR}/")
    print(f"   標註資料: {annotated_file}")

    print("\n✅ 所有資料處理完成！")
    print("   下一步: 人工審核高信心度樣本")


if __name__ == "__main__":
    try:
        process_all_datasets()
    except KeyboardInterrupt:
        print("\n\n⚠️  使用者中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
