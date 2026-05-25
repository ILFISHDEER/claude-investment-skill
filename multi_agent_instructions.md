# 多Agent报告生成指令

> **版本**: v1.1  
> **更新**: 2026-05-25  
> **状态**: 多Agent模式 + 风格动态控制

---

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                      主控Agent (Orchestrator)                  │
│                      - 解析config.yaml                          │
│                      - 调度子Agent                              │
│                      - 合并输出                                │
│                      - **注入风格要求** ← v2.9新增             │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Layer 1      │    │ Layer 2      │    │ Layer 3      │
│ 入口Agent     │    │ 分析Agent     │    │ 决策Agent     │
├──────────────┤    ├──────────────┤    ├──────────────┤
│市场情绪Agent  │    │产业链Agent    │    │铲子股Agent    │
│环境扫描Agent  │    │**供应链Agent**│    │组合构建Agent  │
│投资哲学Agent  │    │护城河Agent    │    │实操指南Agent  │
│              │    │风险矩阵Agent   │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  一致性检查Agent (ConsistencyCheckAgent)        │
│                  - 术语统一                                     │
│                  - 数据一致性                                    │
│                  - **风格统一** ← v2.9新增                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 风格动态控制（v2.9）

### 配置风格

在`config.yaml`中配置`output.style`：

```yaml
output:
  depth: "L2"
  style: "社交媒体风"  # 11种风格可选
  market_focus: "中美双线"
```

### 支持的风格

| 风格 | 最佳深度 | 特点 |
|------|----------|------|
| **一句话风** | L0 | 极简结论 |
| **社交媒体风** | L0-L1 | emoji丰富、易转发 |
| **新闻快讯风** | L0-L2 | 客观、5W1H |
| **内部备忘录风** | L1-L2 | 结论先行、带TODO |
| **专业投行风** | L1-L4 | 专业严谨 |
| **散户科普风** | L1-L3 | 口语化、易懂 |
| **FAQ问答风** | L0-L4 | 由浅入深 |
| **故事叙事风** | L1-L4 | 情节驱动 |
| **对比分析风** | L1-L4 | 并排对比表 |
| **学术论文风** | L3-L4 | 完整方法论 |
| **投资手册风** | L4 | 百科全书式 |

### 风格注入流程

```
config.yaml (style: "社交媒体风")
    ↓
StyleManager 加载 styles/社交媒体风.md
    ↓
提取风格要求（语气/句式/结构/禁用/必用）
    ↓
注入到每个Agent的执行指令
    ↓
Agent按风格要求生成内容
```

### Agent指令中的风格要求

每个Agent收到指令时，会自动包含：

```markdown
## 写作风格要求（必须遵守）

**风格名称**: 社交媒体风
**风格定位**: 社交传播、emoji丰富、易转发

### 语气要求
- 轻松活泼，带表情符号
- 口语化表达
- 制造话题性

### 句式要求
- 平均句长：15-20字
- 多用短句和断句
- 每句可加emoji

### 深度特定要求
当前报告深度: **L2**
- 使用emoji表情
- 300-500字
- 短句为主
- 易转发

### 禁用事项（必须遵守）
- 长段落无emoji
- 专业术语无解释
- 无话题标签
- 过于严肃的表达

### 必用结构（必须包含）
- emoji开头引入
- 3-5个话题标签
- 互动引导（投票/提问）
```

### 风格与深度验证

协调器会自动验证风格与深度是否匹配：

```
风格适配检查
  风格: 学术论文风
  深度: L2
  状态: ⚠️ 风格'学术论文风'用于L2深度效果可能不佳
  
推荐:
  - 专业投行风: ✅ 适合L2 (专业分析)
  - FAQ问答风: ✅ 适合L2 (由浅入深)
```

---

## 执行流程

### 第1层：入口Agent（并行）

**Agent**: 市场情绪Agent、环境扫描Agent、投资哲学Agent

```
输入: config.yaml, 数据文件
输出: 情绪分析、环境扫描、投资逻辑
→ 结果传递给第2层Agent
```

### 第2层：分析Agent（部分并行）

**Agent**: 产业链Agent、**供应链Agent**、护城河Agent、风险矩阵Agent

**供应链Agent**（v2.7新增）：
```
输入: 第1层输出 + tickers数据
输出: 隐形冠军清单、跨行业铲子股、供应链风险分析
→ 识别功能层级遗漏的隐形冠军（如福晶科技）
```

**产业链Agent**:
```
输入: 第1层输出 + 数据文件
依赖: 产业链Agent → 铲子股Agent
输出: 产业链图谱、IC Score、风险评估
→ 结果传递给第3层Agent
```

### 第3层：决策Agent（串行）

**Agent**: 铲子股Agent、组合构建Agent、实操指南Agent

