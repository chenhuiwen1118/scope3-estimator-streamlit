#!/usr/bin/env python3
"""
Scope 3 Estimator - Streamlit Web UI
三層級聯檢索系統的互動式介面
"""

import os
import sys
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from html import escape
import streamlit as st
import pandas as pd

MODEL_CACHE_DIR = (
    Path.home()
    / ".cache"
    / "huggingface"
    / "hub"
    / "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
)


def configure_model_mode():
    """Use offline mode when a local model cache exists; allow downloads on cloud."""
    requested_mode = os.environ.get("SCOPE3_MODEL_MODE", "auto").strip().lower()
    cloud_runtime = bool(
        os.environ.get("STREAMLIT_SHARING")
        or os.environ.get("STREAMLIT_CLOUD")
        or os.environ.get("IS_STREAMLIT_CLOUD")
    )

    if requested_mode in {"offline", "local"}:
        use_offline = True
    elif requested_mode in {"online", "cloud"}:
        use_offline = False
    else:
        use_offline = MODEL_CACHE_DIR.exists() and not cloud_runtime

    offline_value = "1" if use_offline else "0"
    os.environ.setdefault("HF_HUB_OFFLINE", offline_value)
    os.environ.setdefault("TRANSFORMERS_OFFLINE", offline_value)
    return use_offline


MODEL_OFFLINE_MODE = configure_model_mode()

# 加入 src 路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from retrieval.cascade_retriever import CascadeRetriever
from batch_processing import (
    BatchMatchConfig,
    process_batch_file,
    write_batch_results_excel,
)
from search_assistance import apply_context_to_result
from greenhouse_gas import infer_greenhouse_gas_category
from lifecycle_stage import infer_lifecycle_stage, infer_lifecycle_boundary
from applicability_framework import evaluate_factor_applicability
from factor_quality import quality_export
from procurement_reference import (
    enrich_procurement_query,
    load_procurement_training_items,
    load_procurement_synonyms,
)


PROJECT_ROOT = Path(__file__).parent
MOENV_CFP_STATUS_FILE = (
    PROJECT_ROOT
    / "data"
    / "emission_factors"
    / "tier1_local"
    / "moenv_cfp_update_status.json"
)
TIER1_OFFICIAL_SOURCES_STATUS_FILE = (
    PROJECT_ROOT
    / "data"
    / "emission_factors"
    / "tier1_local"
    / "tier1_official_sources_status.json"
)
SCOPE3_COEFFICIENT_NEEDS_FILE = (
    PROJECT_ROOT
    / "data"
    / "reference_data"
    / "scope3_coefficient_needs.json"
)
TIER1_UNIFIED_FILE = PROJECT_ROOT / "data" / "emission_factors" / "tier1_local" / "tier1_unified.csv"


SCOPE3_CATEGORY_OPTIONS = [
    {
        "label": "不指定／由系統判斷",
        "query_hint": "",
    },
    {
        "label": "類別 1：購買商品與服務",
        "query_hint": "Scope 3 Category 1 purchased goods and services 購買商品 服務 原料 零組件 耗材 鋼鐵 鋁 塑膠 橡膠 紙 紙箱 化學品 溶劑 食品 包材 外包服務",
    },
    {
        "label": "類別 2：資本財",
        "query_hint": "Scope 3 Category 2 capital goods 資本財 設備 機械 廠房 固定資產 電腦 伺服器 車輛 工程 建材 生產線",
    },
    {
        "label": "類別 3：燃料與能源相關活動",
        "query_hint": "Scope 3 Category 3 fuel and energy related activities 燃料 能源 電力 上游排放 汽油 柴油 天然氣 液化石油氣 燃料油",
    },
    {
        "label": "類別 4：上游運輸與配送",
        "query_hint": "Scope 3 Category 4 upstream transportation and distribution 上游運輸 配送 物流 貨運 倉儲 海運 空運 鐵路 冷鏈 快遞",
    },
    {
        "label": "類別 5：營運產生廢棄物",
        "query_hint": "Scope 3 Category 5 waste generated in operations 廢棄物 處理 回收 焚化 掩埋 污泥 廢塑膠 廢紙 廢金屬",
    },
    {
        "label": "類別 6：商務旅行",
        "query_hint": "Scope 3 Category 6 business travel 商務旅行 飛機 高鐵 住宿 差旅 航空 台鐵 捷運 計程車 租車",
    },
    {
        "label": "類別 7：員工通勤",
        "query_hint": "Scope 3 Category 7 employee commuting 員工通勤 捷運 公車 汽車 機車 台鐵 高鐵 人公里 車公里",
    },
    {
        "label": "類別 8：上游租賃資產",
        "query_hint": "Scope 3 Category 8 upstream leased assets 上游租賃資產 租用設備 租賃辦公室",
    },
    {
        "label": "類別 9：下游運輸與配送",
        "query_hint": "Scope 3 Category 9 downstream transportation and distribution 下游運輸 配送 出貨 物流",
    },
    {
        "label": "類別 10：銷售產品加工",
        "query_hint": "Scope 3 Category 10 processing of sold products 銷售產品加工 半成品 加工",
    },
    {
        "label": "類別 11：銷售產品使用",
        "query_hint": "Scope 3 Category 11 use of sold products 產品使用 用電 耗能 使用階段",
    },
    {
        "label": "類別 12：銷售產品最終處理",
        "query_hint": "Scope 3 Category 12 end-of-life treatment of sold products 最終處理 廢棄 回收",
    },
    {
        "label": "類別 13：下游租賃資產",
        "query_hint": "Scope 3 Category 13 downstream leased assets 下游租賃資產 出租設備 出租建物",
    },
    {
        "label": "類別 14：加盟",
        "query_hint": "Scope 3 Category 14 franchises 加盟 門市 營運",
    },
    {
        "label": "類別 15：投資",
        "query_hint": "Scope 3 Category 15 investments 投資 股權 債權 融資",
    },
]


