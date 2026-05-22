#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
框架完整性检查 - 一键检查所有维护项

用法：
    python integrity_check.py              # 完整检查
    python integrity_check.py --links    # 只检查链接
    python integrity_check.py --data     # 只检查数据新鲜度
    python integrity_check.py --all      # 完整检查+修复（推荐）
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"\n{'='*50}")
    print(f"🔍 {description}")
    print(f"{'='*50}")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ 通过")
        if result.stdout:
            print(result.stdout)
        return True
    else:
        print("❌ 发现问题")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return False


def check_links(fix=False):
    """检查链接完整性"""
    cmd = "python check_links.py"
    if fix:
        cmd += " --fix"
    return run_command(cmd, "检查双向链接")


def check_data_freshness():
    """检查数据新鲜度"""
    return run_command("python check_freshness.py", "检查数据新鲜度")


def check_output_links():
    """检查输出文件的返回链接"""
    return run_command("python generate_report.py --fix-all", "修复报告返回链接")


def check_hub_integrity():
    """检查枢纽文件完整性"""
    print(f"\n{'='*50}")
    print(f"🔍 检查枢纽文件完整性")
    print(f"{'='*50}")

    required_hubs = [
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

    missing = []
    for hub in required_hubs:
        if not Path(hub).exists():
            missing.append(hub)
            print(f"❌ 缺失: {hub}")

    if missing:
        print(f"\n⚠️  发现 {len(missing)} 个缺失的枢纽文件")
        return False
    else:
        print("✅ 所有枢纽文件存在")
        return True


def generate_health_report():
    """生成健康报告"""
    report = []
    report.append("# 框架健康检查报告\n")
    report.append(f"**检查时间**: 自动生成\n")
    report.append(f"**版本**: v2.5\n\n")

    report.append("## 检查项\n")

    checks = [
        ("枢纽文件完整性", check_hub_integrity()),
        ("数据新鲜度", check_data_freshness()),
        ("链接完整性", check_links()),
        ("报告返回链接", check_output_links()),
    ]

    for name, result in checks:
        status = "✅ 通过" if result else "❌ 失败"
        report.append(f"- {name}: {status}\n")

    # 写入报告
    report_path = Path("reports") / "健康检查-自动.md"
    report_path.parent.mkdir(exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.writelines(report)

    print(f"\n📄 健康报告已生成: {report_path}")
    return all(r for _, r in checks)


def main():
    if '--help' in sys.argv:
        print(__doc__)
        return

    print("""
╔════════════════════════════════════════╗
║     Investment Skill 框架完整性检查    ║
╚════════════════════════════════════════╝
    """)

    if '--links' in sys.argv:
        check_links('--fix' in sys.argv)

    elif '--data' in sys.argv:
        check_data_freshness()

    elif '--all' in sys.argv:
        print("🚀 执行完整检查并自动修复...")
        check_data_freshness()
        check_links(fix=True)
        check_output_links()
        check_hub_integrity()
        print("\n" + "="*50)
        print("✅ 完整检查和修复完成")

    else:
        # 默认执行完整检查（不修复）
        check_data_freshness()
        check_links()
        check_hub_integrity()
        generate_health_report()

    print("\n" + "="*50)
    print("💡 提示: 运行 'python integrity_check.py --all' 可自动修复问题")


if __name__ == '__main__':
    main()
