#!/usr/bin/env python3
"""
Batch matching utilities for procurement and Table 4-1 activity files.

The batch processor adapts supported input formats into search queries, then
uses the existing CascadeRetriever to match emission factors.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Dict, Iterable, List, Optional, Tuple, Union

import math
import re
import pandas as pd

try:
    from factor_quality import quality_export
    from search_assistance import apply_context_to_result
    from greenhouse_gas import infer_greenhouse_gas_category
    from lifecycle_stage import infer_lifecycle_stage, infer_lifecycle_boundary
    from applicability_framework import evaluate_factor_applicability
    from procurement_reference import enrich_procurement_query
    from classification.ghg_classifier import GHGCategoryClassifier
except ImportError:
    from .factor_quality import quality_export
    from .search_assistance import apply_context_to_result
    from .greenhouse_gas import infer_greenhouse_gas_category
    from .lifecycle_stage import infer_lifecycle_stage, infer_lifecycle_boundary
    from .applicability_framework import evaluate_factor_applicability
    from .procurement_reference import enrich_procurement_query
    from .classification.ghg_classifier import GHGCategoryClassifier


FileLike = Union[str, Path, BinaryIO, BytesIO]


PROCUREMENT_SHEETS_EXCLUDE = {"係數對照表"}
GENERIC_MAPPING_HINTS = {
    "spend-based factor",
    "wbcsd material method",
    "epa/eeio asset method",
    "mapping hint",
    "moenv關鍵字",
}
TABLE4_REQUIRED_COLUMNS = {
    "製程及設施名稱",
    "原燃物料或產品名稱",
    "排放型式",
    "活動數據",
    "活動數據單位",
    "數據來源表單名稱",
    "保存單位",
    "活動數據種類",
}
TRAINING_ITEM_REQUIRED_COLUMNS = {
    "原始採購品名",
    "標準品名",
    "大類",
    "Scope 3候選類別",
    "排放係數匹配關鍵字",
}
MATERIAL_ALIASES = {
    "合金鐵": "ferroalloy steel alloy",
    "石墨電極": "graphite electrode",
    "石墨電極消耗": "graphite electrode",
    "石灰石": "limestone calcium carbonate",
    "生石灰": "quicklime calcium oxide lime",
    "廢鋼": "scrap steel",
    "鋼胚": "steel billet",
    "天然氣": "natural gas",
    "液化石油氣": "liquefied petroleum gas LPG",
    "柴油": "diesel fuel",
    "重油": "heavy fuel oil",
    "汽油": "gasoline petrol",
    "電力": "electricity power",
    "外購電力": "purchased electricity",
    "蒸汽": "steam",
    "PET": "polyethylene terephthalate PET plastic",
    "PE": "polyethylene plastic",
    "包裝袋": "plastic packaging bag",
    "大豆油": "soybean oil",
    "白米": "rice",
    "麵粉": "flour wheat flour",
    "砂糖": "sugar",
    "雞蛋": "egg",
    "消毒液": "sanitizer sodium hypochlorite",
    "鹽": "salt sodium chloride",
}
ACCOUNTING_SUBJECT_COLUMNS = [
    "會計科目",
    "會計科目名稱",
    "Accounting Subject",
    "Account",
    "Account Name",
    "科目名稱",
]
ACCOUNTING_CODE_COLUMNS = [
    "會計科目代碼",
    "Accounting Code",
    "Account Code",
    "科目代碼",
]
USEFUL_LIFE_COLUMNS = [
    "使用年限",
    "耐用年限",
    "Useful Life",
]
AMOUNT_COLUMNS = [
    "Total (TWD)",
    "金額",
    "採購金額",
    "決標金額(元)",
    "Amount",
]
GENERIC_ITEM_COLUMNS = [
    "品名",
    "採購品名",
    "品項",
    "採購品項",
    "產品名稱",
    "商品名稱",
    "物品名稱",
    "項目名稱",
    "名稱",
    "原燃物料或產品名稱",
    "Item Name",
    "Item",
    "Product Name",
    "Product",
    "Description",
    "Material",
    "Service",
]
GENERIC_QUANTITY_COLUMNS = [
    "數量",
    "採購數量",
    "使用量",
    "活動數據",
    "用量",
    "重量",
    "Qty",
    "Quantity",
    "Amount Used",
    "Activity Data",
    "Activity Amount",
]
GENERIC_UNIT_COLUMNS = [
    "單位",
    "採購單位",
    "活動數據單位",
    "計量單位",
    "保存單位",
    "Unit",
    "UOM",
    "Measure Unit",
    "Activity Unit",
]
GENERIC_HINT_COLUMNS = [
    "規格",
    "規格型號",
    "材質",
    "說明",
    "用途",
    "類別",
    "產業別",
    "會計科目",
    "Spec/Grade",
    "Specification",
    "Category",
    "Mapping Hint",
]


@dataclass
class BatchMatchConfig:
    top_k: int = 3
    tier1_threshold: float = 0.80
    tier2_threshold: float = 0.70
    tier3_threshold: float = 0.60
    fallback_tier1_threshold: float = 0.55
    fallback_tier2_threshold: float = 0.45
    fallback_tier3_threshold: float = 0.35
    country_priority: str = "TW"
    use_fallback: bool = True
    twd_per_usd: float = 32.0
    twd_per_eur: float = 35.0
    taiwan_industry_context: str = ""
    taiwan_industry_query_hint: str = ""


def clean_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, float) and math.isnan(value):
        return None
    return value


def _string_or_empty(value) -> str:
    value = clean_value(value)
    return "" if value is None else str(value).strip()


def _compact_join(values: Iterable[object]) -> str:
    return " ".join(part for part in (_string_or_empty(v) for v in values) if part)


def _to_float(value) -> Optional[float]:
    value = clean_value(value)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("$", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


@lru_cache(maxsize=1)
def _ghg_classifier() -> GHGCategoryClassifier:
    return GHGCategoryClassifier()


def _first_text(row: pd.Series, columns: Iterable[str]) -> str:
    for column in columns:
        value = _string_or_empty(row.get(column))
        if value:
            return value
    return ""


def _first_float(row: pd.Series, columns: Iterable[str]) -> Optional[float]:
    for column in columns:
        value = _to_float(row.get(column))
        if value is not None:
            return value
    return None


def _unit_text(value) -> str:
    return _string_or_empty(value).lower().replace(" ", "")


def _match_source_label(match: Dict) -> Optional[str]:
    source = clean_value(match.get("source") or match.get("matched_source"))
    source_dept = clean_value(match.get("source_dept") or match.get("matched_source_dept"))
    year = clean_value(match.get("base_year") or match.get("matched_base_year"))
    region = clean_value(
        match.get("region")
        or match.get("matched_region")
        or match.get("country_name")
        or match.get("country")
    )

    label_parts = [str(source)] if source else []
    if source_dept and source_dept != source:
        label_parts.append(str(source_dept))
    label = " / ".join(part for part in label_parts if part)

    meta_parts = [str(part) for part in [year, region] if part]
    if meta_parts:
        label = f"{label}（{'，'.join(meta_parts)}）" if label else "，".join(meta_parts)

    return label or source


def _normalize_match_result(result: Dict, mode: str) -> Dict:
    if not result.get("success") or not result.get("best_match"):
        return {
            "match_status": "未匹配",
            "match_mode": mode,
            "matched_tier": None,
            "matched_tier_name": None,
            "matched_name": None,
            "matched_emission_factor": None,
            "matched_unit": None,
            "matched_greenhouse_gas_category": None,
            "matched_source": None,
            "matched_source_dept": None,
            "matched_factor_source": None,
            "matched_region": None,
            "matched_base_year": None,
            "matched_similarity": None,
            "match_warning": "現有檢索器未找到高於門檻的候選",
            "candidate_count": 0,
        }

    best = result["best_match"]
    lifecycle_stage = infer_lifecycle_stage(best, result.get("tier"))
    lifecycle_boundary = infer_lifecycle_boundary(best, result.get("tier"))
    enriched_best = {
        **best,
        "lifecycle_stage": lifecycle_stage,
        "lifecycle_boundary": lifecycle_boundary,
    }
    applicability = evaluate_factor_applicability(enriched_best, result)
    return {
        "match_status": "已匹配" if mode == "standard" else "低信心候選",
        "match_mode": "標準門檻" if mode == "standard" else "降低門檻備選",
        "matched_tier": result.get("tier"),
        "matched_tier_name": result.get("tier_name"),
        "matched_industry_code": best.get("industry_code"),
        "matched_industry_label": best.get("industry_label"),
        "matched_route_reason": best.get("route_reason"),
        "matched_name": best.get("name") or best.get("product_name"),
        "matched_emission_factor": best.get("emission_factor"),
        "matched_unit": best.get("unit") or best.get("unit_standard"),
        "matched_greenhouse_gas_category": infer_greenhouse_gas_category(best),
        "matched_source": best.get("source"),
        "matched_source_dept": best.get("source_dept"),
        "matched_factor_source": _match_source_label(best),
        "matched_region": best.get("region") or best.get("country_name") or best.get("country"),
        "matched_base_year": best.get("base_year"),
        "matched_lifecycle_stage": lifecycle_stage,
        "matched_lifecycle_boundary": lifecycle_boundary,
        "matched_similarity": best.get("similarity"),
        "matched_original_similarity": best.get("original_similarity"),
        "matched_context_boost": best.get("context_boost"),
        "applicability_score": applicability.get("overall_score"),
        "final_score": applicability.get("final_score"),
        "name_match_score": applicability.get("name_match_score"),
        "name_match_status": applicability.get("name_match_status"),
        "name_match_evidence": applicability.get("name_match_evidence"),
        "name_match_terms": applicability.get("name_match_terms"),
        "name_match_conflicts": applicability.get("name_match_conflicts"),
        "confidence_level": applicability.get("confidence_level"),
        "suitability_decision": applicability.get("decision"),
        "suitability_watch_items": applicability.get("watch_items"),
        "data_quality_level": applicability.get("data_quality_level"),
        "review_status": applicability.get("review_status"),
        "auditability_note": applicability.get("auditability_note"),
        **quality_export(applicability),
        "matched_context_terms": best.get("matched_context_terms"),
        "assisted_rerank_applied": best.get("assisted_rerank_applied"),
        "alternate_version_count": best.get("alternate_version_count"),
        "version_selection_note": best.get("version_selection_note"),
        "match_warning": result.get("warning"),
        "candidate_count": len(result.get("matches", [])),
    }


def _lookup_result(row: pd.Series) -> Optional[Dict]:
    factor_name = clean_value(row.get("lookup_factor_name"))
    factor_value = clean_value(row.get("lookup_factor_value"))
    factor_unit = clean_value(row.get("lookup_factor_unit"))
    if factor_name is None or factor_value is None:
        return None

    match = {
        "match_status": "已匹配",
        "match_mode": "係數對照表",
        "matched_tier": 0,
        "matched_tier_name": "係數對照表",
        "matched_industry_code": None,
        "matched_industry_label": None,
        "matched_route_reason": None,
        "matched_name": factor_name,
        "matched_emission_factor": factor_value,
        "matched_unit": factor_unit,
        "matched_greenhouse_gas_category": infer_greenhouse_gas_category({
            "matched_name": factor_name,
            "unit": factor_unit,
        }),
        "matched_source": "Scope 3 Procurement Data.xlsx / 係數對照表",
        "matched_source_dept": None,
        "matched_factor_source": "Scope 3 Procurement Data.xlsx / 係數對照表（TW）",
        "matched_region": "TW",
        "matched_base_year": None,
        "matched_similarity": 1.0,
        "match_warning": "使用工作簿內係數對照表關鍵字直接匹配",
        "candidate_count": 1,
    }
    lifecycle_stage = infer_lifecycle_stage(match, 0)
    lifecycle_boundary = infer_lifecycle_boundary(match, 0)
    applicability = evaluate_factor_applicability({
        **match,
        "lifecycle_stage": lifecycle_stage,
        "lifecycle_boundary": lifecycle_boundary,
    }, {"tier": 0})
    match.update({
        "matched_lifecycle_stage": lifecycle_stage,
        "matched_lifecycle_boundary": lifecycle_boundary,
        "applicability_score": applicability.get("overall_score"),
        "final_score": applicability.get("final_score"),
        "name_match_score": applicability.get("name_match_score"),
        "name_match_status": applicability.get("name_match_status"),
        "name_match_evidence": applicability.get("name_match_evidence"),
        "name_match_terms": applicability.get("name_match_terms"),
        "name_match_conflicts": applicability.get("name_match_conflicts"),
        "confidence_level": applicability.get("confidence_level"),
        "suitability_decision": applicability.get("decision"),
        "suitability_watch_items": applicability.get("watch_items"),
        "data_quality_level": applicability.get("data_quality_level"),
        "review_status": applicability.get("review_status"),
        "auditability_note": applicability.get("auditability_note"),
        **quality_export(applicability),
    })
    return match


def _activity_amount_and_unit(row: pd.Series) -> Tuple[Optional[float], str, str]:
    if _string_or_empty(row.get("活動數據")):
        amount = _to_float(row.get("活動數據"))
        unit = _string_or_empty(row.get("活動數據單位"))
        return amount, unit, "活動數據"

    qty = _to_float(row.get("Qty"))
    unit = _string_or_empty(row.get("Unit"))
    return qty, unit, "Qty"


def _calculate_emissions(row: pd.Series, match: Dict, config: BatchMatchConfig) -> Dict:
    factor = _to_float(match.get("matched_emission_factor"))
    matched_unit = _unit_text(match.get("matched_unit"))
    if factor is None:
        return {
            "calculated_co2e_kg": None,
            "calculated_co2e_t": None,
            "calculation_status": "無法計算",
            "calculation_basis": "缺少排放係數",
        }

    total_twd = _to_float(row.get("Total (TWD)"))
    amount, source_unit, amount_source = _activity_amount_and_unit(row)
    source_unit_norm = _unit_text(source_unit)

    co2e_kg = None
    basis = None

    if "m.eur" in matched_unit or "meur" in matched_unit:
        if total_twd is not None and config.twd_per_eur:
            amount_meur = total_twd / config.twd_per_eur / 1_000_000
            co2e_kg = amount_meur * factor
            basis = f"Total(TWD) {total_twd:,.0f} / {config.twd_per_eur:g} / 1,000,000 * kgCO2e/M.EUR"
    elif "2022usd" in matched_unit or "usd" in matched_unit:
        if total_twd is not None and config.twd_per_usd:
            amount_usd = total_twd / config.twd_per_usd
            co2e_kg = amount_usd * factor
            basis = f"Total(TWD) {total_twd:,.0f} / {config.twd_per_usd:g} * kgCO2e/USD"
    elif matched_unit in {"元", "twd", "ntd"} or "元" in matched_unit:
        if total_twd is not None:
            co2e_kg = total_twd * factor
            basis = f"Total(TWD) {total_twd:,.0f} * kgCO2e/TWD"
    elif amount is not None:
        converted_amount, converted_unit, conversion_note = _convert_amount_for_factor(
            amount,
            source_unit_norm,
            matched_unit,
        )
        if converted_amount is not None:
            co2e_kg = converted_amount * factor
            basis = f"{amount_source} {amount:g} {source_unit} -> {converted_amount:g} {converted_unit}; * factor"
            if conversion_note:
                basis += f" ({conversion_note})"

    if co2e_kg is None:
        return {
            "calculated_co2e_kg": None,
            "calculated_co2e_t": None,
            "calculation_status": "待人工確認",
            "calculation_basis": f"無可用數量/金額或單位不相容: source={source_unit}, factor_unit={match.get('matched_unit')}",
        }

    return {
        "calculated_co2e_kg": co2e_kg,
        "calculated_co2e_t": co2e_kg / 1000,
        "calculation_status": "已計算",
        "calculation_basis": basis,
    }


def _convert_amount_for_factor(
    amount: float,
    source_unit: str,
    factor_unit: str,
) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    if not factor_unit:
        return None, None, None

    # Factor units are the denominator, e.g. kg CO2e/kg, kg CO2e/m3, kg.
    if "kgco2e/kg" in factor_unit or factor_unit == "kg" or factor_unit.endswith("/kg"):
        if source_unit in {"kg", "公斤"}:
            return amount, "kg", None
        if source_unit in {"t", "ton", "tonne", "mt", "公噸"}:
            return amount * 1000, "kg", "公噸/t/mt 轉 kg"
    if "kgco2e/t" in factor_unit or "kgco2e/tonne" in factor_unit or factor_unit in {"t", "tonne"}:
        if source_unit in {"t", "ton", "tonne", "mt", "公噸"}:
            return amount, "t", None
        if source_unit in {"kg", "公斤"}:
            return amount / 1000, "t", "kg 轉 t"
    if "m3" in factor_unit or factor_unit == "m3":
        if source_unit in {"m3", "m^3", "立方公尺"}:
            return amount, "m3", None
        if source_unit in {"千立方公尺", "1000m3"}:
            return amount * 1000, "m3", "千立方公尺轉 m3"
    if "kwh" in factor_unit or factor_unit in {"度", "kwh"}:
        if source_unit in {"kwh", "度"}:
            return amount, "kWh", None
        if source_unit in {"千度", "1000kwh"}:
            return amount * 1000, "kWh", "千度轉 kWh"
    if factor_unit.endswith("/p") or factor_unit.endswith("/piece") or factor_unit in {"piece", "pcs", "set", "unit"}:
        if source_unit in {"pcs", "piece", "set", "unit", "個", "組"}:
            return amount, source_unit, None
    if factor_unit.endswith("/m") or factor_unit == "m":
        if source_unit in {"m", "公尺"}:
            return amount, "m", None
    if factor_unit.endswith("/l") or factor_unit == "l":
        if source_unit in {"l", "liter", "litre", "公升"}:
            return amount, "L", None

    return None, None, None


def _is_capital_goods_row(row: pd.Series) -> bool:
    criteria = _criteria_classification(row)
    if criteria.get("criteria_is_fixed_asset") is True:
        return True

    values = _compact_join(
        [
            row.get("Scope 3 Category"),
            row.get("ERP ID"),
            row.get("Mapping Hint"),
            row.get("Item Name"),
            row.get("Spec/Grade"),
            row.get("batch_item_name"),
            row.get("品名"),
            row.get("名稱"),
        ]
    ).lower()
    return (
        "category 2" in values
        or "capital goods" in values
        or "asset" in values
        or "epa/eeio asset method" in values
        or any(term in values for term in ["反應釜", "儲槽", "泵浦", "壓縮機", "冷凍櫃", "設備", "機械"])
    )


def _criteria_item_name(row: pd.Series) -> str:
    return _compact_join([
        row.get("Item Name"),
        row.get("Spec/Grade"),
        row.get("原始採購品名"),
        row.get("標準品名"),
        row.get("大類"),
        row.get("子類"),
        row.get("品名"),
        row.get("名稱"),
        row.get("摘要"),
    ])


def _criteria_classification(row: pd.Series) -> Dict:
    item_name = _criteria_item_name(row)
    if not item_name:
        return {
            "criteria_scope3_category": None,
            "criteria_is_fixed_asset": None,
            "criteria_confidence": None,
            "criteria_method": None,
            "criteria_reasoning": None,
            "criteria_recommendation": None,
        }

    result = _ghg_classifier().classify(
        item_name=item_name,
        accounting_subject=_first_text(row, ACCOUNTING_SUBJECT_COLUMNS) or None,
        accounting_subject_code=_first_text(row, ACCOUNTING_CODE_COLUMNS) or None,
        amount=_first_float(row, AMOUNT_COLUMNS),
        useful_life=_first_float(row, USEFUL_LIFE_COLUMNS),
    )
    category = result.get("ghg_category")
    return {
        "criteria_scope3_category": category if category != "unknown" else None,
        "criteria_is_fixed_asset": result.get("is_fixed_asset"),
        "criteria_confidence": result.get("confidence"),
        "criteria_method": result.get("method"),
        "criteria_reasoning": result.get("reasoning"),
        "criteria_recommendation": result.get("recommendation"),
    }


def _enrich_and_rerank_result(result: Dict, procurement_item_name: Optional[str] = None) -> Dict:
    matches = result.get("matches") or []
    if not matches:
        return result

    if procurement_item_name:
        result = dict(result)
        result["procurement_item_name"] = procurement_item_name

    enriched = []
    for match in matches:
        updated = dict(match)
        updated["lifecycle_stage"] = infer_lifecycle_stage(updated, result.get("tier"))
        updated["lifecycle_boundary"] = infer_lifecycle_boundary(updated, result.get("tier"))
        applicability = evaluate_factor_applicability(updated, result)
        updated["applicability_score"] = applicability.get("overall_score")
        updated["final_score"] = applicability.get("final_score")
        updated["confidence_level"] = applicability.get("confidence_level")
        updated["suitability_decision"] = applicability.get("decision")
        updated["suitability_watch_items"] = applicability.get("watch_items")
        updated["data_quality_level"] = applicability.get("data_quality_level")
        updated["review_status"] = applicability.get("review_status")
        updated["auditability_note"] = applicability.get("auditability_note")
        updated["dqr_basis"] = applicability.get("dqr_basis")
        updated["name_match_score"] = applicability.get("name_match_score")
        updated["name_match_status"] = applicability.get("name_match_status")
        updated["name_match_evidence"] = applicability.get("name_match_evidence")
        updated["name_match_terms"] = applicability.get("name_match_terms")
        updated["name_match_conflicts"] = applicability.get("name_match_conflicts")
        enriched.append(updated)

    enriched = sorted(
        enriched,
        key=lambda item: (
            item.get("final_score") or 0.0,
            item.get("similarity") or 0.0,
        ),
        reverse=True,
    )
    result = dict(result)
    result["matches"] = enriched
    result["best_match"] = enriched[0]
    return result


def _run_search(
    retriever,
    query: str,
    config: BatchMatchConfig,
    preferred_tier: Optional[int] = None,
    procurement_item_name: Optional[str] = None,
) -> Dict:
    if not query:
        return _normalize_match_result({"success": False}, "standard")

    context_values = [
        config.taiwan_industry_context,
        config.taiwan_industry_query_hint,
    ]

    if preferred_tier == 3 and getattr(retriever, "tier3", None) is not None:
        results = retriever.tier3.search(
            query=query,
            top_k=config.top_k,
            threshold=config.tier3_threshold,
            country_priority=config.country_priority,
        )
        if results:
            result = apply_context_to_result(
                retriever._format_response(
                    tier=3,
                    query=query,
                    matches=results,
                    message="使用 EEIO 模型排放強度（產業平均）",
                    warning="資本財/設備類批次資料優先採用 EEIO 產業平均；建議人工覆核。",
                ),
                context_values,
            )
            result = _enrich_and_rerank_result(result, procurement_item_name)
            return _normalize_match_result(
                result,
                "standard",
            )

        if config.use_fallback:
            fallback_results = retriever.tier3.search(
                query=query,
                top_k=config.top_k,
                threshold=config.fallback_tier3_threshold,
                country_priority=config.country_priority,
            )
            if fallback_results:
                fallback_result = apply_context_to_result(
                    retriever._format_response(
                        tier=3,
                        query=query,
                        matches=fallback_results,
                        message="使用 EEIO 模型排放強度（產業平均）",
                        warning="資本財/設備類批次資料以降低門檻取得 EEIO 候選；建議人工覆核。",
                    ),
                context_values,
            )
                fallback_result = _enrich_and_rerank_result(fallback_result, procurement_item_name)
                return _normalize_match_result(
                    fallback_result,
                    "fallback",
                )

    result = retriever.search(
        query=query,
        top_k=config.top_k,
        tier1_threshold=config.tier1_threshold,
        tier2_threshold=config.tier2_threshold,
        tier3_threshold=config.tier3_threshold,
        country_priority=config.country_priority,
    )
    result = apply_context_to_result(result, context_values)
    result = _enrich_and_rerank_result(result, procurement_item_name)
    if result.get("success") or not config.use_fallback:
        return _normalize_match_result(result, "standard")

    fallback = retriever.search(
        query=query,
        top_k=config.top_k,
        tier1_threshold=config.fallback_tier1_threshold,
        tier2_threshold=config.fallback_tier2_threshold,
        tier3_threshold=config.fallback_tier3_threshold,
        country_priority=config.country_priority,
    )
    fallback = apply_context_to_result(fallback, context_values)
    fallback = _enrich_and_rerank_result(fallback, procurement_item_name)
    return _normalize_match_result(fallback, "fallback")


def _read_excel_with_detected_header(file: FileLike, sheet_name: str) -> pd.DataFrame:
    preview = pd.read_excel(file, sheet_name=sheet_name, header=None, nrows=8)
    header_row = 0
    for idx, row in preview.iterrows():
        values = {str(v).strip() for v in row.tolist() if pd.notna(v)}
        if {"Item Name", "Spec/Grade"}.issubset(values) or _has_generic_column_set(values):
            header_row = int(idx)
            break
    return pd.read_excel(file, sheet_name=sheet_name, header=header_row).dropna(how="all")


def _column_key(value: object) -> str:
    text = _string_or_empty(value).lower()
    return re.sub(r"[\s\u3000_()（）/／\\-]+", "", text)


def _find_column(columns: Iterable[object], candidates: Iterable[str]) -> Optional[str]:
    column_lookup = {_column_key(column): str(column) for column in columns}
    for candidate in candidates:
        key = _column_key(candidate)
        if key in column_lookup:
            return column_lookup[key]

    for column in columns:
        column_text = _column_key(column)
        for candidate in candidates:
            candidate_key = _column_key(candidate)
            if candidate_key and candidate_key in column_text:
                return str(column)
    return None


def _has_generic_column_set(columns: Iterable[object]) -> bool:
    columns = list(columns)
    return bool(
        _find_column(columns, GENERIC_ITEM_COLUMNS)
        and _find_column(columns, GENERIC_QUANTITY_COLUMNS)
        and _find_column(columns, GENERIC_UNIT_COLUMNS)
    )


def _generic_column_mapping(df: pd.DataFrame) -> Dict[str, str]:
    columns = list(df.columns)
    item_col = _find_column(columns, GENERIC_ITEM_COLUMNS)
    quantity_col = _find_column(columns, GENERIC_QUANTITY_COLUMNS)
    unit_col = _find_column(columns, GENERIC_UNIT_COLUMNS)
    if not item_col or not quantity_col or not unit_col:
        missing = []
        if not item_col:
            missing.append("品名")
        if not quantity_col:
            missing.append("數量")
        if not unit_col:
            missing.append("單位")
        raise ValueError(f"通用批次檔缺少必要欄位: {', '.join(missing)}")

    mapping = {
        "item": item_col,
        "quantity": quantity_col,
        "unit": unit_col,
    }
    hint_cols = [
        column for column in columns
        if str(column) not in {item_col, quantity_col, unit_col}
        and _find_column([column], GENERIC_HINT_COLUMNS)
    ]
    if hint_cols:
        mapping["hint"] = hint_cols[0]
    return mapping


def _normalize_generic_batch_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    mapping = _generic_column_mapping(df)
    normalized = df.copy()
    normalized["batch_item_name"] = normalized[mapping["item"]]
    normalized["batch_quantity"] = normalized[mapping["quantity"]]
    normalized["batch_unit"] = normalized[mapping["unit"]]
    normalized["Item Name"] = normalized["batch_item_name"]
    normalized["Qty"] = normalized["batch_quantity"]
    normalized["Unit"] = normalized["batch_unit"]
    if "Spec/Grade" not in normalized.columns:
        normalized["Spec/Grade"] = normalized[mapping["hint"]] if mapping.get("hint") else ""
    if "Mapping Hint" not in normalized.columns:
        def build_hint(row: pd.Series) -> str:
            return _compact_join([
                row.get(mapping["hint"]) if mapping.get("hint") else "",
                row.get("會計科目"),
                row.get("類別"),
                row.get("產業別"),
            ])

        normalized["Mapping Hint"] = normalized.apply(build_hint, axis=1)
    return normalized, mapping


def _is_generic_batch_row(row: pd.Series) -> bool:
    return bool(
        _string_or_empty(row.get("batch_item_name") or row.get("Item Name"))
        and _to_float(row.get("batch_quantity") or row.get("Qty")) is not None
        and _string_or_empty(row.get("batch_unit") or row.get("Unit"))
    )


def _generic_batch_query(row: pd.Series) -> str:
    item = row.get("batch_item_name") or row.get("Item Name")
    parts = [
        item,
        row.get("Spec/Grade"),
        row.get("Mapping Hint"),
        row.get("batch_unit") or row.get("Unit"),
    ]
    if _is_capital_goods_row(row):
        parts.append("machinery equipment capital goods")
    return enrich_procurement_query(item, parts)


def _is_procurement_row(row: pd.Series) -> bool:
    return bool(_string_or_empty(row.get("Item Name")) and _string_or_empty(row.get("Spec/Grade")))


def _procurement_query(row: pd.Series) -> str:
    # Main item fields first; category is intentionally excluded because it is
    # often generic and can dilute product-specific matching.
    hint = _string_or_empty(row.get("Mapping Hint"))
    hint_for_query = "" if hint.lower() in GENERIC_MAPPING_HINTS else hint
    lookup_name = _string_or_empty(row.get("lookup_factor_name"))

    parts = [row.get("Item Name"), row.get("Spec/Grade"), hint_for_query, lookup_name]
    if _is_capital_goods_row(row):
        parts.append("machinery equipment capital goods")
    return enrich_procurement_query(row.get("Item Name"), parts)


def _is_training_item_row(row: pd.Series) -> bool:
    return bool(_string_or_empty(row.get("原始採購品名")) or _string_or_empty(row.get("標準品名")))


def _training_item_query(row: pd.Series) -> str:
    parts = [
        row.get("原始採購品名"),
        row.get("標準品名"),
        row.get("大類"),
        row.get("子類"),
        row.get("資料型態"),
        row.get("主要材料"),
        row.get("常用單位"),
        row.get("Scope 3候選類別"),
        row.get("排放係數匹配關鍵字"),
        row.get("適用產業"),
    ]
    return enrich_procurement_query(row.get("原始採購品名") or row.get("標準品名"), parts)


def _table4_query(row: pd.Series) -> str:
    material = row.get("原燃物料或產品名稱")
    process = row.get("製程及設施名稱")
    emission_type = row.get("排放型式")
    unit = row.get("活動數據單位")
    material_text = _string_or_empty(material)
    aliases = [
        alias
        for keyword, alias in MATERIAL_ALIASES.items()
        if keyword and keyword in material_text
    ]

    # Put material/product first because it is usually the best proxy for the
    # emission factor. Process and type provide useful disambiguation.
    return _compact_join([material, material, *aliases, process, emission_type, unit])


def _match_dataframe(
    df: pd.DataFrame,
    retriever,
    config: BatchMatchConfig,
    query_builder,
    row_filter=None,
    preferred_tier_builder=None,
    lookup_first: bool = False,
    source_type: str = "",
    source_sheet: str = "",
) -> pd.DataFrame:
    if row_filter is not None:
        df = df[df.apply(row_filter, axis=1)].copy()
    else:
        df = df.copy()

    records: List[Dict] = []
    for _, row in df.iterrows():
        base = {str(col): clean_value(row.get(col)) for col in df.columns}
        criteria = _criteria_classification(row)
        base_query = query_builder(row)
        procurement_item_name = _compact_join([
            row.get("batch_item_name"),
            row.get("Item Name"),
            row.get("原燃物料或產品名稱"),
            row.get("原始採購品名"),
            row.get("標準品名"),
            row.get("品名"),
            row.get("名稱"),
        ])
        match = _lookup_result(row) if lookup_first else None
        preferred_tier = preferred_tier_builder(row) if preferred_tier_builder else None
        if match is None:
            match = _run_search(
                retriever,
                base_query,
                config,
                preferred_tier=preferred_tier,
                procurement_item_name=procurement_item_name,
            )
        calculation = _calculate_emissions(row, match, config)
        match["base_query_text"] = base_query
        match["query_text"] = base_query
        match["assist_note"] = (
            "兩階段輔助排序：產業別只做小幅加權"
            if config.taiwan_industry_context
            else "未指定批次產業別"
        )
        match["taiwan_industry_context"] = config.taiwan_industry_context or None
        match["source_type"] = source_type
        match["source_sheet"] = source_sheet
        records.append({**base, **criteria, **match, **calculation})

    return pd.DataFrame(records)


def process_procurement_workbook(
    file: FileLike,
    retriever,
    config: Optional[BatchMatchConfig] = None,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    config = config or BatchMatchConfig()
    xl = pd.ExcelFile(file)
    lookup_df = _read_lookup_table(file, xl.sheet_names)
    outputs: Dict[str, pd.DataFrame] = {}
    summary_rows = []

    for sheet_name in xl.sheet_names:
        if sheet_name in PROCUREMENT_SHEETS_EXCLUDE:
            continue
        df = _read_excel_with_detected_header(file, sheet_name)
        if TRAINING_ITEM_REQUIRED_COLUMNS.issubset(set(df.columns)):
            matched = _match_dataframe(
                df,
                retriever,
                config,
                query_builder=_training_item_query,
                row_filter=_is_training_item_row,
                source_type="procurement_training_reference",
                source_sheet=sheet_name,
            )
            outputs[sheet_name] = matched
            summary_rows.append(_summary_row(sheet_name, matched))
            continue

        if "Item Name" in df.columns and "Spec/Grade" in df.columns:
            df = _attach_lookup_matches(df, lookup_df)
            matched = _match_dataframe(
                df,
                retriever,
                config,
                query_builder=_procurement_query,
                row_filter=_is_procurement_row,
                preferred_tier_builder=lambda row: 3 if _is_capital_goods_row(row) else None,
                lookup_first=True,
                source_type="procurement_workbook",
                source_sheet=sheet_name,
            )
            outputs[sheet_name] = matched
            summary_rows.append(_summary_row(sheet_name, matched))
            continue

        if _has_generic_column_set(df.columns):
            df, mapping = _normalize_generic_batch_dataframe(df)
            df = _attach_lookup_matches(df, lookup_df)
            matched = _match_dataframe(
                df,
                retriever,
                config,
                query_builder=_generic_batch_query,
                row_filter=_is_generic_batch_row,
                preferred_tier_builder=lambda row: 3 if _is_capital_goods_row(row) else None,
                lookup_first=True,
                source_type="generic_procurement_table",
                source_sheet=sheet_name,
            )
            matched["detected_item_column"] = mapping["item"]
            matched["detected_quantity_column"] = mapping["quantity"]
            matched["detected_unit_column"] = mapping["unit"]
            outputs[sheet_name] = matched
            summary_rows.append(_summary_row(sheet_name, matched))
            continue

    return outputs, pd.DataFrame(summary_rows)


def _read_csv_with_fallback(file: FileLike) -> pd.DataFrame:
    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            if hasattr(file, "seek"):
                file.seek(0)
            return pd.read_csv(file, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if hasattr(file, "seek"):
        file.seek(0)
    if last_error:
        raise last_error
    return pd.read_csv(file)


def process_generic_batch_table(
    file_or_df: Union[FileLike, pd.DataFrame],
    retriever,
    config: Optional[BatchMatchConfig] = None,
    sheet_name: Optional[str] = None,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    config = config or BatchMatchConfig()
    df = file_or_df.copy() if isinstance(file_or_df, pd.DataFrame) else _read_csv_with_fallback(file_or_df)
    df, mapping = _normalize_generic_batch_dataframe(df)
    output_name = sheet_name or "通用批次匹配結果"
    matched = _match_dataframe(
        df,
        retriever,
        config,
        query_builder=_generic_batch_query,
        row_filter=_is_generic_batch_row,
        preferred_tier_builder=lambda row: 3 if _is_capital_goods_row(row) else None,
        source_type="generic_procurement_table",
        source_sheet=output_name,
    )
    matched["detected_item_column"] = mapping["item"]
    matched["detected_quantity_column"] = mapping["quantity"]
    matched["detected_unit_column"] = mapping["unit"]
    return {output_name: matched}, pd.DataFrame([_summary_row(output_name, matched)])


def process_table4_csv(
    file: FileLike,
    retriever,
    config: Optional[BatchMatchConfig] = None,
    sheet_name: Optional[str] = None,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    config = config or BatchMatchConfig()
    df = _read_csv_with_fallback(file)
    if TABLE4_REQUIRED_COLUMNS.issubset(set(df.columns)):
        output_name = sheet_name or "表4-1匹配結果"
        matched = _match_dataframe(
            df,
            retriever,
            config,
            query_builder=_table4_query,
            source_type="table4_activity_csv",
            source_sheet=output_name,
        )
        return {output_name: matched}, pd.DataFrame([_summary_row(output_name, matched)])

    if _has_generic_column_set(df.columns):
        return process_generic_batch_table(df, retriever, config, sheet_name=sheet_name or Path("通用批次").stem)

    table4_missing = TABLE4_REQUIRED_COLUMNS - set(df.columns)
    raise ValueError(
        "批次 CSV 無法辨識欄位。請至少提供「品名、數量、單位」三類欄位；"
        f"若使用表 4-1 格式，缺少欄位: {', '.join(sorted(table4_missing))}"
    )


def _read_lookup_table(file: FileLike, sheet_names: List[str]) -> Optional[pd.DataFrame]:
    if "係數對照表" not in sheet_names:
        return None

    lookup = pd.read_excel(file, sheet_name="係數對照表")
    if lookup.empty or len(lookup.columns) < 4:
        return None

    lookup = lookup.iloc[:, :4].copy()
    lookup.columns = ["keyword", "factor_name", "factor_value", "factor_unit"]
    lookup = lookup.dropna(subset=["keyword", "factor_name"])
    lookup["keyword_clean"] = (
        lookup["keyword"].astype(str).str.replace("*", "", regex=False).str.strip()
    )
    lookup = lookup[lookup["keyword_clean"] != ""]
    return lookup


def _attach_lookup_matches(df: pd.DataFrame, lookup_df: Optional[pd.DataFrame]) -> pd.DataFrame:
    df = df.copy()
    df["lookup_keyword"] = None
    df["lookup_factor_name"] = None
    df["lookup_factor_value"] = None
    df["lookup_factor_unit"] = None

    if lookup_df is None or lookup_df.empty:
        return df

    for idx, row in df.iterrows():
        haystack = _compact_join([row.get("Item Name"), row.get("Spec/Grade"), row.get("Mapping Hint")])
        matched = None
        for _, lookup_row in lookup_df.iterrows():
            keyword = _string_or_empty(lookup_row.get("keyword_clean"))
            if keyword and keyword in haystack:
                matched = lookup_row
                break
        if matched is not None:
            df.at[idx, "lookup_keyword"] = clean_value(matched.get("keyword_clean"))
            df.at[idx, "lookup_factor_name"] = clean_value(matched.get("factor_name"))
            df.at[idx, "lookup_factor_value"] = clean_value(matched.get("factor_value"))
            df.at[idx, "lookup_factor_unit"] = clean_value(matched.get("factor_unit"))

    return df


def process_batch_file(
    file: FileLike,
    filename: str,
    retriever,
    config: Optional[BatchMatchConfig] = None,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    suffix = Path(filename).suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return process_procurement_workbook(file, retriever, config)
    if suffix == ".csv":
        return process_table4_csv(file, retriever, config, sheet_name=Path(filename).stem[:31])
    raise ValueError(f"不支援的檔案格式: {suffix}")


def _summary_row(name: str, df: pd.DataFrame) -> Dict:
    if df.empty:
        avg_similarity = None
        avg_final_score = None
        review_required = 0
        calculated_kg = 0
        calculated_rows = 0
    else:
        avg_similarity = (
            float(df["matched_similarity"].dropna().mean())
            if df["matched_similarity"].notna().any()
            else None
        )
        avg_final_score = (
            float(df["final_score"].dropna().mean())
            if "final_score" in df.columns and df["final_score"].notna().any()
            else None
        )
        review_required = (
            int(df["confidence_level"].isin(["低", "需人工確認"]).sum())
            if "confidence_level" in df.columns
            else 0
        )
        calculated_kg = (
            float(df["calculated_co2e_kg"].dropna().sum())
            if "calculated_co2e_kg" in df.columns
            else 0
        )
        calculated_rows = (
            int(df["calculated_co2e_kg"].notna().sum())
            if "calculated_co2e_kg" in df.columns
            else 0
        )

    return {
        "sheet": name,
        "rows": len(df),
        "lookup_matches": int((df.get("match_mode") == "係數對照表").sum()) if not df.empty else 0,
        "standard_matches": int((df.get("match_mode") == "標準門檻").sum()) if not df.empty else 0,
        "fallback_matches": int((df.get("match_mode") == "降低門檻備選").sum()) if not df.empty else 0,
        "unmatched": int((df.get("match_status") == "未匹配").sum()) if not df.empty else 0,
        "calculated_rows": calculated_rows,
        "total_co2e_kg": calculated_kg,
        "total_co2e_t": calculated_kg / 1000,
        "avg_similarity": avg_similarity,
        "avg_final_score": avg_final_score,
        "review_required": review_required,
    }


def write_batch_results_excel(
    output_path: Union[str, Path, BytesIO],
    sheets: Dict[str, pd.DataFrame],
    summary: pd.DataFrame,
) -> None:
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        used_names = {"Summary"}
        for raw_name, df in sheets.items():
            sheet_name = _safe_sheet_name(raw_name, used_names)
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def _safe_sheet_name(name: str, used_names: set) -> str:
    clean = "".join(ch for ch in str(name) if ch not in "[]:*?/\\").strip() or "Sheet"
    clean = clean[:31]
    candidate = clean
    idx = 2
    while candidate in used_names:
        suffix = f"_{idx}"
        candidate = f"{clean[:31 - len(suffix)]}{suffix}"
        idx += 1
    used_names.add(candidate)
    return candidate
