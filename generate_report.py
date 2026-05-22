#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告生成脚本 - 带自动链接添加
生成报告时自动添加返回链接到主页和输出中心

用法：
    python generate_report.py <主题> <深度> <风格>
    例：python generate_report.py "孙哥方向" "L3" "专业投行风"
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path


def generate_report(theme, depth, style):
    """生成报告并添加返回链接"""

    # 检查数据新鲜度
    print("📊 检查数据新鲜度...")
    os.system("python check_freshness.py")

    # 构建文件名
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{theme}-{depth}-{today}-{style}.md"
    output_path = Path("output") / filename

    print(f"\n📄 报告将生成: {output_path}")
    print("\n现在对AI说：")
    print(f'  "按当前配置生成{theme}的{depth}报告，风格选择{style}"')
    print("\n生成完成后，运行：")
    print(f'  python add_return_links.py "{output_path}"')

    return output_path


def add_return_links(file_path):
    """为已生成的报告添加返回链接"""

    file_path = Path(file_path)
    if not file_path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已有返回链接
        if "## 返回导航" in content:
            print(f"⏭️  已存在返回链接: {file_path.name}")
            return True

        # 添加返回链接
        return_section = """

---

## 返回导航

→ 返回 [[主页]]
→ 查看 [[输出中心|其他报告]]
→ 前往 [[模板中心|生成新报告]]
"""

        # 在文件末尾添加（在最后一个分隔线之后）
        if content.rstrip().endswith('---'):
            # 已有分隔线，直接添加
            new_content = content.rstrip() + return_section
        else:
            # 没有分隔线，添加分隔线
            new_content = content + "\n\n---" + return_section

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"✅ 已添加返回链接到: {file_path.name}")
        return True

    except Exception as e:
        print(f"❌ 添加链接失败: {e}")
        return False


def fix_all_output_files():
    """为 output 目录所有报告添加返回链接"""

    output_dir = Path("output")
    if not output_dir.exists():
        print("❌ output 目录不存在")
        return

    md_files = list(output_dir.glob("*.md"))

    print(f"🔧 检查 {len(md_files)} 个报告文件...\n")

    for file in md_files:
        add_return_links(file)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\n命令:")
        print("  python generate_report.py <主题> <深度> <风格>")
        print("  python generate_report.py --fix <文件路径>")
        print("  python generate_report.py --fix-all")
        return

    if sys.argv[1] == '--fix':
        if len(sys.argv) < 3:
            print("❌ 请提供文件路径")
            return
        add_return_links(sys.argv[2])

    elif sys.argv[1] == '--fix-all':
        fix_all_output_files()

    else:
        theme = sys.argv[1]
        depth = sys.argv[2] if len(sys.argv) > 2 else "L3"
        style = sys.argv[3] if len(sys.argv) > 3 else "专业投行风"
        generate_report(theme, depth, style)


if __name__ == '__main__':
    main()
