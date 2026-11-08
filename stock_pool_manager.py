#!/usr/bin/env python3
"""
股票池自动更新系统
功能：
  1. 自动发现新股票（基于行业、概念、产业链）
  2. 基于6维度评分筛选股票
  3. 红黄灯预警自动剔除
  4. 定期更新维护

使用方法：
    python stock_pool_manager.py --discover {主题}    # 发现新股票
    python stock_pool_manager.py --auto-update        # 自动更新所有主题
    python stock_pool_manager.py --screen A          # 筛选A级以上股票
    python stock_pool_manager.py --add {代码} {主题} {方向}  # 手动添加
"""

import yfinance as yf
import yaml
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

DB_PATH = Path(".claude/investment_stock.db")


@dataclass
class StockScreenCriteria:
    """股票筛选标准"""
    # 价格表现
    min_yoy_return: float = -20.0      # 最低年涨幅（%）
    max_volatility: float = 80.0       # 最高波动率（%）
    max_drawdown: float = -50.0        # 最大回撤（%）

    # 估值
    max_pe: float = 100.0              # 最高PE
    min_market_cap_b: float = 1.0      # 最低市值（亿美元）

    # 财务
    min_revenue_growth: float = -10.0  # 最低营收增速（%）

    # 综合评分
    min_total_score: float = 60.0      # 最低综合分


