# EXIOBASE 資料 RAG 系統整合計劃

**建立日期**: 2026-01-28
**狀態**: 規劃中 📋
**目標**: 將 EXIOBASE 多國 EEIO 資料整合到三層 RAG 檢索系統

---

## 📊 現有資料

### EXIOBASE 資料檔案（已完成）
已成功提取 6 個國家的 GHG 排放強度資料：

```
data/emission_factors/tier3_eeio/
├── EXIOBASE_TW_2022_GHG_intensity.csv  (31 KB, 200 產品)
├── EXIOBASE_GB_2022_GHG_intensity.csv  (33 KB, 200 產品)
├── EXIOBASE_JP_2022_GHG_intensity.csv  (31 KB, 200 產品)
├── EXIOBASE_CN_2022_GHG_intensity.csv  (32 KB, 200 產品)
├── EXIOBASE_KR_2022_GHG_intensity.csv  (31 KB, 200 產品)
└── EXIOBASE_US_2022_GHG_intensity.csv  (33 KB, 200 產品)
```

**資料結構**:
- Country: 國家代碼 (TW, GB, JP, CN, KR, US)
- Product_Number: 1-200
- Product_Name: 產品名稱（英文）
- Product_Code: EXIOBASE 代碼
- Output_MEUR: 經濟產出（百萬歐元）
- CO2/CH4/N2O_kg_per_MEUR: 各氣體排放強度
- Total_CO2e_kg_per_MEUR: 總 CO2e 排放強度

**總記錄數**: 6 國 × 200 產品 = 1,200 筆

---

## 🏗️ 系統架構

### 三層 RAG 檢索架構

```
使用者查詢
    ↓
[Embedding Engine] 查詢向量化
    ↓
┌─────────────────────────────────────┐
│  Tier 1: 本土係數（台灣優先）        │
│  - TWMOEPA_Preview_Data.csv         │
│  - 相似度門檻: 0.80                  │
│  - 若命中 → 直接返回                 │
└─────────────────────────────────────┘
    ↓ (未命中)
┌─────────────────────────────────────┐
│  Tier 2: 國際產業特定                │
│  - Defra UK 2025                    │
│  - GHG Protocol v2.0                │
│  - AGRIBALYSE, Idemat, etc.         │
│  - 相似度門檻: 0.70                  │
│  - 若命中 → 返回最佳匹配              │
└─────────────────────────────────────┘
    ↓ (未命中)
┌─────────────────────────────────────┐
│  Tier 3: EEIO 通用（新增）⭐         │
│  - EXIOBASE (TW優先 → 其他國家)     │
│  - USEEIO                           │
│  - 相似度門檻: 0.60                  │
│  - 若命中 → 返回 + 警告訊息           │
└─────────────────────────────────────┘
    ↓
返回結果 + 資料來源 + 不確定性說明
```

---

## 🎯 整合步驟

### 階段 1: 資料預處理 ✅ 已完成

- [x] 提取 EXIOBASE 6 國資料
- [x] 計算排放強度（kg CO2e per M.EUR）
- [x] 清理與驗證資料
- [x] 更新 tier3_eeio/README.md

### 階段 2: 建立統一資料格式 📋 進行中

需要創建統一的資料格式以便 RAG 檢索：

**目標格式** (`tier3_eeio_unified.csv`):
```csv
source,country,product_id,product_name,product_code,search_text,emission_factor_per_meur,unit,base_year,gwp_version
EXIOBASE,TW,1,Paddy rice,C_PARI,"稻米 水稻 Paddy rice 農業 Agriculture",1244971,kg CO2e/M.EUR,2022,AR5
EXIOBASE,TW,2,Wheat,C_WHEA,"小麥 Wheat 穀物 Grain",487438,kg CO2e/M.EUR,2022,AR5
...
EXIOBASE,JP,1,Paddy rice,C_PARI,"稻米 水稻 Paddy rice 農業 Agriculture 日本",1523456,kg CO2e/M.EUR,2022,AR5
...
```

**欄位說明**:
- `search_text`: 富語意文本，包含：
  - 中文名稱（主要）
  - 英文名稱
  - 同義詞
  - 產業類別
  - 國家名稱（用於優先排序）

### 階段 3: Embedding 向量化 ⏳ 待執行

使用現有的 `EmbeddingEngine` 對 `search_text` 進行向量化：

