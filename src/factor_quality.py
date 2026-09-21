"""Evidence-based factor suitability using handbook table 2, not total CFP DQR."""

from datetime import datetime
try:
    from data_quality import INDICATORS, present, grade
except ImportError:
    from .data_quality import INDICATORS, present, grade

BASIS = "依《碳足跡數據品質評估手冊》第三版（114年10月）表2五項標準評估係數適用性；非產品整體DQR。"


def assess_factor_quality(match, context=None):
    context = context or {}
    rows = []
    for code, label in INDICATORS.items():
        value, evidence = None, "未揭露足夠資料，需回原始來源確認。"
        key = f"dqr_factor_{code}"
        if present(match.get(key)) and present(match.get(key + "_evidence")):
            try:
                value, evidence = grade(match[key]), str(match[key + "_evidence"])
            except (ValueError, TypeError, OverflowError):
                evidence = "來源評級格式不符1–5級，需確認。"
        elif code == "Ti":
            year = match.get("base_year") or match.get("year") or match.get("matched_base_year")
            study_year = context.get("study_year", datetime.now().year)
            try:
                y, s = float(year), float(study_year)
                if not y.is_integer() or not s.is_integer() or not (1900 <= y <= s <= 2200):
                    raise ValueError()
                age = int(s - y)
                evidence = f"研究年度{s:.0f}，數據年度{y:.0f}，差距{age}年。"
                if "study_year" not in context:
                    evidence += "研究年度暫採本年度。"
                if age in {3, 6, 10, 15}:
                    evidence += "位於手冊文字與示例有歧義的邊界，需人工確認。"
                else:
                    value = 1 if age < 3 else 2 if age < 6 else 3 if age < 10 else 4 if age < 15 else 5
            except (TypeError, ValueError, OverflowError):
                evidence = "數據年度或研究年度缺漏／無效，需確認。"
        elif code == "Re":
            evidence = "需確認量測、假設、估算方法及查證紀錄；官方來源或Tier層級不等同已查證。"
        elif code == "Co":
            evidence = "需確認取樣場址、生產量涵蓋率、資料期間及代表性；欄位填寫完整不等同數據完整性。"
        elif code == "Ge":
            region = match.get("region") or match.get("country_name") or match.get("country") or match.get("geographic_scope")
            target = context.get("study_region", "台灣（預設）")
            evidence = f"係數地區：{region if present(region) else '未揭露'}；研究地區：{target}。需確認地域範圍與生產條件，不能僅以國別判定等級。"
        elif code == "Te":
            evidence = "需比對研究企業、製程、材料及技術；名稱相近或產業路由不足以證明技術一致。"
        rows.append({"code": code, "指標": label, "手冊評級": value,
                     "狀態": "待確認" if value is None else "條件相近" if value <= 2 else "需覆核" if value <= 4 else "適用性不足",
                     "判斷依據": evidence})
    missing = [r["指標"] for r in rows if r["手冊評級"] is None]
    weak = [r["指標"] for r in rows if r["手冊評級"] is not None and r["手冊評級"] >= 4]
    return {"factor_quality_criteria": rows, "factor_quality_missing": "、".join(missing),
            "factor_quality_weak": "、".join(weak),
            "data_quality_level": "存在適用性限制" if weak else "資料不足，需覆核" if missing else "五項證據已提供，仍需確認採購情境",
            "dqr_basis": BASIS}


def quality_export(assessment):
    result = {"data_quality_level": assessment["data_quality_level"], "dqr_basis": assessment["dqr_basis"],
              "factor_quality_missing": assessment["factor_quality_missing"], "factor_quality_weak": assessment["factor_quality_weak"]}
    for row in assessment["factor_quality_criteria"]:
        result[f'factor_quality_{row["code"]}_grade'] = row["手冊評級"]
        result[f'factor_quality_{row["code"]}_evidence'] = row["判斷依據"]
    return result
