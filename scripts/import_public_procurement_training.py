#!/usr/bin/env python3
"""Import the public procurement training workbook into reference CSV format."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference_data"
TARGET_FILE = REFERENCE_DIR / "procurement_training_items.csv"
SOURCE_COPY_FILE = REFERENCE_DIR / "procurement_training_source_public.xlsx"
AUDIT_FILE = REFERENCE_DIR / "procurement_training_public_audit.csv"
SOURCE_SHEET = "訓練用去識別版"
AUDIT_SHEET = "公開來源稽核表"

DEFAULT_SOURCE = Path(
    "/Users/sashachen/Documents/Codex/2026-08-14/"
    "referenced-chatgpt-conversation-this-is-an-2/outputs/procurement_training/"
    "匿名採購品名訓練清單_真實公開資料版.xlsx"
)

OUTPUT_COLUMNS = [
    "Training ID",
    "原始採購品名",
    "標準品名",
    "大類",
    "子類",
    "資料型態",
    "主要材料",
    "建議規格欄位",
    "常用單位",
    "Scope 3候選類別",
    "排放係數匹配關鍵字",
    "資料品質",
    "訓練備註",
    "適用產業",
]


def clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def join_terms(*values: object) -> str:
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = clean(value)
        if not text:
            continue
        for part in text.replace(";", "／").replace(",", "／").replace("，", "／").split("／"):
            part = clean(part)
            key = part.lower()
            if part and key not in seen:
                seen.add(key)
                terms.append(part)
    return " / ".join(terms)


def import_workbook(source: Path) -> dict:
    if not source.exists():
        raise FileNotFoundError(f"找不到來源檔案: {source}")

    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_excel(source, sheet_name=SOURCE_SHEET)
    required = {
        "Training ID",
        "原始採購品名",
        "標準品名候選",
        "官方財物次分類",
        "產業分類候選",
        "採購品類候選",
        "Scope 3候選",
        "來源紀錄ID",
        "資料狀態",
        "人工覆核註記",
    }
    missing = sorted(required - set(raw.columns))
    if missing:
        raise ValueError(f"{SOURCE_SHEET} 缺少必要欄位: {missing}")

    converted = pd.DataFrame()
    converted["Training ID"] = raw["Training ID"].map(clean)
    converted["原始採購品名"] = raw["原始採購品名"].map(clean)
    converted["標準品名"] = raw["標準品名候選"].map(clean)
    converted["大類"] = raw["採購品類候選"].map(clean)
    converted["子類"] = raw["官方財物次分類"].map(clean)
    converted["資料型態"] = "公開決標採購品名"
    converted["主要材料"] = raw["官方財物次分類"].map(clean)
    converted["建議規格欄位"] = "採購名稱／官方財物次分類／產業分類／Scope 3候選"
    converted["常用單位"] = ""
    converted["Scope 3候選類別"] = raw["Scope 3候選"].map(clean)
    converted["排放係數匹配關鍵字"] = raw.apply(
        lambda row: join_terms(
            row.get("標準品名候選"),
            row.get("官方財物次分類"),
            row.get("產業分類候選"),
            row.get("採購品類候選"),
            row.get("Scope 3候選"),
        ),
        axis=1,
    )
    converted["資料品質"] = "公開資料候選，需人工覆核"
    converted["訓練備註"] = raw.apply(
        lambda row: "；".join(
            part
            for part in [
                f"來源紀錄ID={clean(row.get('來源紀錄ID'))}",
                clean(row.get("資料狀態")),
                clean(row.get("人工覆核註記")),
            ]
            if part
        ),
        axis=1,
    )
    converted["適用產業"] = raw["產業分類候選"].map(clean)
    converted = converted[OUTPUT_COLUMNS]

    before = len(converted)
    converted = (
        converted.drop_duplicates(
            subset=["原始採購品名", "標準品名", "子類", "適用產業"],
            keep="first",
        )
        .reset_index(drop=True)
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = None
    if TARGET_FILE.exists():
        backup_file = REFERENCE_DIR / f"procurement_training_items.backup_{timestamp}.csv"
        shutil.copy2(TARGET_FILE, backup_file)

    converted.to_csv(TARGET_FILE, index=False, encoding="utf-8-sig")
    shutil.copy2(source, SOURCE_COPY_FILE)

    audit = pd.read_excel(source, sheet_name=AUDIT_SHEET)
    audit.to_csv(AUDIT_FILE, index=False, encoding="utf-8-sig")

    return {
        "source": str(source),
        "target": str(TARGET_FILE),
        "source_copy": str(SOURCE_COPY_FILE),
        "audit_file": str(AUDIT_FILE),
        "backup_file": str(backup_file) if backup_file else "",
        "source_rows": int(before),
        "imported_rows": int(len(converted)),
        "duplicate_rows_removed": int(before - len(converted)),
        "unique_standard_names": int(converted["標準品名"].nunique()),
        "major_categories": int(converted["大類"].nunique()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    result = import_workbook(args.source)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
