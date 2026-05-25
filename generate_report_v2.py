#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版报告生成脚本 - 模块化、可追溯、可验证

功能：
1. 生成报告时自动添加模块依赖元数据
2. 每个章节末尾自动添加模块来源标记
3. 从config.yaml动态读取启用的模块
4. 生成后自动验证报告完整性

用法：
    python generate_report_v2.py                    # 使用config.yaml生成报告
    python generate_report_v2.py --verify <报告路径>  # 验证已有报告
    python generate_report_v2.py --add-metadata <报告路径>  # 为旧报告添加元数据
"""

import os
import sys
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from style_manager import StyleManager


class ModularReportGenerator:
    """模块化报告生成器"""

    def __init__(self, project_root: str = ".", theme: str = None):
        self.project_root = Path(project_root)
        self.theme = theme

        # 支持 themes/ 目录结构
        if theme:
            self.config_file = self.project_root / "themes" / theme / "config.yaml"
            self.data_dir = self.project_root / "themes" / theme / "data"
        else:
            # 回退到根目录（兼容旧版本）
            self.config_file = self.project_root / "config.yaml"
            self.data_dir = self.project_root / "data"

        self.modules_dir = self.project_root / "modules"
        self.templates_dir = self.project_root / "templates"
        self.output_dir = self.project_root / "output"

        self.config: Dict = {}
        self.enabled_modules: List[str] = []
        self.module_metadata: Dict[str, Dict] = {}

        # 初始化风格管理器
        self.style_manager = StyleManager(project_root)

    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)

            self.enabled_modules = self.config.get('modules', {}).get('enabled', [])
            print(f"[OK] 加载配置: {len(self.enabled_modules)} 个模块已启用")
            return True
        except Exception as e:
            print(f"[ERROR] 加载config.yaml失败: {e}")
            return False

    def load_module_metadata(self) -> None:
        """加载所有模块的元数据"""
        if not self.modules_dir.exists():
            print(f"[ERROR] 模块目录不存在: {self.modules_dir}")
            return

        for module_file in self.modules_dir.glob("*.md"):
            module_name = module_file.stem
            try:
                with open(module_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 解析frontmatter
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])
                        if frontmatter:
                            self.module_metadata[module_name] = {
                                'name': frontmatter.get('module', module_name),
                                'version': frontmatter.get('version', 'unknown'),
                                'description': frontmatter.get('description', ''),
                                'last_updated': frontmatter.get('last_updated', ''),
                                'dependencies': frontmatter.get('dependencies', [])
                            }
            except Exception as e:
                print(f"[WARN] 无法解析 {module_name}: {e}")

        print(f"[OK] 加载了 {len(self.module_metadata)} 个模块的元数据")

    def get_data_snapshot(self) -> Dict:
        """获取数据文件快照信息"""
        snapshot = {
            'valuation_date': None,
            'tickers_version': None,
            'catalysts_version': None,
            'data_freshness': {}
        }

        # 获取数据路径
        data_path = self.project_root / self.config.get('data_path', 'data/孙哥方向/')

        # 检查valuation.yaml
        valuation_file = data_path / 'valuation.yaml'
        if valuation_file.exists():
            try:
                with open(valuation_file, 'r', encoding='utf-8') as f:
                    valuation = yaml.safe_load(f)
                    if valuation and 'last_updated' in valuation:
                        snapshot['valuation_date'] = valuation['last_updated']
            except:
                pass

        # 检查tickers.yaml
        tickers_file = data_path / 'tickers.yaml'
        if tickers_file.exists():
            try:
                with open(tickers_file, 'r', encoding='utf-8') as f:
                    tickers = yaml.safe_load(f)
                    if tickers and 'version' in tickers:
                        snapshot['tickers_version'] = tickers['version']
            except:
                pass

        return snapshot

    def generate_report_metadata(self) -> str:
        """生成报告元数据YAML frontmatter"""
        theme = self.config.get('theme', {})
        output = self.config.get('output', {})
        snapshot = self.get_data_snapshot()

        metadata = {
            'report_theme': theme.get('name', 'Unknown'),
            'report_theme_id': theme.get('id', ''),
            'report_description': theme.get('description', ''),
            'report_depth': output.get('depth', 'L3'),
            'report_style': output.get('style', '专业风'),
            'report_market_focus': output.get('market_focus', '中美双线'),
            'report_date': datetime.now().strftime('%Y-%m-%d'),
            'report_version': self.config.get('meta', {}).get('skill_version', '2.0'),
            'generated_by_modules': self.enabled_modules,
            'total_modules': len(self.enabled_modules),
            'data_snapshot': snapshot
        }

        # 转换为YAML字符串
        yaml_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True)
        return f"---\n{yaml_str}---\n"

    def get_module_footer(self, module_name: str) -> str:
        """获取模块来源标记"""
        metadata = self.module_metadata.get(module_name, {})

        if not metadata:
            return f"\n\n---\n*本章节内容来自模块: {module_name}.md*\n"

        name = metadata.get('name', module_name)
        version = metadata.get('version', 'unknown')
        last_updated = metadata.get('last_updated', '')
        description = metadata.get('description', '')

        footer = f"\n\n---\n"
        footer += f"[章节来源] "
        footer += f"模块: `{module_name}.md` | "
        footer += f"版本: v{version}"
        if last_updated:
            footer += f" | 更新: {last_updated}"
        if description:
            footer += f"\n[说明] {description}"
        footer += "\n"

        return footer

    def get_module_section_number(self, module_name: str) -> int:
        """获取模块的章节序号"""
        try:
            # 从模块名中提取序号（如"00-市场情绪分析" -> 0）
            match = re.match(r'^(\d+)-', module_name)
            if match:
                return int(match.group(1))
        except:
            pass
        return 99

    def build_report_structure(self) -> List[Tuple[str, str, str]]:
        """
        构建报告结构
        返回: [(章节序号, 模块名, 章节标题), ...]
        """
        structure = []

        # 按序号排序启用的模块
        sorted_modules = sorted(
            self.enabled_modules,
            key=lambda x: self.get_module_section_number(x)
        )

        for i, module_name in enumerate(sorted_modules, 1):
            # 获取模块标题
            metadata = self.module_metadata.get(module_name, {})
            title = metadata.get('name', module_name)

            # 章节序号
            section_num = self.get_module_section_number(module_name)

            structure.append((section_num, module_name, title))

        return structure

    def generate_report_instructions(self) -> str:
        """生成报告生成指令（给AI的提示，包含风格要求）"""
        structure = self.build_report_structure()

        theme = self.config.get('theme', {})
        output = self.config.get('output', {})

        style_name = output.get('style', '散户科普风')
        depth = output.get('depth', 'L3')

        # 获取风格适配建议
        is_valid, style_msg = self.style_manager.validate_style_depth(style_name, depth)
        style_instructions = self.style_manager.get_agent_style_instructions(style_name, depth)

        instructions = f"""# 报告生成指令

