"""Helpers for labeling greenhouse gas categories in retrieved factors."""

from __future__ import annotations

import re
from typing import Dict


GAS_LABELS = [
    ("CO2", "CO2（二氧化碳）", [r"\bco2\b", "二氧化碳"]),
    ("CH4", "CH4（甲烷）", [r"\bch4\b", "甲烷"]),
    ("N2O", "N2O（氧化亞氮）", [r"\bn2o\b", "氧化亞氮", "一氧化二氮"]),
    ("HFCs", "HFCs（氫氟碳化物）", [r"\bhfc[- ]?\d", r"\bhfcs?\b", "氫氟碳"]),
    ("PFCs", "PFCs（全氟碳化物）", [r"\bpfc[- ]?\d", r"\bpfcs?\b", "全氟碳"]),
    ("SF6", "SF6（六氟化硫）", [r"\bsf6\b", "六氟化硫"]),
    ("NF3", "NF3（三氟化氮）", [r"\bnf3\b", "三氟化氮"]),
]


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


def infer_greenhouse_gas_category(match: Dict) -> str:
    """Return a user-facing greenhouse gas category label for a retrieved factor."""
    text = _text_from_match(match)
    found = []

    for code, label, patterns in GAS_LABELS:
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            found.append(label)

    if found:
        return "、".join(found) + "（已換算為 CO2e）"

    if "co2e" in text or "co₂e" in text or "碳足跡" in text or "產品碳足跡" in text:
        return "CO2e 總量（未拆分氣體）"

    return "CO2e 總量（資料未標示分項氣體）"