```
输入: 第2层输出
依赖: 必须等待产业链Agent完成
输出: 筛选清单、组合配置、操作计划
```

### 第4层：一致性检查（串行）

**Agent**: 一致性检查Agent

```
输入: 所有章节输出
输出: 一致性报告、修复建议
→ 主控Agent统一修正
```

---

## Agent职责分工

| Agent | 专长 | 输入 | 输出 | 依赖 |
|-------|------|------|------|------|
| **市场情绪Agent** | 情绪指标、资金流向 | 市场数据 | 情绪判断 | 无 |
| **环境扫描Agent** | 宏观环境、行业景气 | 宏观数据 | 环境分析 | 无 |
| **投资哲学Agent** | 投资原则、框架 | 主题配置 | 投资逻辑 | 无 |
| **产业链Agent** | 产业链拆解、IC Score | tickers数据 | 产业链图谱 | 市场情绪Agent |
| **护城河Agent** | 竞争壁垒、护城河 | 公司数据 | 护城河评级 | 无 |
| **风险矩阵Agent** | 风险评估、对冲 | 组合数据 | 风险报告 | 无 |
| **铲子股Agent** | 筛选逻辑、仓位 | 产业链输出 | 筛选清单 | 产业链Agent |
| **组合构建Agent** | 仓位配置、价格 | 筛选结果 | 组合方案 | 铲子股Agent |
| **实操指南Agent** | 交易计划、SOP | 组合方案 | 操作指南 | 组合构建Agent |
| **一致性检查Agent** | 术语统一、校验 | 所有章节 | 一致性报告 | 所有Agent |

---

## 通信协议

### Agent消息格式

```json
{
  "message_id": "uuid",
  "from_agent": "市场情绪Agent",
  "to_agent": "产业链Agent",
  "message_type": "DATA",
  "content": {
    "sentiment": "贪婪",
    "vix": 15.5,
    "sector_sentiment": {...}
  },
  "timestamp": "2026-05-24T10:30:00",
  "correlation_id": "uuid"
}
```

### 消息类型

- `DATA`: 数据传递
- `STATUS`: 状态更新
- `REQUEST`: 数据请求
- `RESPONSE`: 数据响应
- `ERROR`: 错误报告

---

## 使用方式

### 方式1：使用协调器（推荐）

```bash
# 完整多Agent工作流（使用config.yaml中配置的风格）
python multi_agent_orchestrator.py --parallel

# 模拟模式（测试依赖关系和风格配置）
python multi_agent_orchestrator.py --simulate

# 单独运行某个Agent（自动注入风格要求）
python multi_agent_orchestrator.py --agent 市场情绪Agent

# 检查状态
python multi_agent_orchestrator.py --check

# 指定主题和风格
python multi_agent_orchestrator.py --theme 物理AI --parallel
```

### 风格切换示例

修改`themes/{主题}/config.yaml`切换风格：

```yaml
# 例1: 社交媒体风格（适合传播）
output:
  style: "社交媒体风"
  depth: "L1"

# 例2: 学术论文风格（适合发表）
output:
  style: "学术论文风"
  depth: "L4"

# 例3: 内部备忘录风格（适合内部汇报）
output:
  style: "内部备忘录风"
  depth: "L1"
```

然后运行：
```bash
python multi_agent_orchestrator.py --theme 物理AI --parallel
```

### 方式2：手动调度（精细控制）

对每个Agent单独执行：

#### Step 1: 市场情绪Agent

```
你现在是 **市场情绪分析Agent**。

系统提示词：
---
[读取 agents/MarketSentimentAgent.md]
---

**写作风格要求（必须遵守）**：
---
[根据config.yaml中的output.style自动加载]
例如：
- 风格: 社交媒体风
- 语气: 轻松活泼，带表情符号
- 句式: 短句为主，15-20字
- 结构: emoji开头 + 话题标签 + 互动引导
---

输入数据：
- config.yaml 配置
- 最新市场数据

执行要求：
1. 读取模块模板 modules/00-市场情绪分析.md
2. **严格按"写作风格要求"的语气和句式生成内容**
3. 根据输入数据填充内容
4. 输出完整章节内容
5. 保存到 .agent_temp/市场情绪Agent_output.md

输出完成后，通知产业链Agent可以开始执行。
```

#### Step 2: 产业链Agent

```
你现在是 **产业链分析Agent**。

系统提示词：
---
[读取 agents/IndustryChainAgent.md]
---

输入数据：
- 来自市场情绪Agent的输出（情绪判断）
- tickers.yaml
- valuation.yaml

依赖检查：
✅ 市场情绪Agent已完成

执行要求：
1. 读取模块模板 modules/15-产业链全景图谱.md
2. 根据情绪判断调整估值溢价
3. 按七层功能价值链拆解
4. 为每个公司计算IC Score
5. 输出完整章节内容
6. 保存到 .agent_temp/产业链Agent_output.md

输出完成后，通知铲子股Agent可以开始执行。
```

