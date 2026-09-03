#!/usr/bin/env python3
"""Import reviewed batch-matching results as the gold standard.

Apple Numbers files must first be exported to Excel or CSV. The script keeps
the reviewed result separate from the procurement training pool because it is a
row-level expected-output standard, not a product-name training list.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation" / "reviewed_batch_standard"
STANDARD_FILE = OUTPUT_DIR / "reviewed_batch_gold_standard.csv"
SUMMARY_FILE = OUTPUT_DIR / "reviewed_batch_gold_standard_summary.json"
SOURCE_DIR = OUTPUT_DIR / "source_csv"

SUPPORTED_SUFFIXES = {".xlsx", ".xls", ".csv"}
SKIP_SHEETS = {"Summary", "摘要", "說明", "使用說明", "Summary-表格 1"}

QUERY_COLUMNS = [
    "Item Name",
    "原始採購品名",
    "標準品名",
    "品名",
    "採購品名",
    "query",
    "base_query_text",
    "query_text",
]
TABLE4_QUERY_COLUMNS = ["原燃物料或產品名稱", "製程及設施名稱", "排放型式", "活動數據單位"]
SPEC_COLUMNS = ["Spec/Grade", "規格", "規格型號", "子類", "主要材料"]
EXPECTED_COLUMNS = {
    "expected_tier": ["matched_tier", "匹配層級", "tier"],
    "expected_tier_name": ["matched_tier_name", "匹配層級名稱", "tier_name"],
    "expected_factor_name": ["matched_name", "係數名稱", "factor_name", "best_name"],
    "expected_factor_value": ["matched_emission_factor", "排放係數", "factor_value"],
    "expected_factor_unit": ["matched_unit", "單位", "factor_unit"],
    "expected_factor_source": ["matched_factor_source", "係數來源", "matched_source", "source"],
    "expected_scope3_category": [
        "criteria_scope3_category",
        "Scope 3候選類別",
        "Scope 3 Category",
        "matched_greenhouse_gas_category",
    ],
    "expected_lifecycle_boundary": ["matched_lifecycle_boundary", "生命週期邊界"],
    "expected_lifecycle_stage": ["matched_lifecycle_stage", "生命週期階段"],
    "expected_quality_decision": ["suitability_decision", "適用性判定"],
    "expected_review_note": ["人工覆核註記", "review_note", "match_warning", "criteria_reasoning"],
}
COPY_SOURCE_SUFFIXES = {".csv", ".xlsx", ".xls", ".numbers"}


def clean(value: object) -> Optional[object]:
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return value


def first_value(row: pd.Series, columns: Iterable[str]) -> Optional[object]:
    for column in columns:
        if column in row.index:
            value = clean(row.get(column))
            if value is not None:
                return value
    return None


def row_query(row: pd.Series) -> Optional[str]:
    if any(column in row.index for column in TABLE4_QUERY_COLUMNS):
        table4_parts = [first_value(row, [column]) for column in TABLE4_QUERY_COLUMNS]
        text = " ".join(str(part) for part in table4_parts if clean(part) is not None).strip()
        if text:
            return text

    parts = [
        first_value(row, QUERY_COLUMNS),
        first_value(row, SPEC_COLUMNS),
    ]
    text = " ".join(str(part) for part in parts if clean(part) is not None).strip()
    return text or None


def source_type_for_row(row: pd.Series) -> Optional[str]:
    explicit = first_value(row, ["source_type"])
    if explicit is not None:
        return str(explicit)
    if any(column in row.index for column in TABLE4_QUERY_COLUMNS):
        return "table4_activity_csv"
    if "Item Name" in row.index:
        return "procurement_workbook"
    return None


def read_source(path: Path) -> Dict[str, pd.DataFrame]:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"不支援 {suffix}。請先將 Numbers 匯出為 Excel (.xlsx) 或 CSV。"
        )
    if suffix == ".csv":
        return {path.stem[:31]: pd.read_csv(path)}

    xl = pd.ExcelFile(path)
    sheets = {}
    for sheet in xl.sheet_names:
        if sheet in SKIP_SHEETS:
            continue
        df = pd.read_excel(path, sheet_name=sheet).dropna(how="all")
        if not df.empty:
            sheets[sheet] = df
    return sheets


def resolve_sources(path: Path) -> List[Path]:
    if path.is_dir():
        sources = sorted(
            item for item in path.iterdir()
            if item.is_file()
            and item.suffix.lower() in SUPPORTED_SUFFIXES
            and not item.name.startswith(".")
            and item.stem not in SKIP_SHEETS
        )
        if not sources:
            raise ValueError(f"資料夾內找不到可匯入的 Excel/CSV: {path}")
        return sources
    return [path]


def normalize_standard(paths: List[Path]) -> pd.DataFrame:
    rows: List[dict] = []
    for path in paths:
        sheets = read_source(path)
        for sheet_name, df in sheets.items():
            if sheet_name in SKIP_SHEETS or path.stem in SKIP_SHEETS:
                continue
            for idx, row in df.iterrows():
                query = row_query(row)
                expected_factor = first_value(row, EXPECTED_COLUMNS["expected_factor_name"])
                if query is None or expected_factor is None:
                    continue

                normalized = {
                    "standard_id": f"RB-{len(rows) + 1:05d}",
                    "source_file": str(path),
                    "source_sheet": sheet_name,
                    "source_row": int(idx) + 2,
                    "source_type": source_type_for_row(row),
                    "query": query,
                }
                for output_column, candidates in EXPECTED_COLUMNS.items():
                    normalized[output_column] = first_value(row, candidates)
                rows.append(normalized)

    return pd.DataFrame(rows)


def import_standard(path: Path) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sources = resolve_sources(path)
    standard = normalize_standard(sources)
    if standard.empty:
        raise ValueError("找不到可作為標準答案的資料列；請確認檔案包含 query/品名 與 matched_name/係數名稱。")

    backup = None
    if STANDARD_FILE.exists():
        backup = OUTPUT_DIR / f"reviewed_batch_gold_standard.backup_{datetime.now():%Y%m%d_%H%M%S}.csv"
        STANDARD_FILE.replace(backup)

    standard.to_csv(STANDARD_FILE, index=False, encoding="utf-8-sig")
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    for source in sources:
        if source.suffix.lower() in COPY_SOURCE_SUFFIXES:
            shutil.copy2(source, SOURCE_DIR / source.name)

    by_type = (
        standard["source_type"].fillna("unknown").value_counts().to_dict()
        if "source_type" in standard.columns
        else {}
    )
    summary = {
        "gold_standard": "人工覆核批次排放係數匹配結果",
        "source_file": str(path),
        "source_files": [str(source) for source in sources],
        "standard_file": str(STANDARD_FILE),
        "backup_file": str(backup) if backup else None,
        "rows": int(len(standard)),
        "unique_queries": int(standard["query"].nunique()),
        "unique_expected_factors": int(standard["expected_factor_name"].nunique()),
        "rows_by_source_type": by_type,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "notes": "This is a reviewed row-level expected-output standard, separate from procurement_training_items.csv.",
    }
    SUMMARY_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    result = import_standard(args.source)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
