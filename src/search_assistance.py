#!/usr/bin/env python3
"""
Two-stage assisted ranking for emission-factor search results.

The base retriever should search with the user's item text only. Optional
Scope 3 or Taiwan industry context is then used as a small reranking signal.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List


MAX_CONTEXT_BOOST = 0.08
BOOST_PER_MATCHED_TERM = 0.015


def _text(value) -> str:
    return "" if value is None else str(value)


def _candidate_text(match: Dict) -> str:
    fields = [
        match.get("name"),
        match.get("product_name"),
        match.get("category"),
        match.get("scope3_category"),
        match.get("source"),
        match.get("region"),
        match.get("country"),
        match.get("country_name"),
        match.get("unit"),
        match.get("unit_standard"),
    ]
    return " ".join(_text(value) for value in fields).lower()


def _terms(context_values: Iterable[str]) -> List[str]:
    raw = " ".join(_text(value) for value in context_values).lower()
    raw = re.sub(r"[，,、／/()（）:：;；\[\]{}|]+", " ", raw)
    terms = []
    seen = set()
    for term in raw.split():
        clean = term.strip()
        if len(clean) < 2 or clean in seen:
            continue
        seen.add(clean)
        terms.append(clean)
    return terms


def apply_context_rerank(
    matches: List[Dict],
    context_values: Iterable[str],
) -> List[Dict]:
    """
    Return matches sorted by original similarity plus a small context boost.

    The original similarity is preserved in ``original_similarity``. The score
    used for display/ranking remains capped at 1.0 and is written back to
    ``similarity`` so existing UI and export code keep working.
    """
    terms = _terms(context_values)
    if not terms:
        return [
            {
                **match,
                "original_similarity": match.get("original_similarity", match.get("similarity")),
                "context_boost": 0.0,
                "matched_context_terms": "",
                "assisted_rerank_applied": False,
            }
            for match in matches
        ]

    reranked = []
    for match in matches:
        candidate_text = _candidate_text(match)
        matched_terms = [term for term in terms if term in candidate_text]
        boost = min(MAX_CONTEXT_BOOST, len(matched_terms) * BOOST_PER_MATCHED_TERM)
        original_similarity = match.get("similarity") or 0.0
        assisted_score = min(1.0, float(original_similarity) + boost)
        reranked.append(
            {
                **match,
                "original_similarity": match.get("original_similarity", match.get("similarity")),
                "context_boost": boost,
                "matched_context_terms": ", ".join(matched_terms[:8]),
                "assisted_rerank_applied": True,
                "similarity": assisted_score,
            }
        )

    return sorted(
        reranked,
        key=lambda item: (item.get("similarity") or 0.0, item.get("original_similarity") or 0.0),
        reverse=True,
    )


def apply_context_to_result(result: Dict, context_values: Iterable[str]) -> Dict:
    if not result.get("success") or not result.get("matches"):
        return result

    updated = dict(result)
    updated["matches"] = apply_context_rerank(result["matches"], context_values)
    updated["best_match"] = updated["matches"][0] if updated["matches"] else None
    updated["assisted_rerank_applied"] = any(
        bool(match.get("assisted_rerank_applied")) for match in updated["matches"]
    )
    return updated
