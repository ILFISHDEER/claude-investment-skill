#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent通信管理器 (Agent Communication Manager)

功能：
1. 管理Agent间的消息传递
2. 数据共享和缓存
3. 依赖数据自动分发
4. 通信状态跟踪

解决的问题：
- Agent间数据传递标准化
- 依赖数据自动注入
- 输出缓存避免重复生成
- 通信状态可视化

用法：
    from agent_communication import AgentCommunicationManager

    comm = AgentCommunicationManager()

    # Agent发送消息
    comm.send_message(from_agent="市场情绪Agent", to_agent="产业链Agent",
                     message_type="DATA", content={...})

    # Agent接收数据
    data = comm.get_dependency_data("产业链Agent", "市场情绪Agent")
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum


class MessageType(Enum):
    """消息类型"""
    DATA = "data"           # 数据传递
    STATUS = "status"       # 状态更新
    ERROR = "error"         # 错误报告
    REQUEST = "request"     # 数据请求
    RESPONSE = "response"     # 数据响应
    CHECKPOINT = "checkpoint"  # 检查点


@dataclass
class AgentMessage:
    """Agent消息"""
    message_id: str
    from_agent: str
    to_agent: str
    message_type: MessageType
    content: Dict
    timestamp: str
    correlation_id: str  # 用于追踪关联消息


