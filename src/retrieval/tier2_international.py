#!/usr/bin/env python3
"""
Tier 2 國際檢索器
基於國際資料庫（AGRIBALYSE, Idemat, etc）的向量檢索系統
"""

from typing import List, Dict, Optional
from pathlib import Path
import pandas as pd
import numpy as np
import logging
import re

from utils.embedding import EmbeddingEngine
from utils.similarity import fast_cosine_similarity_with_norms, precompute_norms

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Short Chinese procurement names are not always aligned with the English-only
# Tier 2 embeddings. These mappings select an existing official industry row;
# they do not create a new emission factor.
CONTROLLED_CATEGORY_MAPPINGS = (
    {
        "query_terms": {"鉛筆", "原子筆", "鋼筆", "彩色筆", "螢光筆", "自動鉛筆", "文具", "書寫用品"},
        "preferred_names": ("Office Supplies (except Paper) Manufacturing",),
        "score": 0.92,
        "reason": "採購品名屬非紙類文具，映射至辦公用品製造業係數。",
    },
)


class Tier2InternationalRetriever:
    """
    Tier 2 國際檢索器

    基於國際產業資料庫，使用向量相似度進行檢索
    提供產業特定的排放係數
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        embeddings_file: str = "tier2_embeddings.npy",
        metadata_file: str = "tier2_metadata.csv",
        embedding_engine: Optional[EmbeddingEngine] = None
    ):
        """
        初始化 Tier 2 國際檢索器

        Args:
            data_dir: 資料目錄路徑
            embeddings_file: Embedding 向量檔案名稱
            metadata_file: 元資料檔案名稱
            embedding_engine: Embedding 引擎（可選，若無則自動創建）
        """
        # 設定路徑
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "emission_factors" / "tier2_international"
        self.data_dir = Path(data_dir)

        logger.info("🔧 初始化 Tier 2 國際檢索器")

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

        # 檢測 schema 版本（支援新舊兩種格式）
        self.name_col = 'category_name_en' if 'category_name_en' in self.metadata.columns else 'name'
        self.source_col = 'source_database' if 'source_database' in self.metadata.columns else 'source'
        self.category_col = 'activity_type_en' if 'activity_type_en' in self.metadata.columns else 'category'

        logger.info(f"   Schema: name={self.name_col}, source={self.source_col}")
        logger.info("✅ Tier 2 國際檢索器初始化完成")

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.70
    ) -> List[Dict]:
        """
        檢索最相關的排放係數

        Args:
            query: 使用者查詢（如「購買電腦設備」）
            top_k: 返回前 k 個結果
            threshold: 相似度門檻

        Returns:
            符合條件的排放係數清單
        """
        controlled_results = self._controlled_category_matches(query, top_k)

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

        if len(filtered_indices) == 0 and not controlled_results:
            logger.warning(f"   ⚠️  無符合門檻的結果（threshold={threshold}）")
            return []

        filtered_sims = similarities[filtered_indices]

        # 4. Top-K
        top_indices_in_filtered = np.argsort(filtered_sims)[::-1][:top_k]
        top_indices = filtered_indices[top_indices_in_filtered]

        # 5. 組裝結果
        results = list(controlled_results)
        for idx in top_indices:
            row = self.metadata.iloc[idx]

            # 動態取得欄位值（支援新舊 schema）
            result = {
                'index': int(idx),
                'name': row[self.name_col],
                'emission_factor': float(row['emission_factor']),
                'unit': row.get('unit', 'unknown'),
                'source': row[self.source_col],
                'category': row.get(self.category_col, 'General'),
                'region': row.get('region', row.get('geographic_scope', 'Global')),
                'base_year': int(row['base_year']) if 'base_year' in row and pd.notna(row.get('base_year')) else int(row.get('year', 0)) if pd.notna(row.get('year')) else None,
                'tier': int(row['tier']) if 'tier' in row and pd.notna(row['tier']) else int(row.get('tier_level', 2)) if pd.notna(row.get('tier_level')) else 2,
                'similarity': float(similarities[idx])
            }

            # 如果有 Scope 3 分類，加入結果
            if 'scope3_category' in row and pd.notna(row['scope3_category']):
                result['scope3_category'] = str(row['scope3_category'])

            if not any(item.get("index") == result["index"] for item in results):
                results.append(result)

        return sorted(results, key=lambda item: item.get("similarity", 0.0), reverse=True)[:top_k]

    def _controlled_category_matches(self, query: str, top_k: int) -> List[Dict]:
        """Return exact industry rows for controlled Chinese procurement terms."""
        normalized = re.sub(r"\s+", "", str(query or "").lower())
        selected = []
        for mapping in CONTROLLED_CATEGORY_MAPPINGS:
            if not any(term.lower() in normalized for term in mapping["query_terms"]):
                continue
            rows = self.metadata[self.metadata[self.name_col].isin(mapping["preferred_names"])]
            for idx, row in rows.head(top_k).iterrows():
                selected.append({
                    "index": int(idx),
                    "name": row[self.name_col],
                    "emission_factor": float(row["emission_factor"]),
                    "unit": row.get("unit", "unknown"),
                    "source": row[self.source_col],
                    "category": row.get(self.category_col, "General"),
                    "region": row.get("region", row.get("geographic_scope", "Global")),
                    "base_year": int(row["base_year"]) if pd.notna(row.get("base_year")) else None,
                    "tier": int(row["tier"]) if pd.notna(row.get("tier")) else 2,
                    "similarity": float(mapping["score"]),
                    "controlled_category_match": True,
                    "controlled_match_reason": mapping["reason"],
                    "scope3_category": str(row["scope3_category"]) if pd.notna(row.get("scope3_category")) else "",
                })
        return selected

    def get_stats(self) -> Dict:
        """
        取得資料庫統計資訊

        Returns:
            統計資訊字典
        """
        stats = {
            'total_records': len(self.metadata),
            'sources': self.metadata[self.source_col].unique().tolist(),
            'source_counts': self.metadata[self.source_col].value_counts().to_dict(),
            'categories': self.metadata[self.category_col].value_counts().head(10).to_dict(),
            'embedding_dimension': self.embeddings.shape[1],
            'tier': 2
        }

        # 如果有 Scope 3 分類，加入統計
        if 'scope3_category' in self.metadata.columns:
            stats['scope3_categories'] = self.metadata['scope3_category'].value_counts().to_dict()

        return stats


# 測試代碼
if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Tier 2 國際檢索器測試")
    print("=" * 70)

    # 初始化
    retriever = Tier2InternationalRetriever()

    # 顯示統計
    stats = retriever.get_stats()
    print(f"\n📊 資料庫統計:")
    print(f"   總記錄數: {stats['total_records']}")
    print(f"   資料來源: {', '.join(stats['sources'])}")
    print(f"   Embedding 維度: {stats['embedding_dimension']}")

    # 測試查詢
    test_queries = [
        "購買牛肉",
        "鋼材",
        "塑膠產品",
        "電子設備"
    ]

    for query in test_queries:
        print(f"\n" + "=" * 70)
        print(f"🔍 查詢: {query}")
        print("=" * 70)

        results = retriever.search(
            query=query,
            top_k=3,
            threshold=0.70
        )

        if results:
            print(f"\n✅ 找到 {len(results)} 個匹配")
            for i, match in enumerate(results, 1):
                print(f"\n   {i}. {match['name'][:60]}")
                print(f"      排放係數: {match['emission_factor']} kg CO2e/{match['unit']}")
                print(f"      來源: {match['source']}")
                print(f"      相似度: {match['similarity']:.4f}")
        else:
            print(f"\n❌ 無符合門檻的結果")
