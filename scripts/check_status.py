#!/usr/bin/env python3
"""
快速查看專案狀態與待辦事項
"""

from pathlib import Path
import re
from datetime import datetime

# 路徑
DOCS_DIR = Path(__file__).parent.parent / "docs"
STATUS_FILE = DOCS_DIR / "STATUS.md"
WORKLOG_FILE = DOCS_DIR / "WORKLOG.md"

def print_header(title, char="="):
    """印出標題"""
    print(f"\n{char * 70}")
    print(f"  {title}")
    print(f"{char * 70}\n")

def read_status():
    """讀取 STATUS.md"""
    if not STATUS_FILE.exists():
        print("❌ STATUS.md 不存在！")
        return None

    with open(STATUS_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def extract_todos(content):
    """提取待辦事項"""
    todos = {
        'high': [],
        'medium': [],
        'low': []
    }

    current_priority = None
    lines = content.split('\n')

    for line in lines:
        if '### 🔴 高優先級' in line:
            current_priority = 'high'
        elif '### 🟡 中優先級' in line:
            current_priority = 'medium'
        elif '### 🟢 低優先級' in line:
            current_priority = 'low'
        elif line.startswith('##'):
            current_priority = None

        if current_priority and re.match(r'^\d+\. \[', line):
            todos[current_priority].append(line.strip())

    return todos

def extract_progress(content):
    """提取進度資訊"""
    # 找到進度區塊
    match = re.search(r'整體完成度: (.+?)%', content)
    if match:
        return match.group(1).strip()
    return "未知"

def extract_current_stage(content):
    """提取當前階段"""
    match = re.search(r'\*\*當前階段\*\*：(.+)', content)
    if match:
        return match.group(1).strip()
    return "未知"

def extract_blockers(content):
    """提取阻礙"""
    blockers = []
    lines = content.split('\n')

    in_blocker_section = False
    current_blocker = []

    for line in lines:
        if '## 🚧 當前阻礙與風險' in line:
            in_blocker_section = True
        elif line.startswith('##') and in_blocker_section:
            break
        elif in_blocker_section and line.startswith('### 阻礙'):
            if current_blocker:
                blockers.append('\n'.join(current_blocker))
            current_blocker = [line.strip()]
        elif in_blocker_section and current_blocker and line.strip():
            current_blocker.append(line.strip())

    if current_blocker:
        blockers.append('\n'.join(current_blocker))

    return blockers

def main():
    """主函數"""
    print_header("📊 Scope 3 Estimator - 專案狀態檢查", "═")

    # 讀取狀態
    content = read_status()
    if not content:
        return

    # 顯示基本資訊
    print(f"📅 檢查時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 狀態檔案：{STATUS_FILE}")
    print()

    # 顯示進度
    progress = extract_progress(content)
    stage = extract_current_stage(content)

    print(f"📈 整體進度：{progress}%")
    print(f"🎯 當前階段：{stage}")
    print()

    # 顯示待辦事項
    todos = extract_todos(content)

    if todos['high']:
        print_header("🔴 高優先級待辦事項", "-")
        for i, todo in enumerate(todos['high'], 1):
            print(f"{todo}")
        print()

    if todos['medium']:
        print_header("🟡 中優先級待辦事項", "-")
        for i, todo in enumerate(todos['medium'][:3], 1):  # 只顯示前 3 個
            print(f"{todo}")
        if len(todos['medium']) > 3:
            print(f"... 還有 {len(todos['medium']) - 3} 個任務")
        print()

    # 顯示阻礙
    blockers = extract_blockers(content)
    if blockers:
        print_header("🚧 當前阻礙", "-")
        for blocker in blockers:
            print(blocker)
            print()

    # 提示
    print_header("💡 快速連結", "-")
    print("📄 完整狀態：docs/STATUS.md")
    print("📝 工作日誌：docs/WORKLOG.md")
    print("🗺️ 開發路線圖：docs/ROADMAP_3-6_MONTHS.md")
    print()

    print("═" * 70)

if __name__ == "__main__":
    main()
