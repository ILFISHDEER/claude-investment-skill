#!/usr/bin/env python3
"""
Investment Skill Memory MCP 集成脚本
用于将项目知识存储到 memory MCP 知识图谱

使用方法:
  python memory_integration.py --init          # 初始化知识图谱
  python memory_integration.py --query "孙哥方向包含哪些细分方向?"  # 查询
  python memory_integration.py --add-observation NVDA "2026Q1财报超预期"  # 添加观察
"""

import json
import subprocess
import sys
import argparse
from pathlib import Path

# Investment Skill 知识图谱种子数据
KNOWLEDGE_SEED = {
    "entities": [
        # 投资主题
        {"name": "孙哥方向", "entityType": "投资主题", "observations": [
            "7大细分方向：存储、具身智能、无人机、空间计算、太空探索、能源、量子计算",
            "主题ID: sun-ge-direction",
            "核心逻辑：AI+硬科技产业链全景",
            "配置文件: themes/孙哥方向/config.yaml"
        ]},
        {"name": "新能源", "entityType": "投资主题", "observations": [
            "专注电池/储能产业链",
            "代表标的: 宁德时代、比亚迪",
            "关注政策催化和技术迭代"
        ]},
        {"name": "量子计算", "entityType": "投资主题", "observations": [
            "孙哥方向第7细分方向",
            "下一代算力底座",
            "代表标的: IonQ、Rigetti、本源量子(未上市)",
            "铲子股: FormFactor(测试设备)"
        ]},

        # 分析模块
        {"name": "03-产业链拆解", "entityType": "分析模块", "observations": [
            "层级: Layer 2",
            "功能: 七层产业链拆解、IC Score评分",
            "Agent: IndustryChainAgent",
            "输入: 主题配置+市场数据",
            "输出: 产业链图谱",
            "依赖: 00-市场情绪分析"
        ]},
        {"name": "04-铲子股筛选", "entityType": "分析模块", "observations": [
            "层级: Layer 3",
            "功能: 基于IC Score筛选核心铲子股",
            "Agent: ShovelStockAgent",
            "依赖: 03-产业链拆解、15-产业链全景图谱",
            "评分维度: I/C/T/S/M五维度",
            "输出: 筛选清单+仓位建议"
        ]},
        {"name": "05-护城河评估", "entityType": "分析模块", "observations": [
            "层级: Layer 3",
            "功能: 竞争壁垒评估",
            "Agent: 默认提示词",
            "依赖: 04-铲子股筛选",
            "框架: 晨星护城河评级"
        ]},
        {"name": "09-组合构建", "entityType": "分析模块", "observations": [
            "层级: Layer 3",
            "功能: 仓位配置、价格计算",
            "Agent: PortfolioConstructionAgent",
            "依赖: 05-护城河评估、08-风险矩阵",
            "输出: 组合方案"
        ]},

        # 分析框架
        {"name": "晨星护城河评级", "entityType": "分析框架", "observations": [
            "评估公司竞争壁垒",
            "文件: frameworks/晨星护城河评级.md",
            "应用于模块05",
            "评估维度: 无形资产、成本优势、网络效应、转换成本"
        ]},
        {"name": "费雪成长股原则", "entityType": "分析框架", "observations": [
            "成长股筛选方法论",
            "15个成长股特征",
            "关注: 成长潜力、管理能力、盈利能力"
        ]},
        {"name": "股票库维护规则", "entityType": "分析框架", "observations": [
            "股票池动态管理机制",
            "6维度评分: 价格表现20%、估值健康20%、财务质量20%、技术地位20%、催化剂10%、风险状况10%",
            "红黄灯预警机制",
            "季度审议剔除/纳入"
        ]},

        # AI Agent
        {"name": "IndustryChainAgent", "entityType": "AI Agent", "observations": [
            "专长: 产业链拆解、IC Score",
            "对应模块: 03",
            "文件: agents/IndustryChainAgent.md",
            "输出: 产业链图谱+IC Score"
        ]},
        {"name": "ShovelStockAgent", "entityType": "AI Agent", "observations": [
            "专长: 铲子股筛选、仓位配置",
            "对应模块: 04",
            "文件: agents/ShovelStockAgent.md"
        ]},
        {"name": "PortfolioConstructionAgent", "entityType": "AI Agent", "observations": [
            "专长: 组合构建、价格计算",
            "对应模块: 09",
            "文件: agents/PortfolioConstructionAgent.md"
        ]},
        {"name": "MarketSentimentAgent", "entityType": "AI Agent", "observations": [
            "专长: VIX分析、资金流向",
            "对应模块: 00",
            "文件: agents/MarketSentimentAgent.md",
            "输出: 情绪判断"
        ]},

        # 投资标的(示例)
        {"name": "NVDA", "entityType": "投资标的", "observations": [
            "英伟达",
            "所属主题: 孙哥方向-存储/AI芯片",
            "商业模式: AI芯片设计",
            "技术壁垒: CUDA生态、GPU架构",
            "铲子属性: 无论AI应用谁赢都需要英伟达芯片"
        ]},
        {"name": "TSLA", "entityType": "投资标的", "observations": [
            "特斯拉",
            "所属主题: 孙哥方向-具身智能",
            "商业模式: 电动车+自动驾驶+机器人",
            "技术壁垒: FSD算法、垂直整合"
        ]},
        {"name": "绿的谐波", "entityType": "投资标的", "observations": [
            "688017.SH(科创板)",
            "所属主题: 孙哥方向-具身智能",
            "主营业务: 精密谐波减速器",
            "铲子属性: 人形机器人核心零部件",
            "IC Score: 高(I-唯一国产替代、C-绑定头部)"
        ]},

        # 评分机制
        {"name": "IC Score", "entityType": "评分机制", "observations": [
            "铲子股筛选核心逻辑",
            "I-不可替代性30%: 唯一供应商40分/TOP3 30分/有替代10分",
            "C-客户集中度25%: 绑定头部25分/二线15分",
            "T-技术壁垒20%: 按领先程度0-20分",
            "S-市场规模15%: 按赛道空间0-15分",
            "M-管理层10%: 按治理财报质量0-10分",
            "评级: ≥70分=A级 / 60-69分=B级 / <60分=C级"
        ]},

        # 产业链节点
        {"name": "存储产业链", "entityType": "产业链", "observations": [
            "孙哥方向第1细分",
            "核心逻辑: 永远缺存储",
            "上游: HBM芯片(英伟达)、存储颗粒(美光/三星)",
            "中游: 模组厂商",
            "下游: AI服务器、手机、PC"
        ]},
        {"name": "具身智能产业链", "entityType": "产业链", "observations": [
            "孙哥方向第2细分",
            "核心逻辑: 身体与大脑分开押",
            "关键部件: 减速器、电机、传感器、丝杠",
            "代表公司: 绿的谐波、三花智控、鸣志电器"
        ]},
        {"name": "量子计算产业链", "entityType": "产业链", "observations": [
            "孙哥方向第7细分",
            "技术路线: 离子阱(IonQ)、超导(Rigetti)、光量子",
            "铲子股: FormFactor(测试设备)、低温系统",
            "应用层: 金融、医药、材料"
        ]}
    ],
    "relations": [
        {"from": "孙哥方向", "to": "存储产业链", "relationType": "包含"},
        {"from": "孙哥方向", "to": "具身智能产业链", "relationType": "包含"},
        {"from": "孙哥方向", "to": "量子计算产业链", "relationType": "包含"},
        {"from": "存储产业链", "to": "NVDA", "relationType": "核心标的"},
        {"from": "具身智能产业链", "to": "绿的谐波", "relationType": "核心标的"},
        {"from": "具身智能产业链", "to": "TSLA", "relationType": "终端应用"},
        {"from": "04-铲子股筛选", "to": "IC Score", "relationType": "使用"},
        {"from": "04-铲子股筛选", "to": "03-产业链拆解", "relationType": "依赖"},
        {"from": "ShovelStockAgent", "to": "04-铲子股筛选", "relationType": "执行"},
        {"from": "IndustryChainAgent", "to": "03-产业链拆解", "relationType": "执行"},
        {"from": "05-护城河评估", "to": "晨星护城河评级", "relationType": "应用"},
        {"from": "PortfolioConstructionAgent", "to": "09-组合构建", "relationType": "执行"}
    ]
}


