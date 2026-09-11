#!/usr/bin/env python3
"""Calculate KPI against the established procurement gold standards.

Outputs:
- data/evaluation/system_kpi_summary.json
- data/evaluation/system_kpi_item_pool_results.csv
- data/evaluation/system_kpi_tender_pressure_results.csv
- data/evaluation/system_kpi_reviewed_batch_results.csv
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import re
import resource
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from procurement_reference import enrich_procurement_query
from retrieval.cascade_retriever import CascadeRetriever

EVALUATION_DIR = PROJECT_ROOT / "data" / "evaluation"
TRAINING_FILE = PROJECT_ROOT / "data" / "reference_data" / "procurement_training_items.csv"
REVIEWED_BATCH_FILE = (
    EVALUATION_DIR / "reviewed_batch_standard" / "reviewed_batch_gold_standard.csv"
)
SYNTHETIC_1000_FILE = PROJECT_ROOT / "data" / "synthetic" / "synthetic_procurement_zh_1000.csv"

SUMMARY_FILE = EVALUATION_DIR / "system_kpi_summary.json"
ITEM_POOL_RESULT_FILE = EVALUATION_DIR / "system_kpi_item_pool_results.csv"
PRESSURE_RESULT_FILE = EVALUATION_DIR / "system_kpi_tender_pressure_results.csv"
REVIEWED_BATCH_RESULT_FILE = EVALUATION_DIR / "system_kpi_reviewed_batch_results.csv"

TARGETS = {
    "item_pool_top3_recall": 0.85,
    "tender_pressure_top3_recall": 0.85,
    "first_choice_f1": 0.70,
    "single_query_latency_sec": 2.0,
    "batch_1000_sec": 7200.0,
    "memory_gb": 8.0,
}

TOKEN_STOPWORDS = {
    "",
    "na",
    "n/a",
    "kg",
    "t",
    "m",
    "mm",
    "cm",
    "pcs",
    "pc",
    "set",
    "lot",
    "unit",
    "範疇3",
    "類別1",
    "類別2",
    "原料",
    "材料",
    "耗材",
    "採購",
    "常用規格",
    "製造業",
    "業",
    "and",
    "of",
    "the",
    "n.e.c.",
}

CATEGORY_ALIASES = {
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


def clean(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def normalize(text: object) -> str:
    text = clean(text).lower()
    text = text.replace("co₂", "co2")
    text = re.sub(r"[\s,，、;；:：/\\|()（）\[\]{}<>《》\"'`]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def split_terms(*values: object) -> List[str]:
    terms: List[str] = []
    for value in values:
        for part in re.split(r"[/,，、;；／\s|]+", clean(value)):
            part = normalize(part)
            if not part or part in TOKEN_STOPWORDS:
                continue
            if len(part) < 2 and not re.search(r"[\u4e00-\u9fff]", part):
                continue
            terms.append(part)
    return terms


def compact_terms(terms: Iterable[str]) -> List[str]:
    seen = set()
    output = []
    for term in terms:
        term = normalize(term)
        if not term or term in TOKEN_STOPWORDS or term in seen:
            continue
        seen.add(term)
        output.append(term)
    return output


def item_gold_terms(row: pd.Series) -> List[str]:
    terms = [
        normalize(row.get("標準品名")),
        normalize(row.get("大類")),
        normalize(row.get("子類")),
    ]
    terms.extend(split_terms(row.get("主要材料"), row.get("排放係數匹配關鍵字")))
    terms.extend(CATEGORY_ALIASES.get(clean(row.get("大類")), []))
    return compact_terms(terms)


def result_text(match: Dict) -> str:
    fields = [
        match.get("name"),
        match.get("product_name"),
        match.get("category"),
        match.get("scope3_category"),
        match.get("source"),
        match.get("source_dept"),
        match.get("industry_code"),
        match.get("industry_label"),
        match.get("product_code"),
    ]
    return normalize(" ".join(clean(field) for field in fields if clean(field)))


def is_item_hit(match: Dict, acceptable_terms: Sequence[str]) -> Tuple[bool, str]:
    text = result_text(match)
    for term in acceptable_terms:
        if term and term in text:
            return True, term
    return False, ""


def build_item_pool(training: pd.DataFrame, n: int) -> pd.DataFrame:
    unique = (
        training.sort_values(["大類", "標準品名", "Training ID"])
        .drop_duplicates(subset=["標準品名"], keep="first")
        .reset_index(drop=True)
    )
    if len(unique) <= n:
        return unique.copy()

    groups = {name: group.copy() for name, group in unique.groupby("大類", sort=True)}
    selected_indices: List[int] = []
    base = n // len(groups)
    remainder = n % len(groups)
    for idx, (_, group) in enumerate(groups.items()):
        take = min(len(group), base + (1 if idx < remainder else 0))
        selected_indices.extend(group.head(take).index.tolist())
    if len(selected_indices) < n:
        remaining = [idx for idx in unique.index.tolist() if idx not in selected_indices]
        selected_indices.extend(remaining[: n - len(selected_indices)])
    return unique.loc[selected_indices].sort_values(["大類", "標準品名"]).reset_index(drop=True)


def build_pressure_pool(training: pd.DataFrame, n: int) -> pd.DataFrame:
    pool = training.sort_values(["大類", "標準品名", "Training ID"]).reset_index(drop=True)
    if len(pool) <= n:
        return pool.copy()
    groups = {name: group.copy() for name, group in pool.groupby("大類", sort=True)}
    selected_indices: List[int] = []
    base = n // len(groups)
    remainder = n % len(groups)
    for idx, (_, group) in enumerate(groups.items()):
        take = min(len(group), base + (1 if idx < remainder else 0))
        selected_indices.extend(group.head(take).index.tolist())
    if len(selected_indices) < n:
        remaining = [idx for idx in pool.index.tolist() if idx not in selected_indices]
        selected_indices.extend(remaining[: n - len(selected_indices)])
    return pool.loc[selected_indices].reset_index(drop=True)


def evaluate_item_rows(retriever: CascadeRetriever, rows: pd.DataFrame, output_file: Path) -> Dict:
    output_rows = []
    top3_hits = 0
    first_hits = 0
    latencies = []

    for _, row in rows.iterrows():
        query = clean(row.get("原始採購品名")) or clean(row.get("標準品名"))
        enriched_query = enrich_procurement_query(query)
        acceptable_terms = item_gold_terms(row)
        started = time.perf_counter()
        result = retriever.search(
            query=enriched_query,
            top_k=3,
            tier1_threshold=0.80,
            tier2_threshold=0.70,
            tier3_threshold=0.60,
            country_priority="TW",
        )
        latency = time.perf_counter() - started
        latencies.append(latency)
        matches = result.get("matches") or []

        top3_hit = False
        first_hit = False
        hit_terms = []
        for rank, match in enumerate(matches[:3], start=1):
            hit, term = is_item_hit(match, acceptable_terms)
            if hit:
                top3_hit = True
                hit_terms.append(f"{rank}:{term}")
                if rank == 1:
                    first_hit = True

        top3_hits += int(top3_hit)
        first_hits += int(first_hit)
        best = matches[0] if matches else {}
        output_rows.append({
            "training_id": row.get("Training ID"),
            "query": query,
            "standard_name": row.get("標準品名"),
            "major_category": row.get("大類"),
            "top3_hit": top3_hit,
            "first_choice_hit": first_hit,
            "hit_terms": " | ".join(hit_terms),
            "result_tier": result.get("tier"),
            "best_name": best.get("name") or best.get("product_name"),
            "best_source": best.get("source"),
            "best_similarity": best.get("similarity"),
            "latency_sec": latency,
        })

    detail = pd.DataFrame(output_rows)
    detail.to_csv(output_file, index=False, encoding="utf-8-sig")
    return metric_summary(detail, top3_hits, first_hits, latencies)


def expected_codes(text: str) -> List[str]:
    text = clean(text)
    codes = re.findall(r"\b[A-Z]-\d+(?:/\d+)?\b", text.upper())
    paren_codes = re.findall(r"\((\d{2,3}(?:/\d{2,3})?)\)", text)
    return compact_terms(codes + paren_codes)


def reviewed_expected_terms(row: pd.Series) -> List[str]:
    factor_name = clean(row.get("expected_factor_name"))
    terms = [normalize(factor_name)]
    terms.extend(expected_codes(factor_name))
    terms.extend(split_terms(factor_name))
    return compact_terms(terms)


def is_reviewed_hit(match: Dict, row: pd.Series) -> Tuple[bool, str]:
    text = result_text(match)
    match_codes = compact_terms(expected_codes(text) + [
        clean(match.get("industry_code")),
        clean(match.get("product_code")),
    ])
    for code in expected_codes(clean(row.get("expected_factor_name"))):
        if code and (code in text or code in match_codes):
            return True, code

    for term in reviewed_expected_terms(row):
        if len(term) < 3 and not re.search(r"[\u4e00-\u9fff]", term):
            continue
        if term and term in text:
            return True, term
    return False, ""


def evaluate_reviewed_batch(retriever: CascadeRetriever, rows: pd.DataFrame, output_file: Path) -> Dict:
    output_rows = []
    top3_hits = 0
    first_hits = 0
    latencies = []

    for _, row in rows.iterrows():
        query = clean(row.get("query"))
        started = time.perf_counter()
        result = retriever.search(
            query=enrich_procurement_query(query),
            top_k=3,
            tier1_threshold=0.80,
            tier2_threshold=0.70,
            tier3_threshold=0.60,
            country_priority="TW",
        )
        latency = time.perf_counter() - started
        latencies.append(latency)
        matches = result.get("matches") or []

        top3_hit = False
        first_hit = False
        hit_terms = []
        for rank, match in enumerate(matches[:3], start=1):
            hit, term = is_reviewed_hit(match, row)
            if hit:
                top3_hit = True
                hit_terms.append(f"{rank}:{term}")
                if rank == 1:
                    first_hit = True

        top3_hits += int(top3_hit)
        first_hits += int(first_hit)
        best = matches[0] if matches else {}
        output_rows.append({
            "standard_id": row.get("standard_id"),
            "query": query,
            "expected_tier_name": row.get("expected_tier_name"),
            "expected_factor_name": row.get("expected_factor_name"),
            "expected_scope3_category": row.get("expected_scope3_category"),
            "top3_hit": top3_hit,
            "first_choice_hit": first_hit,
            "hit_terms": " | ".join(hit_terms),
            "result_tier": result.get("tier"),
            "best_name": best.get("name") or best.get("product_name"),
            "best_source": best.get("source"),
            "best_similarity": best.get("similarity"),
            "latency_sec": latency,
        })

    detail = pd.DataFrame(output_rows)
    detail.to_csv(output_file, index=False, encoding="utf-8-sig")
    return metric_summary(detail, top3_hits, first_hits, latencies)


def metric_summary(detail: pd.DataFrame, top3_hits: int, first_hits: int, latencies: List[float]) -> Dict:
    total = len(detail)
    top3_recall = top3_hits / total if total else 0.0
    first_precision = first_hits / total if total else 0.0
    first_recall = first_hits / total if total else 0.0
    first_f1 = (
        2 * first_precision * first_recall / (first_precision + first_recall)
        if (first_precision + first_recall)
        else 0.0
    )
    return {
        "n": int(total),
        "top3_hits": int(top3_hits),
        "top3_recall": round(top3_recall, 4),
        "first_choice_hits": int(first_hits),
        "first_choice_precision": round(first_precision, 4),
        "first_choice_recall": round(first_recall, 4),
        "first_choice_f1": round(first_f1, 4),
        "mean_latency_sec": round(float(pd.Series(latencies).mean()), 4) if latencies else 0.0,
        "p95_latency_sec": round(float(pd.Series(latencies).quantile(0.95)), 4) if latencies else 0.0,
    }


def memory_gb() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return usage / (1024 ** 3)
    return usage / (1024 ** 2)


def benchmark_batch_1000(retriever: CascadeRetriever, n: int) -> Dict:
    if SYNTHETIC_1000_FILE.exists():
        df = pd.read_csv(SYNTHETIC_1000_FILE).head(n)
        query_column = "採購品名" if "採購品名" in df.columns else df.columns[0]
        queries = [clean(value) for value in df[query_column].tolist()]
    else:
        training = pd.read_csv(TRAINING_FILE)
        source = (training["原始採購品名"].fillna("").astype(str).tolist() * ((n // len(training)) + 1))
        queries = source[:n]

    started = time.perf_counter()
    for query in queries:
        retriever.search(
            query=enrich_procurement_query(query),
            top_k=3,
            tier1_threshold=0.80,
            tier2_threshold=0.70,
            tier3_threshold=0.60,
            country_priority="TW",
        )
    elapsed = time.perf_counter() - started
    return {
        "n": len(queries),
        "elapsed_sec": round(elapsed, 4),
        "estimated_hours": round(elapsed / 3600, 4),
        "mean_latency_sec": round(elapsed / len(queries), 4) if queries else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--item-n", type=int, default=75)
    parser.add_argument("--pressure-n", type=int, default=288)
    parser.add_argument("--batch-n", type=int, default=1000)
    parser.add_argument("--skip-reviewed-batch", action="store_true")
    parser.add_argument("--skip-batch-benchmark", action="store_true")
    args = parser.parse_args()

    logging.disable(logging.CRITICAL)
    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)

    initialized_at = time.perf_counter()
    retriever = CascadeRetriever()
    initialization_sec = time.perf_counter() - initialized_at

    training = pd.read_csv(TRAINING_FILE)
    item_pool = build_item_pool(training, args.item_n)
    pressure_pool = build_pressure_pool(training, args.pressure_n)

    item_metrics = evaluate_item_rows(retriever, item_pool, ITEM_POOL_RESULT_FILE)
    pressure_metrics = evaluate_item_rows(retriever, pressure_pool, PRESSURE_RESULT_FILE)

    reviewed_metrics = None
    if not args.skip_reviewed_batch and REVIEWED_BATCH_FILE.exists():
        reviewed = pd.read_csv(REVIEWED_BATCH_FILE)
        reviewed_metrics = evaluate_reviewed_batch(retriever, reviewed, REVIEWED_BATCH_RESULT_FILE)

    batch_benchmark = None
    if not args.skip_batch_benchmark:
        batch_benchmark = benchmark_batch_1000(retriever, args.batch_n)

    peak_memory_gb = round(memory_gb(), 4)
    summary = {
        "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "standards": {
            "item_pool": str(TRAINING_FILE),
            "reviewed_batch": str(REVIEWED_BATCH_FILE),
            "batch_benchmark_source": str(SYNTHETIC_1000_FILE),
        },
        "targets": TARGETS,
        "initialization_sec": round(initialization_sec, 4),
        "item_pool_top3_n75": item_metrics,
        "tender_language_pressure_n288": pressure_metrics,
        "reviewed_batch_standard": reviewed_metrics,
        "batch_1000_benchmark": batch_benchmark,
        "peak_memory_gb": peak_memory_gb,
        "meets_targets": {
            "item_pool_top3_recall": item_metrics["top3_recall"] >= TARGETS["item_pool_top3_recall"],
            "tender_pressure_top3_recall": pressure_metrics["top3_recall"] >= TARGETS["tender_pressure_top3_recall"],
            "first_choice_f1_item_pool": item_metrics["first_choice_f1"] > TARGETS["first_choice_f1"],
            "single_query_latency_item_pool_p95": item_metrics["p95_latency_sec"] < TARGETS["single_query_latency_sec"],
            "batch_1000": (
                batch_benchmark["elapsed_sec"] < TARGETS["batch_1000_sec"]
                if batch_benchmark else None
            ),
            "memory": peak_memory_gb < TARGETS["memory_gb"],
        },
        "notes": [
            "Item-pool hits use controlled acceptable terms from the anonymized procurement training list.",
            "Reviewed-batch hits compare expected factor names and EEIO industry codes against the current retriever output.",
            "The F1 score is computed as binary first-choice correctness over the evaluated rows.",
        ],
    }
    SUMMARY_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
