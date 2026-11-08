#!/usr/bin/env python3
"""
批量更新所有主题股价数据
使用方法: python update_all_themes.py
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

THEMES = [
    "孙哥方向",
    "新能源",
    "量子计算",
    "物理AI",
    "空间计算",
    "合成生物学"
]

def main():
    print("=" * 60)
    print(f"批量更新所有主题股价 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    total_updated = 0
    total_failed = 0

    for theme in THEMES:
        theme_path = Path(f"themes/{theme}")
        if not theme_path.exists():
            print(f"\n[跳过] 主题不存在: {theme}")
            continue

        print(f"\n[更新] {theme}...")
        result = subprocess.run(
            [sys.executable, "update_stock_data.py", "--theme", theme],
            capture_output=True,
            text=True
        )

        # 解析结果
        for line in result.stdout.split('\n'):
            if 'Updated:' in line and 'Failed:' in line:
                print(f"  {line.strip()}")
                # 提取数字
                parts = line.split(',')
                if len(parts) == 2:
                    updated = int(parts[0].split(':')[1].strip())
                    failed = int(parts[1].split(':')[1].strip())
                    total_updated += updated
                    total_failed += failed

    print("\n" + "=" * 60)
    print(f"总计: 更新 {total_updated} 只股票, 失败 {total_failed}")
    print("=" * 60)

if __name__ == "__main__":
    main()
