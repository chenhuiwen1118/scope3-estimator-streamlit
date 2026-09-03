# EXIOBASE MRIO 資料庫分析報告

**發現日期**: 2026-01-28
**資料來源**: `C:\Users\yjchang\USEEIO\import_emission_factors\data\IOT_2022_pxp\`
**資料類型**: Multi-Regional Input-Output (MRIO) - 多區域投入產出表
**資料庫**: EXIOBASE
**基準年**: 2022

---

## 🎉 重大發現

在你的 USEEIO 專案中發現了 **EXIOBASE 2022** 完整資料！這是全球最權威的 MRIO 資料庫之一。

### 為什麼這很重要？

1. **包含台灣資料** 🇹🇼
   - TW (Taiwan) 有完整的 200 個產品類別 EEIO 係數
   - 比美國 USEEIO 更適合台灣企業使用！
   - 反映台灣的經濟與技術結構

2. **包含英國資料** 🇬🇧
   - GB (Great Britain) 有完整的 200 個產品類別
   - 可以補充或對照 Defra UK 資料
   - EEIO 係數反映整體經濟結構

3. **全球覆蓋**
   - 49 個國家/地區
   - 涵蓋台灣主要貿易夥伴（中國、日本、韓國、美國、歐盟等）
   - 適用於國際供應鏈分析

---

## 📊 資料庫規格

| 項目 | 內容 |
|------|------|
| **資料庫名稱** | EXIOBASE (推測) |
| **版本/年度** | 2022 |
| **國家/地區數** | 49 個 |
| **產品分類** | 200 個（EXIOBASE 產品分類） |
| **產業分類** | 164 個 |
| **環境指標** | 1,114 種 |
| **檔案大小** | 44 MB (F.txt - 環境延伸矩陣) |
| **資料點總數** | 9,800 列 × 1,114 指標 = 1,090 萬個資料點 |

---

## 🌍 涵蓋國家（49個）

### 重點國家（與台灣相關）
- 🇹🇼 **TW - 台灣** ⭐⭐⭐⭐⭐
- 🇬🇧 **GB - 英國** ⭐⭐⭐⭐⭐
- 🇨🇳 CN - 中國
- 🇯🇵 JP - 日本
- 🇰🇷 KR - 韓國
- 🇺🇸 US - 美國
- 🇩🇪 DE - 德國
- 🇫🇷 FR - 法國

### 完整國家列表
1. AT - 奧地利
2. AU - 澳洲
3. BE - 比利時
4. BG - 保加利亞
5. BR - 巴西
6. CA - 加拿大
7. CH - 瑞士
8. CN - 中國
9. CY - 賽普勒斯
10. CZ - 捷克
11. DE - 德國
12. DK - 丹麥
13. EE - 愛沙尼亞
14. ES - 西班牙
15. FI - 芬蘭
16. FR - 法國
17. **GB - 🇬🇧 英國** ⭐
18. GR - 希臘
19. HR - 克羅埃西亞
20. HU - 匈牙利
21. ID - 印尼
22. IE - 愛爾蘭
23. IN - 印度
24. IT - 義大利
25. JP - 日本
26. KR - 韓國
27. LT - 立陶宛
28. LU - 盧森堡
29. LV - 拉脫維亞
30. MT - 馬爾他
31. MX - 墨西哥
32. NL - 荷蘭
33. NO - 挪威
34. PL - 波蘭
35. PT - 葡萄牙
36. RO - 羅馬尼亞
37. RU - 俄羅斯
38. SE - 瑞典
39. SI - 斯洛維尼亞
40. SK - 斯洛伐克
41. TR - 土耳其
42. **TW - 🇹🇼 台灣** ⭐
43. US - 美國
44. WA - 亞洲其他
45. WE - 歐洲其他
46. WF - 非洲其他
47. WL - 美洲其他
48. WM - 中東其他
49. ZA - 南非

---

## 📁 檔案結構

```
IOT_2022_pxp/IOT_2022_pxp/
├── satellite/
│   ├── F.txt                    (44 MB) 環境延伸矩陣 ⭐
│   ├── F_Y.txt                  (889 KB) 最終需求環境影響
│   ├── S.txt                    (46 MB) 社會延伸矩陣
│   ├── M.txt                    (140 MB) 材料流動矩陣
│   ├── unit.txt                 (68 KB) 指標單位
│   └── file_parameters.json     (1.6 KB) 檔案參數
├── products.txt                 (201 行) 產品分類
├── industries.txt               (164 行) 產業分類
├── A.txt                        技術係數矩陣
└── finaldemands.txt             最終需求
```

---

## 🔬 GHG 排放指標

### 已確認的 GHG 指標
1. **CO2 - combustion - air** (kg)
2. **CH4 - combustion - air** (kg)
3. **N2O - combustion - air** (kg)
4. **CO2 - non combustion - Cement production - air** (kg)
5. **CO2 - non combustion - Lime production - air** (kg)
6. **HFC - air** (kg CO2-eq)
7. **PFC - air** (kg CO2-eq)
8. **CO2 - agriculture - peat decay - air** (kg)
9. **CO2 - waste - biogenic - air** (kg)
10. **CO2 - waste - fossil - air** (kg)

### 其他環境指標（超過 1,100 種）
- 空氣污染物：SOx, NOx, PM2.5, PM10, NMVOC 等
- 重金屬：As, Cd, Cr, Cu, Hg, Ni, Pb 等
- 持久性有機污染物：PCBs, PCDD/F, HCB 等
- 水資源使用
- 土地利用
- 材料使用
- 社會指標：就業、工資等

---

## 🎯 資料用途與整合建議

### 1. 優先用途：提供**台灣特定的 EEIO 係數** ⭐⭐⭐⭐⭐

#### 為什麼重要？
- 目前 Tier 3 只有美國 USEEIO
- 台灣與美國的產業結構、能源組成、製造技術差異很大
- 使用 TW 係數比 US 係數更精確

#### 整合到 Tier 3
```
tier3_eeio/
├── USEEIO_*.csv             (美國 EPA)
├── EXIOBASE_TW_2022.csv     (台灣 - 新增) 🆕
└── EXIOBASE_GB_2022.csv     (英國 - 新增) 🆕
```

#### 檢索策略調整
```python
# 修改後的 Tier 3 檢索邏輯
def search_tier3(activity, amount, region='TW'):
    # Step 1: 優先使用台灣 EXIOBASE
    if region == 'TW':
        results = search_exiobase_tw(activity)
        if results['confidence'] >= 0.60:
            return results

    # Step 2: 如果是英國相關，使用英國 EXIOBASE
    if region == 'GB' or 'UK' in activity:
        results = search_exiobase_gb(activity)
        if results['confidence'] >= 0.60:
            return results

    # Step 3: 回退到美國 USEEIO
    return search_useeio(activity)
