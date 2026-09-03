# Tier 3: EEIO 經濟投入產出排放係數資料庫

**精確度等級**: 中 ⭐⭐⭐
**優先順序**: 第三優先（最後選擇）
**區域**: 全球各國
**用途**: 基於經濟部門的通用排放係數（兜底方案）

---

## 🎯 使用原則

當 **Tier 1 (本土)** 與 **Tier 2 (國際產業特定)** 都無法匹配時，使用本層級的 EEIO 係數。

### 什麼是 EEIO？
**EEIO** = Environmentally-Extended Input-Output（環境延伸投入產出）
- 基於國家級經濟統計資料
- 計算各經濟部門的平均排放強度
- 單位通常為「kg CO2e / USD」或「kg CO2e / 本國貨幣」

### EEIO 的特性
| 優勢 | 劣勢 |
|------|------|
| ✅ 涵蓋範圍廣（全產業） | ❌ 精確度較低（產業平均） |
| ✅ 有系統性（投入產出表） | ❌ 無法反映特定產品差異 |
| ✅ 適合初期篩選 | ❌ 可能高估或低估 |
| ✅ 可用於金額資料 | ❌ 依賴貨幣匯率與通膨 |

---

## 📁 資料庫清單

### 1. USEEIO_F_raw_GHGs.csv (1.8 MB)

#### 基本資訊
- **來源**: U.S. Environmental Protection Agency (EPA)
- **模型**: USEEIO v2.0 (United States Environmentally-Extended Input-Output)
- **基準年**: 2017
- **網址**: https://www.epa.gov/land-research/us-environmentally-extended-input-output-useeio-models
- **授權**: 美國政府開放資料

#### 資料結構
```
格式: 25 rows (GHG types) × 9,801 columns (Economic sectors)
範例欄位: AT___Paddy rice, AT___Wheat, US___Construction, ...
```

#### GHG 類型 (25 種)
1. CO2 - combustion - air
2. CH4 - combustion - air
3. N2O - combustion - air
4. CH4 - non combustion - Extraction/production of (natural) gas - air
5. CH4 - non combustion - Extraction/production of crude oil - air
6. N2O - non combustion - Agricultural soils - air
7. ... (共25種)

#### 涵蓋部門
- **農業**: 稻米、小麥、畜牧業等
- **製造業**: 電子、化工、機械、紡織等
- **服務業**: 金融、餐飲、運輸、建築等
- **能源**: 石油、天然氣、電力、煤炭等

#### 資料特性
- ✅ 涵蓋全產業（最完整）
- ✅ 系統性資料（投入產出模型）
- ✅ 美國 EPA 官方認證
- ⚠️ 基於 2017 年資料（需考量時效性）
- ⚠️ 美國經濟結構（與台灣可能有差異）

---

### 2. USEEIO_summary_import_2022.csv (25 KB)

#### 基本資訊
- **來源**: U.S. EPA USEEIO
- **年度**: 2022
- **專長**: 進口商品排放係數

#### 資料結構
```
格式: 220 rows × 10 columns
欄位:
- Sector: NAICS 產業代碼 (如 111CA, 113FF, 211, 221)
- Year: 2022
- Unit: kg 或 kg CO2e
- ReferenceCurrency: USD
- Flowable: GHG 名稱 (CO2, CH4, N2O, SF6, HFCs/PFCs)
- FlowAmount: 排放量 (per USD)
```

#### 涵蓋部門 (44 個)
- 111CA: Oilseed farming (油籽種植)
- 113FF: Forest nurseries and gathering of forest products (林業苗圃)
- 211: Oil and gas extraction (石油天然氣開採)
- 221: Utilities (公用事業)
- 236: Construction (建築)
- 311: Food manufacturing (食品製造)
- ... (共44個摘要級部門)

#### 資料特性
- ✅ 較新的資料 (2022)
- ✅ 專注進口商品
- ✅ 摘要級 (Summary Level)，易於使用
- ✅ 單位清楚 (kg/USD)
- ⚠️ 部門數較少 (44 vs 9,801)

---

### 3. EXIOBASE_TW_2022_GHG_intensity.csv (31 KB) ⭐ 新增