```python
from src.utils.embedding import EmbeddingEngine

# 初始化 Embedding 引擎
engine = EmbeddingEngine(
    model_name="paraphrase-multilingual-MiniLM-L12-v2",
    device="auto"
)

# 讀取統一格式資料
import pandas as pd
df = pd.read_csv("data/emission_factors/tier3_eeio/tier3_eeio_unified.csv")

# 批次向量化
embeddings = engine.encode(
    df['search_text'].tolist(),
    batch_size=32,
    show_progress=True
)

# 儲存向量
import numpy as np
np.save("data/emission_factors/tier3_eeio/embeddings.npy", embeddings)
```

**輸出檔案**:
- `embeddings.npy`: (1200, 384) 維度的向量矩陣

### 階段 4: 建立檢索介面 ⏳ 待執行

創建 RAG 檢索類別：

```python
class Tier3EEIORetriever:
    """Tier 3 EEIO 檢索器"""

    def __init__(self, data_path, embeddings_path):
        self.df = pd.read_csv(data_path)
        self.embeddings = np.load(embeddings_path)
        self.engine = EmbeddingEngine()
        self.norms = precompute_norms(self.embeddings)

    def search(
        self,
        query: str,
        country_priority: str = "TW",
        top_k: int = 5,
        threshold: float = 0.60
    ) -> List[Dict]:
        """
        檢索最相關的排放係數

        Args:
            query: 使用者查詢（如「購買電腦設備」）
            country_priority: 優先國家（預設 TW）
            top_k: 返回前 k 個結果
            threshold: 相似度門檻

        Returns:
            符合條件的排放係數清單
        """
        # 1. 查詢向量化
        query_vector = self.engine.encode_single(query)

        # 2. 計算相似度
        similarities = fast_cosine_similarity_with_norms(
            query_vector,
            self.embeddings,
            self.norms
        )

        # 3. 篩選門檻
        mask = similarities >= threshold
        filtered_indices = np.where(mask)[0]
        filtered_sims = similarities[filtered_indices]

        # 4. 國家優先排序
        # 台灣資料加權 +0.1
        country_boost = np.array([
            0.1 if self.df.iloc[i]['country'] == country_priority else 0.0
            for i in filtered_indices
        ])
        boosted_sims = filtered_sims + country_boost

        # 5. Top-K
        top_indices_in_filtered = np.argsort(boosted_sims)[::-1][:top_k]
        top_indices = filtered_indices[top_indices_in_filtered]

        # 6. 組裝結果
        results = []
        for idx in top_indices:
            row = self.df.iloc[idx]
            results.append({
                'source': row['source'],
                'country': row['country'],
                'product_name': row['product_name'],
                'product_code': row['product_code'],
                'emission_factor': row['emission_factor_per_meur'],
                'unit': row['unit'],
                'similarity': float(similarities[idx]),
                'is_priority_country': row['country'] == country_priority
            })

        return results
```

### 階段 5: 匯率轉換模組 ⏳ 待執行

建立匯率與單位轉換工具：

```python
class CurrencyConverter:
    """匯率轉換器"""

    RATES_2022 = {
        'TWD_to_EUR': 32.5,
        'TWD_to_USD': 30.0,
        'USD_to_EUR': 1.10,
        'GBP_to_EUR': 0.85,
    }

    @classmethod
    def convert_to_eur(cls, amount: float, currency: str) -> float:
        """將指定貨幣金額轉換為歐元"""
        if currency == 'EUR':
            return amount
        elif currency == 'TWD':
            return amount / cls.RATES_2022['TWD_to_EUR']
        elif currency == 'USD':
            return amount / cls.RATES_2022['USD_to_EUR']
        # ... 其他貨幣

    @classmethod
    def calculate_emissions(
        cls,
        amount: float,
        currency: str,
        emission_factor_per_meur: float
    ) -> float:
        """
        計算排放量

        Args:
            amount: 金額
            currency: 貨幣（TWD, USD, EUR, GBP）
            emission_factor_per_meur: 排放係數 (kg CO2e / M.EUR)

        Returns:
            排放量 (kg CO2e)
        """
        # 1. 轉換為歐元
        amount_eur = cls.convert_to_eur(amount, currency)

        # 2. 轉換為百萬歐元
        amount_meur = amount_eur / 1_000_000

        # 3. 計算排放量
        emissions = amount_meur * emission_factor_per_meur

        return emissions
```

### 階段 6: 整合到主檢索系統 ⏳ 待執行

在主檢索系統中加入 Tier 3 檢索邏輯：

