#!/bin/bash

###############################################################################
# Training Data Download Script
#
# 功能：自動下載 Kaggle 與 OCDS 訓練資料集
#
# 使用方法：
#   chmod +x download_training_data.sh
#   ./download_training_data.sh
#
# 前置需求：
#   1. 已安裝 kaggle CLI: pip install kaggle
#   2. 已設定 ~/.kaggle/kaggle.json
#   3. 已安裝 wget 或 curl
#
###############################################################################

set -e  # 遇到錯誤立即停止

# 顏色定義
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 取得腳本所在目錄的父目錄（專案根目錄）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/data/training_data"

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}  Training Data Download Script${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

###############################################################################
# 函數定義
###############################################################################

check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ Error: $1 未安裝${NC}"
        echo -e "${YELLOW}   請執行: $2${NC}"
        return 1
    else
        echo -e "${GREEN}✅ $1 已安裝${NC}"
        return 0
    fi
}

check_kaggle_auth() {
    if [ ! -f ~/.kaggle/kaggle.json ]; then
        echo -e "${RED}❌ Error: Kaggle API credentials 未設定${NC}"
        echo -e "${YELLOW}   請參考 DOWNLOAD_GUIDE.md 設定 kaggle.json${NC}"
        return 1
    else
        echo -e "${GREEN}✅ Kaggle API credentials 已設定${NC}"
        return 0
    fi
}

create_directories() {
    echo -e "\n${BLUE}📂 建立目錄結構...${NC}"
    mkdir -p "$DATA_DIR/raw/kaggle"
    mkdir -p "$DATA_DIR/raw/ocds"
    mkdir -p "$DATA_DIR/processed"
    mkdir -p "$DATA_DIR/annotated"
    mkdir -p "$DATA_DIR/gold_standard"
    echo -e "${GREEN}✅ 目錄結構建立完成${NC}"
}

download_kaggle_dataset() {
    local dataset_id=$1
    local output_dir=$2
    local dataset_name=$3

    echo -e "\n${BLUE}📥 下載 $dataset_name...${NC}"

    cd "$DATA_DIR/raw/kaggle"

    if [ -d "$output_dir" ]; then
        echo -e "${YELLOW}⚠️  目錄 $output_dir 已存在，跳過下載${NC}"
        return 0
    fi

    # 下載資料集
    kaggle datasets download -d "$dataset_id"

    # 解壓縮
    local zip_file="${dataset_id##*/}.zip"
    if [ ! -f "$zip_file" ]; then
        # 嘗試其他可能的檔名
        zip_file=$(ls *.zip 2>/dev/null | head -1)
    fi

    if [ -f "$zip_file" ]; then
        echo -e "${BLUE}📦 解壓縮 $zip_file...${NC}"
        unzip -q "$zip_file" -d "$output_dir"
        rm "$zip_file"
        echo -e "${GREEN}✅ $dataset_name 下載完成${NC}"

        # 顯示檔案資訊
        echo -e "${BLUE}   檔案列表:${NC}"
        ls -lh "$output_dir"
    else
        echo -e "${RED}❌ 找不到 ZIP 檔案${NC}"
        return 1
    fi
}

download_ocds_data() {
    local year=$1

    echo -e "\n${BLUE}📥 下載 OCDS UK Contracts Finder $year...${NC}"

    cd "$DATA_DIR/raw/ocds"

    if [ -f "${year}.jsonl" ]; then
        echo -e "${YELLOW}⚠️  檔案 ${year}.jsonl 已存在，跳過下載${NC}"
        return 0
    fi

    # 下載並解壓縮
    local url="https://data.open-contracting.org/en/publication/128/${year}.jsonl.gz"

    if command -v wget &> /dev/null; then
        wget -c "$url"
    elif command -v curl &> /dev/null; then
        curl -C - -O "$url"
    else
        echo -e "${RED}❌ Error: 需要 wget 或 curl${NC}"
        return 1
    fi

    echo -e "${BLUE}📦 解壓縮 ${year}.jsonl.gz...${NC}"
    gunzip "${year}.jsonl.gz"

    echo -e "${GREEN}✅ OCDS $year 下載完成${NC}"

    # 顯示檔案資訊
    local line_count=$(wc -l < "${year}.jsonl")
    local file_size=$(ls -lh "${year}.jsonl" | awk '{print $5}')
    echo -e "${BLUE}   檔案大小: $file_size${NC}"
    echo -e "${BLUE}   記錄數量: $line_count${NC}"
}

