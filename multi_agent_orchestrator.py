#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多Agent协调器 (Multi-Agent Orchestrator)

功能：
1. 根据config.yaml解析模块依赖关系
2. 调度多个Agent并行/串行执行任务
3. 管理Agent间通信
4. 合并结果生成最终报告
5. 处理错误和重试

解决的问题：
- 单AI上下文溢出（大模块单独Agent处理）
- 专业化不足（每个Agent专精一个领域）
- 生成速度慢（无依赖模块并行）
- 一致性问题（专门Agent负责统一）

用法：
    python multi_agent_orchestrator.py              # 使用默认配置
    python multi_agent_orchestrator.py --parallel  # 启用并行模式
    python multi_agent_orchestrator.py --agent 市场情绪Agent  # 单独运行某个Agent
    python multi_agent_orchestrator.py --check     # 检查Agent状态
"""

import os
import sys
import json
import yaml
import asyncio
import secrets
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from agent_communication import AgentCommunicationManager, MessageType
from report_merger import ReportMerger
from style_manager import StyleManager


class AgentStatus(Enum):
    """Agent状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"        # 失败
    BLOCKED = "blocked"      # 被依赖阻塞


@dataclass
class AgentTask:
    """Agent任务定义"""
    agent_name: str
    module: str              # 对应的模块文件
    dependencies: List[str]  # 依赖的其他Agent
    status: AgentStatus = AgentStatus.PENDING
    output: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class MultiAgentOrchestrator:
    """多Agent协调器"""

    def __init__(self, project_root: str = ".", config_file: str = "config.yaml",
                 theme: str = None, execution_id: str = None):
        self.project_root = Path(project_root)
        self.theme = theme
        self.execution_id = execution_id

        # 支持 themes/ 目录结构
        if theme:
            self.config_file = self.project_root / "themes" / theme / "config.yaml"
            self.data_dir = self.project_root / "themes" / theme / "data"
        else:
            self.config_file = self.project_root / config_file
            self.data_dir = self.project_root / "data"

        self.modules_dir = self.project_root / "modules"
        self.agents_dir = self.project_root / "agents"
        self.output_dir = self.project_root / "output"

        # 主题隔离：生成唯一执行ID
        if not self.execution_id:
            self.execution_id = self._generate_execution_id()

        # 隔离目录：.agent_temp/{theme}_{date}_{suffix}/
        self.temp_base_dir = self.project_root / ".agent_temp"
        self.temp_dir = self.temp_base_dir / self.execution_id

        self.config: Dict = {}
        self.tasks: Dict[str, AgentTask] = {}
        self.execution_order: List[List[str]] = []  # 分层执行顺序

        # 初始化风格管理器
        self.style_manager = StyleManager(project_root)

        # 创建临时目录
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # 元数据文件
        self.metadata_file = self.temp_dir / "_metadata.yaml"

    def _generate_execution_id(self) -> str:
        """生成唯一执行ID：主题_日期_随机后缀"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        theme_slug = (self.theme or "default").replace("/", "_").replace(" ", "_").replace("-", "_")
        random_suffix = secrets.token_hex(4)  # 8位随机字符
        return f"{theme_slug}_{timestamp}_{random_suffix}"

    def save_execution_metadata(self, status: str = "running"):
        """保存执行元数据"""
        metadata = {
            "theme": self.theme,
            "execution_id": self.execution_id,
            "timestamp": datetime.now().isoformat(),
            "temp_dir": str(self.temp_dir),
            "total_agents": len(self.tasks),
            "layers": len(self.execution_order),
            "status": status,
            "agents": {
                name: {
                    "module": task.module,
                    "status": task.status.value,
                    "dependencies": task.dependencies
                }
                for name, task in self.tasks.items()
            }
        }
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            print(f"[Orchestrator] 警告: 无法保存元数据: {e}")

    def load_config(self) -> bool:
        """加载配置"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            print(f"[Orchestrator] 加载配置: {len(self.config.get('modules', {}).get('enabled', []))} 个模块")
            return True
        except Exception as e:
            print(f"[Orchestrator] 错误: 无法加载config.yaml: {e}")
            return False

    def parse_dependencies(self) -> Dict[str, List[str]]:
        """解析模块依赖关系"""
        # 首先检查 system/ 目录
        dependency_rules = self.project_root / "system" / "dependency-rules.yaml"
        if not dependency_rules.exists():
            # 回退到根目录（兼容旧版本）
            dependency_rules = self.project_root / "dependency-rules.yaml"

        deps_map = {}

        if dependency_rules.exists():
            try:
                with open(dependency_rules, 'r', encoding='utf-8') as f:
                    rules = yaml.safe_load(f)
                    for rule in rules.get('requires', []):
                        before = rule.get('before', '')
                        after = rule.get('after', '')
                        if before not in deps_map:
                            deps_map[before] = []
                        deps_map[before].append(after)
            except Exception as e:
                print(f"[Orchestrator] 警告: 无法解析依赖规则: {e}")
        else:
            print(f"[Orchestrator] 警告: 未找到依赖规则文件")

        return deps_map

    def build_execution_plan(self) -> List[List[str]]:
        """
        构建分层执行计划
        返回: [[第1层Agent], [第2层Agent], ...]
        """
        enabled_modules = self.config.get('modules', {}).get('enabled', [])
        deps_map = self.parse_dependencies()

        # 初始化任务
        self.tasks = {}
        for module in enabled_modules:
            agent_name = f"{module}Agent"
            deps = deps_map.get(module, [])
            # 只保留已启用的依赖
            deps = [d for d in deps if d in enabled_modules]
            self.tasks[agent_name] = AgentTask(
                agent_name=agent_name,
                module=module,
                dependencies=[f"{d}Agent" for d in deps]
            )

        # 拓扑排序，分层
        layers = []
        completed = set()
        remaining = set(self.tasks.keys())

        while remaining:
            # 找出当前可以执行的Agent（所有依赖已完成）
            ready = []
            for agent_name in remaining:
                task = self.tasks[agent_name]
                if all(dep in completed for dep in task.dependencies):
                    ready.append(agent_name)

            if not ready:
                # 存在循环依赖
                print(f"[Orchestrator] 错误: 检测到循环依赖")
                break

            layers.append(ready)
            completed.update(ready)
            remaining -= set(ready)

        self.execution_order = layers
        return layers

    def get_agent_system_prompt(self, agent_name: str) -> str:
        """获取Agent系统提示词"""
        # 首先尝试从agents/目录加载
        prompt_file = self.agents_dir / f"{agent_name}.md"
        if prompt_file.exists():
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()

        # 否则使用默认提示词
        return self._generate_default_prompt(agent_name)

    def _generate_default_prompt(self, agent_name: str) -> str:
        """生成默认Agent提示词"""
        task = self.tasks.get(agent_name)
        if not task:
            return ""

        module_name = task.module
        module_file = self.modules_dir / f"{module_name}.md"

        # 读取模块描述
        module_desc = ""
        if module_file.exists():
            try:
                with open(module_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            fm = yaml.safe_load(parts[1])
                            module_desc = fm.get('description', '')
            except:
                pass

        return f"""# {agent_name} 系统提示词

## 角色定位

你是 **{agent_name}**，专门负责处理投资分析报告中的"{module_name}"模块。

## 你的专长

- {module_desc if module_desc else '专业分析和内容生成'}
- 严格按模板格式输出
- 确保数据准确性和时效性

## 你的职责

1. 读取模块模板 `modules/{module_name}.md`
2. 根据输入数据填充内容
3. 按规定的格式和风格输出
4. 确保专业性和准确性

## 输入依赖

{chr(10).join(f'- {dep}' for dep in task.dependencies) if task.dependencies else '无（本Agent是入口点）'}

## 输出要求

- 严格遵循模板中的表格结构
- 所有占位符必须填充或明确标记
- 数据必须注明来源和日期
- 保持专业、客观的风格

## 禁止事项

- 不要输出其他模块的内容（那是其他Agent的职责）
- 不要假设你不知道的数据（使用占位符标记）
- 不要修改模板的结构

## 输出格式

直接输出填充后的Markdown内容，不要包含任何解释或元注释。
"""

    async def run_agent(self, agent_name: str, mode: str = "normal") -> bool:
        """
        运行单个Agent

        Args:
            agent_name: Agent名称
            mode: 运行模式 (normal/simulation)
        """
        task = self.tasks.get(agent_name)
        if not task:
            print(f"[Orchestrator] 错误: 未知Agent {agent_name}")
            return False

        task.status = AgentStatus.RUNNING
        task.start_time = datetime.now()

        print(f"[Orchestrator] Agent启动: {agent_name}")

        try:
            # 获取系统提示词
            system_prompt = self.get_agent_system_prompt(agent_name)

            # 读取模块模板
            module_file = self.modules_dir / f"{task.module}.md"
            if not module_file.exists():
                raise FileNotFoundError(f"模块文件不存在: {task.module}")

            with open(module_file, 'r', encoding='utf-8') as f:
                module_content = f.read()

            # 读取依赖输出
            dependency_data = {}
            for dep in task.dependencies:
                dep_task = self.tasks.get(dep)
                if dep_task and dep_task.output:
                    dependency_data[dep] = dep_task.output

            # 在simulation模式下，模拟Agent输出
            if mode == "simulation":
                await asyncio.sleep(0.5)  # 模拟执行时间
                task.output = self._simulate_agent_output(agent_name, module_content)
                task.status = AgentStatus.COMPLETED
                print(f"[Orchestrator] Agent完成: {agent_name} (模拟)")
            else:
                # 实际模式下，生成Agent指令
                instructions = self._generate_agent_instructions(
                    agent_name, system_prompt, module_content, dependency_data
                )

                # 保存到临时文件（供外部AI使用）
                temp_file = self.temp_dir / f"{agent_name}_instructions.md"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(instructions)

                task.status = AgentStatus.COMPLETED
                task.output = f"[等待外部AI执行] 指令已保存到: {temp_file}"
                print(f"[Orchestrator] Agent就绪: {agent_name}，等待执行")

            task.end_time = datetime.now()
            return True

        except Exception as e:
            task.status = AgentStatus.FAILED
            task.error = str(e)
            task.end_time = datetime.now()
            print(f"[Orchestrator] Agent失败: {agent_name} - {e}")
            return False

    def _simulate_agent_output(self, agent_name: str, module_content: str) -> str:
        """模拟Agent输出（用于测试）"""
        # 简单的模拟：返回模板内容，替换一些占位符
        output = module_content
        output = output.replace("{{VIX}}", "15.5")
        output = output.replace("{{FNG}}", "65")
        output = output.replace("{{PCR}}", "0.85")
        output = output.replace("{{MARGIN}}", "+2.3%")
        output = output.replace("{{FUND_FLOW}}", "+150亿")
        return output

    def _generate_agent_instructions(self, agent_name: str, system_prompt: str,
                                     module_content: str, dependency_data: Dict) -> str:
        """生成Agent执行指令（包含风格要求）"""

        # 获取风格配置
        output_config = self.config.get('output', {})
        style_name = output_config.get('style', '专业投研风')
        depth = output_config.get('depth', 'L3')

        # 从风格管理器获取风格指令
        style_instructions = self.style_manager.get_agent_style_instructions(style_name, depth)

        # 验证风格和深度是否匹配
        is_valid, style_msg = self.style_manager.validate_style_depth(style_name, depth)
        if not is_valid:
            print(f"[Orchestrator] 警告: {style_msg}")

        instructions = f"""# {agent_name} 执行指令

## 系统提示词

{system_prompt}

## 写作风格要求（必须遵守）

{style_instructions}

---

## 报告配置信息

- **主题**: {self.config.get('theme', {}).get('name', 'Unknown')}
- **深度**: {depth}
- **风格**: {style_name}
- **{style_msg}**

## 依赖数据

{chr(10).join(f'### 来自 {dep}:\n{data[:500]}...' for dep, data in dependency_data.items()) if dependency_data else '无依赖数据'}

## 模块模板

请按以下模板填充内容，**同时严格遵守上述写作风格要求**：

```markdown
{module_content}
```

## 执行要求

1. **必须**严格遵循"写作风格要求"中的语气、句式、结构要求
2. **必须**根据报告深度（{depth}）控制篇幅
3. 读取模块模板 `modules/{agent_name.replace('Agent', '')}.md`
4. 根据依赖数据填充相关内容
5. 按模板格式输出完整内容
6. 所有 `[[xxx]]` 或 `[xxx]` 占位符必须填充
7. 在内容末尾添加模块来源标记

## 输出

直接输出填充后的Markdown内容，**写作风格必须与指定的"{style_name}"一致**。
"""
        return instructions

    async def run_parallel(self, agent_names: List[str], mode: str = "normal") -> Dict[str, bool]:
        """并行运行多个Agent"""
        tasks = [self.run_agent(name, mode) for name in agent_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            name: (result if not isinstance(result, Exception) else False)
            for name, result in zip(agent_names, results)
        }

    async def execute(self, mode: str = "normal", parallel: bool = True) -> bool:
        """
        执行完整的多Agent工作流

        Args:
            mode: 运行模式 (normal/simulation)
            parallel: 是否启用并行
        """
        print("\n" + "=" * 60)
        print("多Agent协调器启动")
        print("=" * 60)

        # 加载配置
        if not self.load_config():
            return False

        # 构建执行计划
        layers = self.build_execution_plan()
        if not layers:
            print("[Orchestrator] 错误: 无法构建执行计划")
            return False

        print(f"\n[Orchestrator] 执行计划: {len(layers)} 层")
        for i, layer in enumerate(layers, 1):
            print(f"  第{i}层: {', '.join(layer)}")

        # 逐层执行
        all_success = True

        # 保存初始元数据
        self.save_execution_metadata("running")

        for i, layer in enumerate(layers, 1):
            print(f"\n[Orchestrator] 执行第{i}层...")

            if parallel and len(layer) > 1:
                # 并行执行
                results = await self.run_parallel(layer, mode)
                for name, success in results.items():
                    if not success:
                        all_success = False
            else:
                # 串行执行
                for agent_name in layer:
                    success = await self.run_agent(agent_name, mode)
                    if not success:
                        all_success = False

            # 每层执行后更新元数据
            self.save_execution_metadata("running" if not all_success else "completed")

        # 生成总结
        self._print_summary()

        # 保存最终元数据
        self.save_execution_metadata("completed" if all_success else "failed")

        return all_success

    def _print_summary(self):
        """打印执行总结"""
        print("\n" + "=" * 60)
        print("执行总结")
        print("=" * 60)

        completed = sum(1 for t in self.tasks.values() if t.status == AgentStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == AgentStatus.FAILED)
        pending = sum(1 for t in self.tasks.values() if t.status == AgentStatus.PENDING)

        print(f"  完成: {completed}/{len(self.tasks)}")
        print(f"  失败: {failed}/{len(self.tasks)}")
        print(f"  等待: {pending}/{len(self.tasks)}")

        if failed > 0:
            print("\n  失败的Agent:")
            for name, task in self.tasks.items():
                if task.status == AgentStatus.FAILED:
                    print(f"    - {name}: {task.error}")

    def generate_agent_report(self) -> str:
        """生成Agent执行报告"""
        report = "# 多Agent执行报告\n\n"
        report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        report += "## Agent执行状态\n\n"
        report += "| Agent | 模块 | 状态 | 开始时间 | 结束时间 |\n"
        report += "|-------|------|------|----------|----------|\n"

        for name, task in sorted(self.tasks.items()):
            start = task.start_time.strftime('%H:%M:%S') if task.start_time else '-'
            end = task.end_time.strftime('%H:%M:%S') if task.end_time else '-'
            report += f"| {name} | {task.module} | {task.status.value} | {start} | {end} |\n"

        return report

    def save_state(self):
        """保存执行状态"""
        state_file = self.temp_dir / "orchestrator_state.json"
        state = {
            'timestamp': datetime.now().isoformat(),
            'tasks': {
                name: {
                    'agent_name': t.agent_name,
                    'module': t.module,
                    'status': t.status.value,
                    'error': t.error,
                    'start_time': t.start_time.isoformat() if t.start_time else None,
                    'end_time': t.end_time.isoformat() if t.end_time else None,
                }
                for name, t in self.tasks.items()
            }
        }
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
        print(f"[Orchestrator] 状态已保存到: {state_file}")

    @staticmethod
    def find_latest_execution(project_root: str = ".", theme: str = None) -> Optional[Path]:
        """
        查找指定主题最新的执行目录

        Args:
            project_root: 项目根目录
            theme: 主题名称（None则查找所有主题的最新执行）

        Returns:
            最新执行目录的Path，未找到返回None
        """
        temp_base = Path(project_root) / ".agent_temp"
        if not temp_base.exists():
            return None

        candidates = []
        for item in temp_base.iterdir():
            if not item.is_dir():
                continue

            # 解析目录名: theme_YYYYMMDD_HHMMSS_xxxxxx
            name_parts = item.name.split('_')
            if len(name_parts) < 3:
                continue

            # 检查是否是主题目录
            dir_theme = name_parts[0]
            if theme and dir_theme != theme.replace("/", "_").replace(" ", "_").replace("-", "_"):
                continue

            # 提取时间戳
            try:
                timestamp_str = f"{name_parts[1]}_{name_parts[2]}"
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

                # 检查是否有元数据文件（确认是有效的执行目录）
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

    @staticmethod
    def list_executions(project_root: str = ".", theme: str = None, limit: int = 10) -> List[Tuple[str, Path]]:
        """
        列出执行历史

        Args:
            project_root: 项目根目录
            theme: 主题筛选（None则列出所有主题）
            limit: 返回数量限制

        Returns:
            [(execution_id, path), ...] 按时间倒序
        """
        temp_base = Path(project_root) / ".agent_temp"
        if not temp_base.exists():
            return []

        executions = []
        for item in temp_base.iterdir():
            if not item.is_dir():
                continue

            name_parts = item.name.split('_')
            if len(name_parts) < 3:
                continue

            dir_theme = name_parts[0]
            if theme and dir_theme != theme.replace("/", "_").replace(" ", "_").replace("-", "_"):
                continue

            try:
                timestamp_str = f"{name_parts[1]}_{name_parts[2]}"
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                executions.append((timestamp, item.name, item))
            except (ValueError, IndexError):
                continue

        # 按时间倒序
        executions.sort(key=lambda x: x[0], reverse=True)

        return [(name, path) for _, name, path in executions[:limit]]


def main():
    import argparse

    parser = argparse.ArgumentParser(description='多Agent协调器')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件路径')
    parser.add_argument('--theme', type=str, help='指定主题目录（如：物理AI），自动使用 themes/主题/config.yaml')
    parser.add_argument('--parallel', action='store_true', help='启用并行模式')
    parser.add_argument('--simulate', action='store_true', help='模拟模式（不调用AI）')
    parser.add_argument('--agent', type=str, help='单独运行指定Agent')
    parser.add_argument('--check', action='store_true', help='检查Agent状态')
    parser.add_argument('--project-root', type=str, default='.', help='项目根目录')
    parser.add_argument('--merge', action='store_true', help='执行后自动合并报告')
    parser.add_argument('--merge-only', action='store_true', help='仅执行报告合并')

    args = parser.parse_args()

    # 如果指定了 theme，自动构建配置文件路径
    config_file = args.config
    if args.theme:
        config_file = f"themes/{args.theme}/config.yaml"

    orchestrator = MultiAgentOrchestrator(args.project_root, config_file, theme=args.theme)

    if args.merge_only:
        # 仅执行报告合并
        print("\n[Orchestrator] 执行报告合并...")
        merger = ReportMerger(args.project_root)

        # 加载配置
        config = {}
        if orchestrator.load_config():
            config = orchestrator.config

        report_content = merger.merge_reports(config)
        if report_content:
            output_path = merger.save_report(report_content)
            print(f"\n[Orchestrator] 报告合并完成: {output_path}")
        else:
            print("\n[Orchestrator] 错误: 无法生成报告")
        return

    if args.check:
        # 检查状态
        if orchestrator.load_config():
            layers = orchestrator.build_execution_plan()
            print(f"\n执行计划: {len(layers)} 层")
            for i, layer in enumerate(layers, 1):
                print(f"  第{i}层: {', '.join(layer)}")

    elif args.agent:
        # 单独运行某个Agent
        asyncio.run(orchestrator.run_agent(args.agent, "normal"))

    else:
        # 完整执行
        mode = "simulation" if args.simulate else "normal"
        success = asyncio.run(orchestrator.execute(mode=mode, parallel=args.parallel))

        if success:
            print("\n[Orchestrator] 执行成功")

            # 自动合并报告
            if args.merge:
                print("\n[Orchestrator] 开始合并报告...")
                merger = ReportMerger(args.project_root)
                report_content = merger.merge_reports(orchestrator.config)
                if report_content:
                    output_path = merger.save_report(report_content)
                    print(f"\n[Orchestrator] 报告已生成: {output_path}")
        else:
            print("\n[Orchestrator] 执行失败")
            sys.exit(1)


if __name__ == '__main__':
    main()
