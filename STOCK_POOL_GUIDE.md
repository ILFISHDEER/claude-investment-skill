# 股票池自动更新系统使用指南

## 功能概述

股票池自动更新系统实现了 **6维度评分筛选机制**，支持自动发现、评估和维护股票池。

---

## 6维度评分标准

| 维度 | 权重 | 评分标准 |
|------|------|----------|
| **价格表现** | 20% | 年涨幅>100%=20分，>50%=18分... <-40%=0分 |
| **估值健康** | 20% | PE<15=18分，15-30=15分... >100=3分 |
| **财务质量** | 20% | 营收增速>100%=20分... <0=0分 |
| **技术地位** | 20% | 市值>1000B=20分... <5B=5分 |
| **催化剂** | 10% | 默认5分（需人工判断事件） |
| **风险状况** | 10% | 默认5分（需人工判断风险） |

**评级门槛**：
- A (80-100分): 核心持仓
- B (70-79分): 标准持仓
- C (60-69分): ⚠️ 黄色预警
- D (<60分): 🚨 红色预警（建议剔除）

---

## 筛选阈值

```python
StockScreenCriteria:
    min_yoy_return: -20.0      # 最低年涨幅（%）
    max_volatility: 80.0       # 最高波动率（%）
    max_pe: 100.0              # 最高PE
    min_market_cap_b: 1.0      # 最低市值（亿美元）
    min_revenue_growth: -10.0  # 最低营收增速（%）
    min_total_score: 60.0      # 最低综合分
```

---

## 使用方法

### 1. 预览主题股票池状态（推荐先预览）

```bash
python stock_pool_manager.py --discover 量子计算 --dry-run
```

输出示例：
```
[Step 1] Evaluating existing stocks...
  Screening NVDA... PASS (76分)
  Screening IONQ... FAIL (55分) - 波动率过高
  ...

[Recommendations]
  [-] REMOVE: IONQ (HIGH) - D级评分，波动率92%过高
  [!] WATCH: MSFT (MEDIUM) - C级评分，需持续观察
```

### 2. 自动更新单个主题

```bash
python stock_pool_manager.py --discover 量子计算
```

这将：
1. 评估现有股票
2. 标记D级股票（自动从tickers.yaml移除）
3. 发现新候选股票
4. 生成纳入建议

### 3. 批量更新所有主题

```bash
python stock_pool_manager.py --auto-update --dry-run  # 预览
python stock_pool_manager.py --auto-update            # 执行
```

### 4. 手动添加新股票

```bash
python stock_pool_manager.py --add FORM 量子计算 quantum_components
```

参数：
- `FORM`: 股票代码
- `量子计算`: 主题
- `quantum_components`: 细分方向

---

## 自动发现逻辑

目前支持基于**行业关键词**的候选发现：

```python
industry_mapping = {
    "量子计算": ["Quantum Computing", "Semiconductors", "Technology"],
    "新能源": ["Solar", "Wind", "Nuclear", "Energy Storage"],
    "具身智能": ["Robotics", "Industrial Automation", "Electric Vehicles"],
    "存储": ["Semiconductors", "Memory", "Data Storage"],
}
```

**未来扩展**：
- 接入Yahoo Finance Screener API
- 基于产业链上下游自动关联
- 基于新闻/公告自动识别新概念
- 基于ETF持仓反推成分股

---

## 更新流程

```
                    ┌─────────────────┐
                    │   定期触发      │
                    │ (每周/每月)     │
                    └────────┬────────┘
                             ▼
              ┌──────────────────────────────┐
              │  Step 1: 评估现有股票        │
              │  - 获取Yahoo Finance数据     │
              │  - 计算6维度评分             │
              │  - 生成A/B/C/D评级           │
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │  Step 2: 红黄灯处理          │
              │  D级(红): 自动剔除            │
              │  C级(黄): 加入观察列表        │
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │  Step 3: 发现新候选          │
              │  - 行业关键词扫描             │
              │  - 产业链关联分析             │
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │  Step 4: 候选股票评分        │
              │  - 必须通过6维度筛选         │
              │  - 总分>=60分才建议纳入      │
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │  Step 5: 生成报告            │
              │  - 剔除清单                  │
              │  - 观察清单                  │
              │  - 纳入建议                  │
              └──────────────────────────────┘
```

---

## 文件清单

| 文件 | 用途 |
|------|------|
| `stock_pool_manager.py` | 股票池自动管理主脚本 |
| `maintenance.py` | 月度健康检查（已有） |
| `themes/{主题}/data/tickers.yaml` | 股票清单（自动更新） |

---

## 集成到定期工作流

```bash
# 1. 每周更新股价（已有）
python update_all_themes.py

# 2. 每月评估股票池
python stock_pool_manager.py --auto-update --dry-run > reports/股票池评估-$(date +%Y%m).md

# 3. 季度审议（已有）
python maintenance.py --review quarterly
```

---

## 注意事项

1. **自动剔除谨慎使用**：D级股票自动标记，但建议人工确认后再执行移除
2. **候选发现待完善**：目前使用模拟数据，需接入真实数据源
3. **6维度权重可调**：根据主题特性调整（科技股PE容忍度可更高）
4. **A股数据支持有限**：部分A股在Yahoo Finance数据不完整

---

## 示例：量子计算主题当前状态

基于刚才的运行结果：

### 现有股票评级
| 代码 | 评级 | 总分 | 主要问题 |
|------|------|------|----------|
| GOOGL | A | 77 | - |
| NVDA | A | 76 | - |
| KEYS | A | 63 | - |
| MSFT | C | 62 | 需观察 |
| AMZN | C | 64 | 需观察 |
| IONQ | D | 55 | 🚨 波动率过高 |
| RGTI | D | 57 | 🚨 波动率过高 |
| QBTS | D | 37 | 🚨 综合评分低 |

### 建议操作
- **保留**: GOOGL, NVDA, KEYS (A级)
- **观察**: MSFT, AMZN (C级，下月重新评估)
- **考虑剔除**: IONQ, RGTI, QBTS (D级，波动率过高)
