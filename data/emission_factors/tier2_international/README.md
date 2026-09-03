# Tier 2: 國際產業特定排放係數資料庫

**精確度等級**: 高 ⭐⭐⭐⭐
**優先順序**: 第二優先（當 Tier 1 無匹配時）
**區域**: 全球各國
**用途**: 產業特定、過程導向的排放係數

---

## 🎯 使用原則

當 **Tier 1 (台灣本土係數)** 無法匹配時，使用本層級的國際產業特定係數。
這些資料來自：
- 各國政府官方資料
- 國際標準組織 (如 GHG Protocol)
- 學術機構的生命週期評估 (LCA) 資料

**Tier 2 的優勢**:
- 產業特定，比 EEIO 更精確
- 考量實際製造過程
- 國際認可，可用於查證

---

## 📁 資料庫清單

### 1. Defra_UK_2025_condensed.xlsx (1.8 MB) 🆕

#### 基本資訊
- **來源**: UK Department for Environment, Food & Rural Affairs (英國環境食品與鄉村事務部)
- **年度**: 2025 (最新版)
- **網址**: https://www.gov.uk/government/collections/government-conversion-factors-for-company-reporting
- **語言**: 英文
- **授權**: 英國政府開放資料，可自由使用

#### 資料內容
- **燃料與能源**:
  - 各類燃料燃燒排放 (天然氣、柴油、汽油等)
  - 電力排放係數 (英國與國際)
  - 熱能與蒸汽
- **運輸**:
  - 道路運輸 (汽車、貨車、巴士)
  - 航空 (國內與國際)
  - 海運
  - 鐵路
- **廢棄物處理**:
  - 掩埋
  - 焚化
  - 回收
- **水消耗與廢水處理**

#### 資料格式
- Excel 工作表，每個類別一個分頁
- 包含 CO2, CH4, N2O 的個別排放與 CO2e 總量
- 提供不同 GWP 版本 (AR4, AR5, AR6)

#### 適用情境
- ✅ 能源與電力採購
- ✅ 運輸活動（出差、物流）
- ✅ 廢棄物處理
- ✅ 水資源消耗

---

### 2. GHG_Protocol_Cross_Sector_EF_v2.0_2024.xlsx (424 KB) 🆕

#### 基本資訊
- **來源**: GHG Protocol (世界資源研究所 WRI 與世界企業永續發展委員會 WBCSD)
- **版本**: 2.0 (2024年5月)
- **網址**: https://ghgprotocol.org/calculation-tools
- **語言**: 英文
- **授權**: 免費使用，需標註來源

#### 資料內容
- **跨產業通用排放係數**:
  - 固定燃燒 (Stationary Combustion)
  - 移動燃燒 (Mobile Combustion)
  - 購買電力 (Purchased Electricity)
- **單位轉換表**
- **GWP 值** (AR4, AR5, AR6)

#### 資料特性
- ✅ GHG Protocol 官方認可
- ✅ 全球企業普遍使用
- ✅ 查證機構認可度高
- ✅ 包含最新 GWP 值

#### 適用情境
- ✅ 範疇1：固定與移動燃燒
- ✅ 範疇2：購買電力
- ✅ 範疇3：上下游運輸
- ✅ 需要查證的排放報告

---

### 3. AGRIBALYSE 系列 (法國農業資料)

#### AGRIBALYSE3.1.1_bio.csv (27 KB)
- **來源**: 法國環境與能源管理署 (ADEME)
- **版本**: 3.1.1
- **內容**: 有機農業產品 LCA 資料
- **適用**: 有機食品、農產品

#### AGRIBALYSE3.1.1_conv_janv24.csv (35 KB)
- **內容**: 慣行農業產品 LCA 資料
- **適用**: 一般農產品

#### AGRIBALYSE3.1.1_produits.csv (117 KB)
- **內容**: 加工食品與餐飲產品
- **適用**: 食品加工、餐飲服務

#### 資料特性
- ✅ 歐洲最權威的農業 LCA 資料庫
- ✅ 涵蓋從農場到餐桌的完整生命週期
- ✅ 區分有機與慣行，更精確
- ✅ 適合食品相關產業

#### 適用情境
- ✅ 農產品採購
- ✅ 食品加工原料
- ✅ 餐飲業供應鏈
- ✅ 有機產品認證

---

### 4. IdematDynamic241.csv (318 KB)

#### 基本資訊
- **來源**: 荷蘭 Delft University of Technology
- **版本**: 2024.1
- **專長**: 工程材料與製造過程

#### 資料內容
- **材料**:
  - 金屬 (鋼、鋁、銅、鈦等)
  - 塑膠與聚合物
  - 玻璃與陶瓷
  - 複合材料
- **製造過程**:
  - 射出成型
  - 機械加工
  - 焊接
  - 表面處理

#### 適用情境
- ✅ 製造業原料採購
- ✅ 產品設計與開發
- ✅ 材料選擇評估
- ✅ 工程專案

---

### 5. FootprintCalc1.2-1.csv (249 KB)

#### 基本資訊
- **來源**: 不明 (可能是 Carbon Footprint Calculator)
- **內容**: 通用產品碳足跡係數

#### 適用情境
- ✅ 一般消費性產品
- ✅ 缺乏特定係數時的備援

---

### 6. The_Big_Climate_Database_version_1_1_download_english.csv (107 KB)

#### 基本資訊
- **來源**: 丹麥 The Big Climate Database
- **版本**: 1.1 (英文版)
- **專長**: 消費性產品氣候影響

