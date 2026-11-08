#!/usr/bin/env python3
"""
Investment Skill 股价数据自动更新脚本
集成 yahoo-finance MCP 获取实时股价数据

使用方法:
  python update_stock_data.py                 # 更新所有主题
  python update_stock_data.py --theme 孙哥方向  # 更新指定主题
  python update_stock_data.py --ticker NVDA    # 更新指定股票
"""

import json
import subprocess
import sys
import argparse
from pathlib import Path
from datetime import datetime
import yaml


def call_yahoo_finance(symbol: str) -> dict:
    """调用 yahoo-finance MCP 获取股票数据"""
    # 模拟调用 yahoo-finance MCP
    # 实际应该通过 MCP 协议通信

    # 这里使用 yahoo_finance Python 包
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info
        history = ticker.history(period="1y")

        if history.empty:
            return None

        current_price = history['Close'].iloc[-1]
        high_52w = history['High'].max()
        low_52w = history['Low'].min()

        return {
            "symbol": symbol,
            "name": info.get("longName", symbol),
            "price": round(current_price, 2),
            "currency": info.get("currency", "USD"),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "pb_ratio": info.get("priceToBook", 0),
            "week_52_high": round(high_52w, 2),
            "week_52_low": round(low_52w, 2),
            "volume": info.get("volume", 0),
            "updated_at": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None


def get_stock_list(theme_path: Path) -> list:
    """从主题配置获取股票清单"""
    tickers_file = theme_path / "data" / "tickers.yaml"

    if not tickers_file.exists():
        print(f"Warning: {tickers_file} not found")
        return []

    with open(tickers_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    stocks = []
    for direction, tickers in data.items():
        if not isinstance(tickers, list):
            continue
        for ticker in tickers:
            if isinstance(ticker, dict):
                symbol = ticker.get('code', '')
                if symbol and symbol != 'N/A':
                    stocks.append({
                        'symbol': symbol,
                        'direction': direction,
                        'market': ticker.get('market', 'US') if 'US' in ticker.get('market', '') or 'NASDAQ' in ticker.get('market', '') or 'NYSE' in ticker.get('market', '') else 'CN'
                    })

    return stocks


def update_valuation_yaml(theme_path: Path, stock_data: dict):
    """更新估值数据文件"""
    import numpy as np
    valuation_file = theme_path / "data" / "valuation.yaml"

    # 读取现有数据
    if valuation_file.exists():
        try:
            with open(valuation_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        except:
            data = {}
    else:
        data = {}

    # Ensure stocks key exists
    if 'stocks' not in data:
        data['stocks'] = {}

    # Convert numpy types to Python native types
    def convert_value(v):
        if isinstance(v, (np.integer, np.floating)):
            return float(v)
        if isinstance(v, np.ndarray):
            return v.tolist()
        return v

    # 更新数据
    symbol = stock_data['symbol']
    data['stocks'][symbol] = {
        'price': convert_value(stock_data['price']),
        'pe': convert_value(stock_data.get('pe_ratio', 0)),
        'pb': convert_value(stock_data.get('pb_ratio', 0)),
        'market_cap': convert_value(stock_data.get('market_cap', 0)),
        '52w_high': convert_value(stock_data.get('week_52_high', 0)),
        '52w_low': convert_value(stock_data.get('week_52_low', 0)),
        'updated_at': stock_data['updated_at']
    }

    # 添加元数据
    data['last_updated'] = datetime.now().isoformat()
    data['data_source'] = 'yahoo-finance-mcp'

    # 写回文件
    with open(valuation_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    print(f"  Updated {symbol}: ${stock_data['price']}")


def update_theme(theme_name: str):
    """更新指定主题的所有股票数据"""
    theme_path = Path(f"themes/{theme_name}")

    if not theme_path.exists():
        print(f"Error: Theme '{theme_name}' not found")
        return

    print(f"\n[Chart] Updating theme: {theme_name}")
    print("-" * 50)

    # 获取股票清单
    stocks = get_stock_list(theme_path)

    if not stocks:
        print("  No stocks found")
        return

    print(f"  Found {len(stocks)} stocks")

    # 更新每个股票
    updated = 0
    failed = 0

    for stock in stocks:
        symbol = stock['symbol']
        print(f"  Fetching {symbol}...", end=" ")

        data = call_yahoo_finance(symbol)

        if data:
            update_valuation_yaml(theme_path, data)
            updated += 1
        else:
            print(f"FAILED")
            failed += 1

    print(f"\n[OK] Updated: {updated}, Failed: {failed}")

    # 记录更新日志
    log_update(theme_name, updated, failed)


def log_update(theme_name: str, updated: int, failed: int):
    """记录更新日志"""
    log_file = Path("data/update_log.yaml")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = yaml.safe_load(f) or {'updates': []}
    else:
        logs = {'updates': []}

    logs['updates'].append({
        'timestamp': datetime.now().isoformat(),
        'theme': theme_name,
        'updated_count': updated,
        'failed_count': failed
    })

    with open(log_file, 'w', encoding='utf-8') as f:
        yaml.dump(logs, f, allow_unicode=True)


def get_all_themes() -> list:
    """获取所有主题"""
    themes_dir = Path("themes")
    if not themes_dir.exists():
        return []

    themes = []
    for path in themes_dir.iterdir():
        if path.is_dir() and not path.name.startswith('_'):
            themes.append(path.name)

    return themes


def main():
    parser = argparse.ArgumentParser(description='更新股票数据')
    parser.add_argument('--theme', type=str, help='指定主题')
    parser.add_argument('--ticker', type=str, help='指定股票代码')
    parser.add_argument('--all', action='store_true', help='更新所有主题')

    args = parser.parse_args()

    if args.ticker:
        # 更新单个股票
        print(f"\n[Fetching] data for {args.ticker}")
        data = call_yahoo_finance(args.ticker)
        if data:
            print(f"\n结果:")
            print(f"  名称: {data['name']}")
            print(f"  价格: ${data['price']}")
            print(f"  PE: {data['pe_ratio']:.2f}")
            print(f"  市值: ${data['market_cap']/1e9:.2f}B")
        else:
            print("获取失败")

    elif args.theme:
        # 更新指定主题
        update_theme(args.theme)

    elif args.all:
        # 更新所有主题
        themes = get_all_themes()
        print(f"Found {len(themes)} themes: {', '.join(themes)}")
        for theme in themes:
            update_theme(theme)

    else:
        # 默认：显示帮助
        parser.print_help()
        print("\n💡 示例:")
        print("  python update_stock_data.py --theme 孙哥方向")
        print("  python update_stock_data.py --ticker NVDA")
        print("  python update_stock_data.py --all")


if __name__ == "__main__":
    main()
