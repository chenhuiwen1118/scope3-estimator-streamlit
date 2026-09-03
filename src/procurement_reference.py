"""Procurement-name reference helpers for batch matching."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Dict, List, Optional

import pandas as pd


REFERENCE_DIR = Path(__file__).parent.parent / "data" / "reference_data"
TRAINING_ITEMS_FILE = REFERENCE_DIR / "procurement_training_items.csv"
SYNONYMS_FILE = REFERENCE_DIR / "procurement_synonyms.csv"
OVERBROAD_QUERY_TERMS = {
    "鋼/鋁/銅",
    "碳鋼/不鏽鋼/鋁材",
    "牌號/尺寸/厚度/硬度/表面處理/包裝量（依品項填寫）",
    "範疇3 類別1",
}
TERM_SPLIT_PATTERN = re.compile(r"[/,，、;；／\s|]+")


def _clean(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _term_fragments(*values: object) -> List[str]:
    fragments: List[str] = []
    for value in values:
        text = _clean(value)
        if not text:
            continue
        for part in TERM_SPLIT_PATTERN.split(text):
            part = _clean(part)
            if len(part) < 2:
                continue
            if part in OVERBROAD_QUERY_TERMS:
                continue
            fragments.append(part)
    return fragments


@lru_cache(maxsize=1)
def load_procurement_training_items() -> pd.DataFrame:
    if not TRAINING_ITEMS_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(TRAINING_ITEMS_FILE)


@lru_cache(maxsize=1)
def load_procurement_synonyms() -> pd.DataFrame:
    if not SYNONYMS_FILE.exists():
        return pd.DataFrame()
    return pd.read_csv(SYNONYMS_FILE)


@lru_cache(maxsize=1)
def synonym_lookup() -> Dict[str, Dict[str, str]]:
    lookup: Dict[str, Dict[str, str]] = {}
    synonyms = load_procurement_synonyms()
    if synonyms.empty:
        return lookup

    for _, row in synonyms.iterrows():
        standard = _clean(row.get("映射標準品名"))
        category = _clean(row.get("大類"))
        for key in [_clean(row.get("常見原詞")), _clean(row.get("其他寫法")), standard]:
            if not key:
                continue
            lookup[key.lower()] = {
                "standard_name": standard,
                "major_category": category,
            }
    return lookup


@lru_cache(maxsize=1)
def training_lookup() -> Dict[str, Dict[str, str]]:
    lookup: Dict[str, Dict[str, str]] = {}
    training = load_procurement_training_items()
    if training.empty:
        return lookup

    for _, row in training.iterrows():
        original = _clean(row.get("原始採購品名"))
        standard = _clean(row.get("標準品名"))
        keys = {original.lower(), standard.lower()}
        for part in _term_fragments(
            original,
            standard,
            row.get("大類"),
            row.get("子類"),
            row.get("主要材料"),
            row.get("排放係數匹配關鍵字"),
            row.get("適用產業"),
        ):
            keys.add(part.lower())
        for key in keys:
            if not key:
                continue
            lookup.setdefault(key, {
                "standard_name": standard,
                "major_category": _clean(row.get("大類")),
                "subcategory": _clean(row.get("子類")),
                "data_type": _clean(row.get("資料型態")),
                "material": _clean(row.get("主要材料")),
                "unit": _clean(row.get("常用單位")),
                "scope3_category": _clean(row.get("Scope 3候選類別")),
                "match_keywords": _clean(row.get("排放係數匹配關鍵字")),
                "industry": _clean(row.get("適用產業")),
            })
    return lookup


def enrich_procurement_query(name: str, existing_parts: Optional[List[object]] = None) -> str:
    """Return query text expanded with controlled procurement reference terms."""
    parts = [_clean(part) for part in (existing_parts or []) if _clean(part)]
    raw_name = _clean(name)
    if raw_name:
        parts.insert(0, raw_name)

    lower_name = raw_name.lower()
    candidates = []
    for lookup in [synonym_lookup(), training_lookup()]:
        if lower_name in lookup:
            candidates.append(lookup[lower_name])
        else:
            candidates.extend(
                value
                for key, value in lookup.items()
                if key and (key in lower_name or (len(lower_name) >= 4 and lower_name in key))
            )

    for item in candidates[:5]:
        match_keywords = _clean(item.get("match_keywords"))
        if "/" in match_keywords and len(match_keywords) > 36:
            match_keywords = ""
        parts.extend([
            item.get("standard_name"),
            item.get("major_category"),
            match_keywords,
        ])

    seen = set()
    compacted = []
    for part in parts:
        text = _clean(part)
        key = text.lower()
        if text in OVERBROAD_QUERY_TERMS:
            continue
        if not text or key in seen:
            continue
        seen.add(key)
        compacted.append(text)
    return " ".join(compacted)
