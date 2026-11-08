# Investment Skill - 股票池自动更新系统

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         股票池自动更新系统                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    数据源层 (Data Sources)                           │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │   │
│  │  │ Yahoo       │  │ ETF         │  │ Industry    │  │ Index     │  │   │
│  │  │ Finance     │  │ Holdings    │  │ Chain       │  │ Constitu- │  │   │
│  │  │ Screener    │  │ Scanner     │  │ Scanner     │  │ ents      │  │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘  │   │
│  │         │                │                │               │        │   │
│  │         ▼                ▼                ▼               ▼        │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐│   │
│  │  │              DataSourceConnector (多源融合)                    ││   │
│  │  │  - 去重合并                                                       ││   │
│  │  │  - 置信度评分                                                    ││   │
│  │  │  - 主题相关度计算                                                ││   │
│  │  └─────────────────────────────────────────────────────────────────┘│   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │                    候选股票池 (Candidates)                          │   │
│  │                              │                                        │   │
│  └──────────────────────────────┼────────────────────────────────────┘   │
│                                 │                                            │
│                                 ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  筛选评估层 (Screening)                              │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │           StockPoolManager (6维度评分系统)                 │   │   │
│  │  ├─────────────────────────────────────────────────────────────┤   │   │
│  │  │                                                             │   │   │
│  │  │  维度          权重     数据来源                              │   │   │
│  │  │  ─────────────────────────────────────────                   │   │   │
│  │  │  价格表现       20%     Yahoo Finance 历史数据                │   │   │
│  │  │  估值健康       20%     PE/PB/PS 实时数据                     │   │   │
│  │  │  财务质量       20%     营收增速/利润率                       │   │   │
│  │  │  技术地位       20%     市值/行业排名                       │   │   │
│  │  │  催化剂         10%     人工输入/新闻事件                     │   │   │
│  │  │  风险状况       10%     波动率/回撤/负债                      │   │   │
│  │  │                                                             │   │   │
│  │  │  评级标准:                                                   │   │   │
│  │  │    A (80-100) = 核心持仓                                    │   │   │
│  │  │    B (70-79)  = 标准持仓                                    │   │   │
│  │  │    C (60-69)  = ⚠️ 黄色预警                                 │   │   │
│  │  │    D (<60)    = 🚨 红色预警 (建议剔除)                      │   │   │
│  │  │                                                             │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                              │                                        │   │
│  │                              ▼                                        │   │
│  │           ┌────────────────┬───────────────┐                        │   │
│  │           │                │               │                        │   │
│  │           ▼                ▼               ▼                        │   │
│  │      ┌─────────┐     ┌─────────┐    ┌─────────┐                  │   │
│  │      │  PASS   │     │  WATCH  │    │  FAIL   │                  │   │
│  │      │  (A/B)  │     │  (C)    │    │  (D)    │                  │   │
│  │      └────┬────┘     └────┬────┘    └────┬────┘                  │   │
│  │           │               │               │                       │   │
│  │           ▼               ▼               ▼                       │   │
│  │      保留持仓        加入观察       建议剔除                       │   │
│  │                                                             │   │   │
│  └─────────────────────────────────────────────────────────────┘   │   │
│                                 │                                     │   │
│                                 ▼                                     │   │
│  ┌─────────────────────────────────────────────────────────────────────┐│   │
│  │                  执行层 (Execution)                                ││   │
│  ├─────────────────────────────────────────────────────────────────────┤│   │
│  │                                                                     ││   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             ││   │
│  │  │ tickers.yaml │  │ SQLite DB    │  │ Valuation    │             ││   │
│  │  │ 更新        │  │ 同步         │  │ 更新         │             ││   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             ││   │
│  │                                                                     ││   │
│  │  ┌─────────────────────────────────────────────────────────────┐ ││   │
│  │  │                     更新日志                                   │ ││   │
│  │  │  - changelog.yaml: 变更历史                                   │ ││   │
│  │  │  - 健康检查报告: 月度评分                                     │ ││   │
│  │  │  - 季度审议报告: 剔除/纳入建议                                │ ││   │
│  │  └─────────────────────────────────────────────────────────────┘ ││   │
│  │                                                                     ││   │
│  └─────────────────────────────────────────────────────────────────────┘│   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 数据流向

