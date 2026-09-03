# 📊 Scope 3 訓練資料收集策略

**專案**：Scope 3 Estimator - 訓練資料收集計畫
**版本**：1.0
**建立日期**：2026-01-29
**狀態**：規劃中

---

## 🎯 目標

收集**真實企業採購交易文字描述**資料，用於：
1. **LLM 微調**（階段 3）：訓練模型理解企業採購語言
2. **Embedding 訓練**（階段 2）：增強檢索準確度
3. **GHG 分類器訓練**（階段 1）：提升 15 類別分類準確度
4. **系統測試與驗證**：建立真實場景測試集

---

## ⚠️ 核心原則（非常重要！）

### ❌ 不要這樣做
```
直接搜尋：scope 3 dataset
直接搜尋：carbon footprint transaction data
```
→ **幾乎找不到可用的交易文字資料**

### ✅ 正確策略：拆成三層

1. **Layer 1：交易／採購「文字描述」**（給 LLM 用）
   - 品項名稱、描述文字
   - 供應商資訊（已去識別）
   - 交易金額

2. **Layer 2：活動／產業分類**（給 RAG / mapping 用）
   - 商品類別碼
   - 產業代碼
   - 會計科目

3. **Layer 3：排放係數或產業對應**（給估算用）
   - 我們已經有（9,257 筆排放係數）
   - 這部分不缺

**我們缺的是 Layer 1 與 Layer 2！**

---

## 📋 Scope 3 各類別 × 搜尋策略

### 🟢 Category 1 & 2：採購商品 & 資本財

**優先級**：🔴 **最高**（佔 Scope 3 的 50-80%）

#### 搜尋關鍵字（Kaggle / Google Dataset Search）

**基礎關鍵字**：
```
procurement dataset
purchase order dataset
purchase description text
invoice line item dataset
transaction description dataset
spend analysis dataset
```

**進階關鍵字**（更接近企業資料）：
```
procurement text classification
purchase order description
accounts payable transaction dataset
supplier transaction dataset
```

#### 預期資料格式

```csv
item_id, item_description, category, amount, supplier_id, date
001, "Industrial machinery parts", "Equipment", 50000, SUP123, 2023-01-15
002, "Office stationery supplies", "Office Supplies", 1200, SUP456, 2023-01-16
003, "Steel materials for production", "Raw Materials", 85000, SUP789, 2023-01-17
```

**關鍵欄位**：
- ✅ `item_description`：**最重要！** 給 LLM 學習企業採購語言
- ✅ `category`：可作為 GHG 分類訓練標籤
- ✅ `amount`：協助判斷 Category 1 vs 2

#### 資料用途
1. **LLM 微調**：學習企業如何描述採購品項
2. **Embedding 訓練**：增強「查詢文字 → 排放係數」的檢索
3. **GHG 分類器**：訓練「描述文字 → 15 類別」
4. **會計邏輯訓練**：學習「品項 → 會計科目」的對應

---

### 🟢 Category 2：資本財（專項）

**注意**：公開資料不會直接寫「資本資產」，要換說法

#### 搜尋關鍵字

```
fixed asset dataset
asset purchase dataset
capital expenditure dataset
equipment procurement dataset
machinery purchase dataset
IT asset procurement dataset
```

#### 預期資料格式

```csv
asset_id, asset_description, asset_type, purchase_amount, useful_life, date
A001, "CNC Machining Center", "Machinery", 800000, 10, 2023-02-01
A002, "Dell PowerEdge Server R740", "IT Equipment", 150000, 5, 2023-02-05
A003, "Forklift Truck 3-ton", "Transportation", 350000, 8, 2023-02-10
```

**關鍵欄位**：
- ✅ `asset_type`：協助判斷是否屬於 Category 2
- ✅ `useful_life`：使用年限（判斷固定資產的依據）
- ✅ `purchase_amount`：金額門檻判斷

#### 資料用途
1. **Category 1 vs 2 分類器**：訓練模型判斷「購買商品」vs「資本財」
2. **金額門檻學習**：學習不同企業的資本化政策

---

### 🟢 Category 4 & 9：運輸與物流

**優先級**：🟡 **中高**（資料品質好、容易取得）

#### 搜尋關鍵字

```
freight invoice dataset
logistics transaction dataset
shipping description dataset
transportation cost dataset
delivery service invoice dataset
```

**進階（學術／政府）**：
```
transport activity dataset
freight movement dataset
logistics service procurement dataset
```

#### 預期資料格式

