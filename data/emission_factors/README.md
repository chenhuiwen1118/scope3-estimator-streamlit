# 排放係數資料庫總覽

**更新日期**: 2026-01-28
**架構**: 三級分層 RAG 資料庫
**總檔案數**: 11 個
**總資料量**: 約 5.1 MB

---

## 🏗️ 三級分層架構 (Three-Tier Architecture)

本專案採用 **三級分層 RAG 資料庫**，遵循 GHG Protocol 排放係數選用最佳實踐：

```
┌─────────────────────────────────────────────────┐
│  Tier 1: 本土排放係數 (Local)                    │
│  精確度: ⭐⭐⭐⭐⭐  優先度: 最高                 │
│  檔案數: 1   資料量: 85 KB                       │
└─────────────────────────────────────────────────┘
                    ↓ 無匹配時
┌─────────────────────────────────────────────────┐
│  Tier 2: 國際產業特定係數 (International)        │
│  精確度: ⭐⭐⭐⭐  優先度: 次高                   │
│  檔案數: 8   資料量: 3.2 MB                      │
└─────────────────────────────────────────────────┘
                    ↓ 無匹配時
┌─────────────────────────────────────────────────┐
│  Tier 3: EEIO 通用係數 (EEIO)                    │
│  精確度: ⭐⭐⭐  優先度: 最後兜底                 │
│  檔案數: 2   資料量: 1.8 MB                      │
└─────────────────────────────────────────────────┘
```

---

## 📊 資料庫統計

| Tier | 精確度 | 檔案數 | 資料量 | 涵蓋範圍 | 查證性 |
|------|--------|--------|--------|---------|--------|
| **Tier 1** | ⭐⭐⭐⭐⭐ | 1 | 85 KB | 台灣本土 | ⭐⭐⭐⭐⭐ |
| **Tier 2** | ⭐⭐⭐⭐ | 8 | 3.2 MB | 全球各國 | ⭐⭐⭐⭐⭐ |
| **Tier 3** | ⭐⭐⭐ | 2 | 1.8 MB | 全產業 | ⭐⭐⭐ |
| **總計** | - | **11** | **5.1 MB** | 最廣 | - |

---

## 📁 各層級資料庫內容

### 🥇 Tier 1: 本土排放係數 (Local)
**目錄**: `tier1_local/`

| 檔案 | 來源 | 大小 | 說明 |
|-----|------|------|------|
| TWMOEPA_Preview_Data.csv | 台灣環保署 | 85 KB | 台灣本土產品碳足跡 |

**特性**:
- ✅ 最精確 - 反映台灣本地排放特性
- ✅ 符合台灣電力排放係數
- ✅ 中文名稱，易於匹配
- ✅ 環保署官方認證
- ⚠️ 涵蓋範圍有限

**適用**: 台灣本地產品、台灣供應商、需查證的排放報告

---

### 🥈 Tier 2: 國際產業特定係數 (International)
**目錄**: `tier2_international/`

| 檔案 | 來源 | 大小 | 專長領域 |
|-----|------|------|---------|
| Defra_UK_2025_condensed.xlsx 🆕 | 英國政府 | 1.8 MB | 能源、運輸、廢棄物 |
| GHG_Protocol_Cross_Sector_EF_v2.0_2024.xlsx 🆕 | GHG Protocol | 424 KB | 跨產業標準係數 |
| AGRIBALYSE3.1.1_bio.csv | 法國 ADEME | 27 KB | 有機農業 |
| AGRIBALYSE3.1.1_conv_janv24.csv | 法國 ADEME | 35 KB | 慣行農業 |
| AGRIBALYSE3.1.1_produits.csv | 法國 ADEME | 117 KB | 加工食品 |
| IdematDynamic241.csv | 荷蘭 Delft TU | 318 KB | 工程材料 |
| FootprintCalc1.2-1.csv | - | 249 KB | 產品碳足跡 |
| The_Big_Climate_Database_*.csv | 丹麥 | 107 KB | 消費品 |

**特性**:
- ✅ 產業特定，過程導向
- ✅ 國際認可，查證接受度高
- ✅ 涵蓋廣泛產業
- ✅ 定期更新（年度）
- ⚠️ 需語言翻譯

**適用**: 進口產品、特定產業製程、國際供應鏈

---

### 🥉 Tier 3: EEIO 通用係數 (EEIO)
**目錄**: `tier3_eeio/`

| 檔案 | 來源 | 大小 | 涵蓋部門 |
|-----|------|------|---------|
| USEEIO_F_raw_GHGs.csv | 美國 EPA | 1.8 MB | 9,801 個部門 |
| USEEIO_summary_import_2022.csv | 美國 EPA | 25 KB | 44 個部門 |

**特性**:
- ✅ 涵蓋全產業（最完整）
- ✅ 基於金額計算 (kg/USD)
- ✅ 適合服務業與無實體數量的採購
- ⚠️ 精確度較低（產業平均）
- ⚠️ 基於美國經濟結構
- ⚠️ 查證接受度較低

**適用**: 金額導向採購、服務類別、初期篩選、缺乏特定係數時的兜底方案

---

## 🔍 瀑布式檢索邏輯

