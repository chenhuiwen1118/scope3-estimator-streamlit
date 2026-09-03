# 🌍 Scope 3 Estimator

**三層級聯 RAG 檢索系統 | 台灣範疇三排放係數智慧檢索**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B)](https://streamlit.io/)

An intelligent emission factor retrieval system using three-tier cascade RAG (Retrieval-Augmented Generation) architecture.

## 📖 專案概述

Scope 3 Estimator 是一個基於 **三層級聯 RAG（Retrieval-Augmented Generation）架構** 的排放係數檢索系統，旨在協助企業快速、準確地查找產品與服務的溫室氣體排放係數。

### 🎯 核心特色

- **🟢 Tier 1 (台灣本地)**: 環保署本地排放係數，最高品質（1,108 筆）
- **🟡 Tier 2 (國際產業)**: 國際產業資料庫，產品特定係數（6,949 筆）
- **🟠 Tier 3 (EEIO 模型)**: EXIOBASE 多國 EEIO 模型，產業平均（1,200 筆）
- ✅ **完全本地端運行**: 不依賴雲端 API，保護企業隱私
- ✅ **智慧瀑布式檢索**: 優先使用高品質本地資料，逐層降級
- ✅ **向量化相似度**: 使用 Sentence Transformers 進行語意檢索
- ✅ **多語言支援**: 支援中英文產品描述
- ✅ **GPU 加速**: 自動檢測並使用 CUDA（如有）

### 🔍 檢索邏輯

系統採用 **瀑布式檢索（Cascade Retrieval）**，優先使用高品質本地資料，逐層降級：

```
User Query
    ↓
Tier 1 (threshold: 0.80) → Taiwan EPA Local Data
    ↓ (如果無結果)
Tier 2 (threshold: 0.70) → International Industry Databases
    ↓ (如果無結果)
Tier 3 (threshold: 0.60) → EXIOBASE EEIO Model
    ↓
Return Best Match
```

## 🏗️ 技術架構

```
Streamlit Web UI (app.py)
    ↕
CascadeRetriever (三層級聯)
    ├── Tier1LocalRetriever (台灣本地)
    │   ├── Embeddings: tier1_embeddings.npy (1,108 × 384)
    │   └── Metadata: tier1_metadata.csv
    │
    ├── Tier2InternationalRetriever (國際產業)
    │   ├── Embeddings: tier2_embeddings.npy (6,949 × 384)
    │   └── Metadata: tier2_metadata.csv
    │
    └── Tier3EEIORetriever (EEIO 模型)
        ├── Embeddings: tier3_eeio_embeddings.npy (1,200 × 384)
        └── Metadata: tier3_eeio_metadata.csv

Shared Components:
    ├── EmbeddingEngine (paraphrase-multilingual-MiniLM-L12-v2)
    └── Similarity Utils (Cosine Similarity with Pre-computed Norms)
```

## 📊 資料來源

### Tier 1 - 台灣本地 (1,108 筆)
- **來源**: 台灣環境部（原環保署）
- **年度**: 2013-2023
- **類型**: 本地產品與服務排放係數
- **檔案**: `TWMOEPA_Preview_Data.csv`

### Tier 2 - 國際產業 (6,949 筆)
- **AGRIBALYSE 3.1.1** (2,518 筆): 法國食品生命週期資料庫
- **Idemat 2024** (2,123 筆): 材料排放係數
- **FootprintCalc 1.2** (1,806 筆): 化學品與材料
- **Big Climate Database** (502 筆): 丹麥食品資料庫

### Tier 3 - EEIO 模型 (1,200 筆)
- **來源**: EXIOBASE 2022 (Multi-Regional Input-Output)
- **國家**: TW, GB, JP, CN, KR, US (6 國)
- **產業**: 200 個產業部門
- **單位**: kg CO2e / M.EUR（百萬歐元）

## 🚀 快速開始

### 1. 安裝依賴

```bash
# 建議使用虛擬環境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安裝依賴
pip install -r requirements.txt
```

### 2. 啟動 Web UI

```bash
# 方法 1: 使用啟動腳本（推薦，已設定離線模式）
./run_app.sh

# 方法 2: 直接使用 streamlit（需手動設定離線模式）
HF_HUB_OFFLINE=1 streamlit run app.py
```

系統將自動在瀏覽器開啟：`http://localhost:8501`

### 🔒 離線模式（完全不連接網路）

系統已設定為**完全離線運作**，不會訪問 Hugging Face Hub：

- ✅ `run_app.sh` 已自動啟用離線模式
- ✅ `app.py` 程式碼內強制離線模式
- ✅ `.env` 檔案包含離線設定

**首次使用需確保模型已下載**（約 500MB）：
```bash
# 檢查模型是否存在
ls ~/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2

# 如果不存在，需在有網路時執行一次下載：
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
```

之後即可**完全離線使用**，無需任何網路連線。

### 3. 使用範例

在 Web UI 中輸入查詢：

- **購買塑膠袋** → 命中 Tier 1（台灣本地）
- **紙箱包裝** → 命中 Tier 1（台灣本地）
- **牛肉採購** → 命中 Tier 2（國際產業）
- **購買電腦設備** → 命中 Tier 1 或 Tier 3（EEIO 模型）
- **軟體服務** → 命中 Tier 3（EEIO 模型）

## 🏗️ 專案結構

```
scope3_estimator/
├── data/
│   └── emission_factors/
│       ├── tier1_local/              # Tier 1 台灣環保署資料
│       │   ├── TWMOEPA_Preview_Data.csv
│       │   ├── tier1_unified.csv
│       │   ├── tier1_embeddings.npy   (1,108 vectors × 384 dim)
│       │   └── tier1_metadata.csv
│       │
│       ├── tier2_international/       # Tier 2 國際資料庫
│       │   ├── AGRIBALYSE3.1.1_*.csv
│       │   ├── IdematDynamic241.csv
│       │   ├── The_Big_Climate_Database_*.csv
│       │   ├── FootprintCalc1.2-1.csv
│       │   ├── tier2_unified.csv
│       │   ├── tier2_embeddings.npy   (6,949 vectors × 384 dim)
│       │   └── tier2_metadata.csv
│       │
│       └── tier3_eeio/                # Tier 3 EEIO 模型
│           ├── EXIOBASE_{TW,GB,JP,CN,KR,US}_2022_GHG_intensity.csv
│           ├── product_translations.json
│           ├── tier3_eeio_unified.csv
│           ├── tier3_eeio_embeddings.npy (1,200 vectors × 384 dim)
│           └── tier3_eeio_metadata.csv
│
├── src/
│   ├── retrieval/
│   │   ├── tier1_local.py             # Tier 1 檢索器
│   │   ├── tier2_international.py     # Tier 2 檢索器
│   │   ├── tier3_eeio.py              # Tier 3 檢索器
│   │   └── cascade_retriever.py       # 三層級聯檢索器
│   │
│   └── utils/
│       ├── embedding.py               # Sentence Transformer 引擎
│       └── similarity.py              # 向量相似度計算
│
├── scripts/
│   ├── prepare_tier{1,2,3}_rag_data.py  # 資料預處理
│   ├── build_tier{1,2,3}_embeddings.py  # 向量生成
│   ├── test_tier3_retriever.py          # 單層測試
│   └── test_cascade_retriever.py        # 級聯測試
│
├── app.py                              # Streamlit Web UI
├── run_app.sh                          # 啟動腳本
├── requirements.txt
└── README.md
```

## 🔧 Python API 使用

### 基本使用

```python
from retrieval.cascade_retriever import CascadeRetriever

# 初始化檢索器
retriever = CascadeRetriever()

# 檢索排放係數
result = retriever.search(
    query="購買塑膠袋",
    top_k=5,
    tier1_threshold=0.80,
    tier2_threshold=0.70,
    tier3_threshold=0.60
)

if result['success']:
    best_match = result['best_match']
    print(f"✅ {result['message']}")
    print(f"Tier: {result['tier_name']}")
    print(f"Name: {best_match['name']}")
    print(f"Emission Factor: {best_match['emission_factor']}")
    print(f"Similarity: {best_match['similarity']:.4f}")
else:
    print(f"❌ {result['message']}")
```

### 進階設定

```python
# 調整門檻值
result = retriever.search(
    query="購買電腦設備",
    top_k=3,
    tier1_threshold=0.85,  # 更嚴格的 Tier 1 門檻
    tier2_threshold=0.75,
    tier3_threshold=0.65
)

# Tier 3 國家優先
result = retriever.search(
    query="軟體服務",
    country_priority="TW"  # TW, CN, JP, KR, US, GB
)

# 查看所有匹配結果
for i, match in enumerate(result['matches'], 1):
    print(f"{i}. {match['name']} (相似度: {match['similarity']:.4f})")
```

### 測試腳本

```bash
# 測試單層檢索器
python scripts/test_tier3_retriever.py

# 測試三層級聯檢索器
python scripts/test_cascade_retriever.py
```

## 📊 資料處理流程

### 1. Tier 1 處理

```bash
# 預處理台灣環保署資料
python scripts/prepare_tier1_rag_data.py

# 生成 Embedding 向量
python scripts/build_tier1_embeddings.py
```

**輸出**:
- `tier1_unified.csv` (1,108 records)
- `tier1_embeddings.npy` (1.62 MB)
- `tier1_metadata.csv` (118 KB)

### 2. Tier 2 處理

```bash
# 預處理國際資料庫
python scripts/prepare_tier2_rag_data.py

# 生成 Embedding 向量
python scripts/build_tier2_embeddings.py
```

**輸出**:
- `tier2_unified.csv` (6,949 records)
- `tier2_embeddings.npy` (10.18 MB)
- `tier2_metadata.csv` (573 KB)

### 3. Tier 3 處理

```bash
# 提取 EXIOBASE 多國資料
python scripts/extract_exiobase_ghg_multi.py

# 預處理 EEIO 資料
python scripts/prepare_tier3_rag_data.py

# 生成 Embedding 向量
python scripts/build_tier3_embeddings.py
```

**輸出**:
- `tier3_eeio_unified.csv` (1,200 records)
- `tier3_eeio_embeddings.npy` (1.76 MB)
- `tier3_eeio_metadata.csv` (120 KB)

## 🧪 測試

### 單層測試

```bash
# 測試 Tier 3 EEIO 檢索器
python scripts/test_tier3_retriever.py
```

### 級聯測試

```bash
# 測試三層級聯檢索器
python scripts/test_cascade_retriever.py
```

## ⚠️ 注意事項

### Tier 1 (台灣本地)
- ✅ **最高品質**: 官方公告係數
- ✅ **最相關**: 台灣本地情境
- ⚠️ **覆蓋有限**: 僅 1,108 項產品/服務

### Tier 2 (國際產業)
- ✅ **產品特定**: 針對特定產品類型
- ✅ **資料豐富**: 近 7,000 項記錄
- ⚠️ **地區差異**: 國際平均值，實際情況可能因地區而異

### Tier 3 (EEIO 模型)
- ⚠️ **產業平均**: 基於產業平均排放強度
- ⚠️ **高不確定性**: ±50% ~ ±300% 範圍
- ⚠️ **僅供參考**: 建議僅用於初步估算
- 💡 **重大排放源**: 應要求供應商提供實際數據

## 📈 系統效能

### 初始化時間
- **Tier 1**: ~1 秒
- **Tier 2**: ~2 秒
- **Tier 3**: ~1 秒
- **總計**: ~4-5 秒（首次載入）

### 查詢速度
- **單次查詢**: < 100 ms (GPU) / < 500 ms (CPU)
- **批次查詢**: 支援（使用 batch encoding）

### 記憶體使用
- **Embedding 模型**: ~500 MB
- **向量資料**: ~14 MB (三層總計)
- **總計**: ~1-2 GB (含模型)

## 🛣️ 未來規劃

- [ ] 新增更多國際資料庫（IPCC, EPA, etc）
- [ ] 支援批次查詢與 Excel 匯入/匯出
- [ ] 整合 LLM 提供自然語言解釋
- [ ] 新增排放計算器（金額 → 排放量）
- [ ] 支援多種排放範疇（Scope 1, 2, 3）
- [ ] 新增 API 服務（FastAPI）
- [ ] 支援更多國家（EXIOBASE 49 國）
- [ ] 新增使用者回饋機制，持續改進檢索品質

## 🤝 貢獻

歡迎提交 Issues 或 Pull Requests！

## 📄 授權

MIT License - 詳見 [LICENSE](LICENSE) 檔案

排放係數資料授權：
- **TWMOEPA**: 政府開放資料
- **AGRIBALYSE**: 開放資料，需標註來源
- **Idemat**: 學術使用
- **Big Climate Database**: 開放資料
- **FootprintCalc**: 學術使用
- **EXIOBASE**: 學術使用，需引用來源

## 📧 聯絡

如有任何問題或建議，歡迎聯繫專案維護者。

- **計畫主持人**: 張育傑 教授
- **機構**: 臺北市立大學地球環境暨生物資源學系
- **Email**: yjchang@utaipei.edu.tw

## 🙏 致謝

- **台灣環境部**: 提供本地排放係數資料
- **EXIOBASE**: 提供多國 EEIO 模型
- **AGRIBALYSE, Idemat, Big Climate DB, FootprintCalc**: 國際資料庫
- **Sentence Transformers**: 多語言向量化模型
- **Streamlit**: 快速 Web UI 開發框架

## 相關文件

- [系統開發規劃](../系統開發規劃.md)
- [專案分析與重用評估](../專案分析與重用評估.md)
- [EXIOBASE RAG 整合計劃](docs/EXIOBASE_RAG_整合計劃.md)

---

<div align="center">
  <p><strong>🌍 為企業的淨零轉型賦能</strong></p>
  <p><em>Empowering Net-Zero Transformation</em></p>
    <p><strong>版本</strong>: v0.2.0 | <strong>最後更新</strong>: 2026-01-30</p>
</div>