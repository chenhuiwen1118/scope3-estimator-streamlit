"""Applicability and data-quality framework for emission-factor matches."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    from name_matching import evaluate_name_compatibility
except ImportError:
    from .name_matching import evaluate_name_compatibility


CRITERIA = [
    ("activity_product_compatibility", "Activity/Product compatibility", "活動或產品相容性"),
    ("physical_unit_compatibility", "Physical unit compatibility", "物理單位相容性"),
    ("system_boundary", "System boundary", "系統邊界"),
    ("geography", "Geography", "地理適用性"),
    ("reference_year", "Reference year", "基準年度"),
    ("technology_production_route", "Technology/Production route", "技術或製程路徑"),
    ("ghg_species", "GHG species", "溫室氣體種類"),
    ("scope3_category", "Scope 3 category", "Scope 3 類別"),
    ("data_quality_source", "Data quality and source", "資料品質與來源"),
    ("licence_auditability", "Licence and auditability", "授權與可稽核性"),
]

CRITERION_WEIGHTS = {
    "Activity/Product compatibility": 0.18,
    "Physical unit compatibility": 0.13,
    "System boundary": 0.12,
    "Geography": 0.10,
    "Reference year": 0.09,
    "Technology/Production route": 0.10,
    "GHG species": 0.08,
    "Scope 3 category": 0.06,
    "Data quality and source": 0.10,
    "Licence and auditability": 0.04,
}

SOURCE_RANK = {
    "moenv cfp": 0.90,
    "環境部產品碳足跡": 0.90,
    "cca ghg factor table": 0.86,
    "環境部氣候變遷署": 0.86,
    "moea/taipower electricity factor": 0.84,
    "台電": 0.84,
    "taiwan epa/moe": 0.82,
    "taiwan epa": 0.82,
    "agribalyse": 0.72,
    "idemat": 0.70,
    "exiobase": 0.58,
}

SERVICE_TERMS = [
    "服務", "顧問", "諮詢", "宅配", "貨運", "配送", "運輸", "工程", "裝潢", "租賃",
    "service", "consulting", "freight", "distribution", "transport", "construction",
    "renovation", "rental",
]

OFFICIAL_SOURCE_TERMS = [
    "moenv", "taiwan epa", "cca", "moea", "taipower", "環境部", "氣候變遷署", "能源署", "台電",
]


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _lower_text(*values) -> str:
    return " ".join(_text(value) for value in values if _text(value)).lower()


def _score_status(score: float) -> str:
    if score >= 0.80:
        return "良好"
    if score >= 0.60:
        return "可用但需覆核"
    if score >= 0.40:
        return "低信心"
    return "不明/不建議直接採用"


def _criterion(label_en: str, label_zh: str, score: float, evidence: str) -> Dict:
    score = max(0.0, min(1.0, float(score)))
    return {
        "criterion": label_en,
        "criterion_zh": label_zh,
        "score": round(score, 2),
        "status": _score_status(score),
        "evidence": evidence,
    }


def _source_score(source: str, tier: Optional[int]) -> float:
    source_lower = source.lower()
    for key, score in SOURCE_RANK.items():
        if key.lower() in source_lower:
            return score
    if tier == 1:
        return 0.78
    if tier == 2:
        return 0.66
    if tier == 3:
        return 0.50
    return 0.46


def _reference_year_score(year) -> float:
    try:
        year_int = int(float(year))
    except (TypeError, ValueError):
        return 0.42

    age = max(0, datetime.now().year - year_int)
    if age <= 3:
        return 0.90
    if age <= 6:
        return 0.78
    if age <= 10:
        return 0.62
    if age <= 15:
        return 0.48
    return 0.35


def _scope_category_score(result: Dict, match: Dict) -> float:
    selected = _text(result.get("scope3_category"))
    matched = _text(match.get("scope3_category") or match.get("category"))
    if not selected:
        return 0.68
    if selected and matched and selected.lower() in matched.lower():
        return 0.86
    if selected:
        return 0.68
    if matched:
        return 0.58
    return 0.68


def _is_service_context(text: str, match: Dict) -> bool:
    combined = _lower_text(
        text,
        match.get("name"),
        match.get("product_name"),
        match.get("category"),
        match.get("scope3_category"),
    )
    return any(term.lower() in combined for term in SERVICE_TERMS)


def _system_boundary_score(boundary: str, query_text: str, match: Dict) -> Tuple[float, str]:
    if not boundary:
        return 0.42, "生命週期範疇未明確標示；引用前需回查係數資訊揭露表。"

    boundary_lower = boundary.lower()
    service_context = _is_service_context(query_text, match)
    is_gate = any(term in boundary_lower for term in ["搖籃到大門", "cradle-to-gate", "cradle to gate"])
    is_grave = any(term in boundary_lower for term in ["搖籃到墳墓", "cradle-to-grave", "cradle to grave"])
    is_average = "產業平均" in boundary or "eeio" in boundary_lower

    if service_context and is_grave:
        return 0.88, f"{boundary}；服務型係數通常需涵蓋搖籃到墳墓。"
    if service_context and is_gate:
        return 0.62, f"{boundary}；服務型活動若只到大門，需確認是否漏列交付或使用後階段。"
    if not service_context and is_gate:
        return 0.88, f"{boundary}；商品或原物料採購通常優先採用搖籃到大門。"
    if not service_context and is_grave:
        return 0.78, f"{boundary}；商品係數涵蓋較完整生命週期，需避免與下游階段重複計算。"
    if is_average:
        return 0.58, f"{boundary}；產業平均邊界需於報告標註限制。"
    return 0.68, f"{boundary}；需人工確認是否符合盤查邊界。"


def _unit_score(unit: str, tier: Optional[int]) -> Tuple[float, str]:
    if not unit:
        return 0.38, "係數單位未標示；無法確認是否能與活動數據相乘。"

    unit_lower = unit.lower()
    physical_terms = ["kg", "公斤", "公噸", "ton", " t", "l", "公升", "m2", "m3", "kwh", "tkm"]
    money_terms = ["m.eur", "eur", "usd", "ntd", "元"]
    if any(term in unit_lower for term in physical_terms):
        return 0.86, f"係數單位：{unit}；屬可量測之宣告單位或活動單位，仍需檢查換算。"
    if any(term in unit_lower for term in money_terms):
        score = 0.62 if tier == 3 else 0.58
        return score, f"係數單位：{unit}；屬金額型係數，需確認採購金額年度、幣別與通膨調整。"
    return 0.68, f"係數單位：{unit}；需確認與活動數據之宣告單位一致。"


def _geography_score(geography: str) -> Tuple[float, str]:
    if not geography:
        return 0.42, "地區/國家未標示；無法確認能源結構與本土情境是否一致。"

    geo_lower = geography.lower()
    if geography in {"TW", "台灣", "臺灣", "Taiwan"} or "taiwan" in geo_lower:
        return 0.90, f"地區/國家：{geography}；符合台灣盤查情境，地理代表性較高。"
    if "global" in geo_lower or "world" in geo_lower:
        return 0.55, f"地區/國家：{geography}；全球平均可初估，需標註與台灣能源/製程差異。"
    return 0.48, f"地區/國家：{geography}；非台灣資料，需評估能源結構、生產效率與區域差異。"


def _technology_score(tier: Optional[int], name_text: str, source: str, route_reason: str) -> Tuple[float, str]:
    process_terms = ["固定燃燒", "移動燃燒", "製程", "process", "combustion", "鍋爐", "冷軋", "熱軋", "電鍍"]
    if any(term in name_text for term in process_terms):
        return 0.84, "係數名稱含製程、燃燒方式或材料規格，可作為技術路徑證據；仍需與現場條件比對。"
    if route_reason:
        return 0.66, f"依行業關鍵字路由：{route_reason}；代表產業平均，非供應商特定製程。"
    if tier == 3 or "exiobase" in source.lower():
        return 0.50, "EEIO 為產業平均，通常無法代表特定供應商、製程或材料等級。"
    if tier == 1:
        return 0.72, "本土產品係數具較佳情境相近性，但仍需確認製程、燃料與規格。"
    return 0.60, "技術或製程路徑未完整揭露；需檢視原始資料表。"


def _quality_label_and_score(source: str, tier: Optional[int], data_quality: str) -> Tuple[str, float]:
    text = _lower_text(source, data_quality)
    if any(term in text for term in ["high quality", "高品質", "品質級"]):
        return "品質級/高品質", 0.92
    if any(term in text for term in ["basic quality", "基本品質"]):
        return "品質級/基本品質", 0.84
    if any(term in text for term in ["data estimate", "初估品質", "參考級", "estimated"]):
        return "參考級/初估品質", 0.58
    if any(term in text for term in OFFICIAL_SOURCE_TERMS):
        return "官方來源，審查等級需回原始揭露表確認", 0.78
    if tier == 3:
        return "產業平均估算，未揭露產品級 DQR", 0.50
    return "未揭露品質級別", 0.46


def _auditability_score(
    source: str,
    unit: str,
    year,
    geography: str,
    boundary: str,
    data_quality_label: str,
) -> Tuple[float, str]:
    evidence_fields = [
        bool(source),
        bool(unit),
        bool(year),
        bool(geography),
        bool(boundary),
        data_quality_label != "未揭露品質級別",
    ]
    completeness = sum(evidence_fields) / len(evidence_fields)
    source_lower = source.lower()
    base = 0.35 + completeness * 0.45
    if any(term in source_lower for term in OFFICIAL_SOURCE_TERMS):
        base = max(base, 0.82)
    elif "exiobase" in source_lower:
        base = max(base, 0.62)
    evidence = (
        f"揭露欄位完整度約 {int(completeness * 100)}%；需保留來源、年度、版本、係數名稱、單位、"
        "生命週期範疇、排除項目與引用限制。"
    )
    return min(base, 0.95), evidence


def evaluate_factor_applicability(match: Dict, result: Optional[Dict] = None) -> Dict:
    """Evaluate whether a matched emission factor is fit for use beyond text similarity."""
    result = result or {}
    tier = result.get("tier") or match.get("tier")
    source = _text(
        match.get("source")
        or match.get("matched_source")
        or match.get("source_database")
        or match.get("matched_factor_source")
    )
    unit = _text(match.get("unit") or match.get("unit_standard") or match.get("matched_unit"))
    similarity = match.get("similarity") or match.get("matched_similarity") or 0.0
    try:
        similarity_score = float(similarity)
    except (TypeError, ValueError):
        similarity_score = 0.0

    name_text = _lower_text(match.get("name"), match.get("product_name"), match.get("matched_name"))
    query_text = _lower_text(result.get("original_query"), result.get("query"))
    boundary = _text(
        match.get("lifecycle_boundary")
        or match.get("matched_lifecycle_boundary")
        or result.get("lifecycle_boundary")
    )
    ghg = _text(match.get("matched_greenhouse_gas_category") or match.get("ghg_gas_category"))
    if not ghg:
        ghg = _text(match.get("name") or match.get("product_name"))

    criteria: List[Dict] = []
    name_match = evaluate_name_compatibility(
        result.get("procurement_item_name") or result.get("original_query") or result.get("query"),
        _lower_text(
            match.get("name") or match.get("product_name") or match.get("matched_name"),
            match.get("industry_code"),
            match.get("industry_label"),
            match.get("route_query_hint"),
        ),
    )
    activity_score = (similarity_score * 0.55) + (name_match["score"] * 0.45)
    if name_match["score"] < 0.35:
        activity_score = min(activity_score, 0.45)

    criteria.append(_criterion(
        "Activity/Product compatibility",
        "活動或產品相容性",
        min(1.0, max(activity_score, 0.20)),
        name_match["evidence"],
    ))

    unit_score, unit_evidence = _unit_score(unit, tier)
    criteria.append(_criterion(
        "Physical unit compatibility",
        "物理單位相容性",
        unit_score,
        unit_evidence,
    ))

    boundary_score, boundary_text = _system_boundary_score(boundary, query_text, match)
    criteria.append(_criterion(
        "System boundary",
        "系統邊界",
        boundary_score,
        boundary_text,
    ))

    geography = _text(
        match.get("region")
        or match.get("matched_region")
        or match.get("country_name")
        or match.get("country")
        or match.get("geographic_scope")
    )
    geo_score, geo_evidence = _geography_score(geography)
    criteria.append(_criterion(
        "Geography",
        "地理適用性",
        geo_score,
        geo_evidence,
    ))

    year = match.get("base_year") or match.get("matched_base_year") or match.get("year")
    year_score = _reference_year_score(year)
    criteria.append(_criterion(
        "Reference year",
        "基準年度",
        year_score,
        f"基準年度：{year or '未標示'}；依 DQR 時間相關性，與盤查年度差距越小越佳。",
    ))

    tech_score, tech_evidence = _technology_score(tier, name_text, source, _text(match.get("route_reason")))
    criteria.append(_criterion(
        "Technology/Production route",
        "技術或製程路徑",
        tech_score,
        tech_evidence,
    ))

    ghg_has_explicit_species = any(
        term in ghg.lower()
        for term in ["co2", "ch4", "n2o", "hfc", "pfc", "sf6", "nf3", "co2e", "co₂e"]
    )
    if ghg_has_explicit_species:
        ghg_score = 0.82
        ghg_evidence = f"氣體標註：{ghg or '未標示'}；需確認是否為 CO2e 總量或分項氣體係數。"
    elif any(term in source.lower() for term in ["moenv cfp", "taiwan epa", "環境部產品碳足跡"]):
        ghg_score = 0.76
        ghg_evidence = (
            "產品碳足跡係數通常以 kgCO2e/宣告單位揭露；此筆結果仍需回原始資訊揭露表確認 GWP 版本。"
        )
    else:
        ghg_score = 0.55
        ghg_evidence = f"氣體標註：{ghg or '未標示'}；需確認是否為 CO2e 總量或分項氣體係數。"
    criteria.append(_criterion(
        "GHG species",
        "溫室氣體種類",
        ghg_score,
        ghg_evidence,
    ))

    criteria.append(_criterion(
        "Scope 3 category",
        "Scope 3 類別",
        _scope_category_score(result, match),
        f"使用者選擇：{_text(result.get('scope3_category')) or '未指定'}；資料分類：{_text(match.get('scope3_category') or match.get('category')) or '未標示'}。",
    ))

    data_quality = _text(match.get("data_quality") or match.get("matched_data_quality") or match.get("quality_level"))
    data_quality_label, quality_score = _quality_label_and_score(source, tier, data_quality)
    source_score = max(_source_score(source, tier), quality_score)
    criteria.append(_criterion(
        "Data quality and source",
        "資料品質與來源",
        source_score,
        (
            f"來源：{source or '未標示'}；資料品質：{data_quality_label}。"
            "依可靠性、完整性、時間、地理、技術五項 DQR 指標檢視。"
        ),
    ))

    audit_score, audit_evidence = _auditability_score(source, unit, year, geography, boundary, data_quality_label)
    criteria.append(_criterion(
        "Licence and auditability",
        "授權與可稽核性",
        audit_score,
        audit_evidence,
    ))

    weight_total = sum(CRITERION_WEIGHTS.get(item["criterion"], 0.0) for item in criteria) or 1.0
    weighted_score = round(
        sum(item["score"] * CRITERION_WEIGHTS.get(item["criterion"], 0.0) for item in criteria) / weight_total,
        2,
    )

    final_score = round((similarity_score * 0.45) + (weighted_score * 0.55), 2)
    if name_match["score"] < 0.20:
        final_score = min(final_score, 0.30)
        weighted_score = min(weighted_score, 0.42)
    elif name_match["score"] < 0.35:
        final_score = min(final_score, 0.42)
        weighted_score = min(weighted_score, 0.50)
    elif name_match["score"] < 0.45:
        final_score = min(final_score, 0.58)

    if weighted_score >= 0.80:
        decision = "建議採用"
    elif weighted_score >= 0.65:
        decision = "可採用但需人工覆核"
    elif weighted_score >= 0.50:
        decision = "僅適合初估"
    else:
        decision = "不建議直接採用"

    watch_items = [
        item["criterion_zh"]
        for item in criteria
        if item["score"] < 0.65
    ]
    if name_match["score"] < 0.45 and "品名相容性" not in watch_items:
        watch_items.insert(0, "品名相容性")
    return {
        "overall_score": weighted_score,
        "final_score": final_score,
        "name_match_score": name_match["score"],
        "name_match_status": name_match["status"],
        "name_match_evidence": name_match["evidence"],
        "name_match_terms": name_match["matched_terms"],
        "name_match_conflicts": name_match["conflict_groups"],
        "confidence_level": (
            "高" if final_score >= 0.80 else
            "中" if final_score >= 0.65 else
            "低" if final_score >= 0.50 else
            "需人工確認"
        ),
        "decision": decision,
        "watch_items": "、".join(watch_items) if watch_items else "無明顯低分項目",
        "data_quality_level": data_quality_label,
        "review_status": "需回原始揭露表確認品質級/參考級與第三方查驗狀態",
        "auditability_note": audit_evidence,
        "dqr_basis": "依可靠性、完整性、時間相關性、地理相關性、技術相關性五項指標檢視。",
        "criteria": criteria,
    }
