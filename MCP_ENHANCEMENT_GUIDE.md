# Investment Skill MCP 增强功能使用指南

## B: Yahoo Finance 自动股价更新

### 功能
- 自动获取实时股价、PE、PB、市值
- 计算52周高低点
- 更新到 valuation.yaml
- 支持定时任务

### 安装依赖
```bash
pip install yfinance pyyaml
```

### 使用方法

#### 1. 更新单个股票
```bash
python update_stock_data.py --ticker NVDA
```

**输出示例：**
```
📈 Fetching data for NVDA

结果:
  名称: NVIDIA Corporation
  价格: $150.23
  PE: 65.42
  市值: $3.75T
  52周高点: $195.32
  52周低点: $108.45
```

#### 2. 更新指定主题的所有股票
```bash
python update_stock_data.py --theme 孙哥方向
```

**输出示例：**
```
📊 Updating theme: 孙哥方向
--------------------------------------------------
Found 25 stocks
  Fetching NVDA... OK
  Fetching TSLA... OK
  Fetching 绿的谐波... OK
  ...

✅ Updated: 25, Failed: 0
```

#### 3. 更新所有主题
```bash
python update_stock_data.py --all
```

#### 4. 定时自动更新（Windows Task Scheduler）
```powershell
# 创建每周更新的定时任务
schtasks /create /tn "InvestmentSkill-WeeklyUpdate" /tr "python C:\Users\OpenClawUser\Projects\investment-skill\update_stock_data.py --all" /sc weekly /d MON /st 09:00
```

### 与 MCP 集成

在 Claude 对话中自动获取：
```
用户：更新孙哥方向的股价数据

Claude：
1. 调用 update_stock_data.py --theme 孙哥方向
2. 获取25只股票的最新价格
3. 更新到 themes/孙哥方向/data/valuation.yaml
4. 返回更新摘要

结果：
  - NVDA: $150.23 (+2.5%)
  - TSLA: $248.50 (-1.2%)
  - 绿的谐波: ￥135.80 (+5.3%)
  ...
```

---

## C: SQLite 股票数据库

### 功能
- 替代 YAML 存储，支持复杂查询
- 股价历史追踪
- IC Score 评分记录
- 催化剂事件管理
- 观察记录积累

### 数据库结构

```
.clade/investment_stock.db
├── stocks (股票主表)
│   ├── symbol, name, theme, direction
│   ├── market, industry, sector
│   └── shovel_score, moat_rating
├── stock_prices (股价历史)
│   ├── symbol, price, pe_ratio, pb_ratio
│   ├── volume, market_cap
│   └── price_change_1m/3m/1y
├── ic_scores (IC评分)
│   ├── symbol, i_score, c_score, t_score
│   ├── s_score, m_score, total_score
│   └── rating (A/B/C)
├── catalysts (催化剂)
│   └── symbol, event, event_date, impact
└── observations (观察记录)
    └── symbol, content, category, source
```

### 使用方法

#### 1. 初始化数据库
```bash
python stock_database.py --init
```

**输出：**
```
[OK] Database initialized: .claude/investment_stock.db
Tables created:
  - stocks
  - stock_prices
  - ic_scores
  - catalysts
  - observations
```

#### 2. 从 YAML 导入
```bash
python stock_database.py --import
```

**输出：**
```
📥 Importing 孙哥方向...
  + NVDA
  + TSLA
  + 绿的谐波
  ...

✅ Imported 25 stocks
```

#### 3. 查看股票摘要
```bash
python stock_database.py --summary NVDA
```

**输出：**
```
📊 NVDA - NVIDIA Corporation
==================================================
主题: 孙哥方向
方向: 存储
市场: US
铲子分: 92

股价: $150.23
PE: 65.42
PB: 25.80
市值: $3.75T

IC Score: 92 (A级)
  I:28 C:25 T:20 S:14 M:10

最近观察:
  • H200芯片订单超预期...
  • 竞争对手AMD市场份额下降...
```

#### 4. SQL 查询
```bash
python stock_database.py --query "SELECT * FROM stocks WHERE theme='孙哥方向'"
```

**输出：**
```
symbol | name | theme | direction | shovel_score
-------|------|-------|-------------|--------------
NVDA   | ...  | 孙哥方向 | 存储      | 92
TSLA   | ...  | 孙哥方向 | 具身智能   | 85
绿的谐波| ... | 孙哥方向 | 具身智能   | 78
...

Total: 25 rows
```