class StockPoolManager:
    """股票池管理器"""

    def __init__(self):
        self.db_path = DB_PATH

    def _get_db(self):
        """获取数据库连接"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def discover_by_industry(self, theme: str, industry_keywords: List[str]) -> List[dict]:
        """
        基于行业关键词发现新股票
        目前支持：
        - 通过已有股票的行业关联发现
        - 通过产业链上下游扫描
        """
        print(f"[Discover] Scanning industry: {', '.join(industry_keywords)}")

        # 获取主题现有股票的行业
        with self._get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT industry FROM stocks WHERE theme = ? AND industry IS NOT NULL",
                (theme,)
            )
            existing_industries = [row[0] for row in cursor.fetchall()]

        # TODO: 接入 Yahoo Finance screener 或外部API
        # 这里模拟发现逻辑
        candidates = []

        # 示例：基于主题的行业扩展
        industry_mapping = {
            "量子计算": ["Quantum Computing", "Semiconductors", "Technology"],
            "新能源": ["Solar", "Wind", "Nuclear", "Energy Storage"],
            "具身智能": ["Robotics", "Industrial Automation", "Electric Vehicles"],
            "存储": ["Semiconductors", "Memory", "Data Storage"],
        }

        if theme in industry_mapping:
            target_industries = industry_mapping[theme]
            print(f"  Target industries: {target_industries}")

            # 模拟候选股票（实际应通过API获取）
            candidates = self._mock_candidates(theme, target_industries)

        return candidates

    def _mock_candidates(self, theme: str, industries: List[str]) -> List[dict]:
        """模拟候选股票（实际应替换为真实数据源）"""
        candidates_db = {
            "量子计算": [
                {"code": "IONQ", "name": "IonQ", "reason": "离子阱量子计算龙头"},
                {"code": "RGTI", "name": "Rigetti", "reason": "超导量子计算"},
                {"code": "QBTS", "name": "D-Wave", "reason": "量子退火计算"},
            ],
            "新能源": [
                {"code": "NEE", "name": "NextEra Energy", "reason": "美国最大新能源发电"},
                {"code": "ENPH", "name": "Enphase", "reason": "户用光伏逆变器"},
            ],
            "具身智能": [
                {"code": "ISRG", "name": "Intuitive Surgical", "reason": "手术机器人"},
                {"code": "TER", "name": "Teradyne", "reason": "机器人测试设备"},
            ],
        }

        return candidates_db.get(theme, [])

    def screen_stock(self, symbol: str, criteria: StockScreenCriteria) -> Optional[dict]:
        """
        基于6维度评分筛选股票
        评分维度：
        - 价格表现 (20%): 年涨幅、波动率、回撤
        - 估值健康 (20%): PE、PB、PS
        - 财务质量 (20%): 营收增速、利润率
        - 技术地位 (20%): 市值、行业排名
        - 催化剂 (10%): 近期事件
        - 风险状况 (10%): 负债、现金流
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1y")

            if len(hist) < 30:
                return None

            # 基础数据
            current_price = hist['Close'].iloc[-1]
            year_ago_price = hist['Close'].iloc[0]
            yoy_return = (current_price - year_ago_price) / year_ago_price * 100

            volatility = hist['Close'].pct_change().std() * (252 ** 0.5) * 100

            # 最大回撤
            rolling_max = hist['Close'].expanding().max()
            drawdown = (hist['Close'] - rolling_max) / rolling_max * 100
            max_drawdown = drawdown.min()

            pe = info.get('trailingPE') or info.get('forwardPE', 0)
            pb = info.get('priceToBook', 0)
            market_cap = info.get('marketCap', 0)
            market_cap_b = market_cap / 1e9 if market_cap else 0
            revenue_growth = info.get('revenueGrowth', 0)
            if revenue_growth:
                revenue_growth *= 100

            # 评分计算
            scores = {}

            # 1. 价格表现 (20分)
            if yoy_return > 100:
                scores['price'] = 20
            elif yoy_return > 50:
                scores['price'] = 18
            elif yoy_return > 30:
                scores['price'] = 15
            elif yoy_return > 10:
                scores['price'] = 12
            elif yoy_return > 0:
                scores['price'] = 8
            elif yoy_return > -20:
                scores['price'] = 5
            elif yoy_return > -40:
                scores['price'] = 2
            else:
                scores['price'] = 0

            # 2. 估值健康 (20分)
            if pe <= 0:
                scores['valuation'] = 2  # 亏损
            elif pe < 15:
                scores['valuation'] = 18
            elif pe < 30:
                scores['valuation'] = 15
            elif pe < 50:
                scores['valuation'] = 10
            elif pe < 100:
                scores['valuation'] = 6
            else:
                scores['valuation'] = 3

            # 3. 财务质量 (20分)
            if revenue_growth > 100:
                scores['financial'] = 20
            elif revenue_growth > 50:
                scores['financial'] = 18
            elif revenue_growth > 30:
                scores['financial'] = 15
            elif revenue_growth > 15:
                scores['financial'] = 12
            elif revenue_growth > 0:
                scores['financial'] = 8
            elif revenue_growth > -10:
                scores['financial'] = 4
            else:
                scores['financial'] = 0

            # 4. 技术地位 (20分) - 基于市值
            if market_cap_b > 1000:
                scores['technology'] = 20
            elif market_cap_b > 500:
                scores['technology'] = 18
            elif market_cap_b > 100:
                scores['technology'] = 15
            elif market_cap_b > 50:
                scores['technology'] = 12
            elif market_cap_b > 10:
                scores['technology'] = 10
            elif market_cap_b > 5:
                scores['technology'] = 7
            else:
                scores['technology'] = 5

            # 5. 催化剂 (10分) - 默认中性
            scores['catalyst'] = 5

            # 6. 风险状况 (10分) - 默认中性
            scores['risk'] = 5

            total_score = sum(scores.values())

            # 评级
            if total_score >= 80:
                rating = 'A'
            elif total_score >= 70:
                rating = 'B'
            elif total_score >= 60:
                rating = 'C'
            else:
                rating = 'D'

            # 筛选检查
            passed = True
            failed_reasons = []

            if yoy_return < criteria.min_yoy_return:
                passed = False
                failed_reasons.append(f"年涨幅{yoy_return:.1f}%低于{criteria.min_yoy_return}%")

            if volatility > criteria.max_volatility:
                passed = False
                failed_reasons.append(f"波动率{volatility:.1f}%过高")

            if pe > criteria.max_pe:
                passed = False
                failed_reasons.append(f"PE {pe:.1f}过高")

            if market_cap_b < criteria.min_market_cap_b:
                passed = False
                failed_reasons.append(f"市值{market_cap_b:.1f}B低于{criteria.min_market_cap_b}B")

            if total_score < criteria.min_total_score:
                passed = False
                failed_reasons.append(f"总分{total_score}低于{criteria.min_total_score}")

            return {
                'symbol': symbol,
                'name': info.get('shortName', symbol),
                'price': round(current_price, 2),
                'yoy_return': round(yoy_return, 2),
                'volatility': round(volatility, 2),
                'max_drawdown': round(max_drawdown, 2),
                'pe': pe,
                'pb': pb,
                'market_cap': market_cap,
                'market_cap_b': round(market_cap_b, 2),
                'revenue_growth': round(revenue_growth, 2) if revenue_growth else None,
                'scores': scores,
                'total_score': total_score,
                'rating': rating,
                'passed': passed,
                'failed_reasons': failed_reasons
            }

        except Exception as e:
            print(f"  Error screening {symbol}: {e}")
            return None

    def auto_update_theme(self, theme: str, dry_run: bool = True) -> dict:
        """
        自动更新主题股票池
        流程：
        1. 获取现有股票评分
        2. 标记红黄灯股票
        3. 发现新候选股票
        4. 生成更新建议
        """
        print(f"\n{'='*60}")
        print(f"[Auto Update] Theme: {theme}")
        print(f"{'='*60}")

        results = {
            'theme': theme,
            'timestamp': datetime.now().isoformat(),
            'existing': [],
            'red_flag': [],
            'yellow_flag': [],
            'candidates': [],
            'recommendations': []
        }

        # 1. 获取现有股票
        theme_path = Path(f"themes/{theme}")
        tickers_file = theme_path / "data" / "tickers.yaml"

        if not tickers_file.exists():
            print(f"  Theme not found: {theme}")
            return results

        with open(tickers_file, 'r', encoding='utf-8') as f:
            tickers_data = yaml.safe_load(f) or {}

        criteria = StockScreenCriteria()

        # 2. 评估现有股票
        print("\n[Step 1] Evaluating existing stocks...")
        for direction, stocks in tickers_data.items():
            if not isinstance(stocks, list):
                continue

            for stock in stocks:
                if isinstance(stock, dict) and stock.get('code') and stock.get('code') != 'N/A':
                    symbol = stock['code']
                    print(f"  Screening {symbol}...", end=' ')

                    result = self.screen_stock(symbol, criteria)
                    if result:
                        results['existing'].append(result)
                        status = "PASS" if result['passed'] else "FAIL"
                        print(f"{status} ({result['total_score']}分)")

                        if result['rating'] == 'D':
                            results['red_flag'].append(result)
                        elif result['rating'] == 'C':
                            results['yellow_flag'].append(result)
                    else:
                        print("SKIP (no data)")

        # 3. 发现候选股票
        print("\n[Step 2] Discovering new candidates...")
        candidates = self.discover_by_industry(theme, [])
        for cand in candidates:
            print(f"  Candidate: {cand['code']} - {cand['reason']}")

            # 验证候选
            result = self.screen_stock(cand['code'], criteria)
            if result and result['passed']:
                results['candidates'].append({
                    **result,
                    'discovery_reason': cand['reason']
                })

        # 4. 生成建议
        print("\n[Step 3] Generating recommendations...")
        recommendations = []

        # 剔除建议
        for stock in results['red_flag']:
            recommendations.append({
                'action': 'REMOVE',
                'symbol': stock['symbol'],
                'reason': f"D级评分({stock['total_score']}分)，{', '.join(stock['failed_reasons'][:2])}",
                'urgency': 'HIGH'
            })

        # 观察建议
        for stock in results['yellow_flag']:
            recommendations.append({
                'action': 'WATCH',
                'symbol': stock['symbol'],
                'reason': f"C级评分({stock['total_score']}分)，需持续观察",
                'urgency': 'MEDIUM'
            })

        # 纳入建议
        for stock in results['candidates'][:3]:  # 只建议前3个
            recommendations.append({
                'action': 'ADD',
                'symbol': stock['symbol'],
                'reason': f"A级候选({stock['total_score']}分)，{stock['discovery_reason']}",
                'urgency': 'LOW'
            })

        results['recommendations'] = recommendations

        # 5. 打印报告
        self._print_report(results)

        # 6. 执行更新（如果不是dry-run）
        if not dry_run:
            self._execute_recommendations(theme, recommendations)

        return results

    def _print_report(self, results: dict):
        """打印更新报告"""
        print(f"\n{'='*60}")
        print("[Update Report]")
        print(f"{'='*60}")

        print(f"\nTotal stocks evaluated: {len(results['existing'])}")
        print(f"  - Red flag (D): {len(results['red_flag'])} - 建议剔除")
        print(f"  - Yellow flag (C): {len(results['yellow_flag'])} - 持续观察")
        print(f"  - New candidates: {len(results['candidates'])} - 待纳入")

        if results['red_flag']:
            print("\n[Red Flag - Remove]")
            for s in results['red_flag']:
                print(f"  - {s['symbol']}: {s['total_score']}分, {s['failed_reasons'][0]}")

        if results['candidates']:
            print("\n[Candidates - Add]")
            for s in results['candidates'][:5]:
                print(f"  + {s['symbol']}: {s['total_score']}分, {s.get('discovery_reason', '')}")

        print("\n[Recommendations]")
        for rec in results['recommendations']:
            icon = {"REMOVE": "-", "WATCH": "!", "ADD": "+"}[rec['action']]
            print(f"  [{icon}] {rec['action']}: {rec['symbol']} ({rec['urgency']}) - {rec['reason']}")

    def _execute_recommendations(self, theme: str, recommendations: List[dict]):
        """执行更新建议"""
        print(f"\n[Execute] Applying {len(recommendations)} recommendations...")

        theme_path = Path(f"themes/{theme}")
        tickers_file = theme_path / "data" / "tickers.yaml"

        with open(tickers_file, 'r', encoding='utf-8') as f:
            tickers_data = yaml.safe_load(f) or {}

        for rec in recommendations:
            if rec['action'] == 'REMOVE':
                # 从tickers.yaml移除
                for direction, stocks in tickers_data.items():
                    if isinstance(stocks, list):
                        tickers_data[direction] = [
                            s for s in stocks
                            if not (isinstance(s, dict) and s.get('code') == rec['symbol'])
                        ]
                print(f"  - Removed {rec['symbol']}")

            elif rec['action'] == 'ADD':
                # 这里简化处理，实际应该添加到合适的方向
                print(f"  + Would add {rec['symbol']} (manual review required)")

        # 保存变更
        with open(tickers_file, 'w', encoding='utf-8') as f:
            yaml.dump(tickers_data, f, allow_unicode=True)

    def add_stock(self, symbol: str, theme: str, direction: str, **kwargs):
        """手动添加股票到池子"""
        theme_path = Path(f"themes/{theme}")
        tickers_file = theme_path / "data" / "tickers.yaml"

        if not tickers_file.exists():
            print(f"Error: Theme {theme} not found")
            return False

        with open(tickers_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        # 添加新股票
        new_stock = {
            'name': kwargs.get('name', symbol),
            'code': symbol,
            'market': kwargs.get('market', 'NASDAQ'),
            'status': '上市',
            'notes': kwargs.get('notes', ''),
            'added_date': datetime.now().isoformat()
        }

        if direction not in data:
            data[direction] = []

        # 检查是否已存在
        exists = any(
            isinstance(s, dict) and s.get('code') == symbol
            for s in data.get(direction, [])
        )

        if exists:
            print(f"Stock {symbol} already exists in {direction}")
            return False

        data[direction].append(new_stock)

        with open(tickers_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        print(f"Added {symbol} to {theme}/{direction}")
        return True


def main():
    parser = argparse.ArgumentParser(description='股票池自动管理')
    parser.add_argument('--discover', type=str, help='发现新股票（指定主题）')
    parser.add_argument('--auto-update', action='store_true', help='自动更新所有主题')
    parser.add_argument('--screen', type=str, help='筛选股票（A/B/C/D）')
    parser.add_argument('--add', nargs=3, metavar=('SYMBOL', 'THEME', 'DIRECTION'), help='添加股票')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不执行写入')

    args = parser.parse_args()

    manager = StockPoolManager()

    if args.discover:
        manager.auto_update_theme(args.discover, dry_run=args.dry_run)

    elif args.auto_update:
        themes = ['孙哥方向', '新能源', '量子计算', '物理AI', '空间计算', '合成生物学']
        for theme in themes:
            try:
                manager.auto_update_theme(theme, dry_run=args.dry_run)
            except Exception as e:
                print(f"Error updating {theme}: {e}")

    elif args.screen:
        print(f"Screening stocks with rating >= {args.screen}")
        # TODO: 实现筛选查询

    elif args.add:
        symbol, theme, direction = args.add
        manager.add_stock(symbol, theme, direction)

    else:
        parser.print_help()
        print("\nExamples:")
        print("  python stock_pool_manager.py --discover 量子计算 --dry-run")
        print("  python stock_pool_manager.py --auto-update")
        print("  python stock_pool_manager.py --add FORM 量子计算 quantum_components")


if __name__ == "__main__":
    main()
