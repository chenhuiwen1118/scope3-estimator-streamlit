import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from retrieval.tier1_local import Tier1LocalRetriever


@pytest.fixture(scope="module")
def retriever():
    return Tier1LocalRetriever()


@pytest.mark.parametrize("query", ["cement", "CEMENT", "purchase cement", "水泥"])
def test_cement_recalls_local_cement(retriever, query):
    results = retriever.search(query, top_k=3, threshold=0.8)
    assert results
    assert all(item["tier"] == 1 and "水泥" in item["name"] for item in results)
    assert all(not any(term in item["name"] for term in ("爐碴粉", "熟料", "砂漿")) for item in results)


def test_cross_language_semantic_match_not_penalized_for_script():
    retriever = Tier1LocalRetriever.__new__(Tier1LocalRetriever)
    result = retriever._rerank_with_query_terms(
        [{"name": "木材", "similarity": .85}], "timber"
    )[0]
    assert result["ranking_similarity"] == .85


def test_chinese_domain_conflict_still_penalized():
    retriever = Tier1LocalRetriever.__new__(Tier1LocalRetriever)
    result = retriever._rerank_with_query_terms(
        [{"name": "焦糖布丁", "similarity": .95}], "cement"
    )[0]
    assert result["ranking_similarity"] < .8
