# Investment Skill + Memory MCP 使用指南

## 📋 概述

本文档说明如何在 Investment Skill 项目中使用 **memory MCP** 构建投资知识图谱，实现：

- ✅ 跨会话记忆投资框架和模块关系
- ✅ 快速查询产业链、标的、Agent 信息
- ✅ 自动发现投资标的间的关联
- ✅ 累积投资观察和决策经验

---

## 🗂️ 知识图谱结构

### 实体类型

| 类型 | 示例 | 用途 |
|------|------|------|
| **投资主题** | 孙哥方向、新能源 | 顶层分类 |
| **产业链** | 存储产业链、具身智能产业链 | 产业链全景 |
| **投资标的** | NVDA、TSLA、绿的谐波 | 具体股票 |
| **分析模块** | 03-产业链拆解、04-铲子股筛选 | 报告生成模块 |
| **AI Agent** | IndustryChainAgent、ShovelStockAgent | 执行Agent |
| **分析框架** | 晨星护城河、IC Score | 评估方法论 |
| **评分机制** | 股票库维护规则 | 评分标准 |

### 关系类型

```
孙哥方向 --包含--> 存储产业链
存储产业链 --核心标的--> NVDA
04-铲子股筛选 --使用--> IC Score
04-铲子股筛选 --依赖--> 03-产业链拆解
ShovelStockAgent --执行--> 04-铲子股筛选
```

---

## 🚀 快速开始

### 方式1：命令行脚本

```bash
# 1. 初始化知识图谱
python memory_integration.py --init

# 2. 查询实体
python memory_integration.py --query "孙哥方向"
python memory_integration.py --query "IC Score"

# 3. 添加新观察
python memory_integration.py --add-observation NVDA "2026Q1财报超预期"

# 4. 交互模式
python memory_integration.py --interactive

# 5. 导出为 Claude 格式
python memory_integration.py --export
```

### 方式2：直接在 Claude 对话中使用

由于 memory MCP 已配置，直接在对话中查询：

```
你：知识图谱中，孙哥方向包含哪些细分方向？

Claude：使用 memory.search_nodes
结果：
- 存储产业链
- 具身智能产业链
- 量子计算产业链
...

你：IC Score 的五个维度是什么？

Claude：使用 memory.search_nodes
结果：
- I-不可替代性(30%)
- C-客户集中度(25%)
- T-技术壁垒(20%)
- S-市场规模(15%)
- M-管理层(10%)
```

---

## 💡 实际应用场景

### 场景1：生成报告前快速回顾

```
用户：生成孙哥方向L3报告

Claude：使用 memory.read_graph
→ 获取孙哥方向的7个细分方向
→ 获取已配置的股票清单
→ 获取各方向核心标的

Claude：确认配置
→ 模块启用：03, 04, 05...
→ Agent：IndustryChainAgent, ShovelStockAgent...
→ 框架：IC Score, 晨星护城河

Claude：开始生成...
```

### 场景2：查找相似投资逻辑

```
用户：之前分析过的铲子股有哪些共同特征？

Claude：使用 memory.search_nodes
→ 查找 entityType="投资标的"
→ 筛选包含"铲子属性"的观察

结果：
- NVDA：无论AI应用谁赢都需要英伟达芯片
- 绿的谐波：人形机器人核心零部件
- FormFactor：量子测试设备铲子股

Claude：总结共同特征...
```

### 场景3：追踪标的关联

```
用户：特斯拉和绿的谐波有什么关系？

Claude：使用 memory.search_nodes
→ TSLA：所属主题=孙哥方向-具身智能
→ 绿的谐波：所属主题=孙哥方向-具身智能

Claude：同属具身智能产业链
→ TSLA：终端应用（机器人）
→ 绿的谐波：核心零部件（减速器）

结论：产业链上下游关系
```

### 场景4：记录投资经验

