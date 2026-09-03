#!/bin/bash
# 快速查看專案當前狀態

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║          📊 Scope 3 Estimator - 當前狀態                         ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# 顯示最後更新時間
echo "📅 最後更新："
grep "Last Updated:" ../docs/STATUS.md | tail -1
echo ""

# 顯示整體進度
echo "📈 整體進度："
grep -A 5 "整體完成度:" ../docs/STATUS.md | head -6
echo ""

# 顯示當前階段
echo "🎯 當前階段："
grep "當前階段：" ../docs/STATUS.md
echo ""

# 顯示高優先級待辦事項
echo "🔴 高優先級待辦事項："
sed -n '/### 🔴 高優先級/,/### 🟡 中優先級/p' ../docs/STATUS.md | grep -E "^\d+\. \[" | head -5
echo ""

# 顯示當前阻礙
echo "🚧 當前阻礙："
grep -A 2 "### 阻礙" ../docs/STATUS.md | grep -v "^--$" | head -6
echo ""

# 顯示最新里程碑
echo "📍 最新里程碑："
grep "M0:" ../docs/STATUS.md
echo ""

echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "💡 提示："
echo "   - 完整狀態：查看 docs/STATUS.md"
echo "   - 工作日誌：查看 docs/WORKLOG.md"
echo "   - 開發路線圖：查看 docs/ROADMAP_3-6_MONTHS.md"
echo ""
echo "═══════════════════════════════════════════════════════════════════"