```python
def estimate_emission(activity_description: str, amount: float, unit: str):
    """
    三級瀑布式排放係數檢索
    """
    # Step 1: 檢索 Tier 1 (本土係數)
    results_t1 = search_tier1(activity_description)
    if results_t1['confidence'] >= 0.75:
        return calculate(results_t1, amount, unit, tier=1)

    # Step 2: 檢索 Tier 2 (國際產業特定)
    results_t2 = search_tier2(activity_description)
    if results_t2['confidence'] >= 0.70:
        return calculate(results_t2, amount, unit, tier=2)

    # Step 3: 檢索 Tier 3 (EEIO 通用)
    results_t3 = search_tier3(activity_description)
    if results_t3['confidence'] >= 0.60:
        return calculate(results_t3, amount, unit, tier=3)

    # Step 4: 無法匹配
    return {
        'status': 'no_match',
        'recommendation': '建議人工查找或要求供應商提供數據'
    }
```

---

## 🎯 產業覆蓋率分析

| 產業類別 | Tier 1 | Tier 2 | Tier 3 | 總評 |
|---------|--------|--------|--------|------|
| **台灣本土** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **農業食品** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **工程材料** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **能源** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **運輸** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **製造業** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **服務業** | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **消費品** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 🆕 最新更新 (2026-01-28)

### 新增資料庫
- ✅ **Defra UK 2025** (1.8 MB) - 英國政府最新轉換係數
- ✅ **GHG Protocol v2.0** (424 KB) - GHG Protocol 官方跨產業係數

### 架構調整
- ✅ 建立三級分層目錄結構
- ✅ 每層級獨立 README 說明文件
- ✅ 制定瀑布式檢索策略

### 資料來源
- 從 **opchat** 複製: 7 個檔案 (AGRIBALYSE, Idemat, 台灣等)
- 從 **USEEIO** 複製: 2 個檔案 (EEIO 係數)
- 新下載: 2 個檔案 (Defra, GHG Protocol)

---

## 📝 使用範例

### 範例 1: 台灣本土產品（使用 Tier 1）
```
輸入: "購買台灣有機白米 100 kg"
Tier 1 匹配: "有機白米 (台灣)" - 信心度 0.92 ✅
係數: 1.2 kg CO2e/kg
結果: 100 × 1.2 = 120 kg CO2e
來源: Tier 1 - TWMOEPA
```

### 範例 2: 國際航班（使用 Tier 2）
```
輸入: "國際出差台北-倫敦經濟艙"
Tier 1: 無匹配 ⏩
Tier 2 匹配: "International Flight, Economy" - 信心度 0.88 ✅
係數: 0.15 kg CO2e/passenger-km × 9,598 km
結果: 1,440 kg CO2e
來源: Tier 2 - GHG Protocol v2.0
```

### 範例 3: 軟體服務（使用 Tier 3）
```
輸入: "購買 Salesforce 授權 $30,000"
Tier 1: 無匹配 ⏩
Tier 2: 無匹配 ⏩
Tier 3 匹配: "5112: Software publishers" - 信心度 0.75 ✅
係數: 0.082 kg CO2e/USD
結果: 30,000 × 0.082 = 2,460 kg CO2e
來源: Tier 3 - USEEIO (2022)
警告: 使用 EEIO 通用係數，不確定性較高
```

---

## 🚀 下一步工作

### 立即執行 (1週內)
1. [ ] 解析 Defra 與 GHG Protocol Excel 檔案
2. [ ] 統一各層級資料格式 (CSV)
3. [ ] 建立統一 Schema: `source, tier, category, item_name, unit, ef_value, gwp, year`

### 短期 (1個月內)
4. [ ] 為所有係數生成 multilingual embeddings
5. [ ] 建立三個獨立 FAISS 向量索引 (tier1.index, tier2.index, tier3.index)
6. [ ] 實作瀑布式檢索邏輯
7. [ ] 測試檢索性能與準確度

### 中期 (3個月內)
8. [ ] 擴充 Tier 1: 台灣產業溫室氣體排放係數管理表 6.0.4
9. [ ] 擴充 Tier 2: ELCD, NREL, AusLCI
10. [ ] 建立資料自動更新機制

---

## 📄 授權聲明

### 可自由使用（需標註來源）
- ✅ TWMOEPA (台灣政府開放資料)
- ✅ Defra UK (英國政府開放資料)
- ✅ GHG Protocol (免費使用，需標註)
- ✅ USEEIO (美國政府開放資料)
- ✅ AGRIBALYSE (法國政府開放資料)
- ✅ Big Climate DB (開放資料)

### 需確認授權
- ⚠️ Idemat (荷蘭 Delft TU，需確認學術使用條款)
- ⚠️ FootprintCalc (來源與授權未確認)

---

## 📖 詳細說明文件

- [Tier 1 說明](tier1_local/README.md) - 台灣本土係數使用指南
- [Tier 2 說明](tier2_international/README.md) - 國際產業特定係數使用指南
- [Tier 3 說明](tier3_eeio/README.md) - EEIO 通用係數使用指南與限制

---

## 📞 聯絡資訊

**維護人員**: 張育傑
**專案**: 氣候署範疇三排放源估算輔助系統
**最後更新**: 2026-01-28
**下次審查**: 2026-04-28

---

**重要提醒**:
1. 優先使用 Tier 1 > Tier 2 > Tier 3
2. 重大排放源應人工覆核或要求供應商提供實際數據
3. 定期更新各層級資料庫
4. 記錄使用的係數來源與 Tier 層級，以便查證
