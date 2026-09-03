#!/usr/bin/env python3
"""
三層級聯檢索器
整合 Tier 1, 2, 3 的瀑布式檢索系統
"""

from typing import List, Dict, Optional
from pathlib import Path
import logging

from .tier1_local import Tier1LocalRetriever
from .tier2_international import Tier2InternationalRetriever
from .tier3_eeio import Tier3EEIORetriever
from utils.embedding import EmbeddingEngine
from industry_router import IndustryRoute, detect_industry_routes, route_to_dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CascadeRetriever:
    """
    三層級聯檢索器

    按照優先順序依次檢索：
    1. Tier 1 (台灣本地) - threshold 0.70
    2. Tier 2 (國際產業) - threshold 0.70
    3. Tier 3 (EEIO 模型) - threshold 0.60

    提供統一的檢索介面和結果格式
    """

    def __init__(
        self,
        tier1_enabled: bool = True,
        tier2_enabled: bool = True,
        tier3_enabled: bool = True,
        shared_embedding_engine: bool = True
    ):
        """
        初始化三層級聯檢索器

        Args:
            tier1_enabled: 是否啟用 Tier 1
            tier2_enabled: 是否啟用 Tier 2
            tier3_enabled: 是否啟用 Tier 3
            shared_embedding_engine: 是否共用 Embedding 引擎（節省記憶體）
        """
        logger.info("=" * 70)
        logger.info("🚀 初始化三層級聯檢索器")
        logger.info("=" * 70)

        # 共用 Embedding 引擎（節省記憶體）
        if shared_embedding_engine:
            logger.info("\n🔧 初始化共用 Embedding 引擎...")
            self.embedding_engine = EmbeddingEngine(
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                device="auto"
            )
        else:
            self.embedding_engine = None

        # 初始化各層檢索器
        self.tier1 = None
        self.tier2 = None
        self.tier3 = None

        if tier1_enabled:
            try:
                logger.info("\n📍 初始化 Tier 1 本地檢索器...")
                self.tier1 = Tier1LocalRetriever(embedding_engine=self.embedding_engine)
            except Exception as e:
                logger.warning(f"   ⚠️  Tier 1 初始化失敗: {e}")

        if tier2_enabled:
            try:
                logger.info("\n🌍 初始化 Tier 2 國際檢索器...")
                self.tier2 = Tier2InternationalRetriever(embedding_engine=self.embedding_engine)
            except Exception as e:
                logger.warning(f"   ⚠️  Tier 2 初始化失敗: {e}")

        if tier3_enabled:
            try:
                logger.info("\n🏭 初始化 Tier 3 EEIO 檢索器...")
                self.tier3 = Tier3EEIORetriever(embedding_engine=self.embedding_engine)
            except Exception as e:
                logger.warning(f"   ⚠️  Tier 3 初始化失敗: {e}")

        logger.info("\n" + "=" * 70)
        logger.info("✅ 三層級聯檢索器初始化完成")
        logger.info("=" * 70)

    def search(
        self,
        query: str,
        top_k: int = 5,
        tier1_threshold: float = 0.70,
        tier2_threshold: float = 0.70,
        tier3_threshold: float = 0.60,
        country_priority: str = "TW"
    ) -> Dict:
        """
        瀑布式檢索排放係數

        優先使用高品質的本地資料，逐層降級
        Args:
            query: 使用者查詢
            top_k: 返回結果數
            tier1_threshold: Tier 1 相似度門檻
            tier2_threshold: Tier 2 相似度門檻
            tier3_threshold: Tier 3 相似度門檻
            country_priority: Tier 3 的優先國家

        Returns:
            檢索結果字典
        """
        logger.info(f"\n🔍 查詢: {query}")
        industry_routes = detect_industry_routes(query)
        early_route_codes = {"H-49", "F-41", "M-70/74", "J-63"}
        early_industry_routes = [
            route for route in industry_routes if route.code in early_route_codes
        ]
        deferred_industry_routes = [
            route for route in industry_routes if route.code not in early_route_codes
        ]

        early_routed_response = self._industry_routed_response(
            routes=early_industry_routes,
            query=query,
            country_priority=country_priority,
            top_k=top_k,
        )
        if early_routed_response:
            return early_routed_response

        # Tier 1: 台灣本地
        if self.tier1 is not None:
            logger.info("   → 嘗試 Tier 1 (台灣本地) ...")
            results_t1 = self.tier1.search(
                query=query,
                top_k=top_k,
                threshold=tier1_threshold
            )
            if results_t1:
                logger.info(f"   ✅ Tier 1 找到 {len(results_t1)} 個匹配")
                return self._format_response(
                    tier=1,
                    query=query,
                    matches=results_t1,
                    message="使用台灣本地排放係數（最高品質）"
                )
            logger.info("   → Tier 1 無符合結果，繼續...")

        # Industry-routed Taiwan fallback before international databases.
        deferred_routed_response = self._industry_routed_response(
            routes=deferred_industry_routes,
            query=query,
            country_priority=country_priority,
            top_k=top_k,
        )
        if deferred_routed_response:
            return deferred_routed_response

        # Tier 2: 國際產業
        if self.tier2 is not None:
            logger.info("   → 嘗試 Tier 2 (國際產業) ...")
            results_t2 = self.tier2.search(
                query=query,
                top_k=top_k,
                threshold=tier2_threshold
            )
            if results_t2:
                logger.info(f"   ✅ Tier 2 找到 {len(results_t2)} 個匹配")
                return self._format_response(
                    tier=2,
                    query=query,
                    matches=results_t2,
                    message="使用國際產業排放係數（中等品質）",
                    warning="此為國際平均值，實際情況可能因地區而異"
                )
            logger.info("   → Tier 2 無符合結果，繼續...")

        # Tier 3: EEIO 模型
        if self.tier3 is not None:
            logger.info("   → 嘗試 Tier 3 (EEIO 模型) ...")
            results_t3 = self.tier3.search(
                query=query,
                top_k=top_k,
                threshold=tier3_threshold,
                country_priority=country_priority
            )
            if results_t3:
                logger.info(f"   ✅ Tier 3 找到 {len(results_t3)} 個匹配")
                return self._format_response(
                    tier=3,
                    query=query,
                    matches=results_t3,
                    message="使用 EEIO 模型排放強度（產業平均）",
                    warning=(
                        "⚠️ 此結果基於產業平均排放強度\n"
                        "- 實際排放可能因產品特性而顯著不同\n"
                        "- 不確定性範圍: ±50% ~ ±300%\n"
                        "- 建議僅用於初步估算"
                    )
                )
            logger.info("   → Tier 3 無符合結果")

        # 完全無結果
        logger.warning("   ❌ 三層檢索皆無符合結果")
        return {
            'success': False,
            'tier': None,
            'query': query,
            'matches': [],
            'best_match': None,
            'message': '無法找到相關排放係數，請調整查詢或降低門檻'
        }

    def _format_response(
        self,
        tier: int,
        query: str,
        matches: List[Dict],
        message: str,
        warning: Optional[str] = None
    ) -> Dict:
        """
        格式化檢索結果

        Args:
            tier: 使用的層級
            query: 原始查詢
            matches: 匹配結果清單
            message: 狀態訊息
            warning: 警告訊息（可選）

        Returns:
            統一格式的結果字典
        """
        return {
            'success': True,
            'tier': tier,
            'tier_name': self._get_tier_name(tier),
            'query': query,
            'matches': matches,
            'best_match': matches[0] if matches else None,
            'message': message,
            'warning': warning
        }

    def _industry_routed_response(
        self,
        routes: List[IndustryRoute],
        query: str,
        country_priority: str,
        top_k: int,
    ) -> Optional[Dict]:
        if not routes or self.tier3 is None:
            return None

        routed_results = []
        for route in routes:
            logger.info(f"   → 嘗試台灣產業路由 ({route.code} {route.label}) ...")
            route_matches = self.tier3.search_by_product_code(
                product_code=route.tier3_product_code,
                country_priority=country_priority,
                top_k=max(1, top_k),
                score=route.confidence,
            )
            route_info = route_to_dict(route) or {}
            for item in route_matches:
                item.update(route_info)
            routed_results.extend(route_matches)

        routed_results = sorted(
            routed_results,
            key=lambda item: (
                item.get("is_priority_country", False),
                float(item.get("similarity") or 0.0),
            ),
            reverse=True,
        )[:top_k]
        if not routed_results:
            return None

        labels = "、".join(f"{route.code} {route.label}" for route in routes)
        reasons = "；".join(route.reason for route in routes)
        logger.info(f"   ✅ 台灣產業路由找到 {len(routed_results)} 個匹配")
        return self._format_response(
            tier=3,
            query=query,
            matches=routed_results,
            message=f"使用台灣產業係數（{labels}）",
            warning=(
                f"此為台灣產業平均係數，依關鍵字路由：{reasons} "
                "若有產品專屬本土係數，仍應優先採用產品專屬係數。"
            ),
        )

    def _get_tier_name(self, tier: int) -> str:
        """取得層級名稱"""
        names = {
            1: "Tier 1 - 台灣本地",
            2: "Tier 2 - 國際產業",
            3: "Tier 3 - EEIO 模型"
        }
        return names.get(tier, "Unknown")

    def get_stats(self) -> Dict:
        """
        取得所有層級的統計資訊

        Returns:
            統計資訊字典
        """
        stats = {
            'tier1': self.tier1.get_stats() if self.tier1 else None,
            'tier2': self.tier2.get_stats() if self.tier2 else None,
            'tier3': self.tier3.get_stats() if self.tier3 else None
        }
        return stats