## 报告配置

- **主题**: {theme.get('name', 'Unknown')}
- **深度**: {depth}
- **风格**: {style_name}
- **市场焦点**: {output.get('market_focus', '中美双线')}
- **生成日期**: {datetime.now().strftime('%Y-%m-%d')}

## 风格适配检查

**风格**: {style_name}
**深度**: {depth}
**状态**: {style_msg}

---

## 写作风格要求（必须遵守）

{style_instructions}

---

## 启用的模块 ({len(structure)} 个)

"""

        for section_num, module_name, title in structure:
            metadata = self.module_metadata.get(module_name, {})
            version = metadata.get('version', '?')
            instructions += f"{section_num}. **{title}** (`{module_name}.md` v{version})\n"

        instructions += f"""
## 生成要求

1. **报告头部**: 必须包含以下元数据frontmatter
```yaml
---
report_theme: "{theme.get('name', '')}"
report_depth: "{depth}"
report_style: "{style_name}"
report_date: "{datetime.now().strftime('%Y-%m-%d')}"
generated_by_modules: {self.enabled_modules}
total_modules: {len(self.enabled_modules)}
---
```

2. **写作风格**: 必须严格遵循"写作风格要求"中的规定
   - 语气: 必须与"{style_name}"一致
   - 句式: 必须使用规定的句式特征
   - 结构: 必须包含必用结构中的所有元素

3. **每个章节**: 在内容后添加模块来源标记
```markdown
---
[章节来源] | 模块: `XX-模块名.md` | 版本: vX.X | 更新: YYYY-MM-DD
[说明] 模块描述
```

4. **内容填充**: 按模块文件内容填充，**同时保持风格一致性**

5. **章节编号**: 使用连续编号（如果某个模块被禁用，后续模块自动前移）

## 输出路径

保存到: `output/{theme.get('id', 'theme')}-{datetime.now().strftime('%Y-%m-%d')}-{depth}-{style_name.replace(' ', '_')}.md`

---

