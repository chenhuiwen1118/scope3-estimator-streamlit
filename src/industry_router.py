"""Rule-based industry routing for broad Scope 3 procurement descriptions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class IndustryRoute:
    code: str
    label: str
    tier3_product_code: str
    query_hint: str
    confidence: float
    reason: str


ROUTES = [
    {
        "code": "C-25",
        "label": "金屬製品製造業",
        "tier3_product_code": "C_FABM",
        "keywords_any": ["鋼模", "鋁模", "開模", "修模", "模具", "金型", "die casting mold", "tooling", "mold"],
        "query_hint": "Fabricated metal products, except machinery and equipment 金屬製品製造 模具 開模 修模",
        "reason": "描述含模具、開模或修模費，通常屬金屬製品或模具加工相關支出。",
    },
    {
        "code": "H-49",
        "label": "陸上運輸業",
        "tier3_product_code": "C_TLND",
        "keywords_any": ["宅配", "國內宅配", "陸運", "貨運", "配送", "regional distribution", "freight service", "land transport"],
        "query_hint": "Other land transportation services H-49 陸上運輸 貨運 宅配 配送 regional distribution freight service",
        "reason": "描述含 freight、regional distribution、宅配或國內配送，屬陸上運輸服務。",
    },
    {
        "code": "F-41",
        "label": "營建工程業",
        "tier3_product_code": "C_CONS",
        "keywords_any": ["擴建", "裝潢", "營建", "工程費", "辦公室裝潢", "無塵室", "construction", "renovation"],
        "query_hint": "Construction work F-41 營建工程 建築工程 擴建 裝潢 無塵室工程",
        "reason": "描述含擴建、裝潢或工程費，適合先以營建工程業係數估算。",
    },
    {
        "code": "C-261",
        "label": "半導體製造業",
        "tier3_product_code": "C_OFMA",
        "keywords_any": ["半導體", "mcu", "主晶片", "晶片", "客製化ic", "ic", "semiconductor", "chip"],
        "query_hint": "Computer, Electronic and optical products semiconductor components MCU IC chip 半導體 電子零組件",
        "reason": "描述含半導體、MCU、主晶片或 IC，屬電子零組件與半導體相關採購。",
    },
    {
        "code": "M-70/74",
        "label": "專業、科學及技術服務業",
        "tier3_product_code": "C_OBUS",
        "keywords_any": ["顧問", "諮詢", "consulting", "consultant", "專業服務"],
        "query_hint": "Other business services consulting professional services 顧問 專業服務",
        "reason": "描述含顧問或專業服務，適合以商業服務或專業服務係數估算。",
    },
    {
        "code": "J-63",
        "label": "資訊服務業",
        "tier3_product_code": "C_COMP",
        "keywords_any": ["雲端", "雲端租賃", "cloud", "saas", "iaas", "server rental", "cloud service"],
        "query_hint": "Post and telecommunication services computer related services cloud service data service 雲端 資訊服務",
        "reason": "描述含雲端、SaaS、IaaS 或雲端租賃，屬資訊或電信相關服務支出。",
    },
]


def detect_industry_routes(text: str) -> List[IndustryRoute]:
    haystack = str(text or "").lower()
    routes: List[IndustryRoute] = []
    for rule in ROUTES:
        hits = [keyword for keyword in rule["keywords_any"] if keyword.lower() in haystack]
        if not hits:
            continue
        confidence = min(0.95, 0.72 + len(hits) * 0.05)
        routes.append(
            IndustryRoute(
                code=rule["code"],
                label=rule["label"],
                tier3_product_code=rule["tier3_product_code"],
                query_hint=rule["query_hint"],
                confidence=confidence,
                reason=rule["reason"],
            )
        )
    return routes


def primary_industry_route(text: str) -> Optional[IndustryRoute]:
    routes = detect_industry_routes(text)
    return routes[0] if routes else None


def route_to_dict(route: Optional[IndustryRoute]) -> Optional[Dict]:
    if route is None:
        return None
    return {
        "industry_code": route.code,
        "industry_label": route.label,
        "tier3_product_code": route.tier3_product_code,
        "route_confidence": route.confidence,
        "route_reason": route.reason,
        "route_query_hint": route.query_hint,
    }