#### 5. 更新 IC Score
```bash
python stock_database.py --update-ic NVDA 28 25 20 14 10
```

**输出：**
```
[OK] IC Score for NVDA: 97 (A级)
   I:28 C:25 T:20 S:14 M:10
```

#### 6. 获取铲子股排名
```bash
python stock_database.py --top-shovel
```

**输出：**
```
🏆 Top 10 铲子股 (A级)
============================================================
排名   代码       主题       方向       分数   评级
------------------------------------------------------------
1      NVDA       孙哥方向   存储       97     A
2      TSLA       孙哥方向   具身智能   85     A
3      绿的谐波   孙哥方向   具身智能   78     A
...
```

#### 7. 添加观察记录
```bash
python stock_database.py --add-obs "NVDA Q1财报超预期，数据中心业务增长300%"
```

#### 8. 导出回 YAML
```bash
python stock_database.py --export
```

---

## 实际应用场景

### 场景1：每周股价更新
```bash
# 每周一早上执行
python update_stock_data.py --all

# 自动更新所有主题的股价数据
# 结果保存到 valuation.yaml
```

### 场景2：生成报告前数据准备
```python
# generate_report_v2.py
def prepare_data(theme):
    # 1. 更新股价
    subprocess.run(['python', 'update_stock_data.py', '--theme', theme])

    # 2. 从数据库获取最新IC Score
    db.query(f"SELECT * FROM latest_ic_scores WHERE theme='{theme}'")

    # 3. 获取催化剂
    db.query(f"SELECT * FROM catalysts WHERE theme='{theme}' AND event_date > NOW()")

    return data
```

### 场景3：投资回顾
```bash
# 查看某股票历史表现
python stock_database.py --query "
  SELECT * FROM stock_prices
  WHERE symbol='NVDA'
  AND recorded_at > DATE('now', '-3 months')
  ORDER BY recorded_at DESC
"

# 分析IC Score变化趋势
python stock_database.py --query "
  SELECT evaluated_at, total_score, rating
  FROM ic_scores
  WHERE symbol='NVDA'
  ORDER BY evaluated_at DESC
  LIMIT 10
"
```

### 场景4：跨主题对比
```sql
-- 查询所有主题的A级铲子股
SELECT theme, direction, symbol, total_score
FROM stocks s
JOIN latest_ic_scores ic ON s.symbol = ic.symbol
WHERE ic.rating = 'A'
ORDER BY theme, total_score DESC;
```

---

## 与 MCP 集成

### 在 Claude 中使用

#### 1. 查询股价
```
用户：NVDA 现在多少钱？

Claude：
调用 stock_database.py --summary NVDA
→ 价格: $150.23
→ PE: 65.42
→ 52周区间: $108.45 - $195.32

回答：
NVDA当前股价 $150.23，处于52周区间的中间位置，
PE为65.42，属于合理偏高估值。
```

#### 2. 对比分析
```
用户：孙哥方向里哪个铲子股评分最高？

Claude：
调用 stock_database.py --top-shovel
→ 查询主题='孙哥方向'的A级股票
→ 按IC Score排序

回答：
孙哥方向的A级铲子股排名：
1. NVDA (97分) - 存储产业链，唯一GPU供应商
2. TSLA (85分) - 具身智能终端
3. 绿的谐波 (78分) - 减速器唯一国产替代
```

#### 3. 自动数据同步
```
用户：生成孙哥方向L3报告

Claude：
1. 调用 update_stock_data.py --theme 孙哥方向
   → 更新25只股票的最新价格

2. 从数据库查询：
   - SELECT * FROM stocks WHERE theme='孙哥方向'
   - SELECT * FROM latest_ic_scores WHERE symbol IN (...)
   - SELECT * FROM catalysts WHERE symbol IN (...)

3. 生成报告...
```

---

## 文件清单

| 文件 | 用途 |
|------|------|
| `update_stock_data.py` | Yahoo Finance 股价更新 |
| `stock_database.py` | SQLite 数据库管理 |
| `.claude/investment_stock.db` | SQLite 数据库文件 |
| `data/update_log.yaml` | 更新日志 |

---

## 下一步建议

1. **运行初始化：**
   ```bash
   python stock_database.py --init
   python stock_database.py --import
   ```

2. **测试更新：**
   ```bash
   python update_stock_data.py --ticker NVDA
   ```

3. **查看排名：**
   ```bash
   python stock_database.py --top-shovel
   ```

需要我帮你运行这些测试吗？
