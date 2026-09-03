#!/usr/bin/env python3
"""
Tier 3 EEIO 檢索器
基於 EXIOBASE 多國 EEIO 資料的向量檢索系統
"""

from typing import List, Dict, Optional, Union
from pathlib import Path
import pandas as pd
import numpy as np
import logging

from utils.embedding import EmbeddingEngine
from utils.similarity import fast_cosine_similarity_with_norms, precompute_norms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Tier3EEIORetriever:
    """
    Tier 3 EEIO 檢索器

    基於 EXIOBASE 多國 EEIO 資料，使用向量相似度進行檢索
    支援國家優先排序與相似度門檻篩選
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        embeddings_file: str = "tier3_eeio_embeddings.npy",
        metadata_file: str = "tier3_eeio_metadata.csv",
        embedding_engine: Optional[EmbeddingEngine] = None
    ):
        """
        初始化 Tier 3 EEIO 檢索器

        Args:
            data_dir: 資料目錄路徑
            embeddings_file: Embedding 向量檔案名稱
            metadata_file: 元資料檔案名稱
            embedding_engine: Embedding 引擎（可選，若無則自動創建）
        """
        # 設定路徑
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "emission_factors" / "tier3_eeio"
        self.data_dir = Path(data_dir)

        logger.info("🔧 初始化 Tier 3 EEIO 檢索器")

        # 載入元資料
        metadata_path = self.data_dir / metadata_file
        logger.info(f"   載入元資料: {metadata_path.name}")
        self.metadata = pd.read_csv(metadata_path)
        logger.info(f"   ✓ 載入 {len(self.metadata)} 筆記錄")

        # 載入 Embedding 向量
        embeddings_path = self.data_dir / embeddings_file
        logger.info(f"   載入 Embedding 向量: {embeddings_path.name}")
        self.embeddings = np.load(embeddings_path)
        logger.info(f"   ✓ 向量矩陣: {self.embeddings.shape}")

        # 預計算範數（加速相似度計算）
        logger.info("   預計算向量範數...")
        self.norms = precompute_norms(self.embeddings)
        logger.info("   ✓ 範數計算完成")

        # 初始化 Embedding 引擎
        if embedding_engine is None:
            logger.info("   初始化 Embedding 引擎...")
            self.engine = EmbeddingEngine(
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                device="auto"
            )
        else:
            self.engine = embedding_engine

        logger.info("✅ Tier 3 EEIO 檢索器初始化完成")

    def search(
        self,
        query: str,
        country_priority: str = "TW",
        top_k: int = 5,
        threshold: float = 0.60,
        country_boost: float = 0.1
    ) -> List[Dict]:
        """
        檢索最相關的排放係數

        Args:
            query: 使用者查詢（如「購買電腦設備」）
            country_priority: 優先國家（預設 TW）
            top_k: 返回前 k 個結果
            threshold: 相似度門檻
            country_boost: 優先國家加權值

        Returns:
            符合條件的排放係數清單
        """
        # 1. 查詢向量化
        query_vector = self.engine.encode_single(query)

        # 2. 計算相似度
        similarities = fast_cosine_similarity_with_norms(
            query_vector,
            self.embeddings,
            self.norms
        )

        # 3. 篩選門檻
        mask = similarities >= threshold
        filtered_indices = np.where(mask)[0]

        if len(filtered_indices) == 0:
            logger.warning(f"   ⚠️  無符合門檻的結果（threshold={threshold}）")
            return []

        filtered_sims = similarities[filtered_indices]

        # 4. 國家優先排序
        # 優先國家加權
        country_boosts = np.array([
            country_boost if self.metadata.iloc[i]['country'] == country_priority else 0.0
            for i in filtered_indices
        ])
        boosted_sims = filtered_sims + country_boosts

        # 5. Top-K
        top_indices_in_filtered = np.argsort(boosted_sims)[::-1][:top_k]
        top_indices = filtered_indices[top_indices_in_filtered]

        # 6. 組裝結果
        results = []
        for idx in top_indices:
            row = self.metadata.iloc[idx]
            results.append({
                'index': int(idx),
                'source': row['source'],
                'country': row['country'],
                'country_name': row['country_name'],
                'product_name': row['product_name'],
                'product_code': row['product_code'],
                'emission_factor': float(row['emission_factor_per_meur']),
                'unit': row['unit'],
                'base_year': int(row['base_year']),
                'tier': int(row['tier']),
                'similarity': float(similarities[idx]),
                'is_priority_country': row['country'] == country_priority
            })

        return results

    def search_by_product_code(
        self,
        product_code: str,
        country_priority: str = "TW",
        top_k: int = 5,
        score: float = 0.82,
    ) -> List[Dict]:
        """Return EEIO candidates by exact product code, preferring Taiwan."""
        if not product_code:
            return []

        matches = self.metadata[self.metadata["product_code"] == product_code].copy()
        if matches.empty:
            return []

        matches["priority_rank"] = (matches["country"] == country_priority).astype(int)
        matches = matches.sort_values(
            ["priority_rank", "country"],
            ascending=[False, True],
        ).head(top_k)

        results = []
        for idx, row in matches.iterrows():
            results.append({
                "index": int(idx),
                "source": row["source"],
                "country": row["country"],
                "country_name": row["country_name"],
                "product_name": row["product_name"],
                "product_code": row["product_code"],
                "emission_factor": float(row["emission_factor_per_meur"]),
                "unit": row["unit"],
                "base_year": int(row["base_year"]),
                "tier": int(row["tier"]),
                "similarity": float(score if row["country"] == country_priority else max(score - 0.08, 0.0)),
                "is_priority_country": row["country"] == country_priority,
                "industry_routed": True,
            })
        return results

    def calculate_emissions(
        self,
        amount: float,
        currency: str,
        emission_factor_per_meur: float,
        exchange_rates: Optional[Dict[str, float]] = None
    ) -> float:
        """
        計算排放量

        Args:
            amount: 金額
            currency: 貨幣（TWD, USD, EUR, GBP）
            emission_factor_per_meur: 排放係數 (kg CO2e / M.EUR)
            exchange_rates: 匯率字典（可選，若無則使用 2022 年參考值）

        Returns:
            排放量 (kg CO2e)
        """
        # 預設匯率（2022 年參考值）
        if exchange_rates is None:
            exchange_rates = {
                'TWD_to_EUR': 32.5,
                'USD_to_EUR': 1.10,
                'GBP_to_EUR': 0.85,
                'EUR_to_EUR': 1.0
            }

        # 轉換為歐元
        currency = currency.upper()
        if currency == 'EUR':
            amount_eur = amount
        elif currency == 'TWD':
            amount_eur = amount / exchange_rates['TWD_to_EUR']
        elif currency == 'USD':
            amount_eur = amount / exchange_rates['USD_to_EUR']
        elif currency == 'GBP':
            amount_eur = amount / exchange_rates['GBP_to_EUR']
        else:
            raise ValueError(f"不支援的貨幣: {currency}")

        # 轉換為百萬歐元
        amount_meur = amount_eur / 1_000_000

        # 計算排放量
        emissions = amount_meur * emission_factor_per_meur

        return emissions

    def search_with_emissions(
        self,
        query: str,
        amount: float,
        currency: str = "TWD",
        country_priority: str = "TW",
        top_k: int = 5,
        threshold: float = 0.60
    ) -> Dict:
        """
        檢索並計算排放量（整合功能）

        Args:
            query: 使用者查詢
            amount: 金額
            currency: 貨幣
            country_priority: 優先國家
            top_k: 返回結果數
            threshold: 相似度門檻

        Returns:
            包含檢索結果與排放量的字典
        """
        # 檢索
        results = self.search(
            query=query,
            country_priority=country_priority,
            top_k=top_k,
            threshold=threshold
        )

        if not results:
            return {
                'success': False,
                'message': f'無符合門檻 ({threshold}) 的結果',
                'matches': [],
                'emissions': None
            }

        # 計算排放量（使用最佳匹配）
        best_match = results[0]
        emissions = self.calculate_emissions(
            amount=amount,
            currency=currency,
            emission_factor_per_meur=best_match['emission_factor']
        )

        # 組裝結果
        return {
            'success': True,
            'tier': 3,
            'matches': results,
            'best_match': best_match,
            'query_amount': amount,
            'query_currency': currency,
            'emissions': emissions,
            'emissions_unit': 'kg CO2e',
            'warning': (
                "⚠️ 此結果基於產業平均排放強度（EEIO 模型）\n"
                "- 實際排放可能因產品特性、製造過程、供應鏈而顯著不同\n"
                "- 建議僅用於初步估算或缺乏其他數據時\n"
                "- 重大排放源應要求供應商提供實際排放數據\n"
                "- 不確定性範圍: ±50% ~ ±300%"
            )
        }

    def get_stats(self) -> Dict:
        """
        取得資料庫統計資訊

        Returns:
            統計資訊字典
        """
        return {
            'total_records': len(self.metadata),
            'countries': self.metadata['country'].unique().tolist(),
            'country_counts': self.metadata['country'].value_counts().to_dict(),
            'embedding_dimension': self.embeddings.shape[1],
            'data_source': 'EXIOBASE',
            'base_year': 2022,
            'tier': 3
        }


# 測試代碼
if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Tier 3 EEIO 檢索器測試")
    print("=" * 70)

    # 初始化
    retriever = Tier3EEIORetriever()

    # 顯示統計
    stats = retriever.get_stats()
    print(f"\n📊 資料庫統計:")
    print(f"   總記錄數: {stats['total_records']}")
    print(f"   國家數: {len(stats['countries'])}")
    print(f"   國家: {', '.join(stats['countries'])}")
    print(f"   Embedding 維度: {stats['embedding_dimension']}")

    # 測試查詢
    test_queries = [
        ("購買電腦設備", 300000, "TWD"),
        ("餐廳用餐", 50000, "TWD"),
        ("電力費用", 100000, "TWD"),
        ("鋼鐵材料", 200000, "TWD")
    ]

    for query, amount, currency in test_queries:
        print(f"\n" + "=" * 70)
        print(f"🔍 查詢: {query} ({currency} {amount:,})")
        print("=" * 70)

        result = retriever.search_with_emissions(
            query=query,
            amount=amount,
            currency=currency,
            country_priority="TW",
            top_k=3,
            threshold=0.60
        )

        if result['success']:
            best = result['best_match']
            print(f"\n✅ 找到匹配")
            print(f"   最佳匹配: {best['country_name']} - {best['product_name']}")
            print(f"   排放係數: {best['emission_factor']:,.0f} kg CO2e/M.EUR")
            print(f"   相似度: {best['similarity']:.4f}")
            print(f"   計算排放量: {result['emissions']:,.2f} kg CO2e")

            print(f"\n   其他候選:")
            for i, match in enumerate(result['matches'][1:], 2):
                print(f"      {i}. {match['country_name']} - {match['product_name']} (相似度: {match['similarity']:.4f})")
        else:
            print(f"\n❌ {result['message']}")