```
数据源 → 发现 → 筛选 → 评级 → 决策 → 执行

1. 发现 (Discovery)
   ├─ Yahoo Finance Screener: 行业筛选
   ├─ ETF Holdings: 持仓反推
   ├─ Industry Chain: 产业链扫描
   └─ Index Constituents: 指数成分

2. 筛选 (Screening)
   ├─ 市值门槛: $1B+
   ├─ PE上限: 100
   ├─ 最低年涨幅: -20%
   └─ 最低综合分: 60

3. 评级 (Rating)
   ├─ 6维度评分
   ├─ A/B/C/D 评级
   └─ 红黄灯标记

4. 决策 (Decision)
   ├─ A/B级: 保留
   ├─ C级: 观察
   └─ D级: 剔除

5. 执行 (Execution)
   ├─ 更新 tickers.yaml
   ├─ 同步 SQLite
   └─ 记录变更日志
```

---

## 核心模块

### 1. data_source_connector.py - 数据源连接器

**功能**: 多源股票发现

```bash
# 发现量子计算主题股票
python data_source_connector.py --theme 量子计算 --export

# 输出:
# [Source 1] Industry Screener - 17 stocks
# [Source 2] ETF Holdings - 6 stocks
# [Source 3] Industry Chain - 8 stocks
# [Source 4] Index Constituents - 20 stocks
# [Summary] Total unique candidates: 31
```

**支持的4大数据源**:

| 数据源 | 描述 | 置信度 |
|--------|------|--------|
| **Yahoo Screener** | 按行业筛选（Semiconductors, Technology等） | 0.7 |
| **ETF Holdings** | 从主题ETF持仓反推（QTUM, BOTZ等） | 0.8 |
| **Industry Chain** | 产业链上下游扫描（铲子股优先） | 0.85 |
| **Index Constituents** | 从NASDAQ-100等指数筛选 | 0.75 |

**输出文件**: `data/candidates_{theme}_{date}.yaml`

---

### 2. stock_pool_manager.py - 股票池管理器

**功能**: 6维度评分筛选

```bash
# 预览主题股票池状态
python stock_pool_manager.py --discover 量子计算 --dry-run

# 执行更新
python stock_pool_manager.py --discover 量子计算

# 批量更新所有主题
python stock_pool_manager.py --auto-update --dry-run

# 手动添加股票
python stock_pool_manager.py --add FORM 量子计算 quantum_components
```

**6维度评分标准**:

| 维度 | 权重 | 评分逻辑 | 数据来源 |
|------|------|----------|----------|
| **价格表现** | 20% | 年涨幅>100%=20分...<-40%=0分 | Yahoo Finance |
| **估值健康** | 20% | PE<15=18分...>100=3分 | Yahoo Finance |
| **财务质量** | 20% | 营收增速>100%=20分...<0=0分 | Yahoo Finance |
| **技术地位** | 20% | 市值>1000B=20分...<5B=5分 | Yahoo Finance |
| **催化剂** | 10% | 默认5分（需人工更新） | 人工/新闻 |
| **风险状况** | 10% | 默认5分（需人工更新） | 波动率/回撤 |

**评级门槛**:
- A (80-100): 核心持仓
- B (70-79): 标准持仓
- C (60-69): 黄色预警
- D (<60): 红色预警（自动剔除）

---

### 3. update_stock_data.py - 股价更新

**功能**: 实时股价获取

```bash
# 更新单个主题
python update_stock_data.py --theme 量子计算

# 更新单个股票
python update_stock_data.py --ticker NVDA

# 更新所有主题
python update_stock_data.py --all
```

**更新内容**:
- 当前价格
- PE/PB比率
- 市值
- 52周高低点
- 更新时间戳

---

### 4. stock_database.py - SQLite数据库

**功能**: 持久化存储

```bash
# 查看股票摘要
python stock_database.py --summary NVDA

# 更新IC Score
python stock_database.py --update-ic NVDA 28 25 20 14 10

# 查看A级铲子股排名
python stock_database.py --top-shovel

# SQL查询
python stock_database.py --query "SELECT * FROM stocks WHERE theme='量子计算'"
```

