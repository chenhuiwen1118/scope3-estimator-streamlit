import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from name_matching import evaluate_name_compatibility
from retrieval.tier2_international import Tier2InternationalRetriever


def test_pencil_conflicts_with_generic_paper_product():
    result = evaluate_name_compatibility("鉛筆", "Paper and paper products")

    assert result["score"] <= 0.34
    assert result["status"] == "名稱不相符"


def test_pencil_accepts_non_paper_office_supplies():
    result = evaluate_name_compatibility(
        "鉛筆",
        "Office Supplies (except Paper) Manufacturing",
    )

    assert result["score"] >= 0.65


def test_tier2_controlled_mapping_returns_office_supplies_first():
    retriever = Tier2InternationalRetriever()
    results = retriever.search("鉛筆", top_k=3, threshold=0.70)

    assert results
    assert results[0]["name"] == "Office Supplies (except Paper) Manufacturing"
    assert results[0]["controlled_category_match"] is True
