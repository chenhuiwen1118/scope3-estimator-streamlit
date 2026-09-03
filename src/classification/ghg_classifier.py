"""
GHG Protocol 類別判斷器
根據會計邏輯、物品名稱、金額等資訊，判斷採購項目屬於 Scope 3 的哪個類別
"""

from pathlib import Path
import json
import pandas as pd
from typing import Dict, List, Optional, Tuple
import re


class GHGCategoryClassifier:
    """
    GHG Protocol Scope 3 類別判斷器

    判斷優先級：
    1. 會計科目（最準確）
    2. 財物分類 + 金額門檻
    3. 關鍵字匹配
    4. 預設策略
    """

    def __init__(self,
                 asset_classification_path: Optional[Path] = None,
                 accounting_subject_path: Optional[Path] = None,
                 keyword_rules_path: Optional[Path] = None):
        """
        初始化分類器

        Args:
            asset_classification_path: 財物標準分類對照表路徑
            accounting_subject_path: 會計科目映射表路徑
            keyword_rules_path: 關鍵字規則路徑
        """
        # 設定預設路徑
        if asset_classification_path is None:
            asset_classification_path = Path(__file__).parent.parent.parent / \
                "data" / "reference_data" / "asset_classification_table.csv"

        if accounting_subject_path is None:
            accounting_subject_path = Path(__file__).parent.parent.parent / \
                "data" / "reference_data" / "accounting_subject_mapping.json"

        if keyword_rules_path is None:
            keyword_rules_path = Path(__file__).parent.parent.parent / \
                "data" / "reference_data" / "ghg_category_rules.json"

        # 載入資料
        self.asset_df = None
        if asset_classification_path.exists():
            self.asset_df = pd.read_csv(asset_classification_path)

        self.accounting_mapping = None
        if accounting_subject_path.exists():
            with open(accounting_subject_path, 'r', encoding='utf-8') as f:
                self.accounting_mapping = json.load(f)

        self.keyword_rules = None
        if keyword_rules_path.exists():
            with open(keyword_rules_path, 'r', encoding='utf-8') as f:
                self.keyword_rules = json.load(f)

        # 預設金額門檻（台幣）
        self.default_threshold = 30000  # 中型企業標準

    def classify(self,
                 item_name: str,
                 accounting_subject: Optional[str] = None,
                 accounting_subject_code: Optional[str] = None,
                 amount: Optional[float] = None,
                 useful_life: Optional[int] = None,
                 return_confidence: bool = True) -> Dict:
        """
        判斷採購項目的 GHG Protocol 類別

        Args:
            item_name: 採購項目名稱
            accounting_subject: 會計科目名稱
            accounting_subject_code: 會計科目代碼
            amount: 採購金額（台幣）
            useful_life: 預計使用年限（年）
            return_confidence: 是否返回信心度

        Returns:
            {
                'ghg_category': 1 or 2 or 'unknown',
                'confidence': 0.0-1.0,
                'method': 'accounting' | 'asset_classification' | 'keyword' | 'amount_threshold' | 'default',
                'reasoning': '判斷理由',
                'is_fixed_asset': True/False/None,
                'recommendation': '建議'
            }
        """
        # Level 1: 會計科目判斷（最準確）
        if accounting_subject or accounting_subject_code:
            result = self._classify_by_accounting_subject(
                accounting_subject, accounting_subject_code
            )
            if result['ghg_category'] != 'unknown':
                return result

        # Level 2: 財物分類判斷
        if self.asset_df is not None:
            result = self._classify_by_asset_classification(item_name)
            if result['ghg_category'] != 'unknown':
                # 如果有金額資訊，進一步驗證
                if amount is not None and result['ghg_category'] == 2:
                    if amount < self.default_threshold:
                        result['ghg_category'] = 1
                        result['confidence'] = 0.8
                        result['reasoning'] += f"；但金額 {amount:,.0f} 元低於資本化門檻，改判為 Category 1"
                return result

        # Level 3: 關鍵字匹配
        if self.keyword_rules is not None:
            result = self._classify_by_keywords(item_name, amount)
            if result['ghg_category'] != 'unknown':
                return result

        # Level 4: 金額門檻判斷
        if amount is not None:
            result = self._classify_by_amount(item_name, amount, useful_life)
            return result

        # 預設策略：無法判斷
        return {
            'ghg_category': 'unknown',
            'confidence': 0.0,
            'method': 'default',
            'reasoning': '資訊不足，無法判斷。建議提供會計科目或金額資訊。',
            'is_fixed_asset': None,
            'recommendation': '請補充：(1) 會計科目；(2) 採購金額；(3) 預計使用年限'
        }

    def _classify_by_accounting_subject(self,
                                        subject_name: Optional[str],
                                        subject_code: Optional[str]) -> Dict:
        """Level 1: 根據會計科目判斷"""
        if self.accounting_mapping is None:
            return {'ghg_category': 'unknown'}

        # 搜尋 Category 2 科目
        for subject in self.accounting_mapping['category_2_subjects']['subjects']:
            if subject_code and subject.get('code') == subject_code:
                return {
                    'ghg_category': subject['ghg_category'],
                    'confidence': subject.get('confidence', 1.0),
                    'method': 'accounting',
                    'reasoning': f"會計科目「{subject['name']}」列為固定資產，屬於資本財",
                    'is_fixed_asset': True,
                    'recommendation': '使用「重量/數量」計算排放（平均資料法）'
                }

            if subject_name:
                if subject['name'] in subject_name:
                    return {
                        'ghg_category': subject['ghg_category'],
                        'confidence': subject.get('confidence', 0.9),
                        'method': 'accounting',
                        'reasoning': f"會計科目「{subject['name']}」列為固定資產，屬於資本財",
                        'is_fixed_asset': True,
                        'recommendation': '使用「重量/數量」計算排放（平均資料法）'
                    }

                # 檢查別名
                for alias in subject.get('alias', []):
                    if alias in subject_name:
                        return {
                            'ghg_category': subject['ghg_category'],
                            'confidence': subject.get('confidence', 0.85),
                            'method': 'accounting',
                            'reasoning': f"會計科目「{alias}」為固定資產別名，屬於資本財",
                            'is_fixed_asset': True,
                            'recommendation': '使用「重量/數量」計算排放（平均資料法）'
                        }

        # 搜尋 Category 1 科目
        for subject in self.accounting_mapping['category_1_subjects']['subjects']:
            if subject_code and subject.get('code') == subject_code:
                if subject['ghg_category'] == 'exclude':
                    return {
                        'ghg_category': 'exclude',
                        'confidence': 1.0,
                        'method': 'accounting',
                        'reasoning': f"「{subject['name']}」為非現金支出，不列入 Scope 3",
                        'is_fixed_asset': False,
                        'recommendation': '排除此項目，不計算排放'
                    }

                return {
                    'ghg_category': subject['ghg_category'],
                    'confidence': subject.get('confidence', 1.0),
                    'method': 'accounting',
                    'reasoning': f"會計科目「{subject['name']}」為費用科目，屬於購買商品/勞務",
                    'is_fixed_asset': False,
                    'recommendation': '使用「重量/數量」或「金額」計算排放（視資料可得性）'
                }

            if subject_name:
                if subject['name'] in subject_name:
                    return {
                        'ghg_category': subject['ghg_category'],
                        'confidence': subject.get('confidence', 0.9),
                        'method': 'accounting',
                        'reasoning': f"會計科目「{subject['name']}」為費用科目，屬於購買商品/勞務",
                        'is_fixed_asset': False,
                        'recommendation': '使用「重量/數量」或「金額」計算排放'
                    }

                # 檢查別名
                for alias in subject.get('alias', []):
                    if alias in subject_name:
                        return {
                            'ghg_category': subject['ghg_category'],
                            'confidence': subject.get('confidence', 0.85),
                            'method': 'accounting',
                            'reasoning': f"會計科目「{alias}」為費用科目別名，屬於購買商品/勞務",
                            'is_fixed_asset': False,
                            'recommendation': '使用「重量/數量」或「金額」計算排放'
                        }

        return {'ghg_category': 'unknown'}

    def _classify_by_asset_classification(self, item_name: str) -> Dict:
        """Level 2: 根據財物標準分類判斷"""
        item_name = str(item_name or '').strip()
        if not item_name:
            return {'ghg_category': 'unknown'}

        # 在財物分類表中搜尋
        names = self.asset_df['name'].astype(str)
        matches = self.asset_df[names.str.contains(item_name, case=False, na=False, regex=False)]

        # 採購品名通常比財物分類更長；補上反向包含比對。
        if len(matches) == 0 and len(item_name) >= 2:
            escaped = re.escape(item_name)
            name_pattern = "|".join(
                re.escape(name)
                for name in names.dropna().unique()
                if len(str(name).strip()) >= 2 and str(name).strip() in item_name
            )
            if name_pattern:
                matches = self.asset_df[names.str.contains(name_pattern, case=False, na=False, regex=True)]

        if len(matches) > 0:
            first_match = matches.iloc[0]
            is_fixed_asset = first_match['is_fixed_asset']
            ghg_category = first_match['ghg_category']

            return {
                'ghg_category': ghg_category,
                'confidence': 0.85,
                'method': 'asset_classification',
                'reasoning': f"符合政府財物標準分類「{first_match['category']}」中的「{first_match['name']}」",
                'is_fixed_asset': is_fixed_asset,
                'recommendation': '使用「重量/數量」計算排放' if is_fixed_asset else '視金額決定計算方式'
            }

        return {'ghg_category': 'unknown'}

    def _classify_by_keywords(self, item_name: str, amount: Optional[float] = None) -> Dict:
        """Level 3: 根據關鍵字匹配判斷"""
        item_name_lower = item_name.lower()  # 不區分大小寫

        # Priority 1: Category 1 優先模式（服務類即使金額高也是 Cat 1）
        if 'category_1_priority_patterns' in self.keyword_rules:
            for pattern in self.keyword_rules['category_1_priority_patterns'].get('patterns', []):
                if re.search(pattern, item_name_lower, re.IGNORECASE):
                    confidence = self.keyword_rules['category_1_priority_patterns'].get('confidence', 0.85)
                    return {
                        'ghg_category': 1,
                        'confidence': confidence,
                        'method': 'keyword',
                        'reasoning': f"符合服務/消耗品優先模式（即使金額高也屬 Category 1）",
                        'is_fixed_asset': False,
                        'recommendation': '服務與消耗品為當期費用，不資本化'
                    }

        # Priority 2: Category 1 關鍵字（調整為優先檢查）
        cat1_keywords = self.keyword_rules['category_1_keywords']
        for category, keywords in cat1_keywords.items():
            if isinstance(keywords, list):
                for keyword in keywords:
                    # 使用單詞邊界匹配，避免部分詞誤匹配
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    if re.search(pattern, item_name_lower):
                        return {
                            'ghg_category': 1,
                            'confidence': 0.8,
                            'method': 'keyword',
                            'reasoning': f"包含購買商品/服務關鍵字「{keyword}」（{category}）",
                            'is_fixed_asset': False,
                            'recommendation': '使用「重量/數量」或「金額」計算排放'
                        }

        # Priority 3: Category 2 優先模式（明確的資產購買）
        if 'category_2_priority_patterns' in self.keyword_rules:
            cat2_priority = self.keyword_rules['category_2_priority_patterns']
            min_amount = cat2_priority.get('min_amount', 50000)
            if amount and amount >= min_amount:
                for pattern in cat2_priority.get('patterns', []):
                    if re.search(pattern, item_name_lower, re.IGNORECASE):
                        confidence = cat2_priority.get('confidence', 0.80)
                        return {
                            'ghg_category': 2,
                            'confidence': confidence,
                            'method': 'keyword',
                            'reasoning': f"符合資產購買模式且金額 {amount:,.0f} >= {min_amount:,.0f}",
                            'is_fixed_asset': True,
                            'recommendation': '確認為資本財購買'
                        }

        # Priority 4: Category 2 關鍵字
        cat2_keywords = self.keyword_rules['category_2_keywords']
        for category, keywords in cat2_keywords.items():
            if isinstance(keywords, list):
                for keyword in keywords:
                    # 使用單詞邊界匹配，避免部分詞誤匹配
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    if re.search(pattern, item_name_lower):
                        return {
                            'ghg_category': 2,
                            'confidence': 0.75,
                            'method': 'keyword',
                            'reasoning': f"包含資本財關鍵字「{keyword}」（{category}）",
                            'is_fixed_asset': True,
                            'recommendation': '建議確認會計科目與金額，若金額較小可能屬於 Category 1'
                        }

        # Priority 5: 模糊關鍵字（需要額外判斷）
        ambiguous_keywords = self.keyword_rules['ambiguous_keywords']
        for category, keywords in ambiguous_keywords.items():
            if isinstance(keywords, list):
                for keyword in keywords:
                    # 使用單詞邊界匹配，避免部分詞誤匹配
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    if re.search(pattern, item_name_lower):
                        if amount and amount >= self.default_threshold:
                            return {
                                'ghg_category': 2,
                                'confidence': 0.7,
                                'method': 'keyword',
                                'reasoning': f"包含模糊關鍵字「{keyword}」，且金額 {amount:,.0f} 元 >= 門檻，判定為資本財",
                                'is_fixed_asset': True,
                                'recommendation': '建議確認會計科目'
                            }
                        else:
                            return {
                                'ghg_category': 1,
                                'confidence': 0.65,
                                'method': 'keyword',
                                'reasoning': f"包含模糊關鍵字「{keyword}」，但無金額資訊或金額較小，暫判為購買商品",
                                'is_fixed_asset': False,
                                'recommendation': '建議提供金額與會計科目以提高準確度'
                            }

        return {'ghg_category': 'unknown'}

    def _classify_by_amount(self, item_name: str, amount: float, useful_life: Optional[int] = None) -> Dict:
        """Level 4: 根據金額門檻判斷"""
        if amount >= self.default_threshold:
            if useful_life and useful_life > 2:
                return {
                    'ghg_category': 2,
                    'confidence': 0.7,
                    'method': 'amount_threshold',
                    'reasoning': f"金額 {amount:,.0f} 元 >= 門檻且使用年限 > 2 年，可能為資本財",
                    'is_fixed_asset': True,
                    'recommendation': '建議確認會計科目，確保分類正確'
                }
            else:
                return {
                    'ghg_category': 2,
                    'confidence': 0.6,
                    'method': 'amount_threshold',
                    'reasoning': f"金額 {amount:,.0f} 元 >= 門檻，可能為資本財（需確認使用年限）",
                    'is_fixed_asset': None,
                    'recommendation': '建議提供使用年限與會計科目'
                }
        else:
            return {
                'ghg_category': 1,
                'confidence': 0.75,
                'method': 'amount_threshold',
                'reasoning': f"金額 {amount:,.0f} 元 < 門檻 {self.default_threshold:,.0f} 元，通常為購買商品",
                'is_fixed_asset': False,
                'recommendation': '使用「重量/數量」或「金額」計算排放'
            }

    def batch_classify(self, items: List[Dict]) -> List[Dict]:
        """
        批次分類

        Args:
            items: 採購項目列表，每個項目為 dict，包含 item_name, accounting_subject 等

        Returns:
            分類結果列表
        """
        results = []
        for item in items:
            result = self.classify(
                item_name=item.get('item_name', ''),
                accounting_subject=item.get('accounting_subject'),
                accounting_subject_code=item.get('accounting_subject_code'),
                amount=item.get('amount'),
                useful_life=item.get('useful_life')
            )
            result['original_item'] = item
            results.append(result)

        return results
