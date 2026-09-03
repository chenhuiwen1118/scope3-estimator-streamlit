#!/usr/bin/env python3
"""
Import MOENV product carbon-footprint factors into Tier 1 local data.

This script is intentionally file-based first: download/export the official
MOENV CFP coefficient file, then run this script to refresh the local cache.
If MOENV provides a stable public API later, the downloader can feed the same
normalization pipeline.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.embedding import EmbeddingEngine


TIER1_DIR = PROJECT_ROOT / "data" / "emission_factors" / "tier1_local"
DEFAULT_INPUT = TIER1_DIR / "碳足跡排放係數.csv"
UNIFIED_FILE = TIER1_DIR / "tier1_unified.csv"
METADATA_FILE = TIER1_DIR / "tier1_metadata.csv"
EMBEDDINGS_FILE = TIER1_DIR / "tier1_embeddings.npy"
STATUS_FILE = TIER1_DIR / "moenv_cfp_update_status.json"


COLUMN_ALIASES: Dict[str, Iterable[str]] = {
    "name": ["name", "名稱", "產品名稱", "項目名稱", "排放係數名稱"],
    "emission_factor": ["coe", "emission_factor", "碳係數", "排放係數", "係數", "數值"],
    "unit": ["unit", "單位", "宣告單位", "功能單位"],
    "department": ["departmentname", "公告單位", "單位名稱", "資料來源", "來源"],
    "year": ["announcementyear", "公告年度", "年度", "年份", "基準年"],
}


UNIT_MAPPING = {
    "公斤(kg)": "kg",
    "公斤": "kg",
    "kg": "kg",
    "公噸": "t",
    "噸": "t",
    "ton": "t",
    "tonne": "t",
    "立方公尺(m3)": "m3",
    "立方公尺": "m3",
    "m3": "m3",
    "平方公尺(m2)": "m2",
    "平方公尺": "m2",
    "m2": "m2",
    "度(kwh)": "kWh",
    "度": "kWh",
    "kwh": "kWh",
    "片": "piece",
    "張": "piece",
    "個": "piece",
    "公升": "liter",
    "升": "liter",
    "l": "liter",
    "L": "liter",
}


def read_source(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        for encoding in ("utf-8-sig", "utf-8", "big5", "cp950"):
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(path)
    raise ValueError(f"Unsupported input format: {suffix}")


def pick_column(df: pd.DataFrame, canonical: str) -> Optional[str]:
    normalized = {str(col).strip().lower(): col for col in df.columns}
    for alias in COLUMN_ALIASES[canonical]:
        key = alias.strip().lower()
        if key in normalized:
            return normalized[key]
    return None


def require_column(df: pd.DataFrame, canonical: str) -> str:
    column = pick_column(df, canonical)
    if column is None:
        aliases = ", ".join(COLUMN_ALIASES[canonical])
        raise ValueError(f"Missing required column for {canonical}. Accepted names: {aliases}")
    return column


def clean_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def to_float(value) -> Optional[float]:
    if pd.isna(value):
        return None
    text = str(value).replace(",", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_unit(unit: str) -> str:
    text = clean_text(unit)
    return UNIT_MAPPING.get(text, UNIT_MAPPING.get(text.lower(), text))


def normalize_year(value) -> int:
    if pd.isna(value):
        return datetime.now().year
    text = str(value).strip()
    try:
        year = int(float(text))
    except ValueError:
        return datetime.now().year
    if year < 1911:
        return year + 1911
    return year


def normalize_moenv_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    name_col = require_column(raw_df, "name")
    factor_col = require_column(raw_df, "emission_factor")
    unit_col = require_column(raw_df, "unit")
    dept_col = pick_column(raw_df, "department")
    year_col = pick_column(raw_df, "year")

    records = []
    for _, row in raw_df.iterrows():
        name = clean_text(row.get(name_col))
        factor = to_float(row.get(factor_col))
        if not name or factor is None:
            continue

        unit_original = clean_text(row.get(unit_col))
        unit_standard = normalize_unit(unit_original)
        dept = clean_text(row.get(dept_col)) if dept_col else "環境部產品碳足跡資訊網"
        year = normalize_year(row.get(year_col)) if year_col else datetime.now().year

        records.append(
            {
                "name": name,
                "emission_factor": factor,
                "unit_standard": unit_standard,
                "unit_original": unit_original,
                "source": "MOENV CFP",
                "region": "TW",
                "category": "Taiwan Product Carbon Footprint",
                "base_year": year,
                "source_dept": dept,
                "tier": 1,
                "search_text": f"{name} {unit_standard} 台灣 環境部 產品碳足跡 {dept}",
            }
        )

    if not records:
        raise ValueError("No valid MOENV CFP records found after normalization.")

    return pd.DataFrame(records)


def merge_with_existing(existing_df: pd.DataFrame, moenv_df: pd.DataFrame, replace_moenv: bool) -> pd.DataFrame:
    if replace_moenv and "source" in existing_df.columns:
        existing_df = existing_df[existing_df["source"] != "MOENV CFP"].copy()

    existing_keys = set(
        zip(
            existing_df["name"].astype(str).str.strip().str.lower(),
            existing_df["unit_standard"].astype(str).str.strip().str.lower(),
            existing_df["source"].astype(str).str.strip().str.lower(),
        )
    )

    additions = []
    for _, row in moenv_df.iterrows():
        key = (
            str(row["name"]).strip().lower(),
            str(row["unit_standard"]).strip().lower(),
            str(row["source"]).strip().lower(),
        )
        if key not in existing_keys:
            additions.append(row)
            existing_keys.add(key)

    additions_df = pd.DataFrame(additions)
    if additions_df.empty:
        return existing_df.copy()

    return pd.concat([existing_df, additions_df], ignore_index=True)


def rebuild_embeddings(df: pd.DataFrame) -> None:
    engine = EmbeddingEngine(
        model_name="paraphrase-multilingual-MiniLM-L12-v2",
        device="auto",
    )
    embeddings = engine.encode(
        df["search_text"].fillna("").astype(str).tolist(),
        batch_size=64,
        show_progress=True,
        normalize=True,
    )
    np.save(EMBEDDINGS_FILE, embeddings)


def write_outputs(df: pd.DataFrame) -> None:
    df.to_csv(UNIFIED_FILE, index=False, encoding="utf-8-sig")
    df.drop(columns=["search_text"], errors="ignore").to_csv(
        METADATA_FILE,
        index=False,
        encoding="utf-8-sig",
    )


def write_status(input_path: Path, raw_count: int, normalized_count: int, total_count: int, embeddings_rebuilt: bool) -> None:
    status = {
        "source": "MOENV CFP",
        "source_url": "https://cfp.moenv.gov.tw/WebPage/WebSites/CoefficientDB.aspx",
        "input_file": str(input_path),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "raw_rows": int(raw_count),
        "normalized_rows": int(normalized_count),
        "tier1_total_rows": int(total_count),
        "embeddings_rebuilt": bool(embeddings_rebuilt),
        "note": "File-based import cache. Use official MOENV CFP export/download as input.",
    }
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update Tier 1 local cache with MOENV CFP factors.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="MOENV CFP CSV/XLSX export file. Default: data/emission_factors/tier1_local/碳足跡排放係數.csv",
    )
    parser.add_argument(
        "--replace-moenv",
        action="store_true",
        help="Replace previously imported MOENV CFP records before merging.",
    )
    parser.add_argument(
        "--no-embeddings",
        action="store_true",
        help="Only update CSV metadata; skip embedding rebuild.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and summarize the import without writing files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    print("=" * 80)
    print("MOENV CFP data update")
    print("=" * 80)
    print(f"Input: {input_path}")

    raw_df = read_source(input_path)
    moenv_df = normalize_moenv_df(raw_df)
    existing_df = pd.read_csv(UNIFIED_FILE, encoding="utf-8-sig")
    combined_df = merge_with_existing(existing_df, moenv_df, replace_moenv=args.replace_moenv)

    if args.dry_run:
        print(f"Raw rows: {len(raw_df):,}")
        print(f"Normalized rows: {len(moenv_df):,}")
        print(f"Existing Tier 1 rows: {len(existing_df):,}")
        print(f"Would write Tier 1 total rows: {len(combined_df):,}")
        print("Dry run only. No files were written.")
        return

    backup_path = TIER1_DIR / f"tier1_unified_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    existing_df.to_csv(backup_path, index=False, encoding="utf-8-sig")

    write_outputs(combined_df)

    embeddings_rebuilt = not args.no_embeddings
    if embeddings_rebuilt:
        rebuild_embeddings(combined_df)

    write_status(input_path, len(raw_df), len(moenv_df), len(combined_df), embeddings_rebuilt)

    print(f"Raw rows: {len(raw_df):,}")
    print(f"Normalized rows: {len(moenv_df):,}")
    print(f"Tier 1 total rows: {len(combined_df):,}")
    print(f"Backup: {backup_path}")
    print(f"Status: {STATUS_FILE}")
    print("Done.")


if __name__ == "__main__":
    main()