class AgentCommunicationManager:
    """Agent通信管理器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.comm_dir = self.project_root / ".agent_comm"
        self.cache_dir = self.comm_dir / "cache"
        self.log_file = self.comm_dir / "communication.log"

        # 创建目录
        self.comm_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)

        # 内存缓存
        self.message_log: List[AgentMessage] = []
        self.agent_outputs: Dict[str, Dict] = {}

    def _generate_message_id(self, from_agent: str, to_agent: str) -> str:
        """生成消息ID"""
        timestamp = datetime.now().isoformat()
        content = f"{from_agent}:{to_agent}:{timestamp}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def send_message(self, from_agent: str, to_agent: str,
                    message_type: MessageType, content: Dict,
                    correlation_id: str = None) -> AgentMessage:
        """
        发送消息

        Args:
            from_agent: 发送方Agent名称
            to_agent: 接收方Agent名称
            message_type: 消息类型
            content: 消息内容
            correlation_id: 关联ID（用于追踪）

        Returns:
            AgentMessage对象
        """
        message = AgentMessage(
            message_id=self._generate_message_id(from_agent, to_agent),
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            timestamp=datetime.now().isoformat(),
            correlation_id=correlation_id or message_id
        )

        # 保存到日志
        self._log_message(message)

        # 如果是数据消息，缓存输出
        if message_type == MessageType.DATA:
            self.agent_outputs[from_agent] = content

        return message

    def _log_message(self, message: AgentMessage):
        """记录消息到日志"""
        self.message_log.append(message)

        # 追加到文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            log_entry = json.dumps(asdict(message), ensure_ascii=False)
            f.write(log_entry + '\n')

    def get_dependency_data(self, agent_name: str, dependency: str) -> Optional[Dict]:
        """
        获取Agent的依赖数据

        Args:
            agent_name: 当前Agent名称
            dependency: 依赖的Agent名称

        Returns:
            依赖数据，如果不存在返回None
        """
        # 首先从内存缓存获取
        if dependency in self.agent_outputs:
            return self.agent_outputs[dependency]

        # 尝试从文件缓存获取
        cache_file = self.cache_dir / f"{dependency}_output.json"
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.agent_outputs[dependency] = data
                return data

        return None

    def cache_agent_output(self, agent_name: str, output: Dict):
        """
        缓存Agent输出

        Args:
            agent_name: Agent名称
            output: 输出数据
        """
        # 内存缓存
        self.agent_outputs[agent_name] = output

        # 文件缓存
        cache_file = self.cache_dir / f"{agent_name}_output.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    def get_all_dependencies(self, agent_name: str,
                            dependency_rules: Dict[str, List[str]]) -> Dict[str, Dict]:
        """
        获取Agent的所有依赖数据

        Args:
            agent_name: Agent名称
            dependency_rules: 依赖规则字典 {agent: [dependencies]}

        Returns:
            所有依赖数据的字典
        """
        dependencies = dependency_rules.get(agent_name, [])
        result = {}

        for dep in dependencies:
            data = self.get_dependency_data(agent_name, dep)
            if data:
                result[dep] = data
            else:
                # 发送请求消息
                self.send_message(
                    from_agent=agent_name,
                    to_agent=dep,
                    message_type=MessageType.REQUEST,
                    content={"request": "output_data"}
                )

        return result

    def get_communication_summary(self) -> Dict:
        """获取通信摘要"""
        total_messages = len(self.message_log)

        # 按类型统计
        type_count = {}
        for msg in self.message_log:
            msg_type = msg.message_type.value
            type_count[msg_type] = type_count.get(msg_type, 0) + 1

        # 按Agent统计
        agent_messages = {}
        for msg in self.message_log:
            if msg.from_agent not in agent_messages:
                agent_messages[msg.from_agent] = {'sent': 0, 'received': 0}
            if msg.to_agent not in agent_messages:
                agent_messages[msg.to_agent] = {'sent': 0, 'received': 0}

            agent_messages[msg.from_agent]['sent'] += 1
            agent_messages[msg.to_agent]['received'] += 1

        return {
            'total_messages': total_messages,
            'by_type': type_count,
            'by_agent': agent_messages,
            'cached_outputs': list(self.agent_outputs.keys())
        }

    def print_communication_flow(self):
        """打印通信流程图"""
        print("\n" + "=" * 60)
        print("Agent通信流程")
        print("=" * 60)

        for msg in self.message_log:
            arrow = "→" if msg.message_type == MessageType.DATA else "⇄"
            print(f"{msg.from_agent} {arrow} {msg.to_agent} [{msg.message_type.value}] {msg.timestamp}")

    def export_communication_graph(self) -> str:
        """导出通信图为Mermaid格式"""
        lines = ["```mermaid", "graph LR"]

        # 收集所有通信关系
        relationships = set()
        for msg in self.message_log:
            if msg.message_type == MessageType.DATA:
                relationships.add((msg.from_agent, msg.to_agent))

        # 生成Mermaid语法
        for from_agent, to_agent in relationships:
            lines.append(f"    {from_agent.replace('-', '_')} --> {to_agent.replace('-', '_')}")

        lines.append("```")
        return '\n'.join(lines)

    def clear_cache(self):
        """清除缓存"""
        self.agent_outputs.clear()
        self.message_log.clear()

        # 清除文件缓存
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()

        # 清除日志
        if self.log_file.exists():
            self.log_file.unlink()


# 辅助函数：生成Agent通信图
def generate_agent_flow_chart(dependency_rules: Dict[str, List[str]]) -> str:
    """
    生成Agent依赖关系图（Mermaid格式）

    Args:
        dependency_rules: 依赖规则字典

    Returns:
        Mermaid图表代码
    """
    lines = ["```mermaid", "graph TD"]

    # 添加节点样式
    lines.append("    classDef default fill:#f9f,stroke:#333,stroke-width:2px")
    lines.append("    classDef entry fill:#9f9,stroke:#333,stroke-width:2px")
    lines.append("    classDef exit fill:#99f,stroke:#333,stroke-width:2px")

    # 收集所有Agent
    all_agents = set()
    for agent, deps in dependency_rules.items():
        all_agents.add(agent)
        all_agents.update(deps)

    # 标记入口和出口
    entry_agents = [a for a in all_agents if a not in
                    [d for deps in dependency_rules.values() for d in deps]]
    exit_agents = [a for a in all_agents if a not in dependency_rules]

    # 生成边
    for agent, deps in dependency_rules.items():
        for dep in deps:
            lines.append(f"    {dep} --> {agent}")

    # 添加样式
    for agent in entry_agents:
        lines.append(f"    class {agent} entry")
    for agent in exit_agents:
        lines.append(f"    class {agent} exit")

    lines.append("```")
    return '\n'.join(lines)


# 测试代码
if __name__ == "__main__":
    # 示例用法
    comm = AgentCommunicationManager()

    # 模拟Agent通信
    comm.send_message(
        from_agent="市场情绪Agent",
        to_agent="产业链Agent",
        message_type=MessageType.DATA,
        content={"sentiment": "贪婪", "vix": 15.5}
    )

    comm.cache_agent_output("市场情绪Agent", {"sentiment": "贪婪"})

    data = comm.get_dependency_data("产业链Agent", "市场情绪Agent")
    print(f"获取依赖数据: {data}")

    summary = comm.get_communication_summary()
    print(f"\n通信摘要: {summary}")

    mermaid_chart = comm.export_communication_graph()
    print(f"\nMermaid图表:\n{mermaid_chart}")