#### 基本資訊
- **來源**: EXIOBASE 3 (Multi-Regional Input-Output Database)
- **區域**: 台灣 (TW)
- **基準年**: 2022
- **網址**: https://www.exiobase.eu/
- **授權**: Creative Commons

#### 資料結構
```
格式: 200 rows (產品類別) × 12 columns
欄位:
- Country: TW
- Product_Number: 1-200
- Product_Name: 產品名稱（英文）
- Product_Code: EXIOBASE 代碼 (如 C_PARI, C_WHEA)
- Output_MEUR: 經濟產出 (百萬歐元)
- CO2_kg_per_MEUR: CO2 排放強度
- CH4_kg_per_MEUR: CH4 排放強度
- N2O_kg_per_MEUR: N2O 排放強度
- Total_CO2e_kg_per_MEUR: 總 CO2e 排放強度 (kg per 百萬歐元)
```

#### 產品分類 (200 類)
- **農業**: 稻米、小麥、蔬菜水果、畜牧產品等
- **製造業**: 電子產品、化工、機械、紡織、金屬等
- **能源**: 電力（煤、氣、核、再生能源）、石油產品等
- **服務業**: 運輸、金融、建築、餐飲、住宿等
- **廢棄物處理**: 焚化、掩埋、回收等

#### 排放強度範圍
- 平均: 1,155,393 kg CO2e/M.EUR
- 中位數: 21,549 kg CO2e/M.EUR
- 最小值: 0 kg CO2e/M.EUR (無產出部門)
- 最大值: 27,354,060 kg CO2e/M.EUR (廢棄物焚化)

#### 高排放強度部門 (前5名)
1. Textiles waste incineration: 27.4 M kg/M.EUR
2. Plastic waste incineration: 24.1 M kg/M.EUR
3. Inert/metal waste incineration: 20.6 M kg/M.EUR
4. Sea and coastal transportation: 19.3 M kg/M.EUR
5. Electricity by coal: 12.7 M kg/M.EUR

#### 資料特性
- ✅ **台灣特定資料** (最適合台灣企業)
- ✅ 最新 2022 年資料
- ✅ 涵蓋 200 個產品類別（詳細分類）
- ✅ 包含完整 GHG 拆解 (CO2, CH4, N2O)
- ✅ 基於 MRIO 模型（包含進口排放）
- ⚠️ 單位為 EUR，需匯率轉換
- ⚠️ 仍為產業平均，無法反映特定產品差異

#### GWP 係數
- 採用 IPCC AR5 (100-year)
- CO2: 1
- CH4: 28
- N2O: 265

---

### 4. EXIOBASE_GB_2022_GHG_intensity.csv (33 KB)

#### 基本資訊
- **來源**: EXIOBASE 3 (Multi-Regional Input-Output Database)
- **區域**: 英國 (GB)
- **基準年**: 2022
- **結構**: 與台灣版本相同（200 產品類別）

#### 排放強度範圍
- 平均: 842,902 kg CO2e/M.EUR
- 中位數: 37,154 kg CO2e/M.EUR
- 最大值: 53,090,275 kg CO2e/M.EUR

#### 資料特性
- ✅ 英國特定資料
- ✅ 可用於英國進口商品或國際專案
- ✅ 與台灣資料結構一致，便於比較
- ⚠️ 非台灣優先選擇

---

## 🔍 檢索策略

### RAG 向量檢索設定
```python
# Tier 3 檢索參數建議
tier3_config = {
    "top_k": 15,  # 多檢索候選，因為是通用分類
    "similarity_threshold": 0.60,  # 較低門檻（最後兜底）
    "weight": 0.5,  # 較低權重
    "language": "multilingual",
    "use_sector_classification": True  # 啟用產業分類輔助
}
```

### 檢索邏輯（更新 - 台灣優先）

#### 1. 觸發條件
- Tier 1 無匹配
- Tier 2 相似度 < 0.70

#### 2. 資料庫優先順序 ⭐ 重要更新