TAIWAN_INDUSTRY_OPTIONS = [
    {
        "label": "不指定／由系統判斷",
        "query_hint": "",
    },
    {
        "label": "鋼鐵與金屬製品",
        "query_hint": "Taiwan industry steel iron metal products 鋼鐵 金屬製品 鋼材 鋁材 鑄造 加工",
    },
    {
        "label": "食品飲料製造",
        "query_hint": "Taiwan industry food and beverage manufacturing 食品 飲料 原料 加工 包裝",
    },
    {
        "label": "電子零組件與半導體",
        "query_hint": "Taiwan industry electronic components semiconductor 電子零組件 半導體 晶圓 IC PCB",
    },
    {
        "label": "電腦、電子產品與光學製品",
        "query_hint": "Taiwan industry computer electronic optical products 電腦 電子產品 光學 通訊設備",
    },
    {
        "label": "化學材料與化學製品",
        "query_hint": "Taiwan industry chemical materials chemical products 化學材料 化學品 溶劑 樹脂",
    },
    {
        "label": "塑膠與橡膠製品",
        "query_hint": "Taiwan industry plastic rubber products 塑膠 橡膠 塑膠製品 包材",
    },
    {
        "label": "紙漿、紙及紙製品",
        "query_hint": "Taiwan industry pulp paper paper products 紙漿 紙 紙箱 紙板 包裝",
    },
    {
        "label": "紡織與成衣",
        "query_hint": "Taiwan industry textile apparel fabric garment 紡織 布料 成衣 染整",
    },
    {
        "label": "機械設備製造",
        "query_hint": "Taiwan industry machinery equipment manufacturing 機械 設備 工具機 生產設備",
    },
    {
        "label": "電力及燃氣供應",
        "query_hint": "Taiwan industry electricity gas supply 電力 燃氣 蒸汽 能源供應",
    },
    {
        "label": "營建工程",
        "query_hint": "Taiwan industry construction engineering 營建 工程 建材 土木 建築",
    },
    {
        "label": "批發零售",
        "query_hint": "Taiwan industry wholesale retail 批發 零售 商品 通路 門市",
    },
    {
        "label": "運輸與倉儲",
        "query_hint": "Taiwan industry transportation warehousing logistics 運輸 倉儲 物流 貨運 配送",
    },
    {
        "label": "住宿與餐飲",
        "query_hint": "Taiwan industry accommodation food service hotel restaurant 住宿 餐飲 旅館 餐廳",
    },
    {
        "label": "資訊服務與專業服務",
        "query_hint": "Taiwan industry information professional services 資訊服務 軟體 顧問 專業服務",
    },
]


