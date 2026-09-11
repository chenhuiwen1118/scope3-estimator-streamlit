"""Name compatibility scoring for procurement items and factor names."""

from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Dict, Iterable, List, Set


GENERIC_TERMS = {
    "採購", "購買", "費", "費用", "服務", "材料", "產品", "品項", "項目", "用品",
    "排放", "係數", "碳足跡", "範疇", "category", "scope", "item", "product",
    "service", "material", "purchase", "procurement", "fee", "cost",
}

MATERIAL_GROUPS = {
    "paper_packaging": {"紙箱", "瓦楞", "紙盒", "紙板", "紙容器", "紙包材", "carton", "cardboard", "corrugated"},
    "computer_equipment": {"筆記型電腦", "筆電", "電腦", "伺服器", "螢幕", "laptop", "computer", "server", "monitor"},
    "electronic_component": {"電子零組件", "晶片", "半導體", "二極體", "發光二極體", "pcb", "ic", "mcu", "semiconductor", "chip", "diode"},
    "lighting_product": {"燈泡", "燈管", "照明", "lightbulb", "light bulb", "lighting", "lamp"},
    "mineral": {"石灰", "石灰粉", "石灰石", "生石灰", "熟石灰", "碳酸鈣", "水泥", "礦物", "lime", "limestone", "cement"},
    "metal": {"鋼", "鐵", "鋁", "銅", "不鏽鋼", "合金", "金屬", "steel", "iron", "aluminum", "aluminium", "copper", "metal"},
    "plastic": {"塑膠", "塑料", "樹脂", "pet", "pe", "pp", "pvc", "hdpe", "ldpe", "plastic", "resin"},
    "food": {"食品", "飲料", "牛奶", "雞蛋", "砂糖", "麵粉", "布丁", "蛋糕", "茶", "咖啡", "food", "beverage", "pudding"},
    "fuel_energy": {"電力", "柴油", "汽油", "天然氣", "燃料", "蒸汽", "kwh", "diesel", "gasoline", "naturalgas", "electricity"},
    "transport": {"運輸", "貨運", "物流", "宅配", "配送", "海運", "空運", "transport", "freight", "logistics", "delivery"},
    "construction": {"營建", "工程", "裝潢", "混凝土", "瀝青", "鋼筋", "construction", "renovation", "concrete", "asphalt"},
    "process_equipment": {"反應釜", "儲槽", "泵浦", "壓縮機", "鍋爐", "冷凍櫃", "設備", "機械", "vessel", "reactor", "pump", "compressor", "boiler", "equipment", "machinery"},
    "wood": {"木材", "木板", "木製", "木料", "wood", "timber", "poplar"},
}

COMPATIBLE_GROUPS = {
    frozenset({"metal", "process_equipment"}),
    frozenset({"computer_equipment", "electronic_component"}),
}


def _normalize(text: object) -> str:
    text = "" if text is None else str(text).lower()
    text = text.replace("co₂", "co2")
    return re.sub(r"\s+", " ", text).strip()


def _tokens(text: object) -> List[str]:
    normalized = _normalize(text)
    raw = re.split(r"[^0-9a-zA-Z\u4e00-\u9fff]+", normalized)
    tokens: List[str] = []
    seen = set()
    for token in raw:
        token = token.strip()
        if len(token) < 2 or token in GENERIC_TERMS or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _cjk_bigrams(text: object) -> Set[str]:
    chars = re.findall(r"[\u4e00-\u9fff]", _normalize(text))
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def _groups(text: object) -> Set[str]:
    normalized_raw = _normalize(text)
    normalized = normalized_raw.replace(" ", "")
    token_set = {token.lower() for token in re.split(r"[^0-9a-zA-Z\u4e00-\u9fff]+", normalized_raw) if token}
    found = set()
    for group, terms in MATERIAL_GROUPS.items():
        for term in terms:
            term_lower = term.lower()
            term_norm = term_lower.replace(" ", "")
            if re.fullmatch(r"[a-z0-9]{1,3}", term_lower):
                matched = term_lower in token_set
            elif " " in term:
                matched = term.lower() in normalized_raw
            else:
                matched = term_norm in normalized
            if matched:
                found.add(group)
                break
    return found


def _groups_are_compatible(query_groups: Set[str], candidate_groups: Set[str]) -> bool:
    if query_groups & candidate_groups:
        return True
    for pair in COMPATIBLE_GROUPS:
        if query_groups & pair and candidate_groups & pair:
            return True
    return False


def _overlap_score(query_tokens: Iterable[str], candidate_text: str) -> float:
    tokens = list(query_tokens)
    if not tokens:
        return 0.0
    candidate = _normalize(candidate_text)
    hits = sum(1 for token in tokens if token.lower() in candidate)
    return hits / len(tokens)


def evaluate_name_compatibility(query_name: object, candidate_name: object) -> Dict:
    """Score whether a factor name describes the same product/activity as the query."""
    query = _normalize(query_name)
    candidate = _normalize(candidate_name)
    if not query or not candidate:
        return {
            "score": 0.45,
            "status": "名稱不足",
            "matched_terms": "",
            "conflict_groups": "",
            "evidence": "缺少採購品名或係數名稱，需人工確認。",
        }

    query_compact = query.replace(" ", "")
    candidate_compact = candidate.replace(" ", "")
    query_tokens = _tokens(query)
    candidate_tokens = _tokens(candidate)
    query_groups = _groups(query)
    candidate_groups = _groups(candidate)

    exact_or_contains = query_compact == candidate_compact or query_compact in candidate_compact or candidate_compact in query_compact
    token_score = _overlap_score(query_tokens, candidate)
    q_bigrams = _cjk_bigrams(query)
    c_bigrams = _cjk_bigrams(candidate)
    bigram_score = len(q_bigrams & c_bigrams) / len(q_bigrams) if q_bigrams else 0.0
    sequence_score = SequenceMatcher(None, query_compact, candidate_compact).ratio()

    group_bonus = 0.0
    group_penalty = 0.0
    conflict_groups = sorted(query_groups ^ candidate_groups)
    groups_compatible = bool(query_groups and candidate_groups and _groups_are_compatible(query_groups, candidate_groups))
    if query_groups and candidate_groups:
        if groups_compatible:
            group_bonus = 0.16
        else:
            group_penalty = 0.48

    score = max(token_score, bigram_score, sequence_score * 0.75)
    if exact_or_contains:
        score = max(score, 0.92)
    score = max(0.0, min(1.0, score + group_bonus - group_penalty))
    if groups_compatible:
        score = max(score, 0.66)

    if query_groups and candidate_groups and not _groups_are_compatible(query_groups, candidate_groups):
        score = min(score, 0.34)
    elif query_groups and not candidate_groups and score < 0.55:
        score = min(score, 0.42)

    if score >= 0.82:
        status = "名稱高度相符"
    elif score >= 0.65:
        status = "名稱可接受"
    elif score >= 0.45:
        status = "名稱需覆核"
    else:
        status = "名稱不相符"

    matched_terms = [token for token in query_tokens if token.lower() in candidate]
    evidence = (
        f"採購品名「{query_name}」與係數名稱「{candidate_name}」比對；"
        f"命中詞：{', '.join(matched_terms[:8]) or '無'}。"
    )
    if group_penalty:
        evidence += " 判定為不同材料/活動群，已降低排序。"

    return {
        "score": round(score, 2),
        "status": status,
        "matched_terms": ", ".join(matched_terms[:8]),
        "conflict_groups": ", ".join(conflict_groups) if group_penalty else "",
        "evidence": evidence,
    }