**台灣企業適用**:
```
1️⃣ EXIOBASE_TW_2022_GHG_intensity.csv (台灣特定，優先)
2️⃣ USEEIO_summary_import_2022.csv (美國，較新)
3️⃣ USEEIO_F_raw_GHGs.csv (美國，較舊但完整)
4️⃣ EXIOBASE_GB_2022_GHG_intensity.csv (英國，僅特殊情況)
```

**匹配邏輯**:
```python
# 範例: 使用者輸入 "購買電腦設備 NT$300,000"

# Step 1: 檢索 EXIOBASE_TW (台灣)
→ 匹配: "Computer, electronic and optical products"
→ 排放強度: 150,000 kg CO2e/M.EUR
→ 匯率轉換: NT$ 300,000 ÷ 32.5 (TWD/EUR) = 9,231 EUR
→ 計算: (9,231 ÷ 1,000,000) × 150,000 = 1,385 kg CO2e
→ 數據來源: EXIOBASE TW 2022 ✅

# Step 2: 若台灣資料無匹配，檢索 USEEIO
→ 匹配: "334: Computer and electronic product manufacturing"
→ 排放係數: 0.25 kg CO2e/USD
→ 匯率轉換: NT$ 300,000 ÷ 30 (TWD/USD) = $10,000
→ 計算: 10,000 × 0.25 = 2,500 kg CO2e
→ 數據來源: USEEIO 2022 ⚠️
```

#### 3. 金額與匯率處理

**支援的貨幣輸入**:
- 台幣 (NT$, TWD)
- 美元 ($, USD)
- 歐元 (€, EUR)
- 英鎊 (£, GBP)

**匯率參考值 (2022)**:
```python
exchange_rates_2022 = {
    "TWD_to_EUR": 32.5,   # 1 EUR = 32.5 TWD
    "TWD_to_USD": 30.0,   # 1 USD = 30.0 TWD
    "USD_to_EUR": 1.10,   # 1 EUR = 1.10 USD
    "GBP_to_EUR": 0.85    # 1 EUR = 0.85 GBP
}
```

⚠️ **重要**: 需定期更新匯率，或使用即時匯率 API

#### 4. 單位轉換範例

**EXIOBASE (kg CO2e per M.EUR)**:
```python
# 使用者輸入: "NT$ 500,000"
emission_intensity = 200,000  # kg CO2e / M.EUR
amount_eur = 500,000 / 32.5  # = 15,385 EUR
amount_meur = amount_eur / 1,000,000  # = 0.015385 M.EUR
emissions = amount_meur × emission_intensity  # = 3,077 kg CO2e
```

**USEEIO (kg CO2e per USD)**:
```python
# 使用者輸入: "NT$ 500,000"
emission_factor = 0.30  # kg CO2e / USD
amount_usd = 500,000 / 30  # = 16,667 USD
emissions = amount_usd × emission_factor  # = 5,000 kg CO2e
```

---

## 📊 使用場景與限制

### ✅ 適合使用的情境

1. **初期篩選與熱點分析**
   - 快速識別主要排放源
   - 建立排放清冊初稿
   - 決定哪些項目需要更精確的係數

2. **金額導向的採購活動**
   - 只有金額資訊，無實體數量
   - 範例：「顧問費 $50,000」、「軟體授權 $20,000」

3. **服務類別**
   - 金融服務、保險、諮詢
   - 難以取得實體排放係數的服務

4. **缺乏特定資料時的兜底方案**
   - 無其他來源可用
   - 時間緊迫，需快速估算

### ❌ 不適合使用的情境

1. **已有更精確的係數**
   - 有 Tier 1 或 Tier 2 係數時，不應使用 Tier 3

2. **需要查證的重大排放源**
   - 排放量 > 100 噸 CO2e 的項目
   - 應使用更精確的係數或要求供應商提供實際數據

3. **台灣本地產品**
   - 美國經濟結構與台灣差異大
   - 應優先尋找台灣或亞洲係數

4. **特殊產品或高價值商品**
   - 產業平均無法反映特定產品特性
   - 應使用 LCA 資料

---

## 📊 與其他 Tier 的比較

