# 多源数据集成指南

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Source Connector                        │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────┬───────┴───────┬───────────────┐
        ▼               ▼               ▼               ▼
┌──────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────┐
│   Industry   │ │   ETF    │ │   Chain    │ │    Index     │
│  Screener    │ │ Holdings │ │   Scan     │ │Constituents  │
└──────────────┘ └──────────┘ └────────────┘ └──────────────┘
        │               │               │               │
        └───────────────┴───────┬───────┴───────────────┘
                                ▼
                    ┌─────────────────────┐
                    │ Candidate Pool      │
                    │ (De-duplicate &     │
                    │  Merge Sources)     │
                    └─────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │ 6-Dimension Screener  │
                    │ (Score >= 60 Pass)   │
                    └─────────────────────┘
                                │
                                ▼
                    ┌─────────────────────┐
                    │ Stock Pool Manager  │
                    │ (Add to tickers)   │
                    └─────────────────────┘
```

---

## 数据源详解

### 1. Industry Screener (行业筛选)

**原理**: 基于 Yahoo Finance 行业分类筛选

**覆盖行业**:
```python
INDUSTRY_MAPPING = {
    "量子计算": ["Semiconductors", "Technology", "Electronics"],
    "新能源": ["Solar", "Utilities - Renewable", "Energy"],
    "具身智能": ["Specialty Industrial Machinery", "Electrical Equipment"],
    "存储": ["Semiconductors", "Electronic Components", "Computer Hardware"],
    "空间计算": ["Consumer Electronics", "Technology", "Software"],
    "合成生物学": ["Biotechnology", "Drug Manufacturers"],
}
```

**数据源**: Yahoo Finance (ticker.info)

---

### 2. ETF Holdings (ETF持仓)

**原理**: 从主题相关ETF的Top持仓中反推

**覆盖ETF**:
```python
THEME_ETFS = {
    "量子计算": ["QTUM"],              # Defiance Quantum ETF
    "新能源": ["ICLN", "QCLN", "PBW", "TAN"],  # 清洁能源ETF
    "具身智能": ["BOTZ", "ROBT", "ARKQ"],      # 机器人/自动化ETF
    "存储": ["SMH", "SOXX", "PSI"],            # 半导体ETF
    "空间计算": ["META", "VR"],                  # AR/VR ETF
    "合成生物学": ["ARKG", "XBI"],               # 生物科技ETF
}
```

**加权机制**: 持仓权重越高，置信度越高

---

### 3. Industry Chain (产业链)

**原理**: 基于产业链上下游关系发现

**产业链结构**:
```
量子计算产业链:
├── 上游: 芯片材料、低温系统、微波器件
├── 中游: 量子芯片、量子计算机、量子软件
├── 下游: 金融应用、药物研发、材料设计
└── 铲子股: 半导体设备、测试设备、低温设备

新能源产业链:
├── 上游: 锂矿、钴矿、稀土、多晶硅
├── 中游: 电池、储能系统、光伏组件
├── 下游: 电动车、电网、充电站
└── 铲子股: 电池材料、逆变器、电网设备
```

**铲子股优先**: 铲子股置信度 0.85 > 其他 0.75

---

### 4. Index Constituents (指数成分)

**原理**: 从指数成分中筛选科技股

**支持指数**:
- ^GSPC: S&P 500
- ^IXIC: NASDAQ Composite
- ^NDX: NASDAQ-100 (科技股集中)

**筛选逻辑**: 主题相关主题从NASDAQ-100筛选

---

## 数据融合策略

### 置信度机制

| 数据源 | 基础置信度 | 调整因子 |
|--------|-----------|----------|
| 行业筛选 | 0.70 | - |
| ETF持仓 | 0.80 | -0.02 * 排名 |
| 产业链(铲子) | 0.85 | - |
| 产业链(其他) | 0.75 | - |
| 指数成分 | 0.75 | - |

### 去重与合并

```python
# 同一股票被多个源发现时:
1. 去重: 保留唯一symbol
2. 合并理由: 拼接所有来源的理由
3. 更新置信度: 取最高值
4. 计算相关度: 加权平均各源的相关度
```

---

## 使用方法

### 命令行

```bash
# 发现特定主题的新股票
python data_source_connector.py --theme 量子计算

