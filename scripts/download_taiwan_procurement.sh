#!/bin/bash
# 下載台灣政府電子採購網決標資料 (2024-2025)

BASE_URL="https://web.pcc.gov.tw/tps/tp/OpenData/downloadFile?fileName="
OUTPUT_DIR="/mnt/c/Users/yjchang/Google 雲端硬碟/2026年計畫/氣候署範疇三計畫/scope3_estimator/data/training_data/raw/taiwan_procurement"

mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

echo "================================================"
echo "  下載台灣政府電子採購網決標資料 (2024-2025)"
echo "================================================"

# 2024 年資料（1-12 月，每月上下半月各一個檔案）
for month in {01..12}; do
    for half in 01 02; do
        filename="award_2024${month}${half}.xml"
        echo "下載: $filename"
        curl -L -o "$filename" "${BASE_URL}${filename}" 2>&1 | grep -E "100|error"

        # 檢查檔案大小，如果太小可能是錯誤
        size=$(stat -c%s "$filename" 2>/dev/null || stat -f%z "$filename" 2>/dev/null)
        if [ "$size" -lt 1000 ]; then
            echo "  ⚠️  檔案太小，可能下載失敗"
            rm "$filename"
        else
            echo "  ✓ 完成 ($size bytes)"
        fi

        sleep 1  # 避免請求過於頻繁
    done
done

# 2025 年資料（1-11 月）
for month in {01..11}; do
    for half in 01 02; do
        filename="award_2025${month}${half}.xml"
        echo "下載: $filename"
        curl -L -o "$filename" "${BASE_URL}${filename}" 2>&1 | grep -E "100|error"

        size=$(stat -c%s "$filename" 2>/dev/null || stat -f%z "$filename" 2>/dev/null)
        if [ "$size" -lt 1000 ]; then
            echo "  ⚠️  檔案太小，可能下載失敗"
            rm "$filename"
        else
            echo "  ✓ 完成 ($size bytes)"
        fi

        sleep 1
    done
done

echo ""
echo "================================================"
echo "  下載完成統計"
echo "================================================"
echo "已下載檔案數: $(ls -1 award_*.xml 2>/dev/null | wc -l)"
echo "總大小: $(du -sh . | cut -f1)"
echo "檔案列表:"
ls -lh award_*.xml | tail -20