#### Step 3: 铲子股Agent

```
你现在是 **铲子股筛选Agent**。

系统提示词：
---
[读取 agents/ShovelStockAgent.md]
---

输入数据：
- 来自产业链Agent的输出（IC Score评级）
- 估值数据

依赖检查：
✅ 产业链Agent已完成

执行要求：
1. 读取模块模板 modules/04-铲子股筛选.md
2. 基于IC Score筛选标的
3. 计算仓位配置
4. 输出完整章节内容
5. 保存到 .agent_temp/铲子股Agent_output.md
```

...（依此类推）

#### Step N: 一致性检查Agent

```
你现在是 **一致性检查Agent**。

系统提示词：
---
[读取 agents/ConsistencyCheckAgent.md]
---

输入数据：
- 所有Agent的输出（从 .agent_temp/ 读取）

执行要求：
1. 检查术语一致性
2. 检查数据一致性
3. 检查逻辑连贯性
4. 生成一致性报告
5. 输出修复建议
6. 保存到 .agent_temp/一致性检查Agent_output.md
```

### 方式3：使用通信管理器（程序化）

```python
from agent_communication import AgentCommunicationManager

comm = AgentCommunicationManager()

# Agent发送数据
comm.send_message(
    from_agent="市场情绪Agent",
    to_agent="产业链Agent",
    message_type="DATA",
    content={"sentiment": "贪婪", "vix": 15.5}
)

# Agent获取依赖数据
data = comm.get_dependency_data("产业链Agent", "市场情绪Agent")
```

---

## 输出合并（v2.7增强）

### 自动报告合并

使用报告合并器自动收集所有Agent输出，生成最终报告：

```bash
# 完整执行 + 自动合并报告
python multi_agent_orchestrator.py --parallel --merge

# 仅合并已有Agent输出
python multi_agent_orchestrator.py --merge-only

# 使用报告合并器（独立使用）
python report_merger.py --list                    # 列出可合并的输出
python report_merger.py --output report_final.md  # 指定输出文件名
python report_merger.py --verify                  # 验证报告完整性
```

### 合并流程

```
1. 收集输出    → 从 .agent_temp/ 读取各Agent输出
2. 按序排序    → 按execution_order排序
3. 添加元数据  → 插入YAML frontmatter
4. 生成目录    → 自动创建章节导航
5. 添加标记    → 每个章节添加模块来源标记
6. 输出报告    → 保存到 output/report_YYYYMMDD_HHMM.md
```

### 程序化使用

```python
from report_merger import ReportMerger

merger = ReportMerger()

# 合并报告
report_content = merger.merge_reports(config)

# 保存报告
output_path = merger.save_report(report_content, "report.md")

# 验证报告
result = merger.verify_report(output_path)
# {'has_frontmatter': True, 'has_title': True, 'total_chapters': 16, ...}
```

### 报告结构

生成的报告包含：

```markdown
---
report_title: "新能源产业链分析"
report_theme: "new-energy"
report_depth: "L3"
generated_by_modules:
  - "00-市场情绪分析"
  - "03-产业链拆解"
  - ...
total_modules: 17
data_snapshot:
  valuation_date: "2026-05-24"
---

# 新能源产业链分析
...

## 目录
1. [市场情绪分析](#...)
2. [产业链拆解](#...)
...

## 第一章：市场情绪分析
[内容...]

---
📄 **章节来源** | 模块: `00-市场情绪分析.md` | Agent: `00-市场情绪分析Agent`
💡 量化与定性结合的市场情绪评估，判断当前市场处于贪婪/恐惧/麻木哪个阶段
---

## 附录：Agent执行状态
| Agent | 模块 | 状态 |
|-------|------|------|
| 00-市场情绪分析Agent | 00-市场情绪分析 | ✅ completed |
...
```

---

## 优势对比

| 维度 | 单AI模式 | 多Agent模式 |
|------|----------|-------------|
| **专业性** | ⭐⭐⭐ 通用 | ⭐⭐⭐⭐⭐ 专家级 |
| **上下文** | ⭐⭐ 易溢出 | ⭐⭐⭐⭐⭐ 独立处理 |
| **并行度** | ⭐ 串行 | ⭐⭐⭐⭐⭐ 多层并行 |
| **一致性** | ⭐⭐⭐ 依赖提示词 | ⭐⭐⭐⭐⭐ 专门Agent检查 |
| **容错性** | ⭐⭐ 一错全错 | ⭐⭐⭐⭐ 隔离错误 |
| **调试性** | ⭐⭐ 难定位 | ⭐⭐⭐⭐ 模块化调试 |
| **成本** | ⭐⭐⭐⭐⭐ 低 | ⭐⭐ 较高 |
| **复杂度** | ⭐⭐⭐⭐⭐ 简单 | ⭐⭐ 复杂 |