```

---

### 2. 補充用途：國際供應鏈分析

#### 應用場景
- **情境 1**: 從中國進口原料
  - 使用 CN (中國) 的 EEIO 係數
  - 反映中國製造的實際排放

- **情境 2**: 出口到歐盟
  - 評估產品在歐盟的生命週期排放
  - 使用目標國家的 EEIO 係數

- **情境 3**: 跨國供應鏈盤查
  - 針對不同國家的供應商使用對應國家係數
  - 更精確的 Scope 3 類別 1（採購） 與類別 4（上游運輸）

---

### 3. 進階用途：MRIO 分析（未來開發）

#### 完整 MRIO 分析
EXIOBASE 包含完整的投入產出表（A矩陣）與環境延伸（F矩陣），可以進行：

1. **供應鏈追溯**
   - 計算產品的上游供應鏈排放
   - 識別排放熱點（hotspot analysis）

2. **國際貿易的隱含排放**
   - 計算進口商品的境外排放（embodied emissions）
   - 區分生產地排放 vs 消費地排放

3. **情境分析**
   - 評估供應鏈變更的影響
   - 比較不同採購國家的排放差異

#### 技術需求
- 需要 Python pymrio 或 R 套件
- 計算量較大，適合批次分析
- 建議作為進階功能（第二階段開發）

---

## 🔧 資料提取與轉換計畫

### 階段 1: 提取台灣與英國 GHG 係數（立即執行）

#### 目標
- 從 F.txt 提取 TW 和 GB 的 CO2, CH4, N2O 排放係數
- 轉換為與 USEEIO 一致的格式

#### 步驟
```python
# 1. 讀取 F.txt
import pandas as pd

F = pd.read_csv('satellite/F.txt', sep='\t', index_col=0, header=[0,1])
products = pd.read_csv('products.txt', sep='\t')

# 2. 篩選 GHG 指標
ghg_rows = ['CO2 - combustion - air', 'CH4 - combustion - air', 'N2O - combustion - air']
ghg_data = F.loc[ghg_rows]

# 3. 提取 TW 和 GB 列
tw_cols = [col for col in ghg_data.columns if col[0] == 'TW']
gb_cols = [col for col in ghg_data.columns if col[0] == 'GB']

# 4. 轉換為標準格式
tw_ef = pd.DataFrame({
    'Country': 'TW',
    'Product': products['Name'],
    'CO2_kg': ghg_data[tw_cols].loc['CO2 - combustion - air'].values,
    'CH4_kg': ghg_data[tw_cols].loc['CH4 - combustion - air'].values,
    'N2O_kg': ghg_data[tw_cols].loc['N2O - combustion - air'].values
})

