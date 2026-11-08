#!/usr/bin/env python3
"""
Investment Skill - 一键数据更新脚本
功能：从 Yahoo Finance 自动抓取股票数据，更新到 data/ 层的 YAML 文件

使用方法：
    python update_data.py              # 更新所有主题
    python update_data.py 孙哥方向       # 只更新指定主题
    python update_data.py --dry-run    # 预览，不写入文件

安装依赖：
    pip install yfinance pyyaml
"""

import yfinance as yf
import yaml
import sys
import os
from datetime import datetime
from pathlib import Path

# Windows终端编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ============ 配置 ============
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"


def 解析主题路径(主题名):
    """主题数据目录解析：优先新架构 themes/<主题>/data，兼容旧架构 data/<主题>"""
    新路径 = BASE_DIR / "themes" / 主题名 / "data"
    if 新路径.exists():
        return 新路径
    旧路径 = DATA_DIR / 主题名
    if 旧路径.exists():
        return 旧路径
    return None

# A股代码在 Yahoo Finance 的映射规则
# 上交所代码加 .SS，深交所代码加 .SZ
A股映射 = {
    # 已知的A股代码映射，可按需添加
    "002371.SZ": "002371.SZ",
    "688017.SS": "688017.SS",
    "002050.SZ": "002050.SZ",
    "601100.SS": "601100.SS",
    "603728.SS": "603728.SS",
    "603662.SS": "603662.SS",
    "603893.SS": "603893.SS",
    "002389.SZ": "002389.SZ",
    "688297.SS": "688297.SS",
    "002273.SZ": "002273.SZ",
    "002241.SZ": "002241.SZ",
    "000725.SZ": "000725.SZ",
    "600118.SS": "600118.SS",
    "002151.SZ": "002151.SZ",
    "600879.SS": "600879.SS",
    "601985.SS": "601985.SS",
    "600900.SS": "600900.SS",
    "300750.SZ": "300750.SZ",
    "601012.SS": "601012.SS",
    "300274.SZ": "300274.SZ",
    "600406.SS": "600406.SS",
    "600089.SS": "600089.SS",
    "600438.SS": "600438.SS",
    "688223.SS": "688223.SS",
    "002202.SZ": "002202.SZ",
    "002466.SZ": "002466.SZ",
    "002460.SZ": "002460.SZ",
    "300014.SZ": "300014.SZ",
    "600875.SS": "600875.SS",
    "601727.SS": "601727.SS",
    "003816.SZ": "003816.SZ",
    "000400.SZ": "000400.SZ",
    # 量子计算 A股
    "688027.SS": "688027.SS",  # 国盾量子
    "000555.SZ": "000555.SZ",  # 神州信息
    "300520.SZ": "300520.SZ",  # 科大国创
    "002281.SZ": "002281.SZ",  # 光迅科技
    "688122.SS": "688122.SS",  # 西部超导
    "600105.SS": "600105.SS",  # 永鼎股份
}


