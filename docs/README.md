# 📚 專案文件索引

本目錄包含 Scope 3 Estimator 專案的所有文件與記錄。

---

## 📋 文件列表

### 🗺️ 規劃文件

#### [ROADMAP_3-6_MONTHS.md](./ROADMAP_3-6_MONTHS.md)
**3-6 個月開發路線圖**
- 完整的階段規劃（階段 1-4）
- 詳細任務分解
- 里程碑與交付物
- 風險評估與應對
- KPI 指標

**何時查看**：
- 了解整體計畫
- 查詢特定任務細節
- 評估進度與目標

---

### 📝 工作記錄

#### [WORKLOG.md](./WORKLOG.md)
**工作日誌**
- 每日/每次工作記錄
- 完成的任務
- 遇到的問題與解決方案
- 重要決策記錄
- 技術亮點與經驗

**何時查看**：
- 回顧歷史工作
- 查找過去的決策理由
- 了解技術細節
- 接續上次工作

**更新頻率**：每次工作後立即更新

---

### 📊 當前狀態

#### [STATUS.md](./STATUS.md)
**專案當前狀態**
- 整體進度（百分比）
- 當前階段詳情
- 任務清單（待辦事項）
- 阻礙與風險
- 系統現況統計
- 最新討論與決策

**何時查看**：
- 每次開始工作前
- 了解當前進度
- 查看待辦事項
- 確認阻礙狀況

**更新頻率**：每週或重大變更時

---

### 📖 其他文件

#### [EXIOBASE_RAG_整合計劃.md](./EXIOBASE_RAG_整合計劃.md)
**EXIOBASE RAG 整合計劃**（早期版本）
- Tier 3 EEIO 系統設計
- 資料處理流程
- 技術細節

**狀態**：部分已完成，內容整合至新文件中

---

## 🔄 文件關係圖

```
開始新工作
    ↓
查看 STATUS.md
    ↓
    ├─→ 查看待辦事項
    ├─→ 了解當前進度
    └─→ 確認無阻礙
    ↓
開始工作
    ↓
    ├─→ 需要查詢詳細規劃？→ ROADMAP_3-6_MONTHS.md
    ├─→ 需要回顧歷史？→ WORKLOG.md
    └─→ 需要查技術細節？→ WORKLOG.md
    ↓
完成工作
    ↓
更新 WORKLOG.md
    ↓
更新 STATUS.md（如有進度變更）
```

---

## 📅 快速導航

### 我想...

#### 了解整個專案計畫
👉 閱讀 [ROADMAP_3-6_MONTHS.md](./ROADMAP_3-6_MONTHS.md)

#### 知道現在該做什麼
👉 查看 [STATUS.md](./STATUS.md) → 「當前待辦事項」章節

#### 回顧昨天做了什麼
👉 查看 [WORKLOG.md](./WORKLOG.md) → 最新日期條目

#### 查詢某個任務的詳細內容
👉 查看 [ROADMAP_3-6_MONTHS.md](./ROADMAP_3-6_MONTHS.md) → 對應階段

#### 了解當前進度百分比
👉 查看 [STATUS.md](./STATUS.md) → 「整體進度」章節

#### 查找某個技術決策的理由
👉 查看 [WORKLOG.md](./WORKLOG.md) → 搜尋關鍵字

#### 確認是否有阻礙
👉 查看 [STATUS.md](./STATUS.md) → 「當前阻礙與風險」章節

---

## 🎯 文件維護準則

### WORKLOG.md 更新準則
- ✅ **每次工作後立即更新**
- 記錄：完成的任務、問題、決策、下一步
- 格式：日期 → Session → 工作內容

### STATUS.md 更新準則
- ✅ **每週五定期更新**
- ✅ **重大進度變更時立即更新**
- 更新：進度百分比、任務狀態、阻礙情況

### ROADMAP.md 更新準則
- ✅ **重大計畫變更時才更新**
- 保持穩定，作為基準參考
- 變更需記錄在「變更記錄」章節

---

## 📝 文件模板

### 新增 WORKLOG 條目模板

```markdown
## YYYY-MM-DD（星期X）

### Session N: 工作主題

**時間**：HH:MM - HH:MM

#### 完成工作
1. **任務名稱** ✅
   - 詳細描述
   - 結果

#### 重要決策
**決策 N：決策標題** ✅ 確認/⏳ 待定
- 背景
- 決策內容
- 影響

#### 待解決問題
**問題 N：問題標題**
- 描述
- 影響

#### 下一步行動
- [ ] 行動項目 1
- [ ] 行動項目 2
```

---

## 🔍 搜尋技巧

### 在 WORKLOG.md 中搜尋
```bash
# 搜尋特定日期
grep "2026-01-29" docs/WORKLOG.md

# 搜尋決策記錄
grep "決策" docs/WORKLOG.md

# 搜尋問題
grep "問題" docs/WORKLOG.md
```

### 在 STATUS.md 中搜尋
```bash
# 查看待辦事項
grep "\[ \]" docs/STATUS.md

# 查看阻礙
grep "阻礙" docs/STATUS.md
```

---

## 📧 維護責任

- **WORKLOG.md**: Claude（每次工作後）
- **STATUS.md**: Claude（每週或重大變更時）
- **ROADMAP.md**: 張教授 + Claude（重大計畫變更時）

---

## 🔗 相關連結

- [專案 README](../README.md) - 系統說明與使用指南
- [專案根目錄](../) - 源碼與資料

---

<div align="center">
  <p><strong>📚 Keep Documentation Updated, Keep Progress Visible</strong></p>
  <p><em>Last Updated: 2026-01-29</em></p>
</div>