# 5. 匯出為 CSV
tw_ef.to_csv('EXIOBASE_TW_2022_GHG.csv', index=False)
```

#### 預期輸出
- `EXIOBASE_TW_2022_GHG.csv` (200 行 × 產品)
- `EXIOBASE_GB_2022_GHG.csv` (200 行 × 產品)

---

### 階段 2: 整合到三級架構（1週內）

#### 更新 Tier 3 結構
```
tier3_eeio/
├── README.md                              (更新)
├── USEEIO_F_raw_GHGs.csv                  (美國，9,801部門)
├── USEEIO_summary_import_2022.csv         (美國，44部門)
├── EXIOBASE_TW_2022_GHG.csv              (台灣，200產品) 🆕
└── EXIOBASE_GB_2022_GHG.csv              (英國，200產品) 🆕
```

#### 更新檢索邏輯
- 台灣企業優先使用 EXIOBASE_TW
- 英國相關活動使用 EXIOBASE_GB
- 其他情況使用 USEEIO

---

### 階段 3: 擴充其他國家（未來）

根據需要，可以提取：
- CN (中國) - 台灣最大貿易夥伴
- JP (日本) - 重要供應鏈夥伴
- US (美國) - 比較 EXIOBASE vs USEEIO
- 其他主要貿易夥伴

---

## 📊 與現有資料的比較

| 資料庫 | 區域 | 部門數 | 年度 | 精確度 | 用途 |
|--------|------|--------|------|--------|------|
| **USEEIO** | 美國 | 9,801 | 2017-2022 | 中 | 美國經濟結構 |
| **EXIOBASE TW** 🆕 | 台灣 | 200 | 2022 | 中-高 | 台灣經濟結構 ⭐ |
| **EXIOBASE GB** 🆕 | 英國 | 200 | 2022 | 中-高 | 英國經濟結構 |
| **Defra UK** | 英國 | - | 2025 | 高 | 特定活動（能源、運輸） |

### 互補性
- **EXIOBASE TW**: 提供台灣的產業平均排放強度（EEIO）
- **USEEIO**: 提供更細緻的美國產業分類
- **Defra UK**: 提供更精確的活動基礎係數（process-based）

---

## ⚠️ 使用限制與注意事項

### 1. 資料授權
- **EXIOBASE** 通常為學術開放使用
- 需確認：
  - 是否為完整 EXIOBASE 或衍生資料
  - 商業使用授權
  - 引用要求

### 2. 資料時效
- 基準年：2022
- EEIO 資料更新頻率較低（通常 2-5 年）
- 需考量技術進步與能源結構變化

### 3. 精確度限制
- EEIO 係數為產業平均
- 無法反映特定產品或企業的差異
- 適合初期估算，重大排放源應升級至 Tier 2 或 Tier 1

### 4. 單位與換算
- 原始單位：kg 排放 / 百萬歐元產出
- 需要：
  - 匯率轉換（EUR → USD → TWD）
  - 物價指數調整（2022 → 當前）
  - GWP 值確認（AR5 或 AR6）

---

## 🚀 立即行動計畫

### 本週執行
1. [ ] 撰寫 Python 腳本提取 TW 與 GB 的 GHG 係數
2. [ ] 讀取 products.txt 取得產品名稱
3. [ ] 計算 CO2e 總排放（使用 GWP 值）
4. [ ] 轉換為標準格式 CSV
5. [ ] 移動到 `tier3_eeio/` 目錄

### 下週執行
6. [ ] 整合到 RAG 檢索系統
7. [ ] 實作台灣優先的檢索邏輯
8. [ ] 更新 `tier3_eeio/README.md`
9. [ ] 測試與驗證

### 未來規劃
10. [ ] 確認 EXIOBASE 授權與引用格式
11. [ ] 提取其他重要國家（CN, JP, KR）
12. [ ] 研究完整 MRIO 分析的可行性
13. [ ] 建立單位轉換與匯率更新機制

---

## 📖 參考資源

### EXIOBASE 相關
- **官網**: https://www.exiobase.eu/
- **文件**: https://www.exiobase.eu/index.php/documentation
- **論文**: Stadler et al. (2018) "EXIOBASE 3: Developing a Time Series of Detailed Environmentally Extended Multi-Regional Input-Output Tables"

### MRIO 分析工具
- **pymrio** (Python): https://github.com/konstantinstadler/pymrio
- **R iotables**: https://iotables.ceemid.eu/

### 相關標準
- **System of Environmental-Economic Accounting (SEEA)**: https://seea.un.org/
- **OECD Input-Output Database**: https://www.oecd.org/sti/ind/input-outputtables.htm

---

## 💡 結論與建議

### 重要性評估
這是本專案的 **重大資源**！原因：

1. ✅ **提供台灣特定的 EEIO 係數** - 比美國 USEEIO 更適合台灣企業
2. ✅ **涵蓋 200 個產品類別** - 比 USEEIO summary (44) 更詳細
3. ✅ **2022 年資料** - 相對新穎
4. ✅ **完全免費** - 已在你的專案中
5. ✅ **國際認可** - EXIOBASE 是學術與實務界廣泛使用的資料庫

### 優先順序
⭐⭐⭐⭐⭐ **最高優先度**

應立即：
1. 提取 TW（台灣）GHG 係數
2. 整合到 Tier 3
3. 設定為台灣地區的預設 EEIO 來源

### 對專案的影響
- **大幅提升** Tier 3 的適用性（從美國係數 → 台灣係數）
- **增加** 系統的本土化程度
- **提供** 未來擴充國際供應鏈分析的基礎

---

**撰寫人**: Claude (分析) + 張育傑 (專案負責人)
**日期**: 2026-01-28
**下一步**: 執行資料提取腳本
