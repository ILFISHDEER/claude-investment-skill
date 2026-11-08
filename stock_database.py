#!/usr/bin/env python3
"""
Investment Skill SQLite 股票数据库
替代 YAML 存储，支持复杂查询

数据库: .claude/investment_stock.db

使用方法:
  python stock_database.py --init          # 初始化数据库
  python stock_database.py --import        # 从 YAML 导入
  python stock_database.py --query "SELECT * FROM stocks WHERE theme='孙哥方向'"
  python stock_database.py --update-price NVDA 150.50  # 更新股价
"""

import sqlite3
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager


DB_PATH = Path(".claude/investment_stock.db")


@contextmanager
def get_db():
    """数据库连接上下文"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """初始化数据库表结构"""
    with get_db() as conn:
        cursor = conn.cursor()

        # 股票主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT,
                name_cn TEXT,
                theme TEXT NOT NULL,
                direction TEXT NOT NULL,
                market TEXT DEFAULT 'US',
                industry TEXT,
                sector TEXT,
                shovel_score INTEGER,
                moat_rating TEXT,
                market_cap REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 股价历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                pe_ratio REAL,
                pb_ratio REAL,
                volume INTEGER,
                market_cap REAL,
                week_52_high REAL,
                week_52_low REAL,
                price_change_1m REAL,
                price_change_3m REAL,
                price_change_1y REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (symbol) REFERENCES stocks(symbol),
                UNIQUE(symbol, recorded_at)
            )
        ''')

        # 评分表 (IC Score)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ic_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                i_score INTEGER,  -- 不可替代性
                c_score INTEGER,  -- 客户集中度
                t_score INTEGER,  -- 技术壁垒
                s_score INTEGER,  -- 市场规模
                m_score INTEGER,  -- 管理层
                total_score INTEGER,
                rating TEXT,  -- A/B/C
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (symbol) REFERENCES stocks(symbol),
                UNIQUE(symbol, evaluated_at)
            )
        ''')

        # 催化剂表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS catalysts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                event TEXT NOT NULL,
                event_date DATE,
                impact_level TEXT,  -- HIGH/MEDIUM/LOW
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (symbol) REFERENCES stocks(symbol)
            )
        ''')

        # 观察记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                theme TEXT,
                content TEXT NOT NULL,
                category TEXT,  -- 财务/技术/市场/政策
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (symbol) REFERENCES stocks(symbol)
            )
        ''')

        # 视图：最新股价
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS latest_prices AS
            SELECT sp.* FROM stock_prices sp
            INNER JOIN (
                SELECT symbol, MAX(recorded_at) as max_date
                FROM stock_prices
                GROUP BY symbol
            ) latest ON sp.symbol = latest.symbol AND sp.recorded_at = latest.max_date
        ''')

        # 视图：最新IC Score
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS latest_ic_scores AS
            SELECT ic.* FROM ic_scores ic
            INNER JOIN (
                SELECT symbol, MAX(evaluated_at) as max_date
                FROM ic_scores
                GROUP BY symbol
            ) latest ON ic.symbol = latest.symbol AND ic.evaluated_at = latest.max_date
        ''')

        # 索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_theme ON stocks(theme)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_direction ON stocks(direction)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_prices_symbol ON stock_prices(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ic_symbol ON ic_scores(symbol)')

        conn.commit()

    print(f"[OK] Database initialized: {DB_PATH}")
    print("Tables created:")
    print("  - stocks (股票主表)")
    print("  - stock_prices (股价历史)")
    print("  - ic_scores (IC评分)")
    print("  - catalysts (催化剂)")
    print("  - observations (观察记录)")


def import_from_yaml():
    """从 YAML 导入数据"""
    themes_dir = Path("themes")

    if not themes_dir.exists():
        print("Error: themes/ directory not found")
        return

    imported = 0

    with get_db() as conn:
        cursor = conn.cursor()

        for theme_dir in themes_dir.iterdir():
            if not theme_dir.is_dir() or theme_dir.name.startswith('_'):
                continue

            tickers_file = theme_dir / "data" / "tickers.yaml"
            if not tickers_file.exists():
                continue

            print(f"\n[Import] {theme_dir.name}...")

            with open(tickers_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            theme = data.get('theme', theme_dir.name)

            # Handle complex structure - directions at root level
            for direction, tickers in data.items():
                # Skip non-list entries (like comments, theme, etc.)
                if not isinstance(tickers, list):
                    continue
                for ticker in tickers:
                    try:
                        # Handle both simple string and dict formats
                        if isinstance(ticker, dict):
                            symbol = ticker.get('code', '')
                            name = ticker.get('name', '')
                            market = ticker.get('market', 'US')
                        else:
                            symbol = ticker
                            name = None
                            market = 'US' if '.' not in symbol else 'CN'

                        if not symbol or symbol == 'N/A':
                            continue

                        cursor.execute('''
                            INSERT INTO stocks (symbol, name, theme, direction, market)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT(symbol) DO UPDATE SET
                                theme = excluded.theme,
                                direction = excluded.direction,
                                updated_at = CURRENT_TIMESTAMP
                        ''', (symbol, name, theme, direction, market))
                        imported += 1
                        print(f"  + {symbol}")
                    except Exception as e:
                        print(f"  X {ticker}: {e}")

        conn.commit()

    print(f"\n[OK] Imported {imported} stocks")


def query_database(sql: str):
    """执行 SQL 查询"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()

            if not rows:
                print("No results")
                return

            # 打印表头
            columns = [desc[0] for desc in cursor.description]
            print(" | ".join(columns))
            print("-" * (len(" | ".join(columns)) + 10))

            # 打印数据
            for row in rows:
                print(" | ".join(str(cell) for cell in row))

            print(f"\nTotal: {len(rows)} rows")

        except Exception as e:
            print(f"Error: {e}")


