# Tier 1 官方來源匯入模板

這個資料夾放的是匯入模板，不會自動進入檢索器。

## 環境部/氣候變遷署溫室氣體排放係數管理表

將官方下載或整理後的 CSV/XLSX 匯入：

```bash
python scripts/update_tier1_official_sources.py \
  --source-type cca_ghg_management \
  --input data/emission_factors/tier1_local/official_source_templates/cca_ghg_management_template.csv \
  --replace-source
```

## 經濟部能源署/台電電力排碳係數

將官方年度電力排碳係數整理成 CSV/XLSX 後匯入：

```bash
python scripts/update_tier1_official_sources.py \
  --source-type moea_power \
  --input data/emission_factors/tier1_local/official_source_templates/moea_power_factor_template.csv \
  --replace-source
```

欄位可使用中文或英文別名，必要欄位為名稱、排放係數、單位與年度。匯入正式資料前可先加 `--dry-run` 檢查筆數。