---

## 推荐场景

### 使用多Agent模式

- L3深度报告（模块多、内容复杂）
- 需要IC Score专业评级
- 产业链全景图谱（1000+行）
- 多人协作报告生成
- 需要高质量一致性

### 使用单AI模式

- L0/L1快速结论
- 模块少、内容简单
- 时间紧迫
- 成本敏感

---

## 故障排查

### Agent卡住

```bash
# 检查状态
python multi_agent_orchestrator.py --check

# 查看通信日志
cat .agent_comm/communication.log
```

### 依赖未满足

```bash
# 手动触发依赖Agent
python multi_agent_orchestrator.py --agent 市场情绪Agent
```

### 数据不一致

```bash
# 清除缓存重试
python agent_communication.py --clear-cache
```

---

## 下一步

1. **测试多Agent模式**: 运行 `python multi_agent_orchestrator.py --simulate`
2. **测试供应链Agent**: 运行 `python multi_agent_orchestrator.py --agent 供应链Agent --simulate`
3. **测试风格控制**: 
   - 修改`config.yaml`的`output.style`为不同风格
   - 运行`python multi_agent_orchestrator.py --theme 物理AI --agent 市场情绪Agent`
   - 检查生成的指令是否包含风格要求
4. **对比质量**: 生成同一主题的单AI和多Agent报告对比
5. **风格对比**: 同一主题用不同风格（社交媒体风vs学术论文风）生成，对比效果
6. **调优配置**: 根据实际效果调整Agent分工和风格选择
7. **逐步迁移**: 从关键模块开始，逐步迁移到多Agent

### 风格测试建议

```bash
# 测试1: 社交媒体风格（适合传播）
echo 'output:\n  style: "社交媒体风"\n  depth: "L1"' > themes/物理AI/style_test.yaml
python multi_agent_orchestrator.py --theme 物理AI --agent 市场情绪Agent

# 测试2: 学术论文风格（适合深度研究）
echo 'output:\n  style: "学术论文风"\n  depth: "L4"' > themes/物理AI/style_test.yaml
python multi_agent_orchestrator.py --theme 物理AI --agent 产业链Agent

# 测试3: 内部备忘录风格（适合内部汇报）
echo 'output:\n  style: "内部备忘录风"\n  depth: "L1"' > themes/物理AI/style_test.yaml
python multi_agent_orchestrator.py --theme 物理AI --agent 组合构建Agent
```

---

## 主题扩展（v2.7）

### 支持多主题

框架支持孙哥方向之外的其他产业主题：

| 主题 | 配置文件 | 七层定义 |
|------|----------|----------|
| **孙哥方向** | `config.yaml` | AI Brain → Compute → Sensors → Actuators → Materials → Integration → Industrial |
| **新能源** | `config-新能源.yaml` | 原材料 → 电池材料 → 电芯制造 → Pack → BMS → 系统集成 → 应用 |
| **量子计算** | `config-量子计算.yaml` | 量子比特 → 控制 → 纠错 → 软件 → 云平台 → 应用 → 安全 |

### 使用不同主题

```bash
# 孙哥方向（默认）
python multi_agent_orchestrator.py --parallel

# 新能源主题
python multi_agent_orchestrator.py --config config-新能源.yaml --parallel

# 量子计算主题
python multi_agent_orchestrator.py --config config-量子计算.yaml --parallel
```

### 创建新主题

1. **复制模板**
   ```bash
   cp config-theme-template.yaml config-{新主题}.yaml
   ```

2. **修改配置**
   - 主题名称和ID
   - 产业链七层定义
   - IC Score权重（根据行业特点调整）
   - 主题特定配置

3. **创建数据目录**
   ```bash
   mkdir -p data/{主题ID}/
   cp data/孙哥方向/tickers.yaml data/{主题ID}/
   # 修改股票清单
   ```

4. **测试运行**
   ```bash
   python multi_agent_orchestrator.py --config config-{新主题}.yaml --simulate
   ```

### 双维度分析

**功能层级**（产业链Agent）：
- 按技术功能组织（AI Brain → Compute → ...）
- 适合识别产业链卡位
- 覆盖主要公司

**供应链层级**（供应链Agent）：
- 按供应关系组织（原材料 → 器件 → 模组 → ...）
- 适合识别隐形冠军
- 补充功能层级的盲区

**建议**：双维度结合，功能层级为主(70%)，供应链层级补充(30%)。

---

*多Agent架构 v2.9 - 支持风格动态控制 & 供应链分析 & 主题扩展*