def update_price(symbol: str, price: float, **kwargs):
    """更新股价"""
    with get_db() as conn:
        cursor = conn.cursor()

        # 检查股票是否存在
        cursor.execute('SELECT symbol FROM stocks WHERE symbol = ?', (symbol,))
        if not cursor.fetchone():
            print(f"Error: {symbol} not found in database")
            return

        # 插入股价记录
        cursor.execute('''
            INSERT INTO stock_prices
            (symbol, price, pe_ratio, pb_ratio, market_cap, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            symbol,
            price,
            kwargs.get('pe'),
            kwargs.get('pb'),
            kwargs.get('market_cap'),
            datetime.now().isoformat()
        ))

        conn.commit()

    print(f"[OK] Updated {symbol}: ${price}")


def update_ic_score(symbol: str, i: int, c: int, t: int, s: int, m: int):
    """更新 IC Score"""
    total = i + c + t + s + m

    # 评级
    if total >= 70:
        rating = 'A'
    elif total >= 60:
        rating = 'B'
    else:
        rating = 'C'

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO ic_scores
            (symbol, i_score, c_score, t_score, s_score, m_score, total_score, rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, i, c, t, s, m, total, rating))

        # 更新主表
        cursor.execute('''
            UPDATE stocks SET shovel_score = ?, updated_at = ?
            WHERE symbol = ?
        ''', (total, datetime.now().isoformat(), symbol))

        conn.commit()

    print(f"[OK] IC Score for {symbol}: {total} ({rating})")
    print(f"   I:{i} C:{c} T:{t} S:{s} M:{m}")


def add_observation(content: str, symbol: str = None, theme: str = None, category: str = None):
    """添加观察记录"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO observations (symbol, theme, content, category)
            VALUES (?, ?, ?, ?)
        ''', (symbol, theme, content, category))
        conn.commit()

    print(f"[OK] Observation added")


def get_stock_summary(symbol: str):
    """获取股票摘要"""
    with get_db() as conn:
        cursor = conn.cursor()

        # 基本信息
        cursor.execute('SELECT * FROM stocks WHERE symbol = ?', (symbol,))
        stock = cursor.fetchone()

        if not stock:
            print(f"{symbol} not found")
            return

        print(f"\n[Summary] {stock['symbol']} - {stock['name'] or 'N/A'}")
        print("=" * 50)
        print(f"主题: {stock['theme']}")
        print(f"方向: {stock['direction']}")
        print(f"市场: {stock['market']}")
        print(f"铲子分: {stock['shovel_score'] or 'N/A'}")

        # 最新股价
        cursor.execute('SELECT * FROM latest_prices WHERE symbol = ?', (symbol,))
        price = cursor.fetchone()
        if price:
            print(f"\n股价: ${price['price']:.2f}")
            print(f"PE: {price['pe_ratio']:.2f}")
            print(f"PB: {price['pb_ratio']:.2f}")
            print(f"市值: ${price['market_cap']/1e9:.2f}B")

        # 最新IC Score
        cursor.execute('SELECT * FROM latest_ic_scores WHERE symbol = ?', (symbol,))
        ic = cursor.fetchone()
        if ic:
            print(f"\nIC Score: {ic['total_score']} ({ic['rating']}级)")
            print(f"  I:{ic['i_score']} C:{ic['c_score']} T:{ic['t_score']} S:{ic['s_score']} M:{ic['m_score']}")

        # 最近观察
        cursor.execute('''
            SELECT content, created_at FROM observations
            WHERE symbol = ? ORDER BY created_at DESC LIMIT 3
        ''', (symbol,))
        observations = cursor.fetchall()
        if observations:
            print("\n最近观察:")
            for obs in observations:
                print(f"  • {obs['content'][:50]}...")