def 读取YAML(路径):
    """读取YAML文件"""
    try:
        with open(路径, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def 转为原生类型(值):
    """将numpy类型转为Python原生类型，确保YAML可读"""
    if 值 is None:
        return None
    if hasattr(值, 'item'):  # numpy scalar
        return 值.item()
    if isinstance(值, dict):
        return {k: 转为原生类型(v) for k, v in 值.items()}
    if isinstance(值, list):
        return [转为原生类型(v) for v in 值]
    return 值


def 写入YAML(数据, 路径):
    """写入YAML文件，保留注释格式"""
    数据 = 转为原生类型(数据)
    with open(路径, 'w', encoding='utf-8') as f:
        f.write(f"# 估值数据\n")
        f.write(f"# 自动生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 数据源：Yahoo Finance\n")
        f.write(f"# 下次更新：{(datetime.now().replace(day=datetime.now().day+7)).strftime('%Y-%m-%d')}\n\n")
        yaml.dump(数据, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def 获取股票数据(代码):
    """从Yahoo Finance获取单只股票数据"""
    try:
        # 处理A股代码格式
        yf代码 = A股映射.get(代码, 代码)

        ticker = yf.Ticker(yf代码)
        info = ticker.info
        hist = ticker.history(period="1y")

        # 计算近一年涨幅
        if len(hist) >= 2:
            一年前价格 = hist['Close'].iloc[0]
            当前价格 = hist['Close'].iloc[-1]
            涨幅 = round((当前价格 - 一年前价格) / 一年前价格 * 100, 2)
        else:
            涨幅 = None

        市值 = info.get('marketCap')
        if 市值:
            # Yahoo 的 marketCap 以上市地货币计价，需换算为美元
            # 汇率为近似口径（2026-11-08）；精确市值建议用 tv_data.py（TV 接口统一返回美元）
            货币汇率 = {
                '.KS': 1300, '.KQ': 1300,   # 韩元
                '.HK': 7.8,                  # 港币
                '.SS': 7.2, '.SZ': 7.2,     # 人民币
                '.T': 155,                    # 日元
                '.CO': 6.9,                   # 丹麦克朗
                '.DE': 1.1, '.AS': 1.1,      # 欧元（近似）
            }
            汇率 = next((v for k, v in 货币汇率.items() if 代码.upper().endswith(k)), 1.0)
            市值 = round(市值 / 汇率 / 1e8, 2)  # 转为亿美元

        return {
            'pe': info.get('trailingPE'),
            'ps': info.get('priceToSalesTrailing12Months'),
            'ev_ebitda': info.get('enterpriseToEbitda'),
            'market_cap': 市值,  # 亿美元
            'current_price': round(hist['Close'].iloc[-1], 2) if len(hist) > 0 else None,
            'yoy_return': 涨幅,
            'notes': f"自动更新于 {datetime.now().strftime('%Y-%m-%d')}"
        }
    except Exception as e:
        print(f"  ⚠️  {代码}: 获取失败 ({str(e)[:50]})")
        return None


def 更新主题(主题名, dry_run=False):
    """更新单个主题的数据"""
    主题路径 = 解析主题路径(主题名)
    if 主题路径 is None:
        print(f"❌ 主题不存在（已查找 themes/{主题名}/data 与 data/{主题名}）")
        return False

    tickers文件 = 主题路径 / "tickers.yaml"
    valuation文件 = 主题路径 / "valuation.yaml"

    if not tickers文件.exists():
        print(f"⚠️  {主题名}: 没有 tickers.yaml")
        return False

    print(f"\n📊 正在更新: {主题名}")
    print("-" * 50)

    tickers = 读取YAML(tickers文件)
    当前估值 = 读取YAML(valuation文件).get('valuation', {})
    新估值 = {'valuation': {}}

    # 遍历所有方向
    for 方向, 公司列表 in tickers.items():
        if not isinstance(公司列表, list):
            continue  # 顶层 meta/summary 等非列表键直接跳过
        for 公司 in 公司列表:
            if not isinstance(公司, dict):
                continue
            代码 = 公司.get('code', '')
            公司名 = 公司.get('name', '')
            状态 = 公司.get('status', '')

            if not 代码 or 代码 == 'N/A' or 状态 != '上市':
                # 未上市或无效代码，保留原有数据或留空
                if 代码 in 当前估值:
                    新估值['valuation'][代码] = 当前估值[代码]
                continue

            print(f"  正在获取: {公司名} ({代码})...", end=" ")
            数据 = 获取股票数据(代码)

            if 数据:
                # 保留原有 notes 中的关键信息
                原有备注 = 当前估值.get(代码, {}).get('notes', '')
                if 原有备注 and '自动更新' not in 原有备注:
                    数据['notes'] = 原有备注 + f" | 价格更新于 {datetime.now().strftime('%m-%d')}"

                新估值['valuation'][代码] = 数据
                print(f"✅ PE={数据['pe']}, 市值={数据['market_cap']}亿, 涨幅={数据['yoy_return']}%")
            else:
                # 获取失败，保留旧数据
                if 代码 in 当前估值:
                    新估值['valuation'][代码] = 当前估值[代码]
                    print("⏭️  保留旧数据")

    if not dry_run:
        写入YAML(新估值, valuation文件)
        print(f"✅ {主题名} 更新完成，已写入 {valuation文件}")
    else:
        print(f"👁️  {主题名} 预览模式，未写入")

    return True


def 主函数():
    """主入口"""
    args = sys.argv[1:]
    dry_run = '--dry-run' in args

    if dry_run:
        args.remove('--dry-run')
        print("🔍 预览模式（不写入文件）\n")

    if args:
        # 更新指定主题
        主题名 = args[0]
        更新主题(主题名, dry_run)
    else:
        # 更新所有主题：新架构 themes/<主题>/data 优先，兼容旧架构 data/<主题>
        主题列表 = []
        if (BASE_DIR / "themes").exists():
            主题列表 += [d.name for d in (BASE_DIR / "themes").iterdir()
                      if d.is_dir() and not d.name.startswith("_")
                      and (d / "data" / "tickers.yaml").exists()]
        if DATA_DIR.exists():
            主题列表 += [d.name for d in DATA_DIR.iterdir()
                      if d.is_dir() and d.name not in 主题列表
                      and (d / "tickers.yaml").exists()]

        if not 主题列表:
            print("⚠️  未发现任何主题（需要 themes/<主题>/data/tickers.yaml 或 data/<主题>/tickers.yaml）")
            return

        print(f"发现 {len(主题列表)} 个主题: {', '.join(主题列表)}\n")

        for 主题名 in 主题列表:
            更新主题(主题名, dry_run)

    print("\n" + "=" * 50)
    print("🎉 数据更新完成!")
    print("=" * 50)


if __name__ == "__main__":
    主函数()