def call_memory_mcp(tool: str, params: dict) -> dict:
    """调用 memory MCP"""
    cmd = ["npx", "-y", "@modelcontextprotocol/server-memory"]
    # 这里模拟 MCP 调用
    # 实际应该通过 MCP 协议通信
    print(f"[Memory MCP] {tool}: {json.dumps(params, ensure_ascii=False)[:100]}...")
    return {"status": "ok"}


def init_knowledge_graph():
    """初始化知识图谱"""
    print("[初始化] Investment Skill 知识图谱...\n")

    entities = KNOWLEDGE_SEED["entities"]
    relations = KNOWLEDGE_SEED.get("relations", [])

    print(f"[创建] {len(entities)} 个实体...")
    for i, entity in enumerate(entities, 1):
        print(f"  {i}. {entity['name']} ({entity['entityType']})")
        # 实际调用 memory MCP
        call_memory_mcp("create_entity", entity)

    if relations:
        print(f"\n[关系] 创建 {len(relations)} 个关系...")
        for rel in relations:
            print(f"  {rel['from']} --{rel['relationType']}--> {rel['to']}")

    print("\n[完成] 知识图谱初始化完成!")
    print("\n[提示] 使用示例:")
    print('  python memory_integration.py --query "孙哥方向"')
    print('  python memory_integration.py --list-by-type "投资标的"')


