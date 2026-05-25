#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告合并器 (Report Merger)

功能：
1. 收集各Agent的输出文件
2. 按执行顺序合并
3. 添加报告元数据和章节标记
4. 生成目录和导航
5. 输出最终报告

用法：
    from report_merger import ReportMerger

    merger = ReportMerger()
    report = merger.merge_reports()

    # 或者命令行
    python report_merger.py --input .agent_temp/ --output output/
"""

import re
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class AgentOutput:
    """Agent输出数据"""
    agent_name: str
    module_name: str
    content: str
    order: int
    status: str = "completed"


class ReportMerger:
    """报告合并器"""

    def __init__(self, project_root: str = ".", temp_dir: Path = None,
                 theme: str = None, execution_id: str = None):
        self.project_root = Path(project_root)

        # 确定临时目录
        if temp_dir:
            # 直接指定临时目录
            self.temp_dir = Path(temp_dir)
        elif execution_id:
            # 指定执行ID
            self.temp_dir = self.project_root / ".agent_temp" / execution_id
        elif theme:
            # 指定主题，查找最新的执行
            self.temp_dir = self._find_latest_execution(theme)
            if not self.temp_dir:
                raise FileNotFoundError(f"未找到主题 '{theme}' 的执行记录")
        else:
            # 默认使用当前临时目录（兼容旧版本）
            self.temp_dir = self.project_root / ".agent_temp"

        self.output_dir = self.project_root / "output"
        self.modules_dir = self.project_root / "modules"

        # 确保输出目录存在
        self.output_dir.mkdir(exist_ok=True)

        # 验证临时目录存在
        if not self.temp_dir.exists():
            raise FileNotFoundError(f"临时目录不存在: {self.temp_dir}")

        print(f"[Merger] 使用执行目录: {self.temp_dir}")

        # Agent执行顺序（与协调器一致）
        self.execution_order = [
            # Layer 1: 入口Agent
            ["00-市场情绪分析Agent", "01-市场环境扫描Agent", "02-核心投资哲学Agent",
             "06-催化剂日历Agent", "07-中美对比矩阵Agent", "08-风险矩阵与对冲Agent",
             "11-动态跟踪机制Agent", "13-ETF备选与核心逻辑Agent", "14-深度核心逻辑摘要Agent"],
            # Layer 2: 分析Agent
            ["03-产业链拆解Agent", "16-供应链分析Agent", "15-产业链全景图谱Agent",
             "04-铲子股筛选Agent", "05-护城河评估Agent"],
            # Layer 3: 决策Agent
            ["09-组合构建Agent", "10-实操指南Agent", "12-预测与实际对比Agent"],
        ]

        # Agent到模块的映射
        self.agent_module_map = {
            "00-市场情绪分析Agent": "00-市场情绪分析",
            "01-市场环境扫描Agent": "01-市场环境扫描",
            "02-核心投资哲学Agent": "02-核心投资哲学",
            "03-产业链拆解Agent": "03-产业链拆解",
            "04-铲子股筛选Agent": "04-铲子股筛选",
            "05-护城河评估Agent": "05-护城河评估",
            "06-催化剂日历Agent": "06-催化剂日历",
            "07-中美对比矩阵Agent": "07-中美对比矩阵",
            "08-风险矩阵与对冲Agent": "08-风险矩阵与对冲",
            "09-组合构建Agent": "09-组合构建",
            "10-实操指南Agent": "10-实操指南",
            "11-动态跟踪机制Agent": "11-动态跟踪机制",
            "12-预测与实际对比Agent": "12-预测与实际对比",
            "13-ETF备选与核心逻辑Agent": "13-ETF备选与核心逻辑",
            "14-深度核心逻辑摘要Agent": "14-深度核心逻辑摘要",
            "15-产业链全景图谱Agent": "15-产业链全景图谱",
            "16-供应链分析Agent": "16-供应链分析",
        }

    def _find_latest_execution(self, theme: str) -> Optional[Path]:
        """
        查找指定主题最新的执行目录

        Args:
            theme: 主题名称

        Returns:
            最新执行目录的Path，未找到返回None
        """
        temp_base = self.project_root / ".agent_temp"
        if not temp_base.exists():
            return None

        # 主题slug化（与orchestrator一致）
        theme_slug = theme.replace("/", "_").replace(" ", "_").replace("-", "_")

        candidates = []
        for item in temp_base.iterdir():
            if not item.is_dir():
                continue

            # 解析目录名: theme_YYYYMMDD_HHMMSS_xxxxxx
            name_parts = item.name.split('_')
            if len(name_parts) < 3:
                continue

            # 检查是否是目标主题
            if name_parts[0] != theme_slug:
                continue

            # 提取时间戳
            try:
                timestamp_str = f"{name_parts[1]}_{name_parts[2]}"
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                # 检查是否有元数据文件
                metadata_file = item / "_metadata.yaml"
                if metadata_file.exists():
                    candidates.append((timestamp, item))
            except (ValueError, IndexError):
                continue

        if not candidates:
            return None

        # 按时间排序，返回最新的
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def collect_agent_outputs(self) -> List[AgentOutput]:
        """
        收集所有Agent的输出

        Returns:
            List[AgentOutput]: Agent输出列表
        """
        outputs = []

        # 遍历所有可能的Agent输出
        for layer_idx, layer in enumerate(self.execution_order, 1):
            for agent_idx, agent_name in enumerate(layer, 1):
                # 尝试多种可能的输出文件名
                possible_files = [
                    self.temp_dir / f"{agent_name}_output.md",
                    self.temp_dir / f"{agent_name}.md",
                    self.temp_dir / f"{agent_name}_result.md",
                ]

                content = None
                for file_path in possible_files:
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        break

                # 如果没有找到输出文件，尝试读取指令文件作为占位
                if content is None:
                    instruction_file = self.temp_dir / f"{agent_name}_instructions.md"
                    if instruction_file.exists():
                        with open(instruction_file, 'r', encoding='utf-8') as f:
                            content = f"<!-- {agent_name} 等待执行 -->\n"

                if content:
                    module_name = self.agent_module_map.get(agent_name, "unknown")
                    outputs.append(AgentOutput(
                        agent_name=agent_name,
                        module_name=module_name,
                        content=content,
                        order=layer_idx * 100 + agent_idx
                    ))

        # 按顺序排序
        outputs.sort(key=lambda x: x.order)
        return outputs

    def generate_frontmatter(self, outputs: List[AgentOutput], config: Dict) -> str:
        """
        生成报告元数据frontmatter

        Args:
            outputs: Agent输出列表
            config: 配置数据

        Returns:
            YAML frontmatter字符串
        """
        theme = config.get('theme', {})
        output_config = config.get('output', {})

        frontmatter = {
            'report_title': theme.get('name', '投资分析报告'),
            'report_theme': theme.get('id', 'unknown'),
            'report_depth': output_config.get('depth', 'L3'),
            'report_style': output_config.get('style', '散户科普风'),
            'report_date': datetime.now().strftime('%Y-%m-%d'),
            'generated_by_modules': [o.module_name for o in outputs],
            'total_modules': len(outputs),
            'data_snapshot': {
                'valuation_date': datetime.now().strftime('%Y-%m-%d'),
                'tickers_version': '2.0',
            },
            'agent_execution': {
                'total_agents': len(outputs),
                'completed': sum(1 for o in outputs if o.status == 'completed'),
                'layers': len(self.execution_order),
            }
        }

        return yaml.dump(frontmatter, allow_unicode=True, sort_keys=False)

    def generate_toc(self, outputs: List[AgentOutput]) -> str:
        """
        生成目录

        Args:
            outputs: Agent输出列表

        Returns:
            目录Markdown字符串
        """
        toc = "## 目录\n\n"

        for idx, output in enumerate(outputs, 1):
            # 提取内容中的第一个标题
            first_heading = self._extract_first_heading(output.content)
            if first_heading:
                toc += f"{idx}. [{first_heading}](#{self._anchorize(first_heading)})\n"
            else:
                toc += f"{idx}. [{output.module_name}](#{self._anchorize(output.module_name)})\n"

        toc += "\n---\n\n"
        return toc

    def _extract_first_heading(self, content: str) -> Optional[str]:
        """提取内容中的第一个标题"""
        lines = content.strip().split('\n')
        for line in lines:
            # 匹配 # 标题 或 ## 标题
            match = re.match(r'^#{1,2}\s+(.+)$', line.strip())
            if match:
                return match.group(1).strip()
        return None

    def _anchorize(self, text: str) -> str:
        """将标题转换为锚点ID"""
        # 移除特殊字符，替换空格为-
        anchor = re.sub(r'[^\w\s-]', '', text)
        anchor = re.sub(r'\s+', '-', anchor)
        return anchor.lower()

    def add_module_marker(self, content: str, agent_name: str, module_name: str) -> str:
        """
        添加模块来源标记

        Args:
            content: 原始内容
            agent_name: Agent名称
            module_name: 模块名称

        Returns:
            添加标记后的内容
        """
        # 如果内容已包含模块标记，不重复添加
        if "章节来源" in content or "module:" in content:
            return content

        # 从模块文件读取描述
        module_file = self.modules_dir / f"{module_name}.md"
        description = ""
        if module_file.exists():
            try:
                with open(module_file, 'r', encoding='utf-8') as f:
                    content_lines = f.read().split('\n')
                    # 查找frontmatter中的description
                    for i, line in enumerate(content_lines):
                        if line.startswith('description:'):
                            description = line.split(':', 1)[1].strip().strip('"')
                            break
            except:
                pass

        marker = f"\n\n---\n"
        marker += f"📄 **章节来源** | 模块: `{module_name}.md` | Agent: `{agent_name}`\n"
        if description:
            marker += f"💡 {description}\n"
        marker += "---\n"

        return content + marker

    def clean_content(self, content: str) -> str:
        """
        清理Agent输出内容

        Args:
            content: 原始内容

        Returns:
            清理后的内容
        """
        # 移除AI常见的元注释
        content = re.sub(r'^```markdown\s*\n', '', content)
        content = re.sub(r'\n```\s*$', '', content)

        # 移除"以下是..."等元语言
        content = re.sub(r'^(以下是|这是|此为).{0,30}[：:]\s*\n', '', content)

        # 标准化标题层级
        content = self._normalize_headings(content)

        return content.strip()

    def _normalize_headings(self, content: str) -> str:
        """标准化标题层级"""
        lines = content.split('\n')
        result = []

        for line in lines:
            # 确保标题格式正确
            if re.match(r'^#{1,6}[^\s]', line):
                # 添加空格
                line = re.sub(r'^(#{1,6})', r'\1 ', line)
            result.append(line)

        return '\n'.join(result)

    def merge_reports(self, config: Optional[Dict] = None) -> str:
        """
        合并所有Agent输出为最终报告

        Args:
            config: 配置数据

        Returns:
            完整报告内容
        """
        if config is None:
            config = {}

        # 收集所有Agent输出
        outputs = self.collect_agent_outputs()

        if not outputs:
            print("[Merger] 警告: 未找到任何Agent输出")
            return ""

        print(f"[Merger] 收集到 {len(outputs)} 个Agent输出")

        # 开始构建报告
        report_parts = []

        # 1. Frontmatter
        frontmatter = self.generate_frontmatter(outputs, config)
        report_parts.append(f"---\n{frontmatter}---\n")

        # 2. 报告标题
        theme_name = config.get('theme', {}).get('name', '投资分析报告')
        report_parts.append(f"# {theme_name}\n")
        report_parts.append(f"**生成日期**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        report_parts.append(f"**报告深度**: {config.get('output', {}).get('depth', 'L3')}\n")
        report_parts.append(f"**分析模块**: {len(outputs)} 个\n\n")

        # 3. 执行摘要（来自14-深度核心逻辑摘要）
        summary_output = next((o for o in outputs if "14-" in o.agent_name), None)
        if summary_output:
            report_parts.append("## 执行摘要\n")
            report_parts.append(summary_output.content[:2000])  # 取前2000字符
            report_parts.append("\n\n---\n\n")

        # 4. 目录
        report_parts.append(self.generate_toc(outputs))

        # 5. 各章节内容
        for output in outputs:
            # 跳过执行摘要（已在前面）
            if "14-" in output.agent_name:
                continue

            # 清理内容
            cleaned_content = self.clean_content(output.content)

            # 添加模块标记
            marked_content = self.add_module_marker(
                cleaned_content,
                output.agent_name,
                output.module_name
            )

            report_parts.append(marked_content)
            report_parts.append("\n\n")

        # 6. 附录：Agent执行状态
        report_parts.append("\n\n---\n\n")
        report_parts.append("## 附录：Agent执行状态\n\n")
        report_parts.append("| Agent | 模块 | 状态 |\n")
        report_parts.append("|-------|------|------|\n")
        for output in outputs:
            status_icon = "[OK]" if output.status == "completed" else "[PENDING]"
            report_parts.append(f"| {output.agent_name} | {output.module_name} | {status_icon} {output.status} |\n")

        return '\n'.join(report_parts)

    def save_report(self, content: str, filename: Optional[str] = None) -> str:
        """
        保存报告到文件

        Args:
            content: 报告内容
            filename: 文件名（可选）

        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"report_{timestamp}.md"

        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[Merger] 报告已保存: {output_path}")
        return str(output_path)

    def verify_report(self, report_path: str) -> Dict:
        """
        验证报告完整性

        Args:
            report_path: 报告文件路径

        Returns:
            验证结果
        """
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()

        result = {
            'has_frontmatter': content.startswith('---'),
            'has_title': '# ' in content,
            'has_toc': '## 目录' in content or '## 目錄' in content,
            'total_chapters': content.count('章节来源'),
            'total_placeholders': content.count('[公司]') + content.count('[代码]'),
        }

        return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description='报告合并器')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    parser.add_argument('--output', type=str, help='输出文件名')
    parser.add_argument('--verify', action='store_true', help='验证报告完整性')
    parser.add_argument('--list', action='store_true', help='列出可合并的Agent输出')
    parser.add_argument('--theme', type=str, help='指定主题，自动查找该主题的最新执行')
    parser.add_argument('--execution-id', type=str, help='指定执行ID')
    parser.add_argument('--temp-dir', type=str, help='直接指定临时目录')

    args = parser.parse_args()

    # 初始化Merger，支持多种方式指定执行目录
    try:
        if args.temp_dir:
            merger = ReportMerger(temp_dir=args.temp_dir)
        elif args.execution_id:
            merger = ReportMerger(execution_id=args.execution_id)
        elif args.theme:
            merger = ReportMerger(theme=args.theme)
        else:
            merger = ReportMerger()  # 使用默认临时目录
    except FileNotFoundError as e:
        print(f"[Merger] 错误: {e}")
        print("\n可用选项:")
        print("  --theme 主题名    # 自动查找该主题的最新执行")
        print("  --execution-id ID # 指定具体执行ID")
        print("  --temp-dir 路径   # 直接指定临时目录")
        return

    if args.list:
        # 列出所有可合并的输出
        outputs = merger.collect_agent_outputs()
        print(f"\n找到 {len(outputs)} 个Agent输出:")
        print(f"执行目录: {merger.temp_dir}\n")
        for output in outputs:
            status_icon = "[OK]" if output.status == "completed" else "[PENDING]"
            print(f"  {status_icon} {output.agent_name} ({output.module_name})")
        return

    # 加载配置
    config = {}
    config_path = Path(args.config)
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

    # 合并报告
    print("[Merger] 开始合并报告...")
    report_content = merger.merge_reports(config)

    if not report_content:
        print("[Merger] 错误: 无法生成报告（无Agent输出）")
        return

    # 保存报告
    output_path = merger.save_report(report_content, args.output)

    # 验证报告
    if args.verify:
        result = merger.verify_report(output_path)
        print("\n[Merger] 报告验证结果:")
        for key, value in result.items():
            print(f"  {key}: {value}")

    print(f"\n[Merger] 报告合并完成!")
    print(f"  输出路径: {output_path}")


if __name__ == '__main__':
    main()
