"""CFP data quality handbook, third edition (2025-10), tables 2, 5 and 6."""

import math


INDICATORS = {"Re": "可靠性", "Co": "完整性", "Ti": "時間相關性", "Ge": "地理相關性", "Te": "技術相關性"}
SIDES = {"activity": "活動數據", "factor": "排放係數"}
BASIS = "環境部氣候變遷署《碳足跡數據品質評估手冊》第三版（114年10月），表2、表5、表6及公式(1)–(4)。"
PRODUCT_GRADES = {1: 1, 2: 1, 3: 1, 4: 2, 5: 2, 6: 3, 8: 3, 9: 3, 10: 4, 12: 4, 16: 4, 15: 5, 20: 5, 25: 5}


def present(value):
    return value is not None and str(value).strip().lower() not in {"", "nan", "none", "<na>"}


def grade(value):
    if isinstance(value, bool):
        raise ValueError("評級須為1至5的整數")
    number = float(value)
    if not math.isfinite(number) or number not in (1, 2, 3, 4, 5):
        raise ValueError("評級須為1至5的整數")
    return int(number)


def quality_level(score):
    if score is None:
        return "待評估"
    if not math.isfinite(score) or not 0 <= score <= 5:
        raise ValueError("DQR超出0至5範圍")
    return "高品質" if score <= 1.7 else "基本品質" if score <= 3 else "初估品質"


def evaluate_dqr(record):
    """Require ten matrix grades and their evidence; never infer from Tier/source."""
    rows, issues = [], []
    for code, label in INDICATORS.items():
        item = {"指標": label, "代碼": code}
        for side, title in SIDES.items():
            key = f"dqr_{side}_{code}"
            value = record.get(key)
            evidence = record.get(f"{key}_evidence")
            item[f"{title}依據"] = str(evidence).strip() if present(evidence) else ""
            item[title] = None
            if not present(value):
                issues.append(f"{title}／{label}缺少評級")
            else:
                try:
                    item[title] = grade(value)
                except (ValueError, TypeError, OverflowError):
                    issues.append(f"{title}／{label}評級須為1至5整數")
            if not present(evidence):
                issues.append(f"{title}／{label}缺少評估依據")
        product = item["活動數據"] * item["排放係數"] if all(item[s] is not None for s in SIDES.values()) else None
        item["指標乘積 DQRNi"] = product
        item["轉換等級 DQRi"] = PRODUCT_GRADES.get(product)
        rows.append(item)
    score = None
    if not issues:
        converted = [item["轉換等級 DQRi"] for item in rows]
        score = (sum(converted) + 5 * max(converted)) / 10
    return {"dqr_score": score, "data_quality_level": quality_level(score),
            "dqr_status": "已完成單項評估" if score is not None else "待評估",
            "dqr_missing": "；".join(issues), "dqr_basis": BASIS, "dqr_indicators": rows}


def dqr_export(record):
    result = evaluate_dqr(record)
    output = {k: v for k, v in result.items() if k != "dqr_indicators"}
    for side in SIDES:
        for code in INDICATORS:
            for suffix in ("", "_evidence"):
                key = f"dqr_{side}_{code}{suffix}"
                output[key] = record.get(key)
    for item in result["dqr_indicators"]:
        output[f'dqr_product_{item["代碼"]}'] = item["指標乘積 DQRNi"]
        output[f'dqr_grade_{item["代碼"]}'] = item["轉換等級 DQRi"]
    return output


def aggregate_dqr(records, total_emissions):
    """Use declared complete inventory total, not just successfully matched rows."""
    base = {"dqr_total": None, "data_quality_level": "待評估", "coverage": None, "dqr_basis": BASIS}
    try:
        total = float(total_emissions)
    except (TypeError, ValueError):
        total = float("nan")
    if not math.isfinite(total) or total <= 0:
        return {**base, "status": "需填寫完整盤查範圍的總排放量"}
    assessed, known, weighted = 0.0, 0.0, 0.0
    for record in records:
        value = record.get("calculated_co2e_kg")
        if not present(value):
            continue
        try:
            emissions = float(value)
        except (ValueError, TypeError):
            return {**base, "status": "排放量格式錯誤"}
        if not math.isfinite(emissions) or emissions < 0:
            return {**base, "status": "非有限或負排放量需另行確認權重方法"}
        known += emissions
        score = evaluate_dqr(record)["dqr_score"]
        if score is not None:
            assessed += emissions
            weighted += emissions * score
    if known > total + max(1e-9, total * 1e-9):
        return {**base, "status": "資料列排放量超過完整盤查總量，請確認重複列或盤查範圍"}
    coverage = assessed / total
    if coverage < 0.8 - 1e-12:
        return {**base, "coverage": coverage, "status": "已評估排放量未達80%，暫不給予整體品質等級"}
    score = weighted / assessed
    return {**base, "dqr_total": score, "data_quality_level": quality_level(score),
            "coverage": coverage, "status": "已完成整體評估"}