# 设置最低市值门槛
python data_source_connector.py --theme 新能源 --min-cap 5.0

# 导出候选列表
python data_source_connector.py --theme 量子计算 --export
```

### 集成到股票池管理

```bash
# 1. 发现候选股票
python data_source_connector.py --theme 量子计算 --export

# 2. 6维度评分筛选
python stock_pool_manager.py --discover 量子计算 --dry-run

# 3. 批量更新
python stock_pool_manager.py --auto-update --dry-run
```

---

## 数据流示例

以"量子计算"主题为例:

```
[Source 1: Industry Screener]
  -> Semiconductors: NVDA, AMD, INTC, QCOM, MU, AMAT, LRCX, KLAC...
  -> Technology: MSFT, GOOGL, META, AMZN, CRM...
  Found: 17 stocks

[Source 2: ETF Holdings]
  -> QTUM ETF:
     - IBM (8.50%), GOOGL (7.20%), MSFT (6.80%)
     - NVDA (6.50%), IONQ (5.20%), RGTI (4.80%)
  Found: 6 stocks (加权筛选)

[Source 3: Industry Chain]
  -> 半导体设备: AMAT, LRCX, KLAC, ASML, TER
  -> 测试设备: FORM, TER, KEYS
  Found: 8 stocks (铲子股优先)

[Source 4: Index Constituents]
  -> NASDAQ-100: AAPL, MSFT, AMZN, GOOGL, META, NVDA...
  Found: 20 stocks

[Merge & De-duplicate]
  Total unique: 31 stocks
  - NVDA (4 sources, conf=0.85)
  - MSFT (4 sources, conf=0.80)
  - IONQ (2 sources, conf=0.80)
  - FORM (1 source, conf=0.85 - 铲子股)
  ...

[6-Dimension Screening]
  Pass (>=60分): NVDA, MSFT, GOOGL, AMAT, KEYS, FORM...
  Fail (<60分): IONQ, RGTI (估值过高/波动大)
```

---

## 扩展数据源

### 可集成的额外数据源

1. **新闻/公告API**
   - Alpha Vantage News
   - Bloomberg API
   - 功能: 基于概念热度发现

2. **机构持仓披露**
   - 13F Filings
   - Whale Wisdom
   - 功能: 聪明钱跟踪

3. **IPO/SPAC**
   - IPO Monitor
   - SPAC Track
   - 功能: 新上市公司发现

4. **产业链数据库**
   - Bloomberg SPLC
   - FactSet Supply Chain
   - 功能: 上下游关系图谱

5. **学术/专利数据**
   - Google Scholar
   - USPTO Patents
   - 功能: 技术前沿发现

---

## 质量评估

### 数据质量指标

| 维度 | 当前 | 目标 | 提升方案 |
|------|------|------|----------|
| 覆盖率 | 中等 | 高 | 接入更多ETF |
| 实时性 | 日级 | 小时级 | 接入流式API |
| 准确性 | 高 | 高 | 多源交叉验证 |
| 完整性 | 美股高/A股低 | 高 | 接入A股数据源 |

### 已知限制

1. **A股数据**: Yahoo Finance对A股支持有限
2. **ETF持仓**: Yahoo Finance不直接提供完整持仓
3. **产业链**: 预置映射，需人工维护更新

---

## 文件清单

| 文件 | 用途 |
|------|------|
| `data_source_connector.py` | 多源数据连接器主模块 |
| `stock_pool_manager.py` | 股票池管理（6维度筛选） |
| `data/candidates_{theme}_{date}.yaml` | 候选股票导出 |

---

## 完整工作流

```bash
# 每日股价更新
python update_all_themes.py

# 每周新股票发现
python data_source_connector.py --theme 量子计算 --export
python data_source_connector.py --theme 新能源 --export

# 每月股票池评估
python stock_pool_manager.py --auto-update --dry-run > reports/monthly_review.md

# 季度审议
python maintenance.py --review quarterly
```
