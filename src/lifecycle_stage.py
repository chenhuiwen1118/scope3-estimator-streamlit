"""Helpers for labeling life-cycle stages and calculation boundaries."""

from __future__ import annotations

from typing import Dict, Optional


def _text_from_match(match: Dict) -> str:
    fields = [
        "name",
        "product_name",
        "matched_name",
        "category",
        "scope3_category",
        "source",
        "source_dept",
        "unit",
        "unit_standard",
        "unit_original",
        "description",
        "calculation_basis",
    ]
    return " ".join(str(match.get(field) or "") for field in fields).lower()


def _source_text(match: Dict) -> str:
    return str(match.get("source") or match.get("matched_source") or "").lower()


def _unit_text(match: Dict) -> str:
    return str(match.get("unit") or match.get("unit_standard") or match.get("matched_unit") or "").lower()


def infer_lifecycle_stage(match: Dict, tier: Optional[int] = None) -> str:
    """Return a practical life-cycle stage label for review and reporting."""
    text = _text_from_match(match)
    unit = _unit_text(match)
    source = _source_text(match)
    category = str(match.get("category") or "").lower()

    if tier == 3 or "m.eur" in unit or "eeio" in text or "exiobase" in source:
        return "採購支出／產業平均（Spend-based / EEIO）"

    if any(term in text for term in ["運輸", "物流", "貨運", "配送", "transport", "freight", "shipping", "distribution"]):
        return "運輸與配送（Transport / distribution）"

    if any(term in text for term in ["廢棄", "廢棄物", "回收", "焚化", "掩埋", "waste", "recycling", "incineration", "landfill"]):
        return "廢棄處理／生命終結（End-of-life / waste treatment）"

    if any(term in text for term in ["外購電力", "電力", "用電", "electricity", "power"]) and "產品" not in text:
        return "能源取得／外購電力（Purchased energy）"

    if any(term in text for term in ["固定燃燒", "移動燃燒", "燃料", "柴油", "汽油", "天然氣", "燃料油", "lpg", "combustion", "fuel"]):
        return "能源使用／燃料燃燒（Energy use / combustion）"

    if any(term in text for term in ["製程", "製造", "工廠", "process emission", "manufacturing"]) or category.startswith("附表"):
        return "製程排放／製造階段（Manufacturing / process emissions）"

    if any(term in text for term in ["溫暖化潛勢", "gwp", "hfc", "pfc", "sf6", "nf3"]):
        return "溫室氣體特性值（GWP reference）"

    if any(term in source for term in ["moenv cfp", "taiwan epa"]) or any(term in text for term in ["碳足跡", "產品碳足跡", "cradle-to-gate"]):
        return "原料取得與製造（Cradle-to-gate product/material）"

    return "未標示，需依原始資料邊界人工判定"


def infer_lifecycle_boundary(match: Dict, tier: Optional[int] = None) -> str:
    """Return what life-cycle stages are likely included in the factor calculation."""
    text = _text_from_match(match)
    unit = _unit_text(match)
    source = _source_text(match)
    category = str(match.get("category") or "").lower()

    if any(term in text for term in ["溫暖化潛勢", "gwp"]) or any(term in text for term in ["hfc", "pfc", "sf6", "nf3"]):
        return "不屬於產品生命週期係數；為溫室氣體特性值，用於換算 CO2e。"

    if tier == 3 or "m.eur" in unit or "eeio" in text or "exiobase" in source:
        return "包含上游供應鏈與產業平均生產活動；以採購金額估算，通常不代表單一產品完整生命週期。"

    if any(term in source for term in ["moenv cfp", "taiwan epa"]) or any(term in text for term in ["產品碳足跡", "碳足跡", "cradle-to-gate"]):
        return "通常包含原料取得、上游運輸與製造階段；是否含使用、配送或廢棄階段需回查原始產品碳足跡邊界。"

    if "cca ghg factor table" in source or "氣候變遷署" in text:
        if any(term in text for term in ["固定燃燒", "移動燃燒", "燃燒", "燃料", "柴油", "汽油", "天然氣", "combustion", "fuel"]):
            return "包含燃料於使用端燃燒時的直接排放；通常不含燃料開採、煉製、運輸等上游階段。"
        if category.startswith("附表") or any(term in text for term in ["製程", "製造", "process"]):
            return "包含特定製程或反應本身的排放；通常不含原料取得、設備建置、產品使用與廢棄階段。"
        return "包含公告係數所定義的直接排放或特定活動邊界；需依原表附註確認是否含上游或下游階段。"

    if any(term in source for term in ["moea", "taipower", "台電", "能源署"]) or any(term in text for term in ["外購電力", "電力排碳", "electricity factor"]):
        return "包含發電端燃料燃燒與電力供應平均排放；通常不含用電設備製造、輸配設備建置或產品後續生命週期。"

    if any(term in text for term in ["運輸", "物流", "貨運", "配送", "transport", "freight", "shipping"]):
        return "包含運輸服務執行階段的燃料或能源排放；通常不含貨品製造、倉儲建物與車輛製造。"

    if any(term in text for term in ["廢棄", "廢棄物", "回收", "焚化", "掩埋", "waste", "recycling", "incineration", "landfill"]):
        return "包含廢棄物處理或生命終結處置階段；通常不含產品製造、使用階段與前段採購排放。"

    return "資料未明確標示計算邊界；建議回查原始資料庫文件，確認是否為 cradle-to-gate、gate-to-gate 或使用/廢棄階段係數。"
