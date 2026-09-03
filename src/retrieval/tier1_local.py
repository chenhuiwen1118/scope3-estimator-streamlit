#!/usr/bin/env python3
"""
Tier 1 本地檢索器
基於台灣環保署本地排放係數的向量檢索系統
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

SOURCE_PRIORITY = {
    "taiwan epa": 3,
    "taiwan epa/moe": 2,
    "moenv cfp": 1,
    "cca ghg factor table": 3,
}

CONFLICT_TERMS = {
    "燃燒": ["未燃燒"],
    "固定燃燒": ["未燃燒", "移動燃燒"],
    "移動燃燒": ["未燃燒", "固定燃燒"],
    "牛": ["豬", "雞"],
    "牛肉": ["豬", "豬肉", "雞", "雞肉"],
    "豬": ["牛", "雞"],
    "豬肉": ["牛", "牛肉", "雞", "雞肉"],
}

QUERY_SYNONYMS = {
    "自攻螺絲": ["螺絲", "fastener"],
    "六角螺絲": ["螺絲", "fastener"],
    "內六角螺絲": ["螺絲", "fastener"],
    "石灰粉": ["石灰", "石灰石", "生石灰", "熟石灰", "氫氧化鈣", "lime", "quicklime", "calcium"],
    "石灰": ["石灰石", "生石灰", "熟石灰", "氫氧化鈣", "lime", "quicklime", "calcium"],
    "熟石灰": ["氫氧化鈣", "石灰", "lime", "calcium"],
    "生石灰": ["石灰", "quicklime", "lime"],
    "紙箱": ["瓦楞紙箱", "紙盒", "紙板", "紙包材", "包裝紙箱", "carton", "cardboard", "corrugated"],
    "瓦楞紙箱": ["紙箱", "紙盒", "紙板", "carton", "cardboard", "corrugated"],
    "紙盒": ["紙箱", "瓦楞紙箱", "紙板", "carton", "cardboard"],
    "鋁箔": ["鋁箔片", "鋁箔包材", "aluminium foil", "aluminum foil"],
    "鋁箔片": ["鋁箔", "aluminium foil", "aluminum foil"],
    "銅管": ["copper pipe", "copper tube"],
    "銅片": ["copper plate", "copper sheet"],
    "冷軋鋼板": ["冷軋鋼捲", "碳鋼冷軋鋼捲", "不鏽鋼冷軋鋼捲", "cold rolled steel"],
    "熱軋鋼板": ["熱軋鋼板片", "熱軋鋼捲", "hot rolled steel"],
    "鍍鋅鋼板": ["電鍍鋅鋼捲", "熱浸鍍鋅鋼捲", "galvanized steel"],
}

MINERAL_QUERY_TERMS = {
    "石灰",
    "石灰粉",
    "石灰石",
    "生石灰",
    "熟石灰",
    "氫氧化鈣",
    "碳酸鈣",
    "礦物",
    "水泥",
    "粉體",
}

FOOD_CANDIDATE_TERMS = {
    "食品",
    "飲料",
    "布丁",
    "焦糖",
    "蛋糕",
    "牛奶",
    "豆漿",
    "紅茶",
    "奶茶",
    "咖啡",
    "茶飲",
    "果汁",
    "甜點",
    "pudding",
    "cake",
    "food",
    "beverage",
    "dairy",
}

PAPER_PACKAGING_QUERY_TERMS = {
    "紙箱",
    "瓦楞紙箱",
    "紙盒",
    "紙板",
    "紙包材",
    "包裝紙箱",
    "carton",
    "cardboard",
    "corrugated",
}

ELECTRONICS_CANDIDATE_TERMS = {
    "筆記型電腦",
    "筆電",
    "電腦",
    "電子",
    "notebook",
    "laptop",
    "computer",
    "electronics",
}

MATERIAL_ONLY_QUERY_TERMS = {
    "鋁箔",
    "鋁箔片",
    "銅管",
    "銅片",
    "銅材",
    "鋼板",
    "鋁板",
    "塑膠粒",
    "石灰粉",
}

INCIDENTAL_PACKAGING_TERMS = {
    "包裝",
    "鋁箔包",
    "紙盒裝",
    "瓶裝",
    "罐裝",
    "packaged",
    "packed",
}

GENERIC_QUERY_TERMS = {
    "採購",
    "購買",
    "排放係數",
    "係數",
    "碳排",
    "碳足跡",
}

BROAD_LEXICAL_TERMS = {
    "steel",
    "stainless",
    "stainless steel",
    "aluminium",
    "aluminum",
    "copper",
    "metal",
    "金屬",
    "金屬原料",
    "原料",
    "零組件",
    "耗材",
    "範疇3",
    "類別1",
}


class Tier1LocalRetriever:
    """
    Tier 1 本地檢索器

    基於台灣環保署本地排放係數，使用向量相似度進行檢索
    提供最高準確度的本地排放係數
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        embeddings_file: str = "tier1_embeddings.npy",
        metadata_file: str = "tier1_metadata.csv",
        embedding_engine: Optional[EmbeddingEngine] = None
    ):
        """
        初始化 Tier 1 本地檢索器

        Args:
            data_dir: 資料目錄路徑
            embeddings_file: Embedding 向量檔案名稱
            metadata_file: 元資料檔案名稱
            embedding_engine: Embedding 引擎（可選，若無則自動創建）
        """
        # 設定路徑
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "emission_factors" / "tier1_local"
        self.data_dir = Path(data_dir)

        logger.info("🔧 初始化 Tier 1 本地檢索器")

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

        logger.info("✅ Tier 1 本地檢索器初始化完成")

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.80
    ) -> List[Dict]:
        """
        檢索最相關的排放係數

        Args:
            query: 使用者查詢（如「購買塑膠袋」）
            top_k: 返回前 k 個結果
            threshold: 相似度門檻（Tier 1 使用較高門檻）

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

        # 3. 預篩候選
        # Semantic scores can underrank short Chinese material names such as
        # "石灰粉". Keep a wider candidate pool first, then apply lexical/domain
        # corrections and enforce the user-facing threshold afterward.
        prefilter_threshold = max(0.45, float(threshold) - 0.30)
        mask = similarities >= prefilter_threshold
        filtered_indices = np.where(mask)[0]

        # 4. 組裝候選，並針對同名同單位做版本整理。
        semantic_candidates = [
            self._row_to_result(int(idx), float(similarities[idx]))
            for idx in filtered_indices
        ]
        lexical_candidates = self._lexical_candidates(query, similarities)
        candidates = self._merge_candidates(semantic_candidates, lexical_candidates)
        if not candidates:
            logger.warning(f"   ⚠️  無符合預篩門檻或本土詞彙命中的結果（threshold={prefilter_threshold}）")
            return []

        results = self._dedupe_versions(candidates)
        results = self._rerank_with_query_terms(results, query)
        results = [
            item for item in results
            if float(item.get("ranking_similarity", item.get("similarity", 0.0)) or 0.0) >= threshold
        ]

        if not results:
            logger.warning(f"   ⚠️  無符合詞彙修正後門檻的結果（threshold={threshold}）")
            return []

        # 5. Top-K
        results = sorted(
            results,
            key=lambda item: item.get("ranking_similarity", item.get("similarity", 0.0)),
            reverse=True,
        )[:top_k]

        return results

    def _row_to_result(self, idx: int, similarity: float) -> Dict:
        row = self.metadata.iloc[idx]
        return {
            'index': int(idx),
            'name': row['name'],
            'emission_factor': float(row['emission_factor']),
            'unit_standard': row['unit_standard'],
            'unit_original': row['unit_original'],
            'source': row['source'],
            'region': row['region'],
            'category': row.get('category'),
            'base_year': int(row['base_year']),
            'source_dept': row.get('source_dept'),
            'tier': int(row['tier']),
            'similarity': float(similarity),
            'search_text': row.get('search_text'),
        }

    def _query_terms(self, query: str) -> List[str]:
        normalized = re.sub(r"[，,、／/()（）:：;；\[\]{}|]+", " ", str(query).lower())
        terms = []
        seen = set()
        for term in normalized.split():
            clean = term.strip()
            for generic in GENERIC_QUERY_TERMS:
                clean = clean.replace(generic, "")
            if len(clean) < 2 or clean in seen:
                continue
            seen.add(clean)
            terms.append(clean)
            for synonym in QUERY_SYNONYMS.get(clean, []):
                if synonym not in seen:
                    seen.add(synonym)
                    terms.append(synonym)
        return terms

    def _candidate_text(self, item: Dict) -> str:
        fields = [
            item.get("name"),
            item.get("category"),
            item.get("source"),
            item.get("source_dept"),
            item.get("unit_standard"),
            item.get("unit_original"),
            item.get("search_text"),
        ]
        return " ".join("" if value is None else str(value) for value in fields).lower()

    def _metadata_text(self, row) -> str:
        fields = [
            row.get("name"),
            row.get("category"),
            row.get("source"),
            row.get("source_dept"),
            row.get("unit_standard"),
            row.get("unit_original"),
            row.get("search_text"),
        ]
        return " ".join("" if value is None else str(value) for value in fields).lower()

    def _is_material_query(self, query_lower: str, terms: List[str]) -> bool:
        return any(term in query_lower or term in terms for term in MATERIAL_ONLY_QUERY_TERMS)

    def _is_incidental_packaging_candidate(self, name: str, text: str, terms: List[str]) -> bool:
        if not any(term in text for term in INCIDENTAL_PACKAGING_TERMS):
            return False
        if any(name == term or name.startswith(term) for term in terms):
            return False
        if "包材" in name and any(term in name for term in terms):
            return False
        return True

    def _lexical_candidates(self, query: str, similarities: np.ndarray) -> List[Dict]:
        terms = self._query_terms(query)
        if not terms:
            return []

        rows = []
        for idx, row in self.metadata.iterrows():
            name = str(row.get("name") or "").lower()
            text = self._metadata_text(row)
            matched_terms = [term for term in terms if term in text]
            strong_matched_terms = [
                term for term in matched_terms
                if term not in BROAD_LEXICAL_TERMS
            ]
            if not strong_matched_terms:
                continue

            exact_name_hit = any(term == name for term in strong_matched_terms)
            material_query = self._is_material_query(str(query).lower(), terms)
            incidental_packaging = material_query and self._is_incidental_packaging_candidate(name, text, terms)
            name_contains_hit = any(term in name for term in strong_matched_terms) and not incidental_packaging
            search_text_hit = bool(strong_matched_terms)

            if exact_name_hit:
                score = 0.98
            elif name_contains_hit:
                score = 0.90
            elif incidental_packaging:
                score = 0.48
            elif search_text_hit and len(strong_matched_terms) >= 2:
                score = 0.84
            else:
                score = 0.74

            item = self._row_to_result(int(idx), max(float(similarities[int(idx)]), score))
            item["lexical_local_match"] = True
            item["local_match_terms"] = ", ".join(strong_matched_terms[:8])
            rows.append(item)

        rows = sorted(
            rows,
            key=lambda item: (
                float(item.get("similarity") or 0.0),
                int(item.get("base_year") or 0),
                SOURCE_PRIORITY.get(str(item.get("source") or "").lower(), 0),
            ),
            reverse=True,
        )
        return rows[:50]

    def _merge_candidates(self, *candidate_groups: List[Dict]) -> List[Dict]:
        merged = {}
        for group in candidate_groups:
            for item in group:
                idx = item.get("index")
                if idx is None:
                    continue
                existing = merged.get(idx)
                if existing is None or float(item.get("similarity") or 0.0) > float(existing.get("similarity") or 0.0):
                    merged[idx] = item
        return list(merged.values())

    def _rerank_with_query_terms(self, results: List[Dict], query: str) -> List[Dict]:
        terms = self._query_terms(query)
        query_lower = str(query).lower()
        if not terms:
            return results

        reranked = []
        for item in results:
            text = self._candidate_text(item)
            matched_terms = [term for term in terms if term in text]
            strong_matched_terms = [
                term for term in matched_terms
                if term not in BROAD_LEXICAL_TERMS
            ]
            boost = min(0.12, len(strong_matched_terms) * 0.025)

            penalty_terms = []
            for query_term, conflicts in CONFLICT_TERMS.items():
                if query_term in query_lower:
                    penalty_terms.extend(term for term in conflicts if term in text)
            penalty = min(0.12, len(set(penalty_terms)) * 0.06)

            has_specific_query = any(
                term not in GENERIC_QUERY_TERMS and term not in BROAD_LEXICAL_TERMS and len(term) >= 2
                for term in terms
            )
            lexical_miss_penalty = 0.0
            if has_specific_query and not strong_matched_terms:
                lexical_miss_penalty = 0.30

            mineral_query = any(term in query_lower or term in terms for term in MINERAL_QUERY_TERMS)
            food_candidate = any(term in text for term in FOOD_CANDIDATE_TERMS)
            domain_conflict_penalty = 0.0
            if mineral_query and food_candidate:
                domain_conflict_penalty = 0.45
            material_query = self._is_material_query(query_lower, terms)
            candidate_name = str(item.get("name", "")).lower()
            incidental_packaging = material_query and self._is_incidental_packaging_candidate(candidate_name, text, terms)
            if incidental_packaging:
                domain_conflict_penalty = max(domain_conflict_penalty, 0.45)
            paper_packaging_query = any(term in query_lower or term in terms for term in PAPER_PACKAGING_QUERY_TERMS)
            electronics_candidate = any(term in text for term in ELECTRONICS_CANDIDATE_TERMS)
            if paper_packaging_query and electronics_candidate:
                domain_conflict_penalty = max(domain_conflict_penalty, 0.45)

            exact_name_boost = 0.0
            for term in terms:
                if term in BROAD_LEXICAL_TERMS:
                    continue
                name_segments = [
                    segment.strip()
                    for segment in re.split(r"[/／()（）,，、 ]+", candidate_name)
                    if segment.strip()
                ]
                if term in name_segments or candidate_name.startswith(f"{term} /") or candidate_name.startswith(f"{term}／"):
                    exact_name_boost = max(exact_name_boost, 0.08)

            exact_code_boost = 0.0
            for term in terms:
                if re.search(r"[a-z]+[-]?\d", term, flags=re.IGNORECASE) and term in text:
                    exact_code_boost = max(exact_code_boost, 0.12)

            base_similarity = float(item.get("similarity") or 0.0)
            total_penalty = penalty + lexical_miss_penalty + domain_conflict_penalty
            ranking_similarity = max(0.0, min(1.0, base_similarity + boost + exact_name_boost + exact_code_boost - total_penalty))
            reranked.append({
                **item,
                "original_similarity": item.get("original_similarity", base_similarity),
                "similarity": ranking_similarity,
                "ranking_similarity": ranking_similarity,
                "lexical_boost": boost + exact_name_boost + exact_code_boost,
                "lexical_penalty": total_penalty,
                "matched_query_terms": ", ".join(strong_matched_terms[:8]),
            })
        return reranked

    def _version_group_key(self, item: Dict) -> tuple:
        return (
            str(item.get("name", "")).strip().lower(),
            str(item.get("unit_standard", "")).strip().lower(),
        )

    def _version_priority(self, item: Dict) -> tuple:
        source = str(item.get("source", "")).strip().lower()
        return (
            int(item.get("base_year") or 0),
            SOURCE_PRIORITY.get(source, 0),
            float(item.get("similarity") or 0.0),
        )

    def _dedupe_versions(self, candidates: List[Dict]) -> List[Dict]:
        grouped = {}
        for item in candidates:
            grouped.setdefault(self._version_group_key(item), []).append(item)

        results = []
        for versions in grouped.values():
            sorted_versions = sorted(
                versions,
                key=self._version_priority,
                reverse=True,
            )
            best = dict(sorted_versions[0])
            alternates = sorted_versions[1:]
            if alternates:
                best["alternate_versions"] = alternates
                best["alternate_version_count"] = len(alternates)
                best["version_selection_note"] = (
                    "同名同單位資料依年度、來源優先序選出主版本；其他版本保留供覆核。"
                )
            else:
                best["alternate_versions"] = []
                best["alternate_version_count"] = 0
            results.append(best)

        return results

    def get_stats(self) -> Dict:
        """
        取得資料庫統計資訊

        Returns:
            統計資訊字典
        """
        return {
            'total_records': len(self.metadata),
            'years': sorted(self.metadata['base_year'].unique().tolist()),
            'year_counts': self.metadata['base_year'].value_counts().to_dict(),
            'units': self.metadata['unit_standard'].unique().tolist(),
            'embedding_dimension': self.embeddings.shape[1],
            'data_source': 'Taiwan EPA',
            'tier': 1
        }


# 測試代碼
if __name__ == "__main__":
    print("=" * 70)
    print("🧪 Tier 1 本地檢索器測試")
    print("=" * 70)

    # 初始化
    retriever = Tier1LocalRetriever()

    # 顯示統計
    stats = retriever.get_stats()
    print(f"\n📊 資料庫統計:")
    print(f"   總記錄數: {stats['total_records']}")
    print(f"   年度範圍: {min(stats['years'])} - {max(stats['years'])}")
    print(f"   Embedding 維度: {stats['embedding_dimension']}")

    # 測試查詢
    test_queries = [
        "購買塑膠袋",
        "紙箱包裝",
        "電力使用",
        "汽油運輸"
    ]

    for query in test_queries:
        print(f"\n" + "=" * 70)
        print(f"🔍 查詢: {query}")
        print("=" * 70)

        results = retriever.search(
            query=query,
            top_k=3,
            threshold=0.80
        )

        if results:
            print(f"\n✅ 找到 {len(results)} 個匹配")
            for i, match in enumerate(results, 1):
                print(f"\n   {i}. {match['name']}")
                print(f"      排放係數: {match['emission_factor']} kg CO2e/{match['unit_standard']}")
                print(f"      年度: {match['base_year']}")
                print(f"      相似度: {match['similarity']:.4f}")
        else:
            print(f"\n❌ 無符合門檻的結果")