| 特性 | Tier 1 | Tier 2 | Tier 3 (EEIO) |
|------|--------|--------|---------------|
| **精確度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **涵蓋範圍** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **查證接受度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **數據時效性** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **易用性** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **金額適用性** | ❌ | ❌ | ✅ |

---

## 📝 使用範例

### 範例 1: 電子產品採購（台灣 EXIOBASE）⭐ 新增
```
使用者輸入: "購買電腦設備 NT$ 300,000"
Tier 1: 無匹配（台灣無此產品特定係數）⏩
Tier 2: 無匹配（相似度 < 0.70）⏩
Tier 3 檢索 (EXIOBASE TW): "Computer, electronic and optical products" - 相似度 0.82
排放強度: 118,500 kg CO2e/M.EUR (EXIOBASE TW 2022)
計算過程:
  - 金額換算: NT$ 300,000 ÷ 32.5 = 9,231 EUR
  - 轉為百萬歐元: 9,231 ÷ 1,000,000 = 0.009231 M.EUR
  - 排放計算: 0.009231 × 118,500 = 1,094 kg CO2e
數據來源: Tier 3 - EXIOBASE TW (2022) ✅

優勢: 使用台灣特定係數，比美國 USEEIO 更準確
```

### 範例 2: 餐飲服務（台灣 EXIOBASE）⭐ 新增
```
使用者輸入: "員工聚餐餐飲費用 NT$ 50,000"
Tier 1: 無匹配 ⏩
Tier 2: 無匹配 ⏩
Tier 3 檢索 (EXIOBASE TW): "Food and beverage serving services" - 相似度 0.91
排放強度: 32,400 kg CO2e/M.EUR (EXIOBASE TW 2022)
計算結果:
  - 金額換算: NT$ 50,000 ÷ 32.5 = 1,538 EUR
  - 排放計算: (1,538 ÷ 1,000,000) × 32,400 = 50 kg CO2e
數據來源: Tier 3 - EXIOBASE TW (2022) ✅
```

### 範例 3: 軟體服務採購（美國 USEEIO）
```
使用者輸入: "購買 Salesforce 授權 $30,000"
Tier 1: 無匹配（台灣無軟體服務係數）⏩
Tier 2: 無匹配（國際資料庫缺乏軟體服務）⏩
Tier 3 檢索 (EXIOBASE TW): 無匹配（軟體服務未明確分類）⏩
Tier 3 檢索 (USEEIO): "5112: Software publishers" - 相似度 0.75
排放係數: 0.082 kg CO2e/USD (USEEIO 2022)
計算結果: 30,000 × 0.082 = 2,460 kg CO2e
數據來源: Tier 3 - USEEIO (2022) ⚠️

說明: 無台灣資料時，退回使用美國 USEEIO
警告訊息: "使用美國 EEIO 係數，建議要求供應商提供實際排放數據"
```

### 範例 4: 建築服務（比較台灣 vs 美國）
```
使用者輸入: "辦公室裝修工程 NT$ 3,000,000"

方案 A - 使用 EXIOBASE TW (建議):
→ "Construction work" - 相似度 0.88
→ 排放強度: 68,200 kg CO2e/M.EUR
→ 計算: (3,000,000 ÷ 32.5 ÷ 1,000,000) × 68,200 = 6,295 kg CO2e
→ 數據來源: EXIOBASE TW 2022 ✅

方案 B - 使用 USEEIO (參考):
→ "236: Construction" - 相似度 0.88
→ 排放係數: 0.156 kg CO2e/USD
→ 計算: (3,000,000 ÷ 30) × 0.156 = 15,600 kg CO2e
→ 數據來源: USEEIO 2022 ⚠️

差異: 台灣係數較低（可能反映產業結構與能源組合差異）
建議: 使用方案 A（台灣特定）
```

### 範例 5: 電子產品（應使用 Tier 2）
```
使用者輸入: "購買 100 台筆電"
錯誤做法: 估價 NT$ 3,000,000，使用 EEIO → 約 3,000 kg CO2e ❌
正確做法: 使用 Tier 2 Idemat 或產品 LCA 資料 → 250 kg/台 → 25,000 kg CO2e ✅

說明: 雖然結果相近，但實體產品應優先使用過程導向係數，
      而非基於金額的 EEIO 係數。
```