```
用户：记住这次量子计算分析的关键发现

Claude：使用 memory.add_observations
→ 实体：量子计算产业链
→ 观察：
  - "2026年离子阱技术突破，IonQ订单放量"
  - "FormFactor测试设备是铲子股"
  - "超导路线仍面临纠错难题"

Claude：已记录，下次分析时自动调用
```

---

## 📊 知识图谱数据文件

### 种子数据

- **文件**: `memory-graph-import.json`
- **内容**: 预定义的实体和关系
- **用途**: 初始化知识图谱

### 数据结构

```json
{
  "entities": [
    {
      "name": "孙哥方向",
      "entityType": "投资主题",
      "observations": [
        "7大细分方向：存储、具身智能...",
        "主题ID: sun-ge-direction"
      ]
    }
  ],
  "relations": [
    {
      "from": "孙哥方向",
      "to": "存储产业链",
      "relationType": "包含"
    }
  ]
}
```

---

## 🔧 维护知识图谱

### 定期更新

```bash
# 每季度更新
python memory_integration.py --add-observation 孙哥方向 "2026Q2新增标的: xxx"

# 新主题上线
python memory_integration.py --init  # 重新加载种子数据
```

### 备份

知识图谱数据存储在 memory MCP 的存储中，建议定期导出：

```bash
python memory_integration.py --export
```

---

## 🎯 与项目其他部分集成

### 1. 与 Agent 系统集成

```python
# multi_agent_orchestrator.py
from memory_integration import query_graph

# 执行前查询知识图谱
context = query_graph("孙哥方向")
agent.set_context(context)
```

### 2. 与报告生成集成

```python
# generate_report_v2.py
# 自动获取主题相关信息
entities = search_nodes(theme_name)
for entity in entities:
    report.add_reference(entity)
```

### 3. 与维护脚本集成

```python
# maintenance.py
# 记录评分变化
add_observation("NVDA", "评分从85降至55，技术路线被HBM替代")
```

---

## 📈 预期收益

| 场景 | 之前 | 使用 Memory MCP 后 |
|------|------|-------------------|
| **查找标的** | 翻找 tickers.yaml | 自然语言查询 |
| **关联分析** | 人工对比 | 自动发现关联 |
| **经验复用** | 翻看历史报告 | 知识图谱联想 |
| **Agent上下文** | 每次重新加载 | 跨会话记忆 |

---

## 📝 示例对话

### 示例1：快速查询

```
你：04-铲子股筛选依赖哪些模块？

Claude：查询知识图谱...

结果：
📌 04-铲子股筛选 [分析模块]
依赖关系：
  ├─ 03-产业链拆解
  └─ 15-产业链全景图谱

执行Agent: ShovelStockAgent
使用框架: IC Score 评分机制
```

### 示例2：发现关联

```
你：找出孙哥方向所有的铲子股

Claude：查询知识图谱...

结果：
🔍 孙哥方向 -包含-> 3个产业链

存储产业链：
  └─ 铲子股: NVDA(无论谁赢都需要英伟达)

具身智能产业链：
  └─ 铲子股: 绿的谐波(减速器唯一国产替代)

量子计算产业链：
  └─ 铲子股: FormFactor(测试设备)

总结：共3只核心铲子股
```

### 示例3：记录发现

```
你：记住这次分析发现FormFactor是铲子股

Claude：使用 memory.add_observations

实体: FormFactor
类型: 投资标的
新增观察:
  - "量子计算测试设备铲子股"
  - "绑定IonQ和Rigetti订单放量"
  - "IC Score评分78分，A级"

✅ 已记录，下次分析量子计算时会自动提及
```

---

## 🚀 下一步

1. **运行初始化**：`python memory_integration.py --init`
2. **测试查询**：`python memory_integration.py --query "孙哥方向"`
3. **在 Claude 中使用**：直接对话查询知识图谱
4. **持续积累**：每次分析后添加新观察

需要我帮你运行初始化，或者演示某个具体查询吗？