**数据库表**:
- `stocks`: 股票主表（代码、名称、主题、方向）
- `stock_prices`: 股价历史
- `ic_scores`: IC评分记录
- `catalysts`: 催化剂事件
- `observations`: 观察记录

---

### 5. maintenance.py - 健康检查

**功能**: 定期维护

```bash
# 月度健康检查
python maintenance.py --review monthly

# 季度审议
python maintenance.py --review quarterly

# 单个方向深度评估
python maintenance.py --direction quantum
```

**输出**:
- `reports/健康检查-{日期}.md`
- `reports/季度审议-{季度}.md`

---

## 完整工作流程

### 日常操作

```bash
# 1. 发现新股票（每月一次）
python data_source_connector.py --theme 量子计算 --export

# 2. 更新股价（每周一次）
python update_all_themes.py

# 3. 评估股票池（每月一次）
python stock_pool_manager.py --discover 量子计算 --dry-run
```

### 季度审议

```bash
# 1. 运行月度健康检查
python maintenance.py --review monthly

# 2. 生成季度审议报告
python maintenance.py --review quarterly

# 3. 执行股票池更新（确认后）
python stock_pool_manager.py --auto-update

# 4. 更新股价数据
python update_all_themes.py
```

---

## 文件清单

```
investment-skill/
├── data_source_connector.py    # 多源数据连接器 (NEW)
├── stock_pool_manager.py       # 股票池管理器 (NEW)
├── update_stock_data.py        # 股价更新 (B功能)
├── stock_database.py            # SQLite数据库 (C功能)
├── maintenance.py              # 健康检查 (已有)
├── update_all_themes.py         # 批量更新 (已有)
├── data/
│   └── candidates_{theme}_{date}.yaml  # 候选股票导出
├── themes/{theme}/data/
│   ├── tickers.yaml            # 股票清单 (自动更新)
│   └── valuation.yaml          # 估值数据 (自动更新)
├── reports/
│   ├── 健康检查-{日期}.md
│   └── 季度审议-{季度}.md
└── .clade/
    └── investment_stock.db     # SQLite数据库
```

---

## 当前状态

### ✅ 已实现

| 功能 | 模块 | 状态 |
|------|------|------|
| Yahoo Finance股价更新 | update_stock_data.py | ✅ |
| SQLite数据库管理 | stock_database.py | ✅ |
| 多源股票发现 | data_source_connector.py | ✅ |
| 6维度评分筛选 | stock_pool_manager.py | ✅ |
| 红黄灯预警 | maintenance.py | ✅ |
| 健康检查报告 | maintenance.py | ✅ |

### ⚠️ 需完善

| 功能 | 说明 |
|------|------|
| 真实ETF持仓API | 当前使用模拟数据 |
| 产业链自动扫描 | 当前使用预置映射 |
| A股数据源 | 需要接入A股API |
| 新闻/催化剂自动获取 | 需要接入新闻API |

---

## 示例：量子计算主题

### 当前股票池（部分）

| 代码 | 名称 | 评级 | 总分 | 发现来源 |
|------|------|------|------|----------|
| GOOGL | Alphabet | A | 77 | ETF + 行业 |
| NVDA | NVIDIA | A | 76 | 多源重叠 |
| KEYS | Keysight | A | 63 | 产业链 |
| MSFT | Microsoft | C | 62 | ETF |
| IONQ | IonQ | D | 55 | ETF |

### 建议操作

1. **保留**: GOOGL, NVDA, KEYS (A级)
2. **观察**: MSFT (C级，下月重新评估)
3. **考虑剔除**: IONQ (D级，波动率过高)

---

## 下一步建议

1. **接入真实ETF API**: 使用 financialmodelingprep 或类似服务
2. **完善产业链映射**: 建立完整的产业链知识图谱
3. **添加新闻数据源**: 自动获取催化剂事件
4. **设置定时任务**: 每周自动更新股价，每月自动评估
5. **Web界面**: 创建股票池管理Web界面

需要我帮你实现哪个部分？
