import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from data_quality import aggregate_dqr, evaluate_dqr, quality_level, INDICATORS
from applicability_framework import evaluate_factor_applicability


def record(activity=(1, 1, 1, 1, 1), factor=(1, 1, 1, 1, 1), emissions=1):
    row = {"calculated_co2e_kg": emissions}
    for side, grades in [("activity", activity), ("factor", factor)]:
        for code, score in zip(INDICATORS, grades):
            row[f"dqr_{side}_{code}"] = score
            row[f"dqr_{side}_{code}_evidence"] = "手冊附錄測試案例"
    return row


@pytest.mark.parametrize("factor,expected", [((2, 1, 1, 1, 1), 1), ((1, 1, 2, 1, 1), 1), ((2, 1, 2, 3, 4), 1.6), ((2, 1, 4, 1, 1), 1.6)])
def test_handbook_examples(factor, expected):
    assert evaluate_dqr(record(factor=factor))["dqr_score"] == expected


def test_non_monotonic_conversion_table():
    fifteen = evaluate_dqr(record(activity=(3,)*5, factor=(5,)*5))
    sixteen = evaluate_dqr(record(activity=(4,)*5, factor=(4,)*5))
    assert fifteen["dqr_score"] == 5
    assert sixteen["dqr_score"] == 4


@pytest.mark.parametrize("value", [0, 6, 1.5, True, float("inf"), "wrong", None])
def test_invalid_grades_cannot_receive_quality_label(value):
    row = record()
    row["dqr_factor_Re"] = value
    assert evaluate_dqr(row)["dqr_score"] is None


def test_missing_evidence_is_pending():
    row = record()
    row.pop("dqr_factor_Re_evidence")
    assert evaluate_dqr(row)["data_quality_level"] == "待評估"


@pytest.mark.parametrize("score,expected", [(1.7, "高品質"), (1.700001, "基本品質"), (3, "基本品質"), (3.000001, "初估品質"), (5, "初估品質")])
def test_grade_boundaries(score, expected):
    assert quality_level(score) == expected


def test_aggregate_uses_total_inventory_and_80_percent_gate():
    rows = [record(emissions=79), {"calculated_co2e_kg": 21}]
    assert aggregate_dqr(rows, 100)["dqr_total"] is None
    rows[0]["calculated_co2e_kg"] = 80
    rows[1]["calculated_co2e_kg"] = 20
    assert aggregate_dqr(rows, 100)["dqr_total"] == 1
    assert aggregate_dqr(rows, 100)["coverage"] == .8
    assert aggregate_dqr(rows, None)["dqr_total"] is None
    assert aggregate_dqr(rows, 90)["dqr_total"] is None


def test_weighting_and_negative_emissions():
    rows = [record(emissions=60), record(factor=(2, 1, 2, 3, 4), emissions=20)]
    assert aggregate_dqr(rows, 100)["dqr_total"] == pytest.approx(1.15)
    rows.append(record(emissions=-5))
    assert aggregate_dqr(rows, 100)["dqr_total"] is None


def test_source_and_tier_do_not_invent_quality_evidence():
    match = {"name": "鉛筆", "source": "Taiwan EPA", "tier": 1, "similarity": .8}
    result = {"query": "鉛筆"}
    empty = evaluate_factor_applicability(match, result)
    complete = evaluate_factor_applicability({**match, **record()}, result)
    assert empty["data_quality_level"] == "資料不足，需覆核"
    assert "dqr_score" not in empty
    assert complete["factor_quality_missing"] == ""
    assert complete["final_score"] > empty["final_score"]
    assert not any(c["criterion"] == "Data quality and source" for c in empty["criteria"])


def test_handbook_weakness_changes_suitability():
    match = {"name": "鉛筆", "similarity": .98, "unit": "kg", **record(factor=(1, 1, 1, 1, 5))}
    assessed = evaluate_factor_applicability(match, {"query": "鉛筆"})
    assert assessed["decision"] == "不建議直接採用"
    assert assessed["final_score"] <= .49
    assert "技術相關性" in assessed["factor_quality_weak"]


def test_time_age_and_boundary_use_declared_study_year():
    from factor_quality import assess_factor_quality
    assessed = assess_factor_quality({"base_year": 2024}, {"study_year": 2026})
    assert assessed["factor_quality_criteria"][2]["手冊評級"] == 1
    boundary = assess_factor_quality({"base_year": 2023}, {"study_year": 2026})
    assert boundary["factor_quality_criteria"][2]["手冊評級"] is None