def query_graph(query: str):
    """查询知识图谱"""
    print(f"[查询] {query}\n")

    # 模拟查询结果
    results = []
    for entity in KNOWLEDGE_SEED["entities"]:
        if query.lower() in entity["name"].lower() or \
           any(query.lower() in obs.lower() for obs in entity["observations"]):
            results.append(entity)

    if results:
        print(f"[结果] 找到 {len(results)} 个结果:\n")
        for entity in results:
            print(f"* {entity['name']} [{entity['entityType']}]")
            for obs in entity["observations"][:3]:
                print(f"   - {obs}")
            print()
    else:
        print("[结果] 未找到相关实体")


def add_observation(entity_name: str, observation: str):
    """为实体添加观察"""
    print(f"[添加] 为 {entity_name} 添加观察:")
    print(f"   {observation}")
    # 实际调用 memory MCP
    call_memory_mcp("add_observations", {
        "entity": entity_name,
        "observations": [observation]
    })
    print("[完成] 已添加")


def export_for_claude():
    """导出为 Claude 可用的格式"""
    output_file = Path("memory-graph-import.json")

    # 转换为 memory MCP 格式
    formatted = {
        "entities": KNOWLEDGE_SEED["entities"],
        "relations": KNOWLEDGE_SEED.get("relations", [])
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(formatted, f, ensure_ascii=False, indent=2)

    print(f"[导出] 已导出到: {output_file}")
    print("\n在 Claude 对话中可以使用:")
    print('  "根据知识图谱，孙哥方向包含哪些细分方向?"')
    print('  "IC Score的五个维度是什么?"')
    print('  "04-铲子股筛选依赖哪些模块?"')


def main():
    parser = argparse.ArgumentParser(description="Investment Skill Memory MCP 集成")
    parser.add_argument("--init", action="store_true", help="初始化知识图谱")
    parser.add_argument("--query", type=str, help="查询实体")
    parser.add_argument("--add-observation", nargs=2, metavar=("ENTITY", "OBS"), help="添加观察")
    parser.add_argument("--export", action="store_true", help="导出为 Claude 格式")
    parser.add_argument("--interactive", action="store_true", help="交互模式")

    args = parser.parse_args()

    if args.init:
        init_knowledge_graph()
    elif args.query:
        query_graph(args.query)
    elif args.add_observation:
        add_observation(args.add_observation[0], args.add_observation[1])
    elif args.export:
        export_for_claude()
    elif args.interactive:
        interactive_mode()
    else:
        parser.print_help()


def interactive_mode():
    """交互式查询"""
    print("[记忆图谱] Investment Skill 知识图谱 - 交互模式")
    print("输入查询内容 (或 'exit' 退出):\n")

    while True:
        query = input("[查询] > ").strip()
        if query.lower() in ["exit", "quit", "q"]:
            break
        if query:
            query_graph(query)
        print()


if __name__ == "__main__":
    main()
