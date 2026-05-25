#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告完整性验证脚本
验证生成的报告是否完整、一致、可追溯

用法：
    python check_report_completeness.py <报告路径>    # 验证单个报告
    python check_report_completeness.py --all        # 验证所有报告
    python check_report_completeness.py --fix <报告路径>  # 修复报告问题
"""

import os
import sys
import re
import yaml
from pathlib import Path
from typing import List, Dict, Tuple, Set
from datetime import datetime


class ReportCompletenessChecker:
    """报告完整性检查器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.config_file = self.project_root / "config.yaml"
        self.modules_dir = self.project_root / "modules"
        self.output_dir = self.project_root / "output"
        self.templates_dir = self.project_root / "templates"

        self.config: Dict = {}
        self.enabled_modules: List[str] = []
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def load_config(self) -> bool:
        """加载当前配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            self.enabled_modules = self.config.get('modules', {}).get('enabled', [])
            return True
        except Exception as e:
            self.issues.append(f"❌ 无法加载config.yaml: {e}")
            return False

    def check_report_metadata(self, content: str) -> Tuple[bool, Dict]:
        """检查报告元数据"""
        if not content.startswith('---'):
            self.issues.append("❌ 报告缺少元数据frontmatter")
            return False, {}

        try:
            parts = content.split('---', 2)
            if len(parts) < 3:
                self.issues.append("❌ 元数据格式不正确")
                return False, {}

            metadata = yaml.safe_load(parts[1])
            if not metadata:
                self.issues.append("❌ 元数据为空")
                return False, {}

            return True, metadata

        except Exception as e:
            self.issues.append(f"❌ 无法解析元数据: {e}")
            return False, {}

    def check_required_fields(self, metadata: Dict) -> bool:
        """检查必需字段"""
        required_fields = [
            'report_theme',
            'report_depth',
            'report_style',
            'report_date',
            'generated_by_modules',
            'total_modules'
        ]

        missing = []
        for field in required_fields:
            if field not in metadata:
                missing.append(field)

        if missing:
            self.issues.append(f"❌ 元数据缺少字段: {', '.join(missing)}")
            return False

        return True

    def check_module_consistency(self, metadata: Dict) -> bool:
        """检查模块一致性"""
        report_modules = metadata.get('generated_by_modules', [])
        config_modules = self.enabled_modules

        # 检查数量
        if len(report_modules) != len(config_modules):
            self.warnings.append(
                f"⚠️ 模块数量不匹配: 报告{len(report_modules)}个 vs 配置{len(config_modules)}个"
            )

        # 检查缺失的模块（配置中启用但报告未包含）
        missing_modules = set(config_modules) - set(report_modules)
        if missing_modules:
            self.issues.append(
                f"❌ 报告缺少模块: {', '.join(missing_modules)}"
            )

        # 检查多余的模块（报告包含但配置未启用）
        extra_modules = set(report_modules) - set(config_modules)
        if extra_modules:
            self.warnings.append(
                f"⚠️ 报告包含未启用的模块: {', '.join(extra_modules)}"
            )

        return len(missing_modules) == 0

    def check_data_snapshot(self, metadata: Dict) -> bool:
        """检查数据快照"""
        snapshot = metadata.get('data_snapshot', {})

        if not snapshot:
            self.warnings.append("⚠️ 缺少数据快照")
            return True

        # 检查数据新鲜度
        valuation_date = snapshot.get('valuation_date')
        if valuation_date:
            try:
                data_date = datetime.strptime(valuation_date, '%Y-%m-%d')
                today = datetime.now()
                days_old = (today - data_date).days

                if days_old > 14:
                    self.issues.append(
                        f"🚨 估值数据严重过期: {days_old}天前 ({valuation_date})"
                    )
                elif days_old > 7:
                    self.warnings.append(
                        f"⚠️ 估值数据较旧: {days_old}天前 ({valuation_date})"
                    )
            except:
                pass

        return True

    def check_module_footers(self, content: str) -> bool:
        """检查模块来源标记"""
        # 统计章节数
        chapter_count = len(re.findall(r'^## \d+', content, re.MULTILINE))

        # 统计模块来源标记
        footer_count = len(re.findall(r'章节来源', content))

        if chapter_count == 0:
            self.warnings.append("⚠️ 无法识别章节结构")
            return True

        coverage = footer_count / chapter_count if chapter_count > 0 else 0

        if coverage < 0.5:
            self.issues.append(
                f"❌ 模块来源标记覆盖率过低: {footer_count}/{chapter_count} ({coverage:.0%})"
            )
            return False
        elif coverage < 1.0:
            self.warnings.append(
                f"⚠️ 部分章节缺少模块来源标记: {footer_count}/{chapter_count} ({coverage:.0%})"
            )

        return True

    def check_placeholders(self, content: str) -> bool:
        """检查未填充的占位符"""
        # 查找各种占位符
        placeholders = re.findall(r'\[\[([^\]]+)\]\]', content)  # [[placeholder]]
        bracket_placeholders = re.findall(r'\[([^\]]+)\]', content)  # [placeholder]

        # 过滤掉合理的占位符（如链接、日期格式等）
        unreasonable = []
        for p in placeholders:
            if not any(keyword in p.lower() for keyword in ['date', 'time', 'link', 'url']):
                unreasonable.append(f"[[{p}]]")

        for p in bracket_placeholders:
            # 检查是否像占位符（包含关键词如"公司"、"代码"等）
            if any(keyword in p for keyword in ['公司', '代码', '价格', '市值', '金额']):
                unreasonable.append(f"[{p}]")

        if len(unreasonable) > 20:
            self.issues.append(
                f"❌ 报告中有 {len(unreasonable)} 个未填充的占位符"
            )
            # 显示前10个示例
            for p in unreasonable[:10]:
                self.issues.append(f"    - {p}")
            return False
        elif len(unreasonable) > 5:
            self.warnings.append(
                f"⚠️ 报告中有 {len(unreasonable)} 个占位符"
            )

        return True

    def check_chapter_structure(self, content: str) -> bool:
        """检查章节结构连续性"""
        chapters = re.findall(r'^## (\d+)', content, re.MULTILINE)

        if not chapters:
            self.warnings.append("⚠️ 无法识别章节编号")
            return True

        # 检查章节连续性
        chapter_nums = [int(c) for c in chapters]
        expected = list(range(1, len(chapter_nums) + 1))

        if chapter_nums != expected:
            missing = set(expected) - set(chapter_nums)
            extra = set(chapter_nums) - set(expected)
            if missing:
                self.warnings.append(f"⚠️ 缺失章节编号: {sorted(missing)}")
            if extra:
                self.warnings.append(f"⚠️ 多余章节编号: {sorted(extra)}")

        return True

    def check_links(self, content: str) -> bool:
        """检查链接完整性"""
        # 查找Obsidian风格的链接
        obsidian_links = re.findall(r'\[\[([^\]|]+)\|?([^\]]*)\]\]', content)

        broken_links = []
        for link, alias in obsidian_links:
            # 检查链接目标是否存在（简化检查，实际需要检查文件系统）
            if link.startswith('http'):
                continue  # 外部链接不检查

            # 这里可以做更复杂的检查
            pass

        if broken_links:
            self.warnings.append(f"⚠️ 可能有 {len(broken_links)} 个断链")

        return True

    def verify_report(self, report_path: str) -> Tuple[bool, Dict]:
        """验证完整报告"""
        self.issues = []
        self.warnings = []

        print(f"\n验证报告: {report_path}")
        print("-" * 60)

        # 加载配置
        if not self.load_config():
            return False, {}

        # 读取报告
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.issues.append(f"❌ 无法读取报告: {e}")
            return False, {}

        # 执行各项检查
        checks = [
            ("元数据检查", lambda: self.check_report_metadata(content)),
            ("必需字段检查", lambda c: (self.check_required_fields(c[1]), c[1]) if c[0] else (False, {})),
            ("模块一致性检查", lambda m: (self.check_module_consistency(m[1]), m[1]) if m[0] else (False, {})),
            ("数据快照检查", lambda m: (self.check_data_snapshot(m[1]), m[1])),
            ("模块来源标记检查", lambda m: (self.check_module_footers(content), m[1])),
            ("占位符检查", lambda m: (self.check_placeholders(content), m[1])),
            ("章节结构检查", lambda m: (self.check_chapter_structure(content), m[1])),
            ("链接检查", lambda m: (self.check_links(content), m[1])),
        ]

        result = None
        for check_name, check_func in checks:
            try:
                if result is None:
                    result = check_func()
                else:
                    result = check_func(result)
            except Exception as e:
                self.issues.append(f"❌ {check_name}失败: {e}")

        # 输出结果
        metadata = result[1] if result else {}

        print(f"\n## 验证结果")
        print(f"  问题数: {len(self.issues)}")
        print(f"  警告数: {len(self.warnings)}")

        if self.issues:
            print(f"\n## 问题列表")
            for issue in self.issues:
                print(f"  {issue}")

        if self.warnings:
            print(f"\n## 警告列表")
            for warning in self.warnings:
                print(f"  {warning}")

        success = len(self.issues) == 0

        if success:
            print("\n✅ 报告完整性验证通过！")
        else:
            print(f"\n❌ 报告存在问题，建议修复")

        return success, metadata

    def verify_all_reports(self) -> Dict[str, bool]:
        """验证所有报告"""
        results = {}

        if not self.output_dir.exists():
            print("❌ output目录不存在")
            return results

        reports = list(self.output_dir.glob("*.md"))

        print(f"\n开始验证 {len(reports)} 个报告...")
        print("=" * 60)

        for report in reports:
            success, _ = self.verify_report(str(report))
            results[report.name] = success

        # 汇总
        print("\n" + "=" * 60)
        print("验证汇总")
        print("=" * 60)

        passed = sum(1 for v in results.values() if v)
        failed = len(results) - passed

        print(f"  通过: {passed}/{len(results)}")
        print(f"  失败: {failed}/{len(results)}")

        if failed > 0:
            print("\n失败的报告:")
            for name, success in results.items():
                if not success:
                    print(f"  - {name}")

        return results

    def generate_fix_suggestions(self, report_path: str) -> List[str]:
        """生成修复建议"""
        self.verify_report(report_path)

        suggestions = []

        for issue in self.issues:
            if "缺少元数据" in issue:
                suggestions.append("运行: python generate_report_v2.py --add-metadata <报告路径>")
            elif "模块" in issue and "缺少" in issue:
                suggestions.append("检查config.yaml中的modules.enabled配置")
                suggestions.append("重新生成报告以包含所有模块")
            elif "占位符" in issue:
                suggestions.append("检查AI填充是否完成")
                suggestions.append("手动填充或重新生成报告")
            elif "数据过期" in issue:
                suggestions.append("运行: python update_data.py")
                suggestions.append("然后重新生成报告")

        return suggestions


def main():
    import argparse

    parser = argparse.ArgumentParser(description='报告完整性验证工具')
    parser.add_argument('report', nargs='?', type=str, help='要验证的报告路径')
    parser.add_argument('--all', action='store_true', help='验证所有报告')
    parser.add_argument('--fix-suggestions', action='store_true', help='生成修复建议')
    parser.add_argument('--project-root', type=str, default='.', help='项目根目录')

    args = parser.parse_args()

    checker = ReportCompletenessChecker(args.project_root)

    if args.all:
        checker.verify_all_reports()
    elif args.report:
        success, metadata = checker.verify_report(args.report)

        if args.fix_suggestions and not success:
            print("\n## 修复建议")
            suggestions = checker.generate_fix_suggestions(args.report)
            for suggestion in suggestions:
                print(f"  - {suggestion}")

        sys.exit(0 if success else 1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
