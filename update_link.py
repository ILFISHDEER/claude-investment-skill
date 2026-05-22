#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
链接批量更新工具
当枢纽文件重命名时，批量更新所有引用

用法：
    python update_link.py "旧文件名" "新文件名"
    例：python update_link.py "旧主页.md" "主页.md"

    # 预览模式（不实际修改）
    python update_link.py "旧文件名" "新文件名" --dry-run
"""

import os
import re
import sys
from pathlib import Path


def update_links(old_name, new_name, dry_run=False):
    """
    批量更新文件中的双向链接

    old_name: 旧文件名（不含路径）
    new_name: 新文件名（不含路径）
    dry_run: 如果为True，只预览不修改
    """

    root_dir = Path(__file__).parent

    # 提取文件名（不带路径）
    old_file = Path(old_name).name
    new_file = Path(new_name).name

    # 去掉 .md 后缀用于匹配
    old_base = old_file.replace('.md', '')
    new_base = new_file.replace('.md', '')

    # 需要更新的模式
    patterns = [
        (rf'\[\[{re.escape(old_file)}\]\]', f'[[{new_file}]]'),
        (rf'\[\[{re.escape(old_base)}\]\]', f'[[{new_base}]]'),
        (rf'\[\[{re.escape(old_base)}\|', f'[[{new_base}|'),
    ]

    updated_files = []

    # 遍历所有 Markdown 文件
    for md_file in root_dir.rglob('*.md'):
        # 跳过自身
        if md_file.name == old_file:
            continue

        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            changes = []

            for pattern, replacement in patterns:
                matches = list(re.finditer(pattern, content))
                if matches:
                    for m in matches:
                        changes.append(f"  找到: {m.group()}")
                    content = re.sub(pattern, replacement, content)

            if content != original_content:
                if dry_run:
                    print(f"\n📄 {md_file.relative_to(root_dir)}")
                    for change in changes:
                        print(change)
                    print(f"  将替换为: [[{new_base}]]")
                else:
                    with open(md_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    updated_files.append(md_file)
                    print(f"✅ 已更新: {md_file.relative_to(root_dir)}")

        except Exception as e:
            print(f"❌ 处理失败: {md_file} - {e}")

    if dry_run:
        print(f"\n🔍 预览完成，找到 {len(updated_files)} 个需要更新的文件")
        print(f"实际运行请去掉 --dry-run 参数")
    else:
        print(f"\n✅ 完成，共更新 {len(updated_files)} 个文件")

    return updated_files


def rename_hub_file(old_path, new_path, dry_run=False):
    """
    重命名枢纽文件并更新所有引用

    用法：
        python update_link.py --rename "旧路径" "新路径"
    """

    old_path = Path(old_path)
    new_path = Path(new_path)

    if not old_path.exists():
        print(f"❌ 源文件不存在: {old_path}")
        return

    # 1. 先更新所有引用
    print("📝 第一步：更新所有引用...")
    update_links(old_path.name, new_path.name, dry_run)

    if not dry_run:
        # 2. 重命名文件
        print("\n📝 第二步：重命名文件...")
        try:
            old_path.rename(new_path)
            print(f"✅ 已重命名: {old_path.name} -> {new_path.name}")
        except Exception as e:
            print(f"❌ 重命名失败: {e}")


def main():
    if len(sys.argv) < 2 or '--help' in sys.argv:
        print(__doc__)
        return

    if sys.argv[1] == '--rename':
        if len(sys.argv) < 4:
            print("❌ 请提供旧路径和新路径")
            print("例：python update_link.py --rename '旧主页.md' '主页.md'")
            return
        old_path = sys.argv[2]
        new_path = sys.argv[3]
        dry_run = '--dry-run' in sys.argv
        rename_hub_file(old_path, new_path, dry_run)

    else:
        if len(sys.argv) < 3:
            print("❌ 请提供旧文件名和新文件名")
            print("例：python update_link.py '旧主页.md' '主页.md'")
            return

        old_name = sys.argv[1]
        new_name = sys.argv[2]
        dry_run = '--dry-run' in sys.argv

        update_links(old_name, new_name, dry_run)


if __name__ == '__main__':
    main()
