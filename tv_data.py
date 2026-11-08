#!/usr/bin/env python3
"""
Investment Skill - TradingView 数据源连接器

当 Yahoo Finance 慢/不可达时的备选数据源（TradingView 公开 scanner 接口，
无需账号和 API key）。输出与 update_data.py 完全同构的 valuation.yaml，
两者可互换使用。

使用方法：
    python tv_data.py 合成生物学           # 更新指定主题
    python tv_data.py 合成生物学 --dry-run # 预览，不写入文件
    python tv_data.py                      # 更新所有主题

安装依赖：
    pip install pyyaml requests

注意：scanner 是 TradingView 的非官方公开接口，个人研究够用，
但没有稳定性承诺，请勿作为生产级数据源。
"""

import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests
import yaml

# Windows终端编码修复（与 update_data.py 一致）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 复用 update_data 的工具函数与路径解析（含 themes/ 与 data/ 双架构兼容）
from update_data import BASE_DIR, 解析主题路径, 读取YAML, 写入YAML

SCANNER_URL = "https://scanner.tradingview.com/symbol"
# 请求字段：现价 / 市值 / TTM市盈率 / 近一年涨幅 / 综合技术评级(-1~+1)
FIELDS = "close,market_cap_basic,price_earnings_ttm_basic,Perf.Y,Recommend.All"

# 交易所后缀 → TradingView 前缀（无后缀的美股默认依次尝试 NASDAQ/NYSE）
# 已实证校准：XETR:SAP ✓ EURONEXT:ASML ✓；哥本哈根(.CO)等个别交易所
# scanner 不覆盖，可在 tickers.yaml 条目里用 tv_symbol: "交易所:代码" 显式指定
后缀映射 = {
    ".SZ": "SZSE", ".SS": "SSE", ".KS": "KRX", ".KQ": "KRX",
    ".HK": "HKEX", ".T": "TSE", ".L": "LSE",
    ".DE": "XETR", ".AS": "EURONEXT",
}


def 构造候选代码(代码, 覆盖):
    """生成待尝试的 TradingView 代码列表：显式覆盖 > 后缀映射 > 美股双交易所"""
    if 覆盖:
        return [覆盖]
    大写 = 代码.upper()
    for 后缀, 前缀 in 后缀映射.items():
        if 大写.endswith(后缀):
            return [f"{前缀}:{大写[:-len(后缀)]}"]
    return [f"NASDAQ:{大写}", f"NYSE:{大写}"]


def 获取股票数据(代码, 覆盖=None):
    """从 TradingView scanner 获取单只股票数据，字段与 update_data.py 对齐"""
    for 代码候选 in 构造候选代码(代码, 覆盖):
        try:
            url = f"{SCANNER_URL}?symbol={urllib.parse.quote(代码候选)}&fields={FIELDS}&no_404=true"
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue
            d = r.json()
            if d.get("close") is None:
                continue

            市值 = d.get("market_cap_basic")
            if 市值:
                # 已实证（2026-11-08，对照 Yahoo 币种字段）：scanner 的 market_cap_basic
                # 统一为美元口径（KRX/HKEX/SSE/SZSE/XETR 均是），无需再按上市地换算
                市值 = round(市值 / 1e8, 2)

            return {
                'pe': d.get("price_earnings_ttm_basic"),
                'ps': None,          # scanner 未提供，留空保持 schema 兼容
                'ev_ebitda': None,
                'market_cap': 市值,
                'current_price': round(d["close"], 2),
                'yoy_return': round(d["Perf.Y"], 2) if d.get("Perf.Y") is not None else None,
                'tv_rating': round(d["Recommend.All"], 2) if d.get("Recommend.All") is not None else None,
                'notes': f"TradingView更新于 {datetime.now().strftime('%Y-%m-%d')} ({代码候选})",
            }
        except Exception:
            continue
    return None


def 更新主题(主题名, dry_run=False):
    """更新单个主题（流程与 update_data.py 相同，仅数据源不同）"""
    主题路径 = 解析主题路径(主题名)
    if 主题路径 is None:
        print(f"❌ 主题不存在（已查找 themes/{主题名}/data 与 data/{主题名}）")
        return False

    tickers文件 = 主题路径 / "tickers.yaml"
    valuation文件 = 主题路径 / "valuation.yaml"
    if not tickers文件.exists():
        print(f"⚠️  {主题名}: 没有 tickers.yaml")
        return False

    print(f"\n📊 [TradingView] 正在更新: {主题名}")
    print("-" * 50)

    tickers = 读取YAML(tickers文件)
    当前估值 = 读取YAML(valuation文件).get('valuation', {})
    新估值 = {'valuation': {}}

    for 方向, 公司列表 in tickers.items():
        if not isinstance(公司列表, list):
            continue  # 顶层 meta/summary 等非列表键直接跳过
        for 公司 in 公司列表:
            if not isinstance(公司, dict):
                continue
            代码 = 公司.get('code', '')
            公司名 = 公司.get('name', '')
            状态 = 公司.get('status', '上市')  # 未标注 status 的条目默认按上市处理

            if not 代码 or 代码 in ('N/A', '未上市') or 状态 != '上市':
                if 代码 in 当前估值:
                    新估值['valuation'][代码] = 当前估值[代码]
                continue

            print(f"  正在获取: {公司名} ({代码})...", end=" ")
            数据 = 获取股票数据(代码, 公司.get('tv_symbol'))

            if 数据:
                原有备注 = 当前估值.get(代码, {}).get('notes', '')
                if 原有备注 and '更新' not in 原有备注:
                    数据['notes'] = 原有备注 + " | " + 数据['notes']
                新估值['valuation'][代码] = 数据
                评级 = 数据.get('tv_rating')
                print(f"✅ 现价={数据['current_price']}, 市值={数据['market_cap']}亿, "
                      f"1年={数据['yoy_return']}%, 评级={评级}")
            else:
                if 代码 in 当前估值:
                    新估值['valuation'][代码] = 当前估值[代码]
                    print("⏭️  获取失败，保留旧数据")
                else:
                    print("❌ 获取失败")
            time.sleep(0.35)  # 对公开接口保持礼貌

    if not dry_run:
        写入YAML(新估值, valuation文件)
        print(f"✅ {主题名} 更新完成，已写入 {valuation文件}")
    else:
        print(f"👁️  预览模式，未写入")
    return True


def 主函数():
    args = [a for a in sys.argv[1:] if a != '--dry-run']
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        print("🔍 预览模式（不写入文件）\n")

    if args:
        更新主题(args[0], dry_run)
    else:
        主题列表 = []
        for d in (BASE_DIR / "themes").iterdir() if (BASE_DIR / "themes").exists() else []:
            if d.is_dir() and not d.name.startswith("_") and (d / "data" / "tickers.yaml").exists():
                主题列表.append(d.name)
        if not 主题列表:
            print("⚠️  未发现任何主题")
            return
        print(f"发现 {len(主题列表)} 个主题: {', '.join(主题列表)}\n")
        for 主题名 in 主题列表:
            更新主题(主题名, dry_run)

    print("\n" + "=" * 50)
    print("🎉 数据更新完成!")
    print("=" * 50)


if __name__ == "__main__":
    主函数()
