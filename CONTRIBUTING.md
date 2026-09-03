# 開發協作指南

本文件為 scope3_estimator 專案的 GitHub 協作流程說明。

---

## 一、環境建置（新成員首次加入）

```bash
# 1. Clone 專案
git clone https://github.com/yujchang2017/scope3_estimator.git
cd scope3_estimator

# 2. 建立 Python 虛擬環境
python -m venv .venv

# Windows 啟動
.venv\Scripts\activate

# 3. 安裝套件
pip install -r requirements.txt

# 4. 複製環境設定（向老師索取 .env 內容）
# .env 不會出現在 repo 中，需手動建立

# 5. 下載模型（第一次需要網路，之後離線運作）
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# 6. 重建向量檔（.npy 不在 repo 中，需本地重建）
python scripts/build_tier1_embeddings.py
python scripts/build_tier2_embeddings.py
python scripts/build_tier3_embeddings.py

# 7. 測試系統是否正常
python scripts/test_cascade_retriever.py
```

---

## 二、日常開發流程

### 2.1 開始新任務

```bash
# 確保在最新的 main 上
git checkout main
git pull origin main

# 建立功能分支（用自己的名字前綴）
git checkout -b feat/你的名字-任務描述
# 範例：
git checkout -b feat/wang-tier2-agribalyse-update
git checkout -b feat/chen-ui-batch-upload
```

### 2.2 開發中

```bash
# 查看目前修改了什麼
git status

# 加入修改的檔案（指定檔名，不要用 git add .）
git add src/retrieval/tier2_international.py
git add scripts/build_tier2_embeddings.py

# 提交（寫清楚做了什麼）
git commit -m "feat: 更新 AGRIBALYSE 3.2 資料解析邏輯"

# 推送到 GitHub
git push origin feat/你的名字-任務描述
```

### 2.3 提交 Pull Request (PR)

1. 推送分支後，到 GitHub 網頁會看到 **「Compare & pull request」** 黃色按鈕
2. 點擊後填寫：
   - **Title**：簡短描述（如「更新 Tier2 AGRIBALYSE 3.2 資料」）
   - **Description**：說明改了什麼、為什麼改、怎麼測試的
3. 右側 **Reviewers** 選老師（yujchang2017）
4. 點 **Create pull request**
5. **等老師 review 後才能 merge**，不要自己 merge

### 2.4 老師 Review 後

```bash
# 如果老師要求修改，在同一個分支繼續改
git add 修改的檔案
git commit -m "fix: 根據 review 修正 XXX"
git push origin feat/你的名字-任務描述
# PR 會自動更新，不需要重新建立

# merge 完成後，回到 main 並更新
git checkout main
git pull origin main

# 刪除已合併的分支（保持乾淨）
git branch -d feat/你的名字-任務描述
```

---

## 三、常見操作速查

| 情境 | 指令 |
|------|------|
| 查看目前狀態 | `git status` |
| 查看修改內容 | `git diff` |
| 查看提交歷史 | `git log --oneline -10` |
| 取消未 commit 的修改 | `git checkout -- 檔案名` |
| 取消已 stage 的檔案 | `git reset HEAD 檔案名` |
| 拉取遠端最新 | `git pull origin main` |
| 查看所有分支 | `git branch -a` |
| 切換分支 | `git checkout 分支名` |
| 合併衝突時查看狀態 | `git status`（會顯示衝突檔案） |

---

## 四、合併衝突處理

當兩人改到同一個檔案的同一區域時會發生衝突：

```bash
# 1. 先更新 main
git checkout main
git pull origin main

# 2. 回到自己的分支，合併 main 進來
git checkout feat/你的名字-任務描述
git merge main

# 3. 如果有衝突，打開衝突檔案會看到：
# <<<<<<< HEAD
# 你的修改
# =======
# main 上的修改
# >>>>>>> main

# 4. 手動編輯，保留正確的版本，刪除標記符號

# 5. 解決後
git add 衝突的檔案
git commit -m "merge: 解決與 main 的合併衝突"
git push origin feat/你的名字-任務描述
```

**不確定怎麼解決時，問老師再處理。**

---

## 五、禁止事項

1. **不要直接 push 到 main** — 一律透過 PR
2. **不要用 `git add .` 或 `git add -A`** — 逐一指定檔案，避免意外加入敏感檔案
3. **不要提交這些檔案**（.gitignore + pre-commit hook 會擋，但仍需注意）：
   - `.env`（環境設定）
   - `*.npy`（向量檔，可重建）
   - `models/finetuned/`（微調權重）
   - `data/training_data/industry/`（產業訓練資料）
   - `*_backup_*.csv`（備份檔）
4. **不要用 `git push --force`** — 會覆蓋別人的工作
5. **不要刪除或修改 `.gitignore`** — 如需調整請先討論

---

## 六、Commit Message 格式

```
類型: 簡短描述（中文即可）

類型包括：
- feat:  新功能
- fix:   修 bug
- data:  資料更新
- docs:  文件修改
- test:  測試相關
- chore: 雜項（設定、格式化等）
```

範例：
```
feat: 新增 AGRIBALYSE 3.2 資料解析
fix: 修正 Tier2 NaN 值導致的檢索錯誤
data: 更新 Defra UK 2025 排放係數
docs: 補充 Tier1 README 授權說明
test: 新增 cascade retriever 邊界測試
```

---

## 七、專案結構簡介

```
scope3_estimator/
├── src/                    ← 核心程式碼
│   ├── retrieval/          ← 三層檢索器（Tier1/2/3）
│   ├── classification/     ← GHG 分類器
│   └── utils/              ← 共用工具（embedding、相似度）
├── scripts/                ← 資料處理與測試腳本
├── data/
│   ├── emission_factors/   ← 排放係數資料庫（三層）
│   ├── reference_data/     ← 分類規則
│   └── synthetic/          ← 合成測試資料
├── app.py                  ← Streamlit 主程式
├── requirements.txt        ← Python 套件清單
└── Dockerfile              ← Docker 部署設定
```