def export_to_yaml(theme: str = None):
    """导出回 YAML"""
    with get_db() as conn:
        cursor = conn.cursor()

        if theme:
            cursor.execute('SELECT * FROM stocks WHERE theme = ?', (theme,))
        else:
            cursor.execute('SELECT * FROM stocks')

        stocks = cursor.fetchall()

        # 按主题分组
        themes = {}
        for stock in stocks:
            t = stock['theme']
            d = stock['direction']
            if t not in themes:
                themes[t] = {}
            if d not in themes[t]:
                themes[t][d] = []
            themes[t][d].append(stock['symbol'])

        # 生成 YAML
        for theme_name, directions in themes.items():
            yaml_data = {
                'theme': theme_name,
                'tickers': directions
            }
            print(f"\n# {theme_name}")
            print(yaml.dump(yaml_data, allow_unicode=True))


def get_top_shovel_stocks(limit: int = 10):
    """获取铲子股排名"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.symbol, s.theme, s.direction, ic.total_score, ic.rating
            FROM stocks s
            JOIN latest_ic_scores ic ON s.symbol = ic.symbol
            WHERE ic.total_score >= 70
            ORDER BY ic.total_score DESC
            LIMIT ?
        ''', (limit,))

        stocks = cursor.fetchall()

        print(f"\n[Top] Top {limit} Shovel Stocks (A)")
        print("=" * 60)
        print(f"{'排名':<4} {'代码':<10} {'主题':<12} {'方向':<12} {'分数':<6} {'评级':<4}")
        print("-" * 60)

        for i, stock in enumerate(stocks, 1):
            print(f"{i:<4} {stock['symbol']:<10} {stock['theme']:<12} {stock['direction']:<12} {stock['total_score']:<6} {stock['rating']:<4}")


def main():
    parser = argparse.ArgumentParser(description='SQLite 股票数据库')
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--import', action='store_true', dest='import_yaml', help='从 YAML 导入')
    parser.add_argument('--query', type=str, help='执行 SQL 查询')
    parser.add_argument('--update-price', nargs=2, metavar=('SYMBOL', 'PRICE'), help='更新股价')
    parser.add_argument('--update-ic', nargs=6, metavar=('SYMBOL', 'I', 'C', 'T', 'S', 'M'), help='更新IC Score')
    parser.add_argument('--summary', type=str, help='股票摘要')
    parser.add_argument('--add-obs', type=str, help='添加观察')
    parser.add_argument('--top-shovel', action='store_true', help='铲子股排名')
    parser.add_argument('--export', action='store_true', help='导出 YAML')

    args = parser.parse_args()

    if args.init:
        init_database()
    elif args.import_yaml:
        import_from_yaml()
    elif args.query:
        query_database(args.query)
    elif args.update_price:
        symbol, price = args.update_price
        update_price(symbol, float(price))
    elif args.update_ic:
        symbol, i, c, t, s, m = args.update_ic
        update_ic_score(symbol, int(i), int(c), int(t), int(s), int(m))
    elif args.summary:
        get_stock_summary(args.summary)
    elif args.top_shovel:
        get_top_shovel_stocks()
    elif args.export:
        export_to_yaml()
    elif args.add_obs:
        add_observation(args.add_obs)
    else:
        parser.print_help()
        print("\n💡 示例:")
        print("  python stock_database.py --init")
        print("  python stock_database.py --import")
        print("  python stock_database.py --summary NVDA")
        print("  python stock_database.py --update-price NVDA 150.50")
        print("  python stock_database.py --top-shovel")


if __name__ == "__main__":
    main()
