#!/usr/bin/env python3
"""
Import Taiwan official Scope 3-relevant factors into Tier 1.

Supported source types:
- cca_ghg_management: MOENV/Climate Change Administration GHG factor tables
- moea_power: MOEA Energy Administration / Taipower annual electricity factors

The script is file-based: download/export the official CSV/XLSX, then import it
into Tier 1 and rebuild embeddings for offline retrieval.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple, Union

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.embedding import EmbeddingEngine


TIER1_DIR = PROJECT_ROOT / "data" / "emission_factors" / "tier1_local"
UNIFIED_FILE = TIER1_DIR / "tier1_unified.csv"
METADATA_FILE = TIER1_DIR / "tier1_metadata.csv"
EMBEDDINGS_FILE = TIER1_DIR / "tier1_embeddings.npy"
STATUS_FILE = TIER1_DIR / "tier1_official_sources_status.json"


SOURCE_CONFIGS = {
    "cca_ghg_management": {
        "source": "CCA GHG Factor Table",
        "category": "Taiwan GHG Inventory Factor",
        "source_dept": "環境部氣候變遷署",
        "source_url": "https://www.cca.gov.tw/",
        "default_scope3": "Scope 3 Category 3/4/5/6/7",
    },
    "moea_power": {
        "source": "MOEA/Taipower Electricity Factor",
        "category": "Taiwan Electricity Factor",
        "source_dept": "經濟部能源署/台電",
        "source_url": "https://www.moeaea.gov.tw/",
        "default_scope3": "Scope 3 Category 3",
    },
}


COLUMN_ALIASES: Dict[str, Iterable[str]] = {
    "name": [
        "name",
        "名稱",
        "項目",
        "排放源",
        "活動名稱",
        "係數名稱",
        "電力排碳係數名稱",
    ],
    "emission_factor": [
        "emission_factor",
        "co2e",
        "kgco2e",
        "kg CO2e",
        "排放係數",
        "係數",
        "數值",
        "電力排碳係數",
    ],
    "unit": [
        "unit",
        "單位",
        "係數單位",
        "活動數據單位",
        "排放係數單位",
    ],
    "department": ["department", "departmentname", "公告單位", "資料來源", "來源", "主管機關"],
    "year": ["year", "announcementyear", "年度", "年份", "基準年", "公告年度", "資料年度"],
    "category": ["category", "分類", "類別", "排放類型", "部門"],
    "description": ["description", "說明", "備註", "適用範圍"],
}


UNIT_MAPPING = {
    "公斤(kg)": "kg",
    "公斤": "kg",
    "kg": "kg",
    "公噸": "t",
    "噸": "t",
    "ton": "t",
    "tonne": "t",
    "公升(l)": "liter",
    "公升(L)": "liter",
    "公升": "liter",
    "升": "liter",
    "l": "liter",
    "L": "liter",
    "立方公尺(m3)": "m3",
    "立方公尺": "m3",
    "m3": "m3",
    "度(kwh)": "kWh",
    "度": "kWh",
    "kwh": "kWh",
    "kgco2e/kwh": "kWh",
    "kgco2e/度": "kWh",
    "延噸公里(tkm)": "tkm",
    "tkm": "tkm",
}


def read_source(path: Path) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".ods":
        return pd.read_excel(path, sheet_name=None, header=None)
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


def parse_factor_number(value) -> Tuple[Optional[float], str]:
    if pd.isna(value):
        return None, ""

    text = str(value).replace(",", "").strip()
    if not text or text.startswith("<"):
        return None, text

    text = (
        text.replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("～", "-")
        .replace("至", "-")
    )
    numbers = re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text)
    if not numbers:
        return None, text

    parsed = [float(number) for number in numbers]
    if len(parsed) >= 2 and "-" in text:
        return sum(parsed[:2]) / 2, f"原始範圍值：{value}"
    return parsed[0], f"原始值：{value}" if text != str(parsed[0]) else ""


def normalize_unit(unit: str, source_type: str) -> str:
    text = clean_text(unit)
    if source_type == "moea_power" and not text:
        return "kWh"
    return UNIT_MAPPING.get(text, UNIT_MAPPING.get(text.lower(), text or "unit"))


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


def _cca_record(name: str, factor: float, unit: str, category: str, description: str, year: int = 2024) -> Dict:
    config = SOURCE_CONFIGS["cca_ghg_management"]
    search_parts = [
        name,
        unit,
        category,
        description,
        "台灣",
        "環境部",
        "氣候變遷署",
        config["default_scope3"],
    ]
    return {
        "name": name,
        "emission_factor": factor,
        "unit_standard": unit,
        "unit_original": unit,
        "source": config["source"],
        "region": "TW",
        "category": category,
        "base_year": year,
        "source_dept": config["source_dept"],
        "tier": 1,
        "search_text": " ".join(part for part in search_parts if part),
    }


def _name_from_parts(parts: Iterable) -> str:
    cleaned = []
    for value in parts:
        text = clean_text(value)
        if not text:
            continue
        if text.startswith("註") or text in {"燃料", "英譯名稱", "產品", "製程", "類型"}:
            continue
        cleaned.append(text)
    return " / ".join(cleaned)


def _parse_fixed_combustion(df: pd.DataFrame) -> list:
    records = []
    for idx in range(8, len(df)):
        row = df.iloc[idx]
        name = _name_from_parts([row.get(0), row.get(1), row.get(2), row.get(3)])
        co2 = to_float(row.get(4))
        ch4 = to_float(row.get(5))
        n2o = to_float(row.get(6))
        if not name or co2 is None or ch4 is None or n2o is None:
            continue

        factor = co2 + ch4 * 28 + n2o * 265
        records.append(
            _cca_record(
                f"{name} 固定燃燒排放係數",
                factor,
                "TJ",
                "固定燃燒排放源",
                f"由公告 kg/TJ 係數換算為 kg CO2e/TJ：CO2={co2}, CH4={ch4}, N2O={n2o}, GWP 使用 CO2=1, CH4=28, N2O=265。",
            )
        )
    return records


def _parse_mobile_combustion(df: pd.DataFrame) -> list:
    records = []
    for idx in range(8, 15):
        if idx >= len(df):
            continue
        row = df.iloc[idx]
        name = _name_from_parts([row.get(0), row.get(1)])
        co2 = to_float(row.get(2))
        if name and co2 is not None:
            records.append(
                _cca_record(
                    f"{name} 移動燃燒 CO2 排放係數",
                    co2,
                    "TJ",
                    "移動燃燒排放源",
                    f"公告 CO2 係數，單位 kg CO2/TJ；作為 kg CO2e/TJ 使用。原始 CO2={co2}。",
                )
            )

    for idx in range(23, len(df)):
        row = df.iloc[idx]
        name = _name_from_parts([row.get(0), row.get(1)])
        ch4 = to_float(row.get(2))
        n2o = to_float(row.get(3))
        if not name or ch4 is None:
            continue
        n2o = n2o or 0.0
        factor = ch4 * 28 + n2o * 265
        records.append(
            _cca_record(
                f"{name} 移動燃燒 CH4/N2O 排放係數",
                factor,
                "TJ",
                "移動燃燒排放源",
                f"由公告 kg/TJ 係數換算為 kg CO2e/TJ：CH4={ch4}, N2O={n2o}, GWP 使用 CH4=28, N2O=265。",
            )
        )
    return records


def _unit_from_header(header: str) -> Tuple[str, float, bool]:
    text = header.replace(" ", "")
    if "溫暖化潛勢" in text:
        return "kg", 1.0, True
    if "%" in text or "比率" in text or "修正係數" in text or "氧化係數" in text:
        return "unit", 1.0, False
    if "公斤/公噸" in text:
        return "t", 1.0, True
    if "公噸/兆焦耳" in text:
        return "TJ", 1000.0, True
    if "公噸/公噸" in text or "公噸CO2/公噸" in text or "公噸CO2e/公噸" in text:
        return "t", 1000.0, True
    if "公斤CH4/公斤" in text:
        return "kg", 28.0, True
    if "CO2" in text and "排放係數" in text:
        return "t", 1000.0, True
    return "unit", 1.0, False


def _parse_generic_cca_tables(sheet_name: str, df: pd.DataFrame) -> list:
    records = []
    section = sheet_name
    factor_columns = []

    for _, row in df.iterrows():
        values = [clean_text(value) for value in row.tolist()]
        non_empty = [value for value in values if value]
        if not non_empty:
            continue

        if len(non_empty) == 1 and not re.search(r"\d", non_empty[0]):
            section = non_empty[0]
            continue

        header_columns = []
        for col_idx, text in enumerate(values):
            if not text:
                continue
            unit, multiplier, usable = _unit_from_header(text)
            if usable and any(token in text for token in ["排放係數", "CO2", "CH4", "溫暖化潛勢"]):
                header_columns.append((col_idx, text, unit, multiplier))
        if header_columns:
            factor_columns = header_columns
            continue

        for col_idx, header, unit, multiplier in factor_columns:
            if col_idx >= len(values):
                continue
            factor_value, note = parse_factor_number(values[col_idx])
            if factor_value is None:
                continue

            name = _name_from_parts(values[:col_idx])
            if not name or name.startswith("註") or len(name) < 2:
                continue

            category = f"{sheet_name} / {section}"
            records.append(
                _cca_record(
                    f"{name} {header}",
                    factor_value * multiplier,
                    unit,
                    category,
                    "；".join(part for part in [header, note] if part),
                )
            )
    return records


def normalize_cca_workbook(sheets: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    records = []
    for sheet_name, df in sheets.items():
        if sheet_name == "說明":
            continue
        if sheet_name == "附表一_固定燃燒排放源排放係數":
            records.extend(_parse_fixed_combustion(df))
            continue
        if sheet_name == "附表一_移動燃燒排放源排放係數":
            records.extend(_parse_mobile_combustion(df))
            continue
        records.extend(_parse_generic_cca_tables(sheet_name, df))

    if not records:
        raise ValueError("No valid CCA GHG factor records found after workbook parsing.")

    df = pd.DataFrame(records)
    return df.drop_duplicates(
        subset=["name", "unit_standard", "source", "base_year"],
        keep="first",
    ).reset_index(drop=True)


def raw_row_count(raw_df: Union[pd.DataFrame, Dict[str, pd.DataFrame]]) -> int:
    if isinstance(raw_df, dict):
        return sum(len(sheet_df) for sheet_df in raw_df.values())
    return len(raw_df)


def normalize_records(raw_df: Union[pd.DataFrame, Dict[str, pd.DataFrame]], source_type: str) -> pd.DataFrame:
    if isinstance(raw_df, dict):
        if source_type == "cca_ghg_management":
            return normalize_cca_workbook(raw_df)
        raw_df = next(iter(raw_df.values()))

    config = SOURCE_CONFIGS[source_type]
    name_col = require_column(raw_df, "name")
    factor_col = require_column(raw_df, "emission_factor")
    unit_col = pick_column(raw_df, "unit")
    year_col = pick_column(raw_df, "year")
    dept_col = pick_column(raw_df, "department")
    category_col = pick_column(raw_df, "category")
    description_col = pick_column(raw_df, "description")

    records = []
    for _, row in raw_df.iterrows():
        name = clean_text(row.get(name_col))
        factor = to_float(row.get(factor_col))
        if not name or factor is None:
            continue

        unit_original = clean_text(row.get(unit_col)) if unit_col else ""
        unit_standard = normalize_unit(unit_original, source_type)
        year = normalize_year(row.get(year_col)) if year_col else datetime.now().year
        dept = clean_text(row.get(dept_col)) if dept_col else config["source_dept"]
        category = clean_text(row.get(category_col)) if category_col else config["category"]
        description = clean_text(row.get(description_col)) if description_col else ""

        search_parts = [
            name,
            unit_standard,
            category,
            description,
            "台灣",
            config["source_dept"],
            config["default_scope3"],
        ]

        records.append(
            {
                "name": name,
                "emission_factor": factor,
                "unit_standard": unit_standard,
                "unit_original": unit_original or unit_standard,
                "source": config["source"],
                "region": "TW",
                "category": category,
                "base_year": year,
                "source_dept": dept,
                "tier": 1,
                "search_text": " ".join(part for part in search_parts if part),
            }
        )

    if not records:
        raise ValueError("No valid records found after normalization.")

    return pd.DataFrame(records)


def merge_with_existing(existing_df: pd.DataFrame, source_df: pd.DataFrame, source_type: str, replace_source: bool) -> pd.DataFrame:
    source_name = SOURCE_CONFIGS[source_type]["source"]
    if replace_source and "source" in existing_df.columns:
        existing_df = existing_df[existing_df["source"] != source_name].copy()

    existing_keys = set(
        zip(
            existing_df["name"].astype(str).str.strip().str.lower(),
            existing_df["unit_standard"].astype(str).str.strip().str.lower(),
            existing_df["source"].astype(str).str.strip().str.lower(),
            existing_df["base_year"].astype(str).str.strip().str.lower(),
        )
    )

    additions = []
    for _, row in source_df.iterrows():
        key = (
            str(row["name"]).strip().lower(),
            str(row["unit_standard"]).strip().lower(),
            str(row["source"]).strip().lower(),
            str(row["base_year"]).strip().lower(),
        )
        if key not in existing_keys:
            additions.append(row)
            existing_keys.add(key)

    if not additions:
        return existing_df.copy()

    return pd.concat([existing_df, pd.DataFrame(additions)], ignore_index=True)


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


def update_status(source_type: str, input_path: Path, raw_count: int, normalized_count: int, total_count: int, embeddings_rebuilt: bool) -> None:
    if STATUS_FILE.exists():
        try:
            status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            status = {}
    else:
        status = {}

    config = SOURCE_CONFIGS[source_type]
    status[source_type] = {
        "source": config["source"],
        "source_url": config["source_url"],
        "input_file": str(input_path),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "raw_rows": int(raw_count),
        "normalized_rows": int(normalized_count),
        "tier1_total_rows": int(total_count),
        "embeddings_rebuilt": bool(embeddings_rebuilt),
    }
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Taiwan official factors into Tier 1.")
    parser.add_argument(
        "--source-type",
        choices=sorted(SOURCE_CONFIGS.keys()),
        required=True,
        help="Official source type to import.",
    )
    parser.add_argument("--input", type=Path, required=True, help="CSV/XLSX file exported from official source.")
    parser.add_argument("--replace-source", action="store_true", help="Replace existing records from this source.")
    parser.add_argument("--no-embeddings", action="store_true", help="Skip embedding rebuild.")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    raw_df = read_source(input_path)
    source_df = normalize_records(raw_df, args.source_type)
    existing_df = pd.read_csv(UNIFIED_FILE, encoding="utf-8-sig")
    combined_df = merge_with_existing(
        existing_df,
        source_df,
        source_type=args.source_type,
        replace_source=args.replace_source,
    )

    print("=" * 80)
    print(f"Tier 1 official source import: {args.source_type}")
    print("=" * 80)
    print(f"Input: {input_path}")
    print(f"Raw rows: {raw_row_count(raw_df):,}")
    print(f"Normalized rows: {len(source_df):,}")
    print(f"Existing Tier 1 rows: {len(existing_df):,}")
    print(f"Output Tier 1 rows: {len(combined_df):,}")

    if args.dry_run:
        print("Dry run only. No files were written.")
        return

    backup_path = TIER1_DIR / f"tier1_unified_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    existing_df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    write_outputs(combined_df)

    embeddings_rebuilt = not args.no_embeddings
    if embeddings_rebuilt:
        rebuild_embeddings(combined_df)

    update_status(
        args.source_type,
        input_path,
        raw_count=raw_row_count(raw_df),
        normalized_count=len(source_df),
        total_count=len(combined_df),
        embeddings_rebuilt=embeddings_rebuilt,
    )

    print(f"Backup: {backup_path}")
    print(f"Status: {STATUS_FILE}")
    print("Done.")


if __name__ == "__main__":
    main()
