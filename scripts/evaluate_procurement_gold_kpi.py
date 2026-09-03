#!/usr/bin/env python3
"""Evaluate item-level KPI using the anonymized procurement training list.

The training list is treated as the item-level main-pool gold standard. Because
the list defines procurement item classes rather than exact emission-factor IDs,
the evaluator uses controlled acceptable terms from each gold row:

- 標準品名
- 主要材料
- 排放係數匹配關鍵字
- 大類 / 子類

Top-3 Recall is counted as hit when any of the top 3 retrieved factors contains
an acceptable item/material/category term. First-choice F1 is computed as binary
correct/incorrect for the best ranked recommendation.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from procurement_reference import enrich_procurement_query
from retrieval.cascade_retriever import CascadeRetriever


TRAINING_FILE = PROJECT_ROOT / "data" / "reference_data" / "procurement_training_items.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "evaluation"
GOLD_POOL_FILE = OUTPUT_DIR / "procurement_item_gold_pool_75.csv"
RESULT_FILE = OUTPUT_DIR / "procurement_item_gold_kpi_results.csv"
SUMMARY_FILE = OUTPUT_DIR / "procurement_item_gold_kpi_summary.json"

ITEM_POOL_SIZE = 75
TOKEN_STOPWORDS = {
    "",
    "na",
    "n/a",
    "kg",
    "m",
    "mm",
    "cm",
    "pcs",
    "pc",
    "set",
    "lot",
    "範疇3",
    "類別1",
    "類別2",
    "原料",
    "材料",
    "耗材",
    "採購",
    "常用規格",
    "steel",
    "metal",
    "plastic",
    "rubber",
    "chemical",
}


def clean(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def normalize(text: str) -> str:
    text = clean(text).lower()
    text = re.sub(r"[\s,，、;；:：/\\|()（）\\[\\]{}<>《》\"'`]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_terms(*values: object) -> List[str]:
    terms: List[str] = []
    for value in values:
        text = clean(value)
        if not text:
            continue
        parts = re.split(r"[/,，、;；\s]+", text)
        for part in parts:
            part = normalize(part)
            if not part or part in TOKEN_STOPWORDS:
                continue
            if len(part) < 2 and not re.search(r"[\u4e00-\u9fff]", part):
                continue
            terms.append(part)
    return terms


def build_acceptable_terms(row: pd.Series) -> List[str]:
    standard = normalize(row.get("標準品名"))
    major = normalize(row.get("大類"))
    sub = normalize(row.get("子類"))
    material_terms = split_terms(row.get("主要材料"))
    keyword_terms = split_terms(row.get("排放係數匹配關鍵字"))

    terms = [standard, major, sub]
    terms.extend(material_terms)
    terms.extend(keyword_terms)

    # Add domain-level fallbacks. These make the evaluator suitable for item
    # classes where the factor database only has broader material or industry
    # coefficients.
    category_aliases = {
        "金屬原料": ["鋼", "鐵", "銅", "鋁", "steel", "iron", "copper", "aluminium", "aluminum"],
        "塑膠原料": ["塑膠", "樹脂", "plastic", "polyethylene", "polypropylene", "pet"],
        "包裝材料": ["紙箱", "紙", "包裝", "carton", "cardboard", "packaging"],
        "標準扣件": ["螺絲", "螺栓", "扣件", "fastener", "screw", "bolt"],
        "橡膠原料": ["橡膠", "rubber"],
        "化學與潤滑": ["化學", "潤滑", "油", "chemical", "lubricant", "oil"],
        "物流批發": ["運輸", "貨運", "配送", "transport", "freight", "distribution"],
        "工程廠務": ["工程", "營建", "construction", "renovation"],
        "電子材料": ["電子", "半導體", "晶片", "semiconductor", "electronic", "chip"],
        "模具與治具": ["模具", "治具", "金屬製品", "mold", "tooling", "fabricated metal"],
    }
    terms.extend(category_aliases.get(clean(row.get("大類")), []))

    seen = set()
    compacted = []
    for term in terms:
        term = normalize(term)
        if not term or term in TOKEN_STOPWORDS or term in seen:
            continue
        seen.add(term)
        compacted.append(term)
    return compacted


def match_text(result_match: Dict) -> str:
    fields = [
        result_match.get("name"),
        result_match.get("product_name"),
        result_match.get("category"),
        result_match.get("scope3_category"),
        result_match.get("source"),
        result_match.get("source_dept"),
        result_match.get("industry_code"),
        result_match.get("industry_label"),
        result_match.get("product_code"),
    ]
    return normalize(" ".join(clean(field) for field in fields if clean(field)))


def is_hit(result_match: Dict, acceptable_terms: Sequence[str]) -> Tuple[bool, str]:
    text = match_text(result_match)
    for term in acceptable_terms:
        if term and term in text:
            return True, term
    return False, ""


def build_gold_pool(training: pd.DataFrame, n: int = ITEM_POOL_SIZE) -> pd.DataFrame:
    unique = (
        training.sort_values(["大類", "標準品名", "Training ID"])
        .drop_duplicates(subset=["標準品名"], keep="first")
        .reset_index(drop=True)
    )
    if len(unique) <= n:
        return unique.copy()

    # Deterministic stratified sampling by major category.
    groups = {name: group.copy() for name, group in unique.groupby("大類", sort=True)}
    selected_indices: List[int] = []

    base = n // len(groups)
    remainder = n % len(groups)
    for idx, (name, group) in enumerate(groups.items()):
        take = min(len(group), base + (1 if idx < remainder else 0))
        selected_indices.extend(group.head(take).index.tolist())

    # If some groups were too small, top up from remaining standards.
    if len(selected_indices) < n:
        remaining = [idx for idx in unique.index.tolist() if idx not in selected_indices]
        selected_indices.extend(remaining[: n - len(selected_indices)])

    return unique.loc[selected_indices].sort_values(["大類", "標準品名"]).reset_index(drop=True)


def evaluate(args: argparse.Namespace) -> Dict:
    logging.disable(logging.CRITICAL)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    training = pd.read_csv(TRAINING_FILE)
    gold = build_gold_pool(training, n=args.n)
    gold.to_csv(GOLD_POOL_FILE, index=False, encoding="utf-8-sig")

    retriever = CascadeRetriever()
    rows = []
    top3_hits = 0
    first_hits = 0
    latencies = []

    for _, row in gold.iterrows():
        query = clean(row.get("原始採購品名")) or clean(row.get("標準品名"))
        enriched_query = enrich_procurement_query(query)
        acceptable_terms = build_acceptable_terms(row)

        started = time.perf_counter()
        result = retriever.search(
            query=enriched_query,
            top_k=3,
            tier1_threshold=args.tier1_threshold,
            tier2_threshold=args.tier2_threshold,
            tier3_threshold=args.tier3_threshold,
            country_priority="TW",
        )
        latency = time.perf_counter() - started
        latencies.append(latency)

        matches = result.get("matches") or []
        hit_terms = []
        top3_hit = False
        first_hit = False
        for rank, match in enumerate(matches[:3], start=1):
            hit, term = is_hit(match, acceptable_terms)
            if hit:
                top3_hit = True
                hit_terms.append(f"{rank}:{term}")
                if rank == 1:
                    first_hit = True

        top3_hits += int(top3_hit)
        first_hits += int(first_hit)

        best = matches[0] if matches else {}
        rows.append({
            "Training ID": row.get("Training ID"),
            "query": query,
            "standard_name": row.get("標準品名"),
            "major_category": row.get("大類"),
            "subcategory": row.get("子類"),
            "acceptable_terms": " | ".join(acceptable_terms),
            "top3_hit": top3_hit,
            "first_choice_hit": first_hit,
            "hit_terms": " | ".join(hit_terms),
            "result_success": result.get("success", False),
            "result_tier": result.get("tier"),
            "result_tier_name": result.get("tier_name"),
            "best_name": best.get("name") or best.get("product_name"),
            "best_source": best.get("source"),
            "best_similarity": best.get("similarity"),
            "latency_sec": latency,
        })

    detail = pd.DataFrame(rows)
    detail.to_csv(RESULT_FILE, index=False, encoding="utf-8-sig")

    total = len(detail)
    top3_recall = top3_hits / total if total else 0.0
    first_precision = first_hits / total if total else 0.0
    first_recall = first_hits / total if total else 0.0
    first_f1 = (
        2 * first_precision * first_recall / (first_precision + first_recall)
        if (first_precision + first_recall)
        else 0.0
    )

    summary = {
        "gold_standard": "匿名採購品名訓練清單 procurement_training_items.csv",
        "gold_pool_file": str(GOLD_POOL_FILE),
        "detail_file": str(RESULT_FILE),
        "n": total,
        "unique_standard_names_available": int(training["標準品名"].nunique()),
        "top3_hits": int(top3_hits),
        "top3_recall": round(top3_recall, 4),
        "first_choice_hits": int(first_hits),
        "first_choice_precision": round(first_precision, 4),
        "first_choice_recall": round(first_recall, 4),
        "first_choice_f1": round(first_f1, 4),
        "mean_latency_sec": round(float(detail["latency_sec"].mean()), 4),
        "p95_latency_sec": round(float(detail["latency_sec"].quantile(0.95)), 4),
        "targets": {
            "top3_recall": args.target_top3_recall,
            "first_choice_f1": args.target_first_f1,
        },
        "meets_targets": {
            "top3_recall": bool(top3_recall >= args.target_top3_recall),
            "first_choice_f1": bool(first_f1 > args.target_first_f1),
        },
        "notes": (
            "Gold labels are item-level procurement classes, not exact emission-factor IDs. "
            "A hit is counted when retrieved factor metadata contains controlled acceptable terms."
        ),
    }
    SUMMARY_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=ITEM_POOL_SIZE)
    parser.add_argument("--tier1-threshold", type=float, default=0.80)
    parser.add_argument("--tier2-threshold", type=float, default=0.70)
    parser.add_argument("--tier3-threshold", type=float, default=0.60)
    parser.add_argument("--target-top3-recall", type=float, default=0.85)
    parser.add_argument("--target-first-f1", type=float, default=0.70)
    args = parser.parse_args()
    print(json.dumps(evaluate(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