现在请按以上配置生成完整报告，**写作风格必须与"{style_name}"完全一致**。
"""

        return instructions

    def verify_report(self, report_path: str) -> Tuple[bool, List[str]]:
        """验证报告的完整性和一致性"""
        issues = []

        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 1. 检查是否有元数据frontmatter
            if not content.startswith('---'):
                issues.append("[ERROR] 报告缺少元数据frontmatter")
            else:
                try:
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        metadata = yaml.safe_load(parts[1])
                        if metadata:
                            # 检查必需字段
                            required = ['report_theme', 'report_depth', 'generated_by_modules']
                            for field in required:
                                if field not in metadata:
                                    issues.append(f"[ERROR] 元数据缺少字段: {field}")

                            # 检查模块数量是否匹配
                            if 'generated_by_modules' in metadata:
                                report_modules = metadata['generated_by_modules']
                                config_modules = self.enabled_modules

                                # 检查缺失的模块
                                missing = set(config_modules) - set(report_modules)
                                if missing:
                                    issues.append(f"[WARN] 报告缺少模块: {missing}")

                                # 检查多余的模块
                                extra = set(report_modules) - set(config_modules)
                                if extra:
                                    issues.append(f"[WARN] 报告包含未启用的模块: {extra}")
                except Exception as e:
                    issues.append(f"[ERROR] 无法解析报告元数据: {e}")

            # 2. 检查章节是否有模块来源标记
            module_sections = re.findall(r'##?\s+\d*\.?\s*([^\n]+)', content)
            chapters_without_footer = 0

            for section in module_sections[:20]:  # 只检查前20个章节
                # 检查是否有模块来源标记
                section_pattern = re.escape(section.strip())
                if not re.search(f"{section_pattern}.*?---.*?模块来源", content, re.DOTALL):
                    chapters_without_footer += 1

            if chapters_without_footer > 5:
                issues.append(f"[WARN] {chapters_without_footer} 个章节缺少模块来源标记")

            # 3. 检查占位符是否已填充
            placeholder_count = len(re.findall(r'\[\[.*?\]\]', content))
            if placeholder_count > 10:
                issues.append(f"[WARN] 报告中有 {placeholder_count} 个未填充的占位符")

            return len(issues) == 0, issues

        except Exception as e:
            return False, [f"[ERROR] 无法读取报告: {e}"]

    def add_metadata_to_existing_report(self, report_path: str) -> bool:
        """为已有的报告添加元数据"""
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 如果已有元数据，跳过
            if content.startswith('---') and 'report_theme' in content[:500]:
                print(f"[SKIP] 报告已有元数据: {report_path}")
                return True

            # 生成元数据
            metadata = self.generate_report_metadata()

            # 在文件开头添加元数据
            new_content = metadata + "\n" + content

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"[OK] 已添加元数据到: {report_path}")
            return True

        except Exception as e:
            print(f"[ERROR] 添加元数据失败: {e}")
            return False

    def print_generation_summary(self) -> None:
        """打印报告生成摘要（包含风格信息）"""
        print("\n" + "=" * 60)
        print("模块化报告生成摘要")
        print("=" * 60)

        print(f"\n## 配置信息")
        theme = self.config.get('theme', {})
        output = self.config.get('output', {})
        style_name = output.get('style', '散户科普风')
        depth = output.get('depth', 'L3')
        print(f"  主题: {theme.get('name', 'Unknown')}")
        print(f"  深度: {depth}")
        print(f"  风格: {style_name}")
        print(f"  启用模块: {len(self.enabled_modules)} 个")

        # 添加风格适配检查
        is_valid, style_msg = self.style_manager.validate_style_depth(style_name, depth)
        print(f"\n## 风格适配检查")
        print(f"  {style_msg}")

        # 如果不适配，列出推荐风格
        if not is_valid or '⚠️' in style_msg or '勉强' in style_msg:
            print(f"\n  推荐风格:")
            profile = self.style_manager.parse_style_profile(style_name)
            if depth in profile.best_depths:
                print(f"    - {style_name}: ✅ 适合{depth}")
            else:
                # 查找适合当前深度的风格
                available_styles = self.style_manager.list_available_styles()
                for style_info in available_styles:
                    if depth in style_info['best_depths']:
                        print(f"    - {style_info['name']}: ✅ 适合{depth} ({style_info['positioning']})")
                        break

        print(f"\n## 模块清单")
        for i, module_name in enumerate(self.enabled_modules, 1):
            metadata = self.module_metadata.get(module_name, {})
            title = metadata.get('name', module_name)
            version = metadata.get('version', '?')
            print(f"  {i:2}. {title} (v{version})")

        print(f"\n## 生成指令")
        print("  请将以下指令复制给AI:")
        print("  " + "-" * 50)
        print(f"  请基于config.yaml配置生成{theme.get('name', '主题')}的深度报告")
        print(f"  要求：包含模块元数据frontmatter，每个章节添加模块来源标记")
        print("  " + "-" * 50)

        print("\n" + "=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='模块化报告生成工具')
    parser.add_argument('--theme', type=str, help='指定主题目录（如：物理AI）')
    parser.add_argument('--verify', type=str, help='验证指定报告')
    parser.add_argument('--add-metadata', type=str, help='为旧报告添加元数据')
    parser.add_argument('--instructions', action='store_true', help='输出生成指令')
    parser.add_argument('--project-root', type=str, default='.', help='项目根目录')

    args = parser.parse_args()

    generator = ModularReportGenerator(args.project_root, theme=args.theme)

    # 加载配置
    if not generator.load_config():
        sys.exit(1)

    generator.load_module_metadata()

    if args.verify:
        print(f"验证报告: {args.verify}")
        success, issues = generator.verify_report(args.verify)
        if issues:
            for issue in issues:
                print(f"  {issue}")
        if success:
            print("[OK] 报告验证通过")
        sys.exit(0 if success else 1)

    elif args.add_metadata:
        success = generator.add_metadata_to_existing_report(args.add_metadata)
        sys.exit(0 if success else 1)

    elif args.instructions:
        print(generator.generate_report_instructions())

    else:
        # 默认：打印生成摘要和指令
        generator.print_generation_summary()
        print("\n## 完整生成指令:\n")
        print(generator.generate_report_instructions())


if __name__ == '__main__':
    main()