```csv
shipment_id, service_description, transport_mode, distance_km, weight_kg, cost, date
S001, "Sea freight Shanghai to Kaohsiung", "Sea", 850, 15000, 12000, 2023-03-01
S002, "Air cargo express to Japan", "Air", 2200, 500, 35000, 2023-03-02
S003, "Domestic truck delivery Taipei-Taichung", "Road", 180, 2000, 8000, 2023-03-03
```

**關鍵欄位**：
- ✅ `transport_mode`：運輸方式（海運、空運、陸運）
- ✅ `distance_km` + `weight_kg`：計算噸-公里
- ✅ `service_description`：LLM 學習運輸描述語言

#### 資料用途
1. **LLM 訓練**：辨識「這是 Scope 3 - Transportation」
2. **運輸模式分類**：自動判斷運輸方式
3. **排放計算**：距離 × 重量 × 運輸排放係數

---

### 🟢 Category 6 & 7：商務旅行 & 員工通勤

**優先級**：🟡 **中**（資料形式接近真實企業）

#### 搜尋關鍵字

```
business travel expense dataset
travel expense report dataset
corporate travel invoice dataset
employee commuting survey dataset
travel reimbursement dataset
```

#### 預期資料格式

```csv
expense_id, description, category, transport_mode, distance, amount, date
E001, "Flight to Tokyo for client meeting", "Business Travel", "Air", 2100, 15000, 2023-04-01
E002, "Hotel accommodation Tokyo 3 nights", "Business Travel", "Hotel", 0, 12000, 2023-04-02
E003, "Taxi to airport", "Business Travel", "Taxi", 25, 800, 2023-04-01
```

**關鍵欄位**：
- ✅ `description`：出差描述（LLM 訓練）
- ✅ `transport_mode`：交通工具分類
- ✅ `distance`：計算排放

---

### 🟢 Category 1：服務型支出（能源、維修）

**優先級**：🟢 **低中**（文字形式接近真實發票）

#### 搜尋關鍵字

```
utility bill dataset
energy invoice dataset
service contract dataset
maintenance service invoice dataset
facility management invoice dataset
```

#### 預期資料格式

```csv
invoice_id, service_description, service_type, amount, unit, date
I001, "Electricity consumption 5000 kWh", "Utility", 15000, "kWh", 2023-05-01
I002, "Preventive maintenance for HVAC system", "Maintenance", 25000, "service", 2023-05-05
I003, "Water supply 500 m3", "Utility", 3000, "m3", 2023-05-01
```

---

## 🗂️ 資料平台與搜尋策略

### 1️⃣ Kaggle（首選）

**URL**：https://www.kaggle.com/datasets

**搜尋策略**：

**步驟 1：基礎搜尋**
```
procurement
purchase order
invoice
transaction description
expense report
```

**步驟 2：篩選條件**
- Language: English
- File type: CSV / JSON
- Sort by: Relevance / Most votes

**步驟 3：進階搜尋**
```
procurement nlp
purchase text classification
transaction categorization
spend analytics
```

**預期結果類型**：
- ✅ 企業採購資料（去識別）
- ✅ 政府公開採購
- ✅ 研究用合成資料

---

### 2️⃣ Google Dataset Search（非常強）

**URL**：https://datasetsearch.research.google.com/

**搜尋策略**：

**高品質關鍵字**：
```
purchase order description dataset
open procurement text dataset
invoice line item text dataset
transaction text classification
supplier spending dataset
```

**預期來源**：
- OECD / EU / World Bank
- 政府採購（OCDS - Open Contracting Data Standard）
- 學術機構開放資料

**特別推薦**：
- **OCDS（Open Contracting Data Standard）**
  - 全球政府採購資料標準
  - 包含：tender description, contract description
  - 格式：JSON / CSV
  - 網址：https://www.open-contracting.org/data/

---

### 3️⃣ GitHub（研究取向）

**URL**：https://github.com/search?type=repositories

**搜尋策略**：

```
procurement nlp dataset
transaction text classification
spend analysis nlp
invoice text extraction
purchase order classification
```

**預期結果**：
- ✅ 研究論文附帶資料集
- ✅ 合成資料生成腳本
- ✅ 預處理腳本

**範例 Repositories**：
- `spend-classification-dataset`
- `procurement-text-nlp`
- `invoice-line-item-classification`

---

### 4️⃣ 其他資料來源

#### (A) 政府公開採購平台

**台灣**：
- 政府電子採購網：https://web.pcc.gov.tw/
- 資料格式：標案名稱、採購項目、金額
- 用途：訓練「公部門採購語言」

**國際**：
- EU TED (Tenders Electronic Daily)
- USA SAM (System for Award Management)