#### 資料內容
- 食品與飲料
- 家用產品
- 個人護理品
- 電子產品

#### 適用情境
- ✅ 零售業
- ✅ 消費品採購
- ✅ 辦公室用品

---

## 🔍 檢索策略

### RAG 向量檢索設定
```python
# Tier 2 檢索參數建議
tier2_config = {
    "top_k": 10,  # 多檢索幾個候選
    "similarity_threshold": 0.70,  # 中等門檻
    "weight": 0.8,  # 次高權重
    "language": "multilingual"  # 支援多語言
}
```

### 檢索邏輯
1. **觸發條件**: Tier 1 無匹配或相似度 < 0.75
2. **檢索 Tier 2**: 搜尋所有國際資料庫
3. **資料源優先順序**:
   - GHG Protocol (查證認可度最高)
   - Defra (政府官方)
   - AGRIBALYSE (農業專業)
   - Idemat (工程材料)
   - 其他
4. **信心度判斷**:
   - 若相似度 ≥ 0.70 → 使用 Tier 2 係數 ✅
   - 若相似度 < 0.70 → 轉至 Tier 3 ⏩

---

## 📊 資料品質比較

| 資料庫 | 完整性 | 精確度 | 查證性 | 更新頻率 |
|--------|--------|--------|--------|----------|
| **Defra UK** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 年度更新 |
| **GHG Protocol** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 不定期 |
| **AGRIBALYSE** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 年度更新 |
| **Idemat** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 年度更新 |
| **Big Climate DB** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 不定期 |
| **FootprintCalc** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | 未知 |

---

## 📝 使用範例

### 範例 1: 能源採購 (Defra)
```
使用者輸入: "天然氣消耗 10,000 m³"
Tier 1: 無匹配 ⏩
Tier 2 檢索: "Natural Gas" - 相似度 0.95 (Defra)
排放係數: 2.02 kg CO2e/m³
計算結果: 10,000 × 2.02 = 20,200 kg CO2e
數據來源: Tier 2 - Defra UK 2025 ✅
```

### 範例 2: 航空差旅 (GHG Protocol)
```
使用者輸入: "國際航班台北-倫敦經濟艙"
Tier 1: 無匹配 ⏩
Tier 2 檢索: "International Flight, Economy" - 相似度 0.88 (GHG Protocol)
排放係數: 0.15 kg CO2e/passenger-km
距離: 9,598 km
計算結果: 9,598 × 0.15 = 1,440 kg CO2e
數據來源: Tier 2 - GHG Protocol v2.0 ✅
```

### 範例 3: 有機食材 (AGRIBALYSE)
```
使用者輸入: "有機番茄 500 kg"
Tier 1: 無台灣資料 ⏩
Tier 2 檢索: "Tomato, organic" - 相似度 0.92 (AGRIBALYSE_bio)
排放係數: 0.3 kg CO2e/kg
計算結果: 500 × 0.3 = 150 kg CO2e
數據來源: Tier 2 - AGRIBALYSE 3.1.1 ✅
```

---

## 🚀 資料擴充計畫

### 短期 (3個月內)
- [ ] 解析 Defra 與 GHG Protocol Excel 檔案
- [ ] 建立統一的 CSV 格式
- [ ] 為每筆資料加上中文翻譯

### 中期 (6個月內)
- [ ] 下載 ELCD (歐盟資料庫)
- [ ] 整合 NREL (美國再生能源實驗室)
- [ ] 加入澳洲 AusLCI

### 長期 (12個月內)
- [ ] 定期更新 Defra 年度版本
- [ ] 追蹤 GHG Protocol 更新
- [ ] 建立自動化更新機制

---

---

## 📜 資料授權聲明

| 資料集 | 來源機構 | 授權條款 | 衍生利用 |
|--------|---------|---------|---------|
| Defra UK 2025 | UK Department for Environment, Food & Rural Affairs | UK Open Government Licence v3.0 | 允許（需註明出處 "© Crown copyright"） |
| GHG Protocol v2.0 | World Resources Institute / WBCSD | 免費使用 | 允許（需標註 GHG Protocol 為來源） |
| AGRIBALYSE 3.1.1 | ADEME (法國環境與能源管理局) | Etalab Open Licence 2.0 | 允許（需註明出處） |
| Big Climate Database | CONCITO (丹麥綠色智庫) | CC BY-SA 4.0 | 允許（衍生作品須以相同授權釋出，需註明出處） |
| Idemat 2024 | TU Delft (荷蘭台夫特理工大學) | 待確認（可能含 NC 非商業限制） | ⚠️ 商業利用前須確認授權 |
| FootprintCalc | 待確認 | 待確認 | ⚠️ 使用前須確認授權 |

**注意事項**：
- Big Climate Database 採用 CC BY-SA 4.0，其 ShareAlike 條款要求衍生作品以相同授權釋出。本專案若公開使用該資料之衍生檔案（如 `tier2_metadata.csv` 中 Big Climate DB 欄位），須以 CC BY-SA 4.0 授權。
- Idemat 授權條款尚未確認，建議聯繫 TU Delft 確認是否允許學術/非商業衍生利用。
- `tier2_embeddings.npy` 為上述資料經 sentence-transformers 模型產生之 384 維向量表示，無法還原原始資料內容。

---

**維護人員**: 張育傑
**最後更新**: 2026-06-18
**下次審查**: 2026-09-18