show_summary() {
    echo -e "\n${BLUE}======================================${NC}"
    echo -e "${BLUE}  下載摘要${NC}"
    echo -e "${BLUE}======================================${NC}"

    echo -e "\n${GREEN}已下載的資料集:${NC}"

    # Kaggle 資料集
    if [ -d "$DATA_DIR/raw/kaggle/singapore_procurement" ]; then
        local sg_files=$(ls "$DATA_DIR/raw/kaggle/singapore_procurement" | wc -l)
        echo -e "  ✅ Singapore Government Procurement ($sg_files files)"
    fi

    if [ -d "$DATA_DIR/raw/kaggle/sf_procurement" ]; then
        local sf_files=$(ls "$DATA_DIR/raw/kaggle/sf_procurement" | wc -l)
        echo -e "  ✅ San Francisco Procurement ($sf_files files)"
    fi

    if [ -d "$DATA_DIR/raw/kaggle/purchase_orders_misc" ]; then
        echo -e "  ✅ Purchase Orders (misc)"
    fi

    if [ -d "$DATA_DIR/raw/kaggle/spend_analytics" ]; then
        echo -e "  ✅ Spend Analytics"
    fi

    # OCDS 資料集
    local ocds_count=$(ls "$DATA_DIR/raw/ocds"/*.jsonl 2>/dev/null | wc -l)
    if [ $ocds_count -gt 0 ]; then
        echo -e "  ✅ OCDS UK Contracts ($ocds_count years)"
        ls "$DATA_DIR/raw/ocds"/*.jsonl 2>/dev/null | while read file; do
            local line_count=$(wc -l < "$file")
            local filename=$(basename "$file")
            echo -e "     - $filename: $line_count records"
        done
    fi

    echo -e "\n${BLUE}總磁碟使用量:${NC}"
    du -sh "$DATA_DIR/raw"

    echo -e "\n${GREEN}🎉 下載完成！${NC}"
    echo -e "${YELLOW}下一步：請執行資料處理腳本${NC}"
    echo -e "${YELLOW}  python scripts/process_training_data.py${NC}"
}

###############################################################################
# 主程式
###############################################################################

main() {
    echo -e "${BLUE}專案目錄: $PROJECT_ROOT${NC}"
    echo -e "${BLUE}資料目錄: $DATA_DIR${NC}"
    echo ""

    # 檢查前置需求
    echo -e "${BLUE}🔍 檢查前置需求...${NC}"

    local all_checks_passed=true

    check_command "kaggle" "pip install kaggle" || all_checks_passed=false
    check_command "unzip" "sudo apt-get install unzip" || all_checks_passed=false

    if command -v wget &> /dev/null || command -v curl &> /dev/null; then
        echo -e "${GREEN}✅ wget 或 curl 已安裝${NC}"
    else
        echo -e "${RED}❌ Error: 需要 wget 或 curl${NC}"
        all_checks_passed=false
    fi

    check_kaggle_auth || all_checks_passed=false

    if [ "$all_checks_passed" = false ]; then
        echo -e "\n${RED}❌ 前置需求檢查失敗，請安裝必要工具後重試${NC}"
        exit 1
    fi

    # 建立目錄
    create_directories

    # 詢問要下載哪些資料集
    echo -e "\n${BLUE}請選擇要下載的資料集:${NC}"
    echo "1) 全部下載（推薦，約 250 MB）"
    echo "2) 僅 Kaggle 資料集（約 135 MB）"
    echo "3) 僅 OCDS 資料集（約 150 MB）"
    echo "4) 自訂選擇"
    echo "5) 取消"
    read -p "請輸入選項 (1-5): " choice

    case $choice in
        1)
            # 全部下載
            download_kaggle_dataset "shivamb/government-procurement-dataset" "singapore_procurement" "Singapore Government Procurement"
            download_kaggle_dataset "vineethakkinapalli/san-francisco-procurement-data" "sf_procurement" "San Francisco Procurement"
            download_ocds_data "2024"
            download_ocds_data "2023"
            ;;
        2)
            # 僅 Kaggle
            download_kaggle_dataset "shivamb/government-procurement-dataset" "singapore_procurement" "Singapore Government Procurement"
            download_kaggle_dataset "vineethakkinapalli/san-francisco-procurement-data" "sf_procurement" "San Francisco Procurement"

            read -p "是否下載其他 Kaggle 資料集? (y/n): " extra
            if [ "$extra" = "y" ]; then
                download_kaggle_dataset "danialxahid/purchase-orders" "purchase_orders_misc" "Purchase Orders (misc)"
                download_kaggle_dataset "mukeshmanral/spend-analytics" "spend_analytics" "Spend Analytics"
            fi
            ;;
        3)
            # 僅 OCDS
            read -p "下載幾年的資料? (1-5): " years
            case $years in
                1)
                    download_ocds_data "2024"
                    ;;
                2)
                    download_ocds_data "2024"
                    download_ocds_data "2023"
                    ;;
                3)
                    download_ocds_data "2024"
                    download_ocds_data "2023"
                    download_ocds_data "2022"
                    ;;
                *)
                    for year in 2024 2023 2022 2021 2020; do
                        download_ocds_data "$year"
                    done
                    ;;
            esac
            ;;
        4)
            # 自訂選擇
            read -p "下載 Singapore Gov Procurement? (y/n): " sg
            [ "$sg" = "y" ] && download_kaggle_dataset "shivamb/government-procurement-dataset" "singapore_procurement" "Singapore Government Procurement"

            read -p "下載 San Francisco Procurement? (y/n): " sf
            [ "$sf" = "y" ] && download_kaggle_dataset "vineethakkinapalli/san-francisco-procurement-data" "sf_procurement" "San Francisco Procurement"

            read -p "下載 OCDS 2024? (y/n): " ocds
            [ "$ocds" = "y" ] && download_ocds_data "2024"
            ;;
        5)
            echo -e "${YELLOW}已取消${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}無效的選項${NC}"
            exit 1
            ;;
    esac

    # 顯示摘要
    show_summary
}

# 執行主程式
main
