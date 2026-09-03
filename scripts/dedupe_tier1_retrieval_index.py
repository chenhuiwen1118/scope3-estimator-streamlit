#!/usr/bin/env python3
"""
Build a de-duplicated Tier 1 retrieval index without deleting source records.

Rows are merged only when name, unit, and emission factor are the same. Rows
with the same name and unit but different factors are retained for review.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TIER1_DIR = PROJECT_ROOT / "data" / "emission_factors" / "tier1_local"
UNIFIED_FILE = TIER1_DIR / "tier1_unified.csv"
EMBEDDINGS_FILE = TIER1_DIR / "tier1_embeddings.npy"
DEDUPED_UNIFIED_FILE = TIER1_DIR / "tier1_unified_deduped.csv"
DEDUPED_METADATA_FILE = TIER1_DIR / "tier1_metadata_deduped.csv"
DEDUPED_EMBEDDINGS_FILE = TIER1_DIR / "tier1_embeddings_deduped.npy"
REPORT_FILE = TIER1_DIR / "tier1_deduplication_report.csv"

SOURCE_PRIORITY = {
    "Taiwan EPA": 4,
    "CCA GHG Factor Table": 4,
    "Taiwan EPA/MOE": 3,
    "MOENV CFP": 2,
}


def norm_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def main() -> None:
    df = pd.read_csv(UNIFIED_FILE)
    embeddings = np.load(EMBEDDINGS_FILE)
    if len(df) != len(embeddings):
        raise ValueError(
            f"Row count mismatch: {UNIFIED_FILE.name} has {len(df)} rows, "
            f"{EMBEDDINGS_FILE.name} has {len(embeddings)} vectors."
        )

    work = df.copy()
    work["_original_index"] = range(len(work))
    work["_name_key"] = work["name"].map(norm_text)
    work["_unit_key"] = work["unit_standard"].map(norm_text).str.lower()
    work["_factor_key"] = pd.to_numeric(work["emission_factor"], errors="coerce").round(10)
    work["_source_priority"] = work["source"].map(SOURCE_PRIORITY).fillna(0).astype(int)
    work["_year_sort"] = pd.to_numeric(work["base_year"], errors="coerce").fillna(0)

    grouped = work.groupby(["_name_key", "_unit_key", "_factor_key"], dropna=False)
    report = grouped.agg(
        duplicate_group_rows=("_original_index", "size"),
        duplicate_sources=("source", lambda s: " | ".join(sorted({norm_text(v) for v in s if norm_text(v)}))),
        duplicate_years=("base_year", lambda s: " | ".join(sorted({norm_text(v) for v in s if norm_text(v)}))),
        duplicate_source_depts=("source_dept", lambda s: " | ".join(sorted({norm_text(v) for v in s if norm_text(v)})[:12])),
    ).reset_index()

    report["duplicate_group_key"] = (
        report["_name_key"] + " | " + report["_unit_key"] + " | " + report["_factor_key"].astype(str)
    )

    chosen_indices = []
    group_meta = {}
    for key, group in grouped:
        ranked = group.sort_values(
            ["_source_priority", "_year_sort", "_original_index"],
            ascending=[False, False, True],
        )
        chosen = ranked.iloc[0]
        chosen_indices.append(int(chosen["_original_index"]))
        group_meta[int(chosen["_original_index"])] = {
            "duplicate_group_key": f"{key[0]} | {key[1]} | {key[2]}",
            "alternate_version_count": max(len(group) - 1, 0),
            "duplicate_sources": " | ".join(sorted({norm_text(v) for v in group["source"] if norm_text(v)})),
            "duplicate_years": " | ".join(sorted({norm_text(v) for v in group["base_year"] if norm_text(v)})),
            "dedupe_note": (
                "檢索索引已合併同名、同單位、同係數的重複列；原始資料仍保留於 tier1_unified.csv。"
                if len(group) > 1
                else ""
            ),
        }

    chosen_indices = sorted(chosen_indices)
    deduped = df.iloc[chosen_indices].copy()
    for column in [
        "duplicate_group_key",
        "alternate_version_count",
        "duplicate_sources",
        "duplicate_years",
        "dedupe_note",
    ]:
        deduped[column] = [group_meta[index][column] for index in chosen_indices]

    deduped_embeddings = embeddings[chosen_indices]
    deduped.to_csv(DEDUPED_UNIFIED_FILE, index=False, encoding="utf-8-sig")
    deduped.drop(columns=["search_text"]).to_csv(
        DEDUPED_METADATA_FILE,
        index=False,
        encoding="utf-8-sig",
    )
    np.save(DEDUPED_EMBEDDINGS_FILE, deduped_embeddings)
    report.sort_values("duplicate_group_rows", ascending=False).to_csv(
        REPORT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    duplicate_groups = int((report["duplicate_group_rows"] > 1).sum())
    removed = len(df) - len(deduped)
    ambiguous = (
        work.groupby(["_name_key", "_unit_key"], dropna=False)["_factor_key"]
        .nunique()
        .reset_index(name="factor_count")
    )
    ambiguous_count = int((ambiguous["factor_count"] > 1).sum())

    print(f"source_rows={len(df)}")
    print(f"deduped_rows={len(deduped)}")
    print(f"removed_from_retrieval_index={removed}")
    print(f"merged_duplicate_groups={duplicate_groups}")
    print(f"same_name_unit_multiple_factor_groups_retained={ambiguous_count}")
    print(f"wrote={DEDUPED_UNIFIED_FILE}")
    print(f"wrote={DEDUPED_METADATA_FILE}")
    print(f"wrote={DEDUPED_EMBEDDINGS_FILE}")
    print(f"wrote={REPORT_FILE}")


if __name__ == "__main__":
    main()