---

## ⚠️ 重要警告

### 不確定性聲明
使用 Tier 3 EEIO 係數時，系統應顯示：

```
⚠️ 此結果基於產業平均排放強度（EEIO 模型）
- 實際排放可能因產品特性、製造過程、供應鏈而顯著不同
- 建議僅用於初步估算或缺乏其他數據時
- 重大排放源應要求供應商提供實際排放數據
- 不確定性範圍: ±50% ~ ±300%
```

### 查證建議
- **篩選階段**: 可使用 EEIO 快速建立清冊
- **正式報告**: 重大排放源應升級至 Tier 2 或 Tier 1
- **第三方查證**: 查證機構可能要求更精確的係數

### 資料更新
- USEEIO 模型約每 3-5 年更新一次
- 需定期檢查 EPA 網站是否有新版本
- 考慮通膨與技術進步的影響

---

## 🚀 擴充計畫

### ✅ 已完成 (2026-01-28)
- [x] 整合 EXIOBASE 台灣資料 (200 產品類別)
- [x] 整合 EXIOBASE 英國資料 (200 產品類別)
- [x] 提取 GHG 排放強度 (kg CO2e per M.EUR)
- [x] 建立 v2 提取腳本 (`extract_exiobase_ghg_v2.py`)
- [x] 更新 README 說明文件

### 短期 (3個月內)
- [ ] 實作 RAG 檢索時的台灣優先邏輯
- [ ] 建立即時匯率 API 整合 (TWD, USD, EUR)
- [ ] 加入通膨調整機制 (2022 → 當前年度)
- [ ] 解析 USEEIO_F_raw_GHGs.csv 寬格式資料
- [ ] 建立 NAICS / EXIOBASE 產業代碼中英對照表
- [ ] 開發單位轉換輔助函數

### 中期 (6個月內)
- [ ] 提取更多 EXIOBASE 國家資料 (優先: JP, CN, KR, US)
- [ ] 整合其他 EEIO 模型:
  - GLORIA (全球投入產出)
  - 日本 3EID
- [ ] 建立不確定性量化模型
- [ ] 開發「EEIO vs LCA」自動選擇邏輯
- [ ] 產品實體單位與金額的混合模式

### 長期 (12個月內)
- [ ] 開發混合 LCA-EEIO 模型
- [ ] 建立台灣專屬 EEIO 模型（若有官方資源）
- [ ] 自動偵測何時應升級至更精確係數
- [ ] 供應鏈多層級追蹤 (進口排放拆解)
- [ ] 與環保署產業資料整合

---

## 🔗 相關資源

- **USEEIO 模型說明**: https://www.epa.gov/land-research/useeio-models-and-tools
- **NAICS 產業分類**: https://www.census.gov/naics/
- **GHG Protocol Scope 3 計算指引**: https://ghgprotocol.org/scope-3-calculation-guidance
- **投入產出模型介紹**: https://ieeio.github.io/

---

---

## 📜 資料授權聲明

| 資料集 | 來源機構 | 授權條款 | 衍生利用 |
|--------|---------|---------|---------|
| USEEIO v2.0 | US EPA (美國環保署) | 美國聯邦政府公共領域 (Public Domain) | 自由使用，無授權限制 |
| EXIOBASE 3 | NTNU / TNO / WU Vienna 等歐洲研究聯盟 | Creative Commons (CC BY-SA 4.0) | 允許（需註明出處，衍生作品須以相同授權釋出） |

**注意事項**：
- USEEIO 為美國聯邦政府產出，不受著作權保護，可自由使用於任何目的。
- EXIOBASE 採用 CC BY-SA 4.0，學術與非商業使用皆允許，但衍生作品須以相同授權釋出並標註原始來源。
- `tier3_embeddings.npy` 為上述資料經 sentence-transformers 模型產生之 384 維向量表示，無法還原原始資料內容。

---

**維護人員**: 張育傑
**最後更新**: 2026-06-18
**下次審查**: 2026-09-18

**重要提醒**: Tier 3 是最後選擇。優先使用 Tier 1 與 Tier 2！
