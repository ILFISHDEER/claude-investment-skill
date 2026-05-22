#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
链接检查与修复工具
检查所有 Markdown 文件的双向链接，报告死链和孤立文件

用法：
    python check_links.py              # 检查并报告
    python check_links.py --fix        # 尝试自动修复
    python check_links.py --orphan     # 只检查孤立文件
"""

import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# 配置
ROOT_DIR = Path(__file__).parent
EXCLUDE_DIRS = {'.git', '.obsidian', '__pycache__', 'node_modules'}
EXCLUDE_FILES = {'README.md', 'CHANGELOG.md'}

# 枢纽文件清单（不应该被孤立）
HUB_FILES = [
    '主页.md',
    '框架指南.md',
    '使用与调教指南.md',
    'SKILL.md',
    '模板中心.md',
    '输出中心.md',
    '数据层中心.md',
    '方法论中心.md',
    '回测中心.md',
]

# 需要自动添加返回链接的目录
AUTO_LINK_DIRS = {
    'templates': '模板中心',
    'output': '输出中心',
    'modules': '主页#分析模块',
    'frameworks': '方法论中心',
    'core_logic': '主页#深度分析',
}


def find_all_md_files():
    """查找所有 Markdown 文件"""
    md_files = []
    for root, dirs, files in os.walk(ROOT_DIR):
        # 排除目录
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            if file.endswith('.md') and file not in EXCLUDE_FILES:
                md_files.append(Path(root) / file)

    return md_files


def extract_links(content):
    """提取 [[...]] 格式的双向链接"""
    # 匹配 [[文件名]] 或 [[路径/文件名|显示名]]
    pattern = r'\[\[([^\]]+)\]\]'
    links = re.findall(pattern, content)

    # 清理链接（去掉显示名部分）
    clean_links = []
    for link in links:
        # 处理 [[路径/文件名|显示名]] 格式
        if '|' in link:
            link = link.split('|')[0]
        clean_links.append(link.strip())

    return clean_links


def get_file_by_link(link, all_files):
    """根据链接查找对应的实际文件"""
    # 尝试直接匹配
    for f in all_files:
        if f.name == link or f.stem == link:
            return f

    # 尝试添加 .md 后缀匹配
    link_with_md = link if link.endswith('.md') else link + '.md'
    for f in all_files:
        if f.name == link_with_md:
            return f

    return None


def check_links():
    """检查所有链接"""
    all_files = find_all_md_files()
    file_to_links = {}
    link_to_files = defaultdict(list)

    print("🔍 扫描文件中...")

    # 收集所有链接
    for file in all_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()

            links = extract_links(content)
            file_to_links[file] = links

            for link in links:
                link_to_files[link].append(file)
        except Exception as e:
            print(f"⚠️  读取失败: {file} - {e}")

    # 检查死链
    print("\n" + "="*50)
    print("❌ 死链检查")
    print("="*50)

    dead_links = []
    for file, links in file_to_links.items():
        for link in links:
            target = get_file_by_link(link, all_files)
            if target is None and not link.startswith('#'):
                dead_links.append((file, link))
                print(f"❌ {file.name} -> [[{link}]] (目标不存在)")

    if not dead_links:
        print("✅ 未发现死链")

    # 检查孤立文件
    print("\n" + "="*50)
    print("🏝️ 孤立文件检查")
    print("="*50)

    orphaned = []
    for file in all_files:
        # 检查是否被其他文件引用
        is_referenced = False
        for links in file_to_links.values():
            if file.stem in links or file.name in links:
                is_referenced = True
                break

        # 枢纽文件不应该被孤立
        if not is_referenced and file.name not in EXCLUDE_FILES:
            orphaned.append(file)
            if file.name in HUB_FILES:
                print(f"🔴 [枢纽] {file.name} - 未被任何文件引用!")
            else:
                print(f"🟡 {file.name} - 未被引用")

    if not orphaned:
        print("✅ 未发现孤立文件")

    # 检查缺少返回链接的文件
    print("\n" + "="*50)
    print("🔗 缺少返回链接的文件")
    print("="*50)

    missing_links = []
    for file in all_files:
        relative_path = file.relative_to(ROOT_DIR)
        parent_dir = relative_path.parts[0] if relative_path.parts else ''

        # 检查是否在需要自动链接的目录
        if parent_dir in AUTO_LINK_DIRS:
            hub = AUTO_LINK_DIRS[parent_dir]
            content = file_to_links.get(file, [])

            # 检查是否已经有返回链接
            has_return_link = any(hub in link for link in content)

            if not has_return_link:
                missing_links.append((file, hub))
                print(f"⚠️  {file.name} 缺少返回 [[{hub}]] 的链接")

    if not missing_links:
        print("✅ 所有文件都有返回链接")

    return dead_links, orphaned, missing_links


def fix_missing_links(missing_links):
    """自动添加返回链接"""
    print("\n" + "="*50)
    print("🔧 自动修复")
    print("="*50)

    for file, hub in missing_links:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 在文件末尾添加返回链接
            return_section = f"""

---

## 返回导航

→ 返回 [[{hub}]]
→ 返回 [[主页]]
"""

            if "## 返回导航" not in content:
                with open(file, 'a', encoding='utf-8') as f:
                    f.write(return_section)
                print(f"✅ 已添加返回链接到: {file.name}")
            else:
                print(f"⏭️  已存在返回链接: {file.name}")

        except Exception as e:
            print(f"❌ 修复失败: {file} - {e}")


def main():
    if '--help' in sys.argv:
        print(__doc__)
        return

    dead_links, orphaned, missing_links = check_links()

    # 统计
    print("\n" + "="*50)
    print("📊 统计")
    print("="*50)
    print(f"总文件数: {len(find_all_md_files())}")
    print(f"死链: {len(dead_links)}")
    print(f"孤立文件: {len(orphaned)}")
    print(f"缺少返回链接: {len(missing_links)}")

    if '--fix' in sys.argv and missing_links:
        fix_missing_links(missing_links)

    # 返回码：0=没问题，1=有问题
    if dead_links or any(f.name in HUB_FILES for f in orphaned):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