# 測試代碼
if __name__ == "__main__":
    print("=" * 70)
    print("🧪 三層級聯檢索器測試")
    print("=" * 70)

    # 初始化
    retriever = CascadeRetriever()

    # 顯示統計
    print("\n📊 資料庫統計:")
    stats = retriever.get_stats()
    for tier_name, tier_stats in stats.items():
        if tier_stats:
            print(f"\n   {tier_name.upper()}:")
            print(f"      記錄數: {tier_stats['total_records']}")

    # 測試查詢
    test_queries = [
        "購買塑膠袋",      # 應該命中 Tier 1
        "牛肉採購",        # 應該命中 Tier 2
        "購買軟體服務",    # 應該命中 Tier 3
        "購買電腦設備"     # 可能命中多層
    ]

    for query in test_queries:
        print(f"\n" + "=" * 70)
        print(f"🔍 測試查詢: {query}")
        print("=" * 70)

        result = retriever.search(query=query, top_k=3)

        if result['success']:
            print(f"\n✅ {result['message']}")
            print(f"   使用層級: {result['tier_name']}")
            print(f"   找到 {len(result['matches'])} 個匹配")

            if result['warning']:
                print(f"\n⚠️  注意事項:")
                print(f"   {result['warning']}")

            print(f"\n📋 最佳匹配:")
            best = result['best_match']
            if 'name' in best:
                print(f"   名稱: {best['name']}")
            elif 'product_name' in best:
                print(f"   產品: {best['product_name']}")
            print(f"   排放係數: {best['emission_factor']}")
            print(f"   相似度: {best['similarity']:.4f}")
        else:
            print(f"\n❌ {result['message']}")