# 頁面設定
st.set_page_config(
    page_title="Scope 3 Estimator",
    page_icon="◎",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    :root {
        --surface: #ffffff;
        --surface-soft: #f7f4ee;
        --ink: #1f2a24;
        --muted: #687168;
        --line: #d8d2c6;
        --accent: #2f6f5e;
        --accent-deep: #173d35;
        --accent-gold: #b89b5e;
        --accent-soft: #edf3ef;
        --success-soft: #edf6ef;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(184, 155, 94, 0.12), transparent 32rem),
            linear-gradient(180deg, #fbfaf6 0%, #f5f7f3 46%, #ffffff 100%);
        color: var(--ink);
    }

    .block-container {
        max-width: 1180px;
        padding-top: 2.4rem;
        padding-bottom: 3rem;
    }

    section[data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(247, 244, 238, 0.92));
        border-right: 1px solid rgba(104, 113, 104, 0.22);
        backdrop-filter: blur(18px);
    }

    section[data-testid="stSidebar"]::before {
        content: "";
        display: block;
        height: 4px;
        background: linear-gradient(90deg, var(--accent-deep), var(--accent), var(--accent-gold));
        margin: 0 -1rem 1rem -1rem;
    }

    h1, h2, h3, [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {
        color: var(--ink);
        letter-spacing: 0;
    }

    .product-hero {
        position: relative;
        padding: 30px 0 30px 0;
        border-bottom: 1px solid var(--line);
        margin-bottom: 24px;
        overflow: hidden;
    }

    .eyebrow {
        color: var(--accent);
        font-size: clamp(1.05rem, 1.7vw, 1.42rem);
        font-weight: 760;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        margin-bottom: 14px;
    }

    .product-title {
        font-size: clamp(2.2rem, 5vw, 4.4rem);
        line-height: 1.03;
        font-weight: 760;
        letter-spacing: 0;
        margin: 0;
        color: var(--ink);
    }

    .product-subtitle {
        margin-top: 14px;
        color: var(--muted);
        font-size: clamp(1.02rem, 2vw, 1.28rem);
        line-height: 1.55;
        max-width: 760px;
    }

    .hero-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 18px;
    }

    .meta-pill {
        border: 1px solid rgba(47, 111, 94, 0.28);
        background: rgba(255, 255, 255, 0.72);
        border-radius: 999px;
        color: var(--accent-deep);
        padding: 7px 12px;
        font-size: 0.84rem;
        font-weight: 680;
        box-shadow: none;
    }

    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(104, 113, 104, 0.18);
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 10px 28px rgba(31, 42, 36, 0.06);
    }

    div[data-testid="stMetricLabel"] p {
        color: var(--muted);
        font-weight: 650;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid var(--line);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        color: var(--muted);
        font-weight: 650;
        padding: 12px 18px;
    }

    .stTabs [aria-selected="true"] {
        color: var(--ink);
        background: #ffffff;
        border: 1px solid var(--line);
        border-bottom-color: #ffffff;
    }

    div.stButton > button,
    div.stFormSubmitButton > button,
    div.stDownloadButton > button {
        border-radius: 8px;
        border: 1px solid #000000;
        background: #000000;
        color: #ffffff;
        font-weight: 700;
        min-height: 44px;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
    }

    div.stButton > button:hover,
    div.stFormSubmitButton > button:hover,
    div.stDownloadButton > button:hover {
        border-color: #000000;
        background: #000000;
        color: #ffffff;
    }

    div.stFormSubmitButton > button[kind="primary"],
    div.stFormSubmitButton > button[kind="primary"]:hover,
    div.stFormSubmitButton > button[kind="primary"]:focus {
        border-color: #000000;
        background: #000000;
        color: #ffffff;
    }

    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div,
    textarea {
        border-radius: 8px;
        border-color: var(--line);
        background-color: #ffffff;
    }

    [data-testid="stFileUploader"] {
        background: #ffffff;
        border: 1px dashed rgba(47, 111, 94, 0.38);
        border-radius: 8px;
        padding: 14px;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
    }

    .small-note {
        color: var(--muted);
        font-size: 0.92rem;
        line-height: 1.6;
    }

    .section-label {
        display: inline-flex;
        align-items: center;
        color: var(--accent-deep);
        background: rgba(237, 243, 239, 0.92);
        border: 1px solid rgba(47, 111, 94, 0.22);
        border-radius: 999px;
        padding: 5px 10px;
        font-size: 0.78rem;
        font-weight: 750;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }

    .detail-panel {
        border: 1px solid rgba(104, 113, 104, 0.18);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.82);
        padding: 16px 18px;
        margin: 8px 0 14px 0;
        box-shadow: 0 12px 30px rgba(31, 42, 36, 0.06);
    }

    .detail-title {
        color: var(--ink);
        font-size: 1rem;
        font-weight: 750;
        margin-bottom: 8px;
    }

    .detail-body {
        color: var(--muted);
        line-height: 1.65;
        font-size: 0.94rem;
    }

    .detail-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        margin-top: 12px;
    }

    .detail-item {
        border-top: 1px solid rgba(210, 210, 215, 0.72);
        padding-top: 10px;
    }

    .detail-label {
        color: var(--muted);
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 3px;
    }

    .detail-value {
        color: var(--ink);
        font-size: 0.94rem;
        line-height: 1.45;
        word-break: break-word;
    }

    @media (max-width: 720px) {
        .eyebrow {
            font-size: 1rem;
            line-height: 1.45;
        }

        .product-title {
            font-size: 2.05rem;
            line-height: 1.14;
        }

        .detail-grid {
            grid-template-columns: 1fr;
        }

    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<section class="product-hero">
    <div class="eyebrow">Scope 3 Estimator｜範疇三排放係數輔助系統</div>
    <h1 class="product-title">讓採購資料，<br/>快速轉成碳排洞察。</h1>
    <p class="product-subtitle">
        以台灣本地係數為優先，整合國際資料庫與 EEIO 模型。
        支援單筆查詢、批次配對與二氧化碳當量（CO2e）試算，協助盤查資料更快進入可判讀狀態。
    </p>
    <div class="hero-meta">
        <span class="meta-pill">離線模型 Offline</span>
        <span class="meta-pill">Excel / CSV 批次處理</span>
        <span class="meta-pill">CO2e 試算</span>
        <span class="meta-pill">三層級聯檢索</span>
    </div>
</section>
""", unsafe_allow_html=True)

model_mode_label = "本機離線模型" if MODEL_OFFLINE_MODE else "雲端線上模型"
st.caption(f"模型模式：{model_mode_label}")


# 初始化檢索器（使用 session_state 避免重複載入）
@st.cache_resource
def load_retriever():
    """載入檢索器（僅初始化一次）"""
    with st.spinner("🔧 初始化檢索系統..."):
        return CascadeRetriever()


def load_moenv_cfp_status():
    if not MOENV_CFP_STATUS_FILE.exists():
        return None
    try:
        return json.loads(MOENV_CFP_STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_tier1_official_sources_status():
    if not TIER1_OFFICIAL_SOURCES_STATUS_FILE.exists():
        return {}
    try:
        return json.loads(TIER1_OFFICIAL_SOURCES_STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_scope3_coefficient_needs():
    if not SCOPE3_COEFFICIENT_NEEDS_FILE.exists():
        return []
    try:
        data = json.loads(SCOPE3_COEFFICIENT_NEEDS_FILE.read_text(encoding="utf-8"))
        return data.get("categories", [])
    except Exception:
        return []


def _csv_record_count(path):
    if not path.exists():
        return None
    try:
        return max(sum(1 for _ in path.open("r", encoding="utf-8-sig")) - 1, 0)
    except Exception:
        return None


def _clean_detail_value(value):
    if value is None:
        return None
    if pd.isna(value) if not isinstance(value, (list, dict, tuple)) else False:
        return None
    text = str(value).strip()
    return text if text else None


def _match_name(match):
    return _clean_detail_value(match.get("name") or match.get("product_name") or match.get("matched_name"))


def _match_unit(match):
    return _clean_detail_value(match.get("unit") or match.get("unit_standard") or match.get("unit_original"))


def _match_source_label(match):
    source = _clean_detail_value(match.get("source") or match.get("matched_source"))
    source_dept = _clean_detail_value(match.get("source_dept") or match.get("matched_source_dept"))
    year = _clean_detail_value(match.get("base_year") or match.get("matched_base_year"))
    region = _clean_detail_value(
        match.get("region")
        or match.get("matched_region")
        or match.get("country_name")
        or match.get("country")
    )

    label_parts = [source]
    if source_dept and source_dept != source:
        label_parts.append(source_dept)
    label = " / ".join(part for part in label_parts if part)

    meta_parts = [part for part in [year, region] if part]
    if meta_parts:
        label = f"{label}（{'，'.join(meta_parts)}）" if label else "，".join(meta_parts)

    return label or "未標示來源"


def _format_factor(match):
    factor = match.get("emission_factor")
    unit = _match_unit(match)
    if factor is None:
        return "-"
    try:
        factor_text = f"{float(factor):,.4f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        factor_text = str(factor)

    if not unit:
        return f"{factor_text} kg CO2e"

    unit_lower = unit.lower()
    if "co2" in unit_lower or "co₂" in unit_lower:
        return f"{factor_text} {unit}"
    return f"{factor_text} kg CO2e/{unit}"


def _format_similarity(score):
    if score is None:
        return "-"
    try:
        return f"{float(score):.1%}"
    except (TypeError, ValueError):
        return str(score)


def _confidence_text(score):
    if score is None:
        return "未提供相似度"
    try:
        score = float(score)
    except (TypeError, ValueError):
        return "相似度格式無法判讀"
    if score >= 0.75:
        return "高信心：文字語意與資料庫項目接近，仍建議確認單位與適用邊界。"
    if score >= 0.60:
        return "中等信心：可作為初步估算，建議人工覆核名稱、單位與來源。"
    return "低信心：僅適合參考，建議改寫查詢或調整門檻後再比對。"


def _source_quality_text(tier):
    return {
        1: "Tier 1 台灣本地係數：優先採用，通常最適合台灣盤查情境。",
        2: "Tier 2 國際產業係數：可補足本地資料缺口，需留意地區與製程差異。",
        3: "Tier 3 EEIO 產業平均：適合採購金額型初估，不宜直接視為產品專屬係數。",
    }.get(tier, "資料層級未標示，建議回到原始來源確認。")


def _context_values(*selected_options):
    parts = []
    for option in selected_options:
        hint = option.get("query_hint", "")
        if hint:
            parts.extend([option["label"], hint])
    return parts


def _enrich_and_rerank_result(result, procurement_item_name=None):
    matches = result.get("matches") or []
    if not matches:
        return result

    if procurement_item_name:
        result["procurement_item_name"] = procurement_item_name

    enriched = []
    for match in matches:
        updated = dict(match)
        updated["lifecycle_stage"] = infer_lifecycle_stage(updated, result.get("tier"))
        updated["lifecycle_boundary"] = infer_lifecycle_boundary(updated, result.get("tier"))
        applicability = evaluate_factor_applicability(updated, result)
        updated["applicability_score"] = applicability["overall_score"]
        updated["final_score"] = applicability["final_score"]
        updated["confidence_level"] = applicability["confidence_level"]
        updated["suitability_decision"] = applicability["decision"]
        updated["suitability_watch_items"] = applicability["watch_items"]
        updated["data_quality_level"] = applicability.get("data_quality_level")
        updated["review_status"] = applicability.get("review_status")
        updated["auditability_note"] = applicability.get("auditability_note")
        updated["dqr_basis"] = applicability.get("dqr_basis")
        updated["name_match_score"] = applicability.get("name_match_score")
        updated["name_match_status"] = applicability.get("name_match_status")
        updated["name_match_evidence"] = applicability.get("name_match_evidence")
        updated["name_match_terms"] = applicability.get("name_match_terms")
        updated["name_match_conflicts"] = applicability.get("name_match_conflicts")
        updated["_applicability"] = applicability
        enriched.append(updated)

    enriched = sorted(
        enriched,
        key=lambda item: (
            item.get("final_score") or 0.0,
            item.get("similarity") or 0.0,
        ),
        reverse=True,
    )
    result["matches"] = enriched
    result["best_match"] = enriched[0]
    result["ranking_note"] = "已依語意相似度與係數適用性重新排序。"
    return result


def _detail_rows(match, result):
    location = _clean_detail_value(
        match.get("region")
        or " / ".join(
            part for part in [
                _clean_detail_value(match.get("country")),
                _clean_detail_value(match.get("country_name")),
            ]
            if part
        )
    )
    rows = [
        ("原始輸入", result.get("original_query") or result.get("query")),
        ("範疇三類別", result.get("scope3_category")),
        ("台灣產業類別", result.get("taiwan_industry")),
        ("主檢索文字", result.get("query")),
        ("輔助排序", result.get("assist_note")),
        ("匹配名稱", _match_name(match)),
        ("排放係數", _format_factor(match)),
        ("溫室氣體類別", infer_greenhouse_gas_category(match)),
        ("生命週期階段", match.get("lifecycle_stage") or infer_lifecycle_stage(match, result.get("tier"))),
        ("包含生命週期邊界", match.get("lifecycle_boundary") or infer_lifecycle_boundary(match, result.get("tier"))),
        ("相似度", _format_similarity(match.get("similarity"))),
        ("品名相容性", f"{match.get('name_match_status', '-')}（{_format_similarity(match.get('name_match_score'))}）"),
        ("品名判斷依據", match.get("name_match_evidence")),
        ("品名衝突群組", match.get("name_match_conflicts")),
        ("適用性判斷", match.get("suitability_decision")),
        ("需覆核項目", match.get("suitability_watch_items")),
        ("資料品質等級", match.get("data_quality_level")),
        ("審查/查驗狀態", match.get("review_status")),
        ("DQR 評估依據", match.get("dqr_basis")),
        ("可稽核性提示", match.get("auditability_note")),
        ("原始相似度", _format_similarity(match.get("original_similarity"))),
        ("輔助加分", _format_similarity(match.get("context_boost"))),
        ("命中輔助詞", match.get("matched_context_terms")),
        ("其他版本數", match.get("alternate_version_count")),
        ("版本選擇說明", match.get("version_selection_note")),
        ("資料層級", result.get("tier_name")),
        ("台灣行業代碼", match.get("industry_code")),
        ("台灣行業別", match.get("industry_label")),
        ("行業路由理由", match.get("route_reason")),
        ("係數來源", _match_source_label(match)),
        ("來源資料庫", match.get("source")),
        ("來源機關/單位", match.get("source_dept")),
        ("地區/國家", location),
        ("基準年度", match.get("base_year")),
        ("分類", match.get("category") or match.get("scope3_category")),
        ("產品代碼", match.get("product_code")),
        ("資料索引", match.get("index")),
    ]
    return [(label, _clean_detail_value(value)) for label, value in rows if _clean_detail_value(value)]


def render_match_details(match, result):
    rows = _detail_rows(match, result)
    row_map = dict(rows)
    tier = result.get("tier") or match.get("tier")
    name = row_map.get("匹配名稱", "-")
    user_query = result.get("original_query") or result.get("query", "")
    category_text = result.get("scope3_category") or "未指定範疇三類別"
    industry_text = result.get("taiwan_industry") or "未指定台灣產業類別"

    st.markdown(
        f"""
        <div class="detail-panel">
            <div class="detail-title">這筆結果代表什麼</div>
            <div class="detail-body">
                系統先以「{escape(str(user_query))}」進行主檢索，再以「{escape(str(category_text))}」與「{escape(str(industry_text))}」做小幅輔助排序，最接近
                <strong>{escape(name)}</strong>。
                建議先確認名稱是否符合實際採購內容，再確認排放係數單位是否能與活動數據或採購金額相乘。
            </div>
            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">推薦係數</div>
                    <div class="detail-value">{escape(row_map.get("排放係數", "-"))}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">檢索信心</div>
                    <div class="detail-value">{escape(row_map.get("相似度", "-"))}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">溫室氣體類別</div>
                    <div class="detail-value">{escape(str(row_map.get("溫室氣體類別", "-")))}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">資料層級</div>
                    <div class="detail-value">{escape(str(row_map.get("資料層級", "-")))}</div>
                </div>
                <div class="detail-item">
                    <div class="detail-label">係數來源</div>
                    <div class="detail-value">{escape(str(row_map.get("係數來源", "-")))}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(f"{_source_quality_text(tier)}\n\n{_confidence_text(match.get('similarity'))}")

    applicability = match.get("_applicability") or evaluate_factor_applicability(match, result)
    st.markdown("##### 適用性與資料品質")
    st.metric("適用性建議", applicability.get("decision", "-"))
    quality_items = applicability.get("factor_quality_criteria", [])
    quality_watch_items = [item["指標"] for item in quality_items if item["手冊評級"] is None or item["手冊評級"] >= 3]
    st.caption(f"需覆核項目：{'、'.join(quality_watch_items) or '無明顯低分項目'}")
    st.caption(f"資料品質：{applicability.get('data_quality_level', '-')}；{applicability.get('dqr_basis', '')}")
    st.caption("手冊評級為1–5級，越低越佳；缺乏佐證時標示待確認。以下為係數品質指標，並非產品整體DQR。")
    assessment_rows = []
    for item in quality_items:
        level = item["手冊評級"]
        assessment_rows.append({
            "評估項目": item["指標"],
            "手冊評級": f"第{level}級" if level is not None else "待確認",
            "狀態": item["狀態"],
            "判斷依據": item["判斷依據"],
        })
    st.dataframe(
        pd.DataFrame(assessment_rows),
        use_container_width=True,
        hide_index=True,
    )

    alternate_versions = match.get("alternate_versions") or []
    if alternate_versions:
        st.markdown("##### 其他版本")
        alternate_rows = []
        for item in alternate_versions[:20]:
            alternate_rows.append({
                "名稱": item.get("name") or item.get("product_name"),
                "係數": item.get("emission_factor"),
                "單位": item.get("unit") or item.get("unit_standard"),
                "來源": item.get("source"),
                "年度": item.get("base_year"),
                "相似度": _format_similarity(item.get("similarity")),
            })
        st.dataframe(
            pd.DataFrame(alternate_rows),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("##### 欄位摘要")
    st.dataframe(
        pd.DataFrame(rows, columns=["欄位", "內容"]),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("查看原始資料欄位"):
        st.json(match, expanded=False)


def _single_result_download_df(result):
    rows = []
    matches = result.get("matches") or []
    for rank, match in enumerate(matches, start=1):
        lifecycle_stage = match.get("lifecycle_stage") or infer_lifecycle_stage(match, result.get("tier"))
        lifecycle_boundary = match.get("lifecycle_boundary") or infer_lifecycle_boundary(match, result.get("tier"))
        applicability = match.get("_applicability") or evaluate_factor_applicability(
            {
                **match,
                "lifecycle_stage": lifecycle_stage,
                "lifecycle_boundary": lifecycle_boundary,
            },
            result,
        )
        rows.append({
            "rank": rank,
            "query": result.get("original_query") or result.get("query"),
            "enriched_query": result.get("query"),
            "scope3_category_context": result.get("scope3_category"),
            "taiwan_industry_context": result.get("taiwan_industry"),
            "tier": result.get("tier"),
            "tier_name": result.get("tier_name"),
            "factor_name": match.get("name") or match.get("product_name"),
            "emission_factor": match.get("emission_factor"),
            "unit": match.get("unit") or match.get("unit_standard"),
            "greenhouse_gas_category": infer_greenhouse_gas_category(match),
            "factor_source": _match_source_label(match),
            "source_database": match.get("source"),
            "source_dept": match.get("source_dept"),
            "region": match.get("region") or match.get("country_name") or match.get("country"),
            "base_year": match.get("base_year"),
            "lifecycle_stage": lifecycle_stage,
            "lifecycle_boundary": lifecycle_boundary,
            "similarity": match.get("similarity"),
            "name_match_score": applicability.get("name_match_score"),
            "name_match_status": applicability.get("name_match_status"),
            "name_match_evidence": applicability.get("name_match_evidence"),
            "name_match_terms": applicability.get("name_match_terms"),
            "name_match_conflicts": applicability.get("name_match_conflicts"),
            "original_similarity": match.get("original_similarity"),
            "context_boost": match.get("context_boost"),
            "applicability_score": applicability.get("overall_score"),
            "final_score": applicability.get("final_score"),
            "confidence_level": applicability.get("confidence_level"),
            "suitability_decision": applicability.get("decision"),
            "watch_items": applicability.get("watch_items"),
            "data_quality_level": applicability.get("data_quality_level"),
            "review_status": applicability.get("review_status"),
            "auditability_note": applicability.get("auditability_note"),
            **quality_export(applicability),
            "industry_code": match.get("industry_code"),
            "industry_label": match.get("industry_label"),
            "route_reason": match.get("route_reason"),
            "product_code": match.get("product_code"),
            "raw_match_json": json.dumps(match, ensure_ascii=False, default=str),
        })
    return pd.DataFrame(rows)


def _dataframe_to_xlsx_bytes(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="檢索結果", index=False)
    buffer.seek(0)
    return buffer.getvalue()


# 載入檢索器
try:
    retriever = load_retriever()
    st.sidebar.success("系統已就緒")
except Exception as e:
    st.error(f"初始化失敗：{e}")
    st.stop()


st.sidebar.header("系統資訊")
stats = retriever.get_stats()

if stats['tier1']:
    st.sidebar.metric(
        "Tier 1 去重檢索索引",
        f"{stats['tier1']['total_records']:,} 筆",
        help="實際用於搜尋配對的台灣本地係數索引；已合併同名、同單位、同係數的重複資料。"
    )
    raw_tier1_count = _csv_record_count(TIER1_UNIFIED_FILE)
    if raw_tier1_count and raw_tier1_count != stats['tier1']['total_records']:
        st.sidebar.caption(
            f"原始整合資料 {raw_tier1_count:,} 筆；檢索索引已去重。"
        )

if stats['tier2']:
    st.sidebar.metric(
        "Tier 2 (國際產業)",
        f"{stats['tier2']['total_records']:,} 筆",
        help="國際產業資料庫 (AGRIBALYSE, Idemat, etc)"
    )

if stats['tier3']:
    st.sidebar.metric(
        "Tier 3 (EEIO 模型)",
        f"{stats['tier3']['total_records']:,} 筆",
        help="EXIOBASE 多國 EEIO 模型"
    )

st.sidebar.divider()

st.sidebar.header("環境部 CFP 資料")
moenv_status = load_moenv_cfp_status()
if moenv_status:
    st.sidebar.caption(f"最後更新：{moenv_status.get('updated_at', '-')}")
    st.sidebar.metric(
        "原始整合資料",
        f"{int(moenv_status.get('tier1_total_rows', 0)):,} 筆",
        help="資料匯入後的原始 Tier 1 整合筆數；不等於實際檢索索引筆數。"
    )
    st.sidebar.caption("來源：環境部產品碳足跡資訊網本地快取")
else:
    st.sidebar.info("尚未執行環境部 CFP 匯入更新。")

st.sidebar.divider()

st.sidebar.header("官方 Tier 1 來源")
official_status = load_tier1_official_sources_status()
if official_status:
    for status in official_status.values():
        st.sidebar.caption(f"{status.get('source', '-')}")
        st.sidebar.caption(f"更新：{status.get('updated_at', '-')}")
        st.sidebar.caption(f"匯入：{int(status.get('normalized_rows', 0)):,} 筆")
        if status.get("tier1_total_rows"):
            st.sidebar.caption(
                f"原始整合後：{int(status.get('tier1_total_rows', 0)):,} 筆"
            )
else:
    st.sidebar.info("尚未匯入排放係數管理表或年度電力係數。")

st.sidebar.divider()

# 側邊欄 - 進階設定
st.sidebar.header("進階設定")

tier1_threshold = st.sidebar.slider(
    "Tier 1 門檻",
    min_value=0.0,
    max_value=1.0,
    value=0.80,
    step=0.05,
    help="Tier 1 相似度門檻（較高門檻確保本地資料品質）"
)

tier2_threshold = st.sidebar.slider(
    "Tier 2 門檻",
    min_value=0.0,
    max_value=1.0,
    value=0.70,
    step=0.05,
    help="Tier 2 相似度門檻"
)

tier3_threshold = st.sidebar.slider(
    "Tier 3 門檻",
    min_value=0.0,
    max_value=1.0,
    value=0.60,
    step=0.05,
    help="Tier 3 相似度門檻（較低門檻以提供備選方案）"
)

top_k = st.sidebar.number_input(
    "顯示結果數",
    min_value=1,
    max_value=10,
    value=5,
    help="返回前 N 個相似結果"
)

country_priority = st.sidebar.selectbox(
    "Tier 3 優先國家",
    options=["TW", "CN", "JP", "KR", "US", "GB"],
    index=0,
    help="EEIO 模型優先國家（僅影響 Tier 3）"
)


single_tab, batch_tab = st.tabs(["單筆查詢 Search", "批次配對 Batch"])

with single_tab:
    st.markdown('<div class="section-label">單筆查詢 · Single item</div>', unsafe_allow_html=True)
    st.header("排放係數檢索")

    with st.form("single_search_form", clear_on_submit=False):
        # 輸入欄位
        query = st.text_input(
            "請描述採購項目",
            placeholder="例如：筆記型電腦、瓦楞紙箱、牛肉採購...",
            help="輸入產品或服務的描述後按 Enter，或點選開始檢索，即可查詢排放係數"
        )
        context_cols = st.columns(2)
        with context_cols[0]:
            scope3_category_label = st.selectbox(
                "範疇三類別（選填）",
                options=[option["label"] for option in SCOPE3_CATEGORY_OPTIONS],
                index=0,
                help="若已知道 GHG Protocol Scope 3 類別，可指定類別協助檢索；不確定時維持不指定即可。"
            )
        with context_cols[1]:
            taiwan_industry_label = st.selectbox(
                "台灣產業類別（選填）",
                options=[option["label"] for option in TAIWAN_INDUSTRY_OPTIONS],
                index=0,
                help="若知道採購資料所屬產業，可指定產業背景協助檢索；此欄位只作為語意提示，不會硬性過濾結果。"
            )
        scope3_category = next(
            option for option in SCOPE3_CATEGORY_OPTIONS
            if option["label"] == scope3_category_label
        )
        taiwan_industry = next(
            option for option in TAIWAN_INDUSTRY_OPTIONS
            if option["label"] == taiwan_industry_label
        )

        submitted = st.form_submit_button("開始檢索", type="primary", use_container_width=True)

    # 按 Enter 或點選「開始檢索」都會提交表單。
    if submitted:
        if not query:
            st.warning("請先輸入採購項目。")
        else:
            with st.spinner("檢索中..."):
                enriched_query = enrich_procurement_query(query)
                # 執行檢索
                result = retriever.search(
                    query=enriched_query,
                    top_k=top_k,
                    tier1_threshold=tier1_threshold,
                    tier2_threshold=tier2_threshold,
                    tier3_threshold=tier3_threshold,
                    country_priority=country_priority
                )
                result["original_query"] = query
                result["query"] = enriched_query
                result["procurement_item_name"] = query
                if scope3_category["query_hint"]:
                    result["scope3_category"] = scope3_category["label"]
                if taiwan_industry["query_hint"]:
                    result["taiwan_industry"] = taiwan_industry["label"]
                context_values = _context_values(scope3_category, taiwan_industry)
                result = apply_context_to_result(result, context_values)
                result = _enrich_and_rerank_result(result, procurement_item_name=query)
                result["assist_note"] = (
                    "已套用兩階段輔助排序：主檢索使用原始輸入，類別/產業只做小幅加權。"
                    if context_values
                    else "未指定輔助條件，依原始輸入排序。"
                )

                # 顯示結果
                if result['success']:
                    # 成功訊息
                    st.success(result['message'])

                    # 顯示使用的層級
                    tier_colors = {
                        1: "Tier 1",
                        2: "Tier 2",
                        3: "Tier 3"
                    }
                    st.info(f"{tier_colors.get(result['tier'], 'Tier')} · {result['tier_name']}")

                    # 警告訊息
                    if result.get('warning'):
                        st.warning(result['warning'])
                    if result.get("ranking_note"):
                        st.caption(result["ranking_note"])

                    st.divider()

                    download_df = _single_result_download_df(result)
                    if not download_df.empty:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_query = "".join(
                            ch for ch in str(query).strip()[:24]
                            if ch.isalnum() or ch in ("_", "-")
                        ) or "search"
                        download_cols = st.columns(2)
                        with download_cols[0]:
                            st.download_button(
                                "下載檢索結果 CSV",
                                data=download_df.to_csv(index=False, encoding="utf-8-sig"),
                                file_name=f"排放係數檢索結果_{safe_query}_{timestamp}.csv",
                                mime="text/csv",
                                use_container_width=True,
                            )
                        with download_cols[1]:
                            st.download_button(
                                "下載檢索結果 Excel",
                                data=_dataframe_to_xlsx_bytes(download_df),
                                file_name=f"排放係數檢索結果_{safe_query}_{timestamp}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                            )

                    # 最佳匹配
                    st.subheader("最佳匹配")
                    best = result['best_match']

                    # 顯示詳細資訊
                    info_cols = st.columns(4)

                    with info_cols[0]:
                        if 'name' in best:
                            st.metric("名稱", best['name'][:30] + "..." if len(best['name']) > 30 else best['name'])
                        elif 'product_name' in best:
                            st.metric("產品", best['product_name'][:30] + "..." if len(best['product_name']) > 30 else best['product_name'])

                    with info_cols[1]:
                        ef = best['emission_factor']
                        unit = best.get('unit') or best.get('unit_standard', 'unknown')
                        st.metric("排放係數", f"{ef:,.4f} kg CO2e/{unit}")

                    with info_cols[2]:
                        st.metric("溫室氣體類別", infer_greenhouse_gas_category(best))

                    with info_cols[3]:
                        st.metric("檢索信心", _format_similarity(best.get("similarity")), help="檢索匹配分數，可能包含詞彙或類別規則加權；不代表係數正確率或數據品質。")

                    st.markdown(
                        f"""
                        <div class="detail-panel source-strip">
                            <div class="detail-label">係數來源</div>
                            <div class="detail-value">{escape(_match_source_label(best))}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # 完整資訊
                    with st.expander("完整資訊：推薦係數與覆核重點", expanded=True):
                        render_match_details(best, result)

                    st.divider()

                    # 其他候選
                    if len(result['matches']) > 1:
                        st.subheader(f"其他候選 ({len(result['matches']) - 1})")

                        # 建立 DataFrame
                        df_matches = pd.DataFrame(result['matches'][1:])

                        df_matches["ghg_gas_category"] = df_matches.apply(
                            lambda row: infer_greenhouse_gas_category(row.to_dict()),
                            axis=1,
                        )
                        df_matches["factor_source"] = df_matches.apply(
                            lambda row: _match_source_label(row.to_dict()),
                            axis=1,
                        )
                        df_matches["lifecycle_stage"] = df_matches.apply(
                            lambda row: row.get("lifecycle_stage") or infer_lifecycle_stage(row.to_dict(), result.get("tier")),
                            axis=1,
                        )

                        # 選擇顯示欄位
                        display_cols = []
                        if 'name' in df_matches.columns:
                            display_cols.append('name')
                        elif 'product_name' in df_matches.columns:
                            display_cols.append('product_name')

                        display_cols.extend([
                            'emission_factor',
                            'ghg_gas_category',
                            'lifecycle_stage',
                            'factor_source',
                            'similarity',
                            'suitability_decision',
                            'data_quality_level',
                            'review_status',
                        ])

                        if 'unit' in df_matches.columns:
                            display_cols.append('unit')
                        elif 'unit_standard' in df_matches.columns:
                            display_cols.append('unit_standard')

                        if 'source' in df_matches.columns:
                            display_cols.append('source')

                        # 顯示表格
                        column_labels = {
                            "name": "係數名稱",
                            "product_name": "係數名稱",
                            "emission_factor": "排放係數",
                            "ghg_gas_category": "溫室氣體類別",
                            "lifecycle_stage": "生命週期階段",
                            "factor_source": "係數來源",
                            "similarity": "相似度",
                            "suitability_decision": "適用性判斷",
                            "data_quality_level": "資料品質",
                            "review_status": "審查/查驗狀態",
                            "unit": "單位",
                            "unit_standard": "單位",
                            "source": "來源資料庫",
                        }
                        display_df = df_matches[display_cols].rename(columns=column_labels)
                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True
                        )

                else:
                    # 失敗訊息
                    st.error(result['message'])
                    st.info("建議改用更通用的描述，或降低相似度門檻。")

with batch_tab:
    st.markdown('<div class="section-label">批次配對 · Batch workflow</div>', unsafe_allow_html=True)
    st.header("批次排放係數配對")

    uploaded_files = st.file_uploader(
        "上傳 Excel 或 CSV 檔案",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        help="支援 Excel、CSV；檔案只要包含品名、數量、單位三類欄位即可"
    )
    if uploaded_files:
        st.caption(
            "已上傳："
            + "、".join(uploaded_file.name for uploaded_file in uploaded_files)
        )

    st.markdown(
        '<p class="small-note">系統會自動辨識 Excel/CSV 欄位；只要每列有品名、數量、單位，即可轉成檢索文字、配對排放係數，並追加 CO2e 計算結果。批次產業類別會套用到本次上傳的所有資料列。</p>',
        unsafe_allow_html=True
    )
    training_count = len(load_procurement_training_items())
    synonym_count = len(load_procurement_synonyms())
    if training_count or synonym_count:
        st.caption(
            f"已載入批次檢索參考資料：採購品名 {training_count:,} 筆、同義詞 {synonym_count:,} 筆。"
        )

    batch_industry_label = st.selectbox(
        "批次預設台灣產業類別（選填）",
        options=[option["label"] for option in TAIWAN_INDUSTRY_OPTIONS],
        index=0,
        help="套用到本次上傳的所有批次資料列；只作為檢索語意提示，不會硬性過濾結果。"
    )
    batch_industry = next(
        option for option in TAIWAN_INDUSTRY_OPTIONS
        if option["label"] == batch_industry_label
    )

    batch_col1, batch_col2 = st.columns(2)
    with batch_col1:
        twd_per_usd = st.number_input(
            "TWD / USD",
            min_value=1.0,
            value=32.0,
            step=0.5,
            help="用於 kgCO2e/USD 類係數的金額換算"
        )
    with batch_col2:
        twd_per_eur = st.number_input(
            "TWD / EUR",
            min_value=1.0,
            value=35.0,
            step=0.5,
            help="用於 kgCO2e/M.EUR 類 EEIO 係數的金額換算"
        )

    if st.button(
        "開始批次配對",
        type="primary",
        use_container_width=True,
        disabled=not uploaded_files,
    ):
        if not uploaded_files:
            st.warning("請先上傳至少一個檔案。")
        else:
            config = BatchMatchConfig(
                top_k=int(top_k),
                tier1_threshold=float(tier1_threshold),
                tier2_threshold=float(tier2_threshold),
                tier3_threshold=float(tier3_threshold),
                country_priority=country_priority,
                twd_per_usd=float(twd_per_usd),
                twd_per_eur=float(twd_per_eur),
                taiwan_industry_context=(
                    batch_industry["label"] if batch_industry["query_hint"] else ""
                ),
                taiwan_industry_query_hint=batch_industry["query_hint"],
            )

            combined_sheets = {}
            summary_frames = []
            progress = st.progress(0, text="準備批次配對...")
            status_box = st.empty()

            with st.spinner("批次配對中..."):
                total_files = len(uploaded_files)
                for file_index, uploaded_file in enumerate(uploaded_files, start=1):
                    try:
                        status_box.info(f"正在處理 {file_index}/{total_files}：{uploaded_file.name}")
                        data = BytesIO(uploaded_file.getvalue())
                        sheets, summary = process_batch_file(
                            data,
                            uploaded_file.name,
                            retriever,
                            config,
                        )

                        file_stem = Path(uploaded_file.name).stem
                        if not sheets:
                            st.warning(
                                f"{uploaded_file.name} 未產生批次結果。請確認檔案是否包含品名、數量、單位三類欄位。"
                            )
                        for sheet_name, df in sheets.items():
                            combined_sheets[f"{file_stem}_{sheet_name}"] = df

                        if summary is not None and not summary.empty:
                            summary = summary.copy()
                            summary.insert(0, "file", uploaded_file.name)
                            summary_frames.append(summary)
                    except Exception as e:
                        st.error(f"{uploaded_file.name} 處理失敗: {e}")
                    finally:
                        progress.progress(
                            file_index / total_files,
                            text=f"已處理 {file_index}/{total_files} 個檔案",
                        )

            if combined_sheets:
                summary_all = (
                    pd.concat(summary_frames, ignore_index=True)
                    if summary_frames
                    else pd.DataFrame()
                )
                st.success(f"已完成 {len(combined_sheets)} 張資料表。")
                if not summary_all.empty:
                    st.dataframe(summary_all, use_container_width=True, hide_index=True)

                output = BytesIO()
                write_batch_results_excel(output, combined_sheets, summary_all)
                output.seek(0)

                st.download_button(
                    "下載結果 Excel",
                    data=output,
                    file_name="批次排放係數匹配結果.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.error("本次批次配對沒有產生可下載結果。請確認上傳檔案是否包含品名、數量、單位三類欄位，或先用單筆查詢確認檢索器是否可用。")

st.divider()
st.header("使用說明")

with st.expander("資料與計算說明", expanded=False):
    st.header("資料與計算說明")

    st.markdown("""
    ### 檢索層級

    - **Tier 1**：台灣本地排放係數，優先採用。
    - **Tier 2**：國際產業資料庫，適合一般材料、產品或服務。
    - **Tier 3**：EEIO 產業平均模型，適合資本財、設備或初步估算。
    - **分類準則**：會計科目對照表與財物/資產分類表用於輔助判斷 Scope 3 類別，尤其是 Category 1（購買商品及勞務）與 Category 2（資本財）。

    ### 批次檔案

    - 支援 Excel、CSV 檔案格式
    - 批次檔案只要包含「品名、數量、單位」三類欄位即可；欄位名稱可使用中文或英文，例如：品名/採購品名/產品名稱/Item Name、數量/Qty/Quantity、單位/Unit/UOM。
    - 若檔案另有規格、材質、用途、類別、會計科目或產業別欄位，系統會作為輔助語意，不會取代主品名。
    - 已載入匿名採購品名訓練資料與同義詞參考資料，可用於品名正規化與檢索語意擴充
    - 輸出保留原始欄位，並追加準則判斷 Scope 3 類別、是否固定資產、判斷依據、匹配層級、係數名稱、排放係數、單位、來源、相似度、生命週期階段、資料品質、審查/查驗狀態、適用性分數、綜合分數、信心等級、CO2e 計算量與計算依據

    ### 覆核建議

    - 若 Tier 1 有合理匹配，通常優先採用。
    - 係數引用前需確認活動/產品相容性、宣告單位、生命週期範疇、地理範疇、盤查年度、技術路徑、GHG 種類、資料品質、審查揭露與授權限制。
    - Tier 2、Tier 3 結果仍需依供應商、製程、地區與盤查邊界覆核。
    - 適用性判斷參考手冊的可靠性、完整性、時間、地理、技術相關性。評級須有證據，缺資料則需覆核；檢索信心不代表係數正確率或產品整體DQR。
    - 標示為 `待人工確認` 的列，代表單位或係數不宜自動換算，申報前需人工確認。
    """)

with st.expander("Scope 3 係數需求地圖", expanded=False):
    needs = load_scope3_coefficient_needs()
    if needs:
        needs_df = pd.DataFrame(needs)
        st.dataframe(
            needs_df[
                [
                    "category",
                    "name",
                    "priority",
                    "needed_factors",
                    "taiwan_sources",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("尚未載入 Scope 3 係數需求資料。")


# 頁尾
st.divider()
st.markdown("""
<div style='text-align: center; color: #6e6e73; font-size: 0.88em; padding: 10px 0 20px;'>
    <p>Scope 3 Estimator｜範疇三排放係數輔助系統</p>
    <p>Sentence Transformers · EXIOBASE · 台灣本地排放係數</p>
</div>
""", unsafe_allow_html=True)