```python
class EmissionFactorRetriever:
    """三層 RAG 檢索系統"""

    def __init__(self):
        self.tier1_retriever = Tier1Retriever()  # 台灣本土
        self.tier2_retriever = Tier2Retriever()  # 國際產業特定
        self.tier3_retriever = Tier3EEIORetriever()  # EEIO 通用

    def search(self, query: str, amount: float = None, currency: str = "TWD"):
        """
        三層級聯檢索

        Returns:
            {
                'tier': 1/2/3,
                'matches': [...],
                'confidence': 0.85,
                'emissions': 1234.5,  # 若提供金額
                'warning': "..."  # 若使用 Tier 3
            }
        """
        # 1. Tier 1 檢索
        tier1_results = self.tier1_retriever.search(query, threshold=0.80)
        if tier1_results:
            return self._format_response(1, tier1_results, amount, currency)

        # 2. Tier 2 檢索
        tier2_results = self.tier2_retriever.search(query, threshold=0.70)
        if tier2_results:
            return self._format_response(2, tier2_results, amount, currency)

        # 3. Tier 3 檢索（新增）
        tier3_results = self.tier3_retriever.search(
            query,
            country_priority="TW",
            threshold=0.60
        )
        if tier3_results:
            response = self._format_response(3, tier3_results, amount, currency)
            response['warning'] = (
                "⚠️ 此結果基於產業平均排放強度（EEIO 模型）\n"
                "- 實際排放可能因產品特性、製造過程而顯著不同\n"
                "- 建議僅用於初步估算\n"
                "- 重大排放源應要求供應商提供實際數據\n"
                "- 不確定性範圍: ±50% ~ ±300%"
            )
            return response

        # 4. 無匹配
        return {'tier': None, 'matches': [], 'error': '無法找到相關排放係數'}
```

---

## 📝 待辦事項

### 高優先級
- [ ] 創建資料預處理腳本 `prepare_tier3_data.py`
  - 載入 6 個 EXIOBASE CSV
  - 生成統一格式 `tier3_eeio_unified.csv`
  - 添加中文翻譯與同義詞
  - 構建 `search_text` 欄位

- [ ] 創建 Embedding 腳本 `build_tier3_embeddings.py`
  - 載入統一資料
  - 批次向量化
  - 儲存 embeddings.npy

- [ ] 創建檢索類別 `src/retrieval/tier3_eeio.py`
  - Tier3EEIORetriever
  - 相似度計算
  - 國家優先排序

### 中優先級
- [ ] 匯率轉換模組 `src/utils/currency.py`
  - 支援 TWD, USD, EUR, GBP
  - 通膨調整（可選）
  - API 整合（未來）

- [ ] 單元測試
  - 測試檢索準確性
  - 測試匯率轉換
  - 測試國家優先邏輯

- [ ] 整合到主系統
  - 修改 `EmissionFactorRetriever`
  - 加入 Tier 3 邏輯
  - 錯誤處理

### 低優先級
- [ ] 效能優化
  - FAISS 向量索引
  - 快取機制
  - 批次查詢

- [ ] 使用者介面
  - Streamlit 展示
  - 結果視覺化
  - 不確定性範圍顯示

---

## 🔍 預期成效

### 檢索準確性提升
- **涵蓋率**: 從 ~60% 提升至 ~95%（加入 Tier 3 兜底）
- **台灣相關性**: 優先使用台灣 EXIOBASE 資料
- **國際化**: 支援 6 個主要經濟體

### 使用者體驗改善
- **無匹配率降低**: 從 ~40% 降至 ~5%
- **結果透明度**: 明確標示資料來源與不確定性
- **國家適配**: 自動選擇最適合的國家資料

### 系統完整性
- **三層架構完成**: Tier 1 + Tier 2 + Tier 3 ✅
- **符合 GHG Protocol**: 遵循國際標準
- **可擴充**: 易於加入更多國家資料

---

## 📚 參考資源

- **EXIOBASE**: https://www.exiobase.eu/
- **GHG Protocol Scope 3**: https://ghgprotocol.org/scope-3-calculation-guidance
- **Sentence Transformers**: https://www.sbert.net/
- **內部文件**:
  - `data/emission_factors/tier3_eeio/README.md`
  - `docs/EXIOBASE_MRIO_分析報告.md`

---

**維護人員**: 張育傑
**最後更新**: 2026-01-28
**下次審查**: 2026-02-28