#### (B) 學術資料集

**搜尋平台**：
- UCI Machine Learning Repository
- Zenodo
- figshare

**關鍵字**：
```
procurement dataset
purchasing dataset
transaction dataset
```

---

## 📊 資料收集優先級

### 🔴 Phase 1：立即執行（Week 1-2）

1. **Kaggle 採購資料集**
   - 搜尋：`procurement dataset`, `purchase order`
   - 目標：找到 3-5 個高品質資料集
   - 總量目標：10,000+ 筆採購文字描述

2. **政府公開採購**
   - 台灣政府電子採購網（中文）
   - OCDS 標準資料（英文）
   - 目標：5,000+ 筆

**總目標 Phase 1**：**15,000+ 筆採購文字**

---

### 🟡 Phase 2：短期執行（Week 3-4）

3. **Google Dataset Search**
   - 搜尋：高品質學術／政府資料
   - 目標：補充特定類別（運輸、資本財）
   - 總量目標：5,000+ 筆

4. **GitHub 研究資料**
   - 尋找預處理腳本
   - 學習合成資料方法
   - 目標：找到 2-3 個研究專案

**總目標 Phase 2**：**累積 20,000+ 筆**

---

### 🟢 Phase 3：中期執行（Month 2-3）

5. **合成資料生成**
   - 基於真實資料的模板
   - 結合 LLM 生成採購描述
   - 目標：生成 50,000+ 筆高品質合成資料

6. **用戶回饋資料**
   - 系統上線後收集用戶查詢
   - 用戶標註正確係數
   - 目標：1,000+ 筆真實查詢

**總目標 Phase 3**：**累積 70,000+ 筆**

---

## 🛠️ 資料處理流程

### 步驟 1：資料下載與清理

```python
# 腳本：scripts/download_training_data.py

def download_kaggle_dataset(dataset_name):
    """從 Kaggle 下載資料集"""
    # 使用 Kaggle API

def clean_procurement_data(df):
    """清理採購資料"""
    # 1. 移除重複
    # 2. 標準化欄位名稱
    # 3. 處理缺失值
    # 4. 文字清理
```

### 步驟 2：資料標準化

**統一欄位格式**：
```csv
id, description, category, amount, supplier, date, source
001, "Steel pipes 100mm x 6m", "Raw Materials", 50000, "SUP123", 2023-01-01, "kaggle_procurement_v1"
002, "Office chairs ergonomic", "Office Furniture", 15000, "SUP456", 2023-01-02, "gov_procurement_tw"
```

### 步驟 3：GHG 類別標註

**自動標註**（使用我們剛建立的 GHGCategoryClassifier）：
```python
classifier = GHGCategoryClassifier()

for item in procurement_data:
    result = classifier.classify(
        item_name=item['description'],
        amount=item['amount']
    )
    item['ghg_category'] = result['ghg_category']
    item['confidence'] = result['confidence']
```

### 步驟 4：人工審核

**優先審核**：
- 信心度 < 70% 的項目
- 金額 > 100,000 的項目（高影響）
- 模糊分類（Category 1 vs 2）

**目標**：
- Phase 1：審核 1,000 筆（建立 Gold Standard）
- Phase 2：審核 500 筆（驗證自動標註）

---

## 📈 預期成果

### 資料集規模（6 個月目標）

| 階段 | 資料來源 | 數量 | 累積總量 |
|------|----------|------|----------|
| Phase 1 | Kaggle + 政府採購 | 15,000 | 15,000 |
| Phase 2 | Google Dataset + GitHub | 5,000 | 20,000 |
| Phase 3 | 合成資料 + 用戶回饋 | 50,000 | 70,000 |

### 資料品質指標

- ✅ **覆蓋率**：15 個 Scope 3 類別全覆蓋
- ✅ **準確度**：人工審核的 Gold Standard 達 1,000+ 筆
- ✅ **多樣性**：包含中英文、不同產業、不同金額範圍
- ✅ **真實性**：至少 30% 來自真實企業／政府採購

---

## 🔗 相關文件

- 專案路線圖：`docs/ROADMAP_3-6_MONTHS.md`
- 工作日誌：`docs/WORKLOG.md`
- 當前狀態：`docs/STATUS.md`
- GHG 分類器：`src/classification/ghg_classifier.py`

---

## 📞 聯絡資訊

- **專案負責人**：張育傑 教授
- **Email**：yjchang@utaipei.edu.tw

---

<div align="center">
  <p><strong>📊 Data is the Foundation of AI</strong></p>
  <p><em>Last Updated: 2026-01-29 by Claude</em></p>
</div>
