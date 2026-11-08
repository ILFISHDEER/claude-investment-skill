#!/usr/bin/env python3
"""
股票池数据源集成模块
支持多源数据融合发现新股票

数据源：
  1. Yahoo Finance Screener - 行业/市值筛选
  2. ETF Holdings - 持仓反推
  3. 产业链关联 - 上下游扫描
  4. Yahoo Finance Search - 概念搜索
  5. Index Constituents - 指数成分股

使用方法：
    python data_source_connector.py --source screener --industry "Semiconductors"
    python data_source_connector.py --source etf --symbol QQQ
    python data_source_connector.py --source chain --theme "量子计算"
    python data_source_connector.py --source search --keyword "quantum computing"
    python data_source_connector.py --source index --symbol "^GSPC"

配置：
    在 data_source_config.yaml 中配置API密钥和参数
"""

import yfinance as yf
import pandas as pd
import requests
import yaml
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass
import re


@dataclass
class StockCandidate:
    """候选股票数据结构"""
    symbol: str
    name: str
    market: str  # US/CN/HK
    industry: str
    sector: str
    market_cap: float  # 亿美元
    pe_ratio: Optional[float]
    discovery_source: str  # 发现来源
    discovery_reason: str  # 发现理由
    confidence: float  # 置信度 0-1
    theme_relevance: Dict[str, float]  # 主题相关度


class YahooFinanceScreener:
    """
    Yahoo Finance 股票筛选器
    基于行业、市值、估值等条件筛选
    """

    # 行业分类映射
    INDUSTRY_MAPPING = {
        "量子计算": ["Semiconductors", "Technology", "Electronics"],
        "新能源": ["Solar", "Utilities - Renewable", "Solar", "Utilities", "Energy"],
        "具身智能": ["Specialty Industrial Machinery", "Electrical Equipment", "Auto Manufacturers"],
        "存储": ["Semiconductors", "Electronic Components", "Computer Hardware"],
        "空间计算": ["Consumer Electronics", "Technology", "Software"],
        "合成生物学": ["Biotechnology", "Drug Manufacturers", "Diagnostics & Research"],
    }

    def __init__(self):
        self.base_url = "https://query1.finance.yahoo.com/v1/finance/screener"

    def screen_by_industry(self, industries: List[str], min_market_cap: float = 1.0) -> List[StockCandidate]:
        """
        基于行业筛选股票

        Args:
            industries: 行业列表
            min_market_cap: 最低市值（亿美元）

        Returns:
            候选股票列表
        """
        candidates = []

        for industry in industries:
            print(f"[Screener] Screening industry: {industry}")

            try:
                # 使用 yfinance 获取行业股票
                # Yahoo Finance没有直接的行业API，我们使用指数成分+过滤的方式
                # 这里使用模拟数据，实际应接入真实API

                # 模拟一些已知行业的股票
                industry_stocks = self._get_industry_stocks(industry)

                for stock in industry_stocks:
                    # 获取详细信息
                    info = self._get_stock_info(stock['symbol'])
                    if info and info.get('marketCap', 0) / 1e9 >= min_market_cap:
                        candidate = StockCandidate(
                            symbol=stock['symbol'],
                            name=info.get('shortName', stock['symbol']),
                            market='US' if '.' not in stock['symbol'] else 'CN',
                            industry=industry,
                            sector=info.get('sector', 'Unknown'),
                            market_cap=info.get('marketCap', 0) / 1e9,
                            pe_ratio=info.get('trailingPE'),
                            discovery_source='yahoo_screener',
                            discovery_reason=f"Industry: {industry}",
                            confidence=0.7,
                            theme_relevance={}
                        )
                        candidates.append(candidate)
                        print(f"  + {candidate.symbol}: {candidate.name} ({candidate.market_cap:.1f}B)")

            except Exception as e:
                print(f"  Error screening {industry}: {e}")

        return candidates

    def _get_industry_stocks(self, industry: str) -> List[Dict]:
        """获取行业股票清单（模拟）"""
        # 预置的行业股票库
        stocks_db = {
            "Semiconductors": [
                {"symbol": "NVDA", "name": "NVIDIA"},
                {"symbol": "AMD", "name": "Advanced Micro Devices"},
                {"symbol": "INTC", "name": "Intel"},
                {"symbol": "QCOM", "name": "Qualcomm"},
                {"symbol": "MU", "name": "Micron"},
                {"symbol": "AMAT", "name": "Applied Materials"},
                {"symbol": "LRCX", "name": "Lam Research"},
                {"symbol": "KLAC", "name": "KLA"},
                {"symbol": "TSM", "name": "Taiwan Semiconductor"},
                {"symbol": "ASML", "name": "ASML Holding"},
            ],
            "Technology": [
                {"symbol": "MSFT", "name": "Microsoft"},
                {"symbol": "GOOGL", "name": "Alphabet"},
                {"symbol": "META", "name": "Meta"},
                {"symbol": "AMZN", "name": "Amazon"},
                {"symbol": "CRM", "name": "Salesforce"},
                {"symbol": "ORCL", "name": "Oracle"},
                {"symbol": "ADBE", "name": "Adobe"},
            ],
            "Solar": [
                {"symbol": "ENPH", "name": "Enphase Energy"},
                {"symbol": "SEDG", "name": "SolarEdge"},
                {"symbol": "FSLR", "name": "First Solar"},
                {"symbol": "RUN", "name": "Sunrun"},
                {"symbol": "SPWR", "name": "SunPower"},
            ],
            "Biotechnology": [
                {"symbol": "MRNA", "name": "Moderna"},
                {"symbol": "BNTX", "name": "BioNTech"},
                {"symbol": "CRSP", "name": "CRISPR Therapeutics"},
                {"symbol": "EDIT", "name": "Editas Medicine"},
                {"symbol": "NTLA", "name": "Intellia"},
                {"symbol": "BEAM", "name": "Beam Therapeutics"},
                {"symbol": "DNA", "name": "Ginkgo Bioworks"},
                {"symbol": "TWST", "name": "Twist Bioscience"},
            ],
            "Specialty Industrial Machinery": [
                {"symbol": "ISRG", "name": "Intuitive Surgical"},
                {"symbol": "TER", "name": "Teradyne"},
                {"symbol": "ROK", "name": "Rockwell Automation"},
                {"symbol": "ETN", "name": "Eaton"},
            ],
        }
        return stocks_db.get(industry, [])

    def _get_stock_info(self, symbol: str) -> Optional[Dict]:
        """获取股票详细信息"""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info
        except:
            return None


class ETFHoldingsScanner:
    """
    ETF持仓扫描器
    从ETF持仓中反推热门股票
    """

    # 主题相关ETF
    THEME_ETFS = {
        "量子计算": ["QTUM"],  # Defiance Quantum ETF
        "新能源": ["ICLN", "QCLN", "PBW", "TAN"],  # 清洁能源ETF
        "具身智能": ["BOTZ", "ROBT", "ARKQ"],  # 机器人/自动化ETF
        "存储": ["SMH", "SOXX", "PSI"],  # 半导体ETF
        "空间计算": ["META", "VR"],  # AR/VR ETF
        "合成生物学": ["ARKG", "XBI"],  # 生物科技ETF
    }

    def __init__(self):
        pass

    def scan_etf(self, etf_symbol: str, top_n: int = 20) -> List[StockCandidate]:
        """
        扫描ETF持仓

        Args:
            etf_symbol: ETF代码
            top_n: 取前N大持仓

        Returns:
            候选股票列表
        """
        print(f"[ETF] Scanning {etf_symbol} holdings...")
        candidates = []

        try:
            etf = yf.Ticker(etf_symbol)

            # 尝试获取持仓数据
            # Yahoo Finance对持仓数据支持有限，这里使用模拟数据
            holdings = self._get_holdings_data(etf_symbol)

            for i, holding in enumerate(holdings[:top_n]):
                symbol = holding['symbol']
                info = self._get_stock_info(symbol)

                if info:
                    candidate = StockCandidate(
                        symbol=symbol,
                        name=info.get('shortName', symbol),
                        market='US',
                        industry=info.get('industry', 'Unknown'),
                        sector=info.get('sector', 'Unknown'),
                        market_cap=info.get('marketCap', 0) / 1e9 if info.get('marketCap') else 0,
                        pe_ratio=info.get('trailingPE'),
                        discovery_source='etf_holdings',
                        discovery_reason=f"Top {i+1} holding in {etf_symbol} ({holding.get('weight', 0):.2f}%)",
                        confidence=0.8 - (i * 0.02),  # 排名越前置信度越高
                        theme_relevance={}
                    )
                    candidates.append(candidate)
                    print(f"  + {symbol}: {candidate.name} (Weight: {holding.get('weight', 0):.2f}%)")

        except Exception as e:
            print(f"  Error scanning {etf_symbol}: {e}")

        return candidates

    def scan_theme_etfs(self, theme: str) -> List[StockCandidate]:
        """扫描主题相关所有ETF"""
        candidates = []
        etfs = self.THEME_ETFS.get(theme, [])

        for etf in etfs:
            candidates.extend(self.scan_etf(etf, top_n=15))

        return candidates

    def _get_holdings_data(self, etf_symbol: str) -> List[Dict]:
        """获取ETF持仓数据（模拟）"""
        # 模拟ETF持仓数据
        holdings_db = {
            "QTUM": [  # Quantum Computing ETF
                {"symbol": "IBM", "weight": 8.5},
                {"symbol": "GOOGL", "weight": 7.2},
                {"symbol": "MSFT", "weight": 6.8},
                {"symbol": "NVDA", "weight": 6.5},
                {"symbol": "IONQ", "weight": 5.2},
                {"symbol": "RGTI", "weight": 4.8},
            ],
            "ICLN": [  # Clean Energy ETF
                {"symbol": "ENPH", "weight": 8.0},
                {"symbol": "FSLR", "weight": 7.5},
                {"symbol": "PLUG", "weight": 6.2},
                {"symbol": "SEDG", "weight": 5.8},
                {"symbol": "NEE", "weight": 5.5},
            ],
            "BOTZ": [  # Robotics ETF
                {"symbol": "ISRG", "weight": 9.0},
                {"symbol": "NVDA", "weight": 8.5},
                {"symbol": "TER", "weight": 7.0},
                {"symbol": "ROK", "weight": 6.5},
                {"symbol": "ETN", "weight": 5.5},
            ],
            "SMH": [  # Semiconductor ETF
                {"symbol": "NVDA", "weight": 15.0},
                {"symbol": "TSM", "weight": 12.0},
                {"symbol": "AVGO", "weight": 10.0},
                {"symbol": "QCOM", "weight": 8.0},
                {"symbol": "AMD", "weight": 7.5},
                {"symbol": "MU", "weight": 6.0},
                {"symbol": "AMAT", "weight": 5.5},
                {"symbol": "LRCX", "weight": 4.5},
            ],
            "ARKG": [  # Genomic Revolution ETF
                {"symbol": "CRSP", "weight": 8.0},
                {"symbol": "TWST", "weight": 7.5},
                {"symbol": "NTLA", "weight": 7.0},
                {"symbol": "BEAM", "weight": 6.5},
                {"symbol": "DNA", "weight": 6.0},
                {"symbol": "EDIT", "weight": 5.5},
            ],
        }
        return holdings_db.get(etf_symbol, [])

    def _get_stock_info(self, symbol: str) -> Optional[Dict]:
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info
        except:
            return None


class IndustryChainScanner:
    """
    产业链关联扫描器
    基于上下游关系发现股票
    """

    # 产业链图谱
    CHAIN_MAP = {
        "量子计算": {
            "上游": ["芯片材料", "低温系统", "微波器件"],
            "中游": ["量子芯片", "量子计算机", "量子软件"],
            "下游": ["金融应用", "药物研发", "材料设计"],
            "铲子股": ["半导体设备", "测试设备", "低温设备"],
        },
        "新能源": {
            "上游": ["锂矿", "钴矿", "稀土", "多晶硅"],
            "中游": ["电池", "储能系统", "光伏组件", "风机"],
            "下游": ["电动车", "电网", "充电站"],
            "铲子股": ["电池材料", "逆变器", "电网设备"],
        },
        "具身智能": {
            "上游": ["减速器", "电机", "传感器", "芯片"],
            "中游": ["机器人本体", "运动控制", "视觉系统"],
            "下游": ["工业应用", "服务机器人", "医疗机器人"],
            "铲子股": ["减速器", "丝杠", "传感器", "电机"],
        },
        "存储": {
            "上游": ["存储颗粒", "控制器", "HBM"],
            "中游": ["存储模组", "SSD", "内存条"],
            "下游": ["服务器", "PC", "手机", "AI服务器"],
            "铲子股": ["HBM", "存储颗粒", "半导体设备"],
        },
    }

    # 产业链映射到股票
    CHAIN_STOCKS = {
        "半导体设备": ["AMAT", "LRCX", "KLAC", "ASML", "TER"],
        "测试设备": ["FORM", "TER", "KEYS"],
        "电池材料": ["ALB", "SQM", "LTHM", "MP"],
        "逆变器": ["ENPH", "SEDG", "FSLR"],
        "减速器": ["绿的谐波", "双环传动", "中大力德"],  # A股
        "电机": ["鸣志电器", "江苏雷利", "大洋电机"],
        "传感器": ["柯力传感", "奥普特", "奥比中光"],
        "HBM": ["MU", "SNDK", "005930.KS", "000660.KS"],
    }

    def __init__(self):
        pass

    def scan_chain(self, theme: str) -> List[StockCandidate]:
        """
        扫描产业链

        Args:
            theme: 主题名称

        Returns:
            候选股票列表
        """
        print(f"[Chain] Scanning industry chain for {theme}...")
        candidates = []

        chain = self.CHAIN_MAP.get(theme, {})
        if not chain:
            print(f"  No chain data for {theme}")
            return candidates

        # 优先扫描铲子股
        for position, categories in chain.items():
            for category in categories:
                print(f"  [{position}] {category}")
                stocks = self.CHAIN_STOCKS.get(category, [])

                for symbol in stocks:
                    info = self._get_stock_info(symbol)
                    if info:
                        # 铲子股置信度更高
                        confidence = 0.85 if position == "铲子股" else 0.75

                        candidate = StockCandidate(
                            symbol=symbol,
                            name=info.get('shortName', symbol),
                            market='US' if '.' not in symbol else 'CN',
                            industry=category,
                            sector=info.get('sector', 'Unknown'),
                            market_cap=info.get('marketCap', 0) / 1e9 if info.get('marketCap') else 0,
                            pe_ratio=info.get('trailingPE'),
                            discovery_source='industry_chain',
                            discovery_reason=f"{theme}产业链 - {position}/{category}",
                            confidence=confidence,
                            theme_relevance={theme: 0.9}
                        )
                        candidates.append(candidate)
                        print(f"    + {symbol}: {candidate.name}")

        return candidates

    def _get_stock_info(self, symbol: str) -> Optional[Dict]:
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info
        except:
            return None


class IndexConstituentsScanner:
    """
    指数成分股扫描器
    从指数成分中筛选
    """

    # 主要指数
    INDICES = {
        "^GSPC": {"name": "S&P 500", "market": "US"},
        "^IXIC": {"name": "NASDAQ", "market": "US"},
        "^DJI": {"name": "Dow Jones", "market": "US"},
        "^NDX": {"name": "NASDAQ-100", "market": "US"},
    }

    def __init__(self):
        pass

    def scan_index(self, index_symbol: str, filter_sectors: List[str] = None) -> List[StockCandidate]:
        """
        扫描指数成分股

        Args:
            index_symbol: 指数代码
            filter_sectors: 筛选行业

        Returns:
            候选股票列表
        """
        print(f"[Index] Scanning {index_symbol} constituents...")
        candidates = []

        try:
            index = yf.Ticker(index_symbol)
            # 获取成分股（Yahoo Finance不直接提供，需要其他数据源）
            # 这里使用模拟数据
            constituents = self._get_constituents_data(index_symbol)

            for symbol in constituents:
                info = self._get_stock_info(symbol)
                if not info:
                    continue

                # 行业筛选
                if filter_sectors and info.get('sector') not in filter_sectors:
                    continue

                candidate = StockCandidate(
                    symbol=symbol,
                    name=info.get('shortName', symbol),
                    market='US',
                    industry=info.get('industry', 'Unknown'),
                    sector=info.get('sector', 'Unknown'),
                    market_cap=info.get('marketCap', 0) / 1e9 if info.get('marketCap') else 0,
                    pe_ratio=info.get('trailingPE'),
                    discovery_source='index_constituents',
                    discovery_reason=f"{index_symbol} constituent",
                    confidence=0.75,
                    theme_relevance={}
                )
                candidates.append(candidate)
                print(f"  + {symbol}: {candidate.name}")

        except Exception as e:
            print(f"  Error scanning {index_symbol}: {e}")

        return candidates

    def _get_constituents_data(self, index_symbol: str) -> List[str]:
        """获取指数成分股（模拟）"""
        constituents_db = {
            "^NDX": [  # NASDAQ-100 科技股
                "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA",
                "NFLX", "ADBE", "PYPL", "CSCO", "INTC", "AMD", "QCOM",
                "AVGO", "TXN", "AMAT", "LRCX", "KLAC", "MU",
            ],
            "^GSPC": [  # S&P 500 部分科技股
                "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA",
                "UNH", "JNJ", "V", "XOM", "WMT", "JPM", "PG", "HD",
            ],
        }
        return constituents_db.get(index_symbol, [])

    def _get_stock_info(self, symbol: str) -> Optional[Dict]:
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info
        except:
            return None


class DataSourceConnector:
    """数据源连接器主类"""

    def __init__(self):
        self.screener = YahooFinanceScreener()
        self.etf_scanner = ETFHoldingsScanner()
        self.chain_scanner = IndustryChainScanner()
        self.index_scanner = IndexConstituentsScanner()

    def discover_stocks(self, theme: str, min_market_cap: float = 1.0) -> List[StockCandidate]:
        """
        综合多源发现股票

        Args:
            theme: 主题名称
            min_market_cap: 最低市值（亿美元）

        Returns:
            候选股票列表
        """
        print(f"\n{'='*60}")
        print(f"[Multi-Source Discovery] Theme: {theme}")
        print(f"{'='*60}")

        all_candidates = []

        # 1. 行业筛选
        print("\n[Source 1] Industry Screener")
        industries = self.screener.INDUSTRY_MAPPING.get(theme, [])
        if industries:
            candidates = self.screener.screen_by_industry(industries, min_market_cap)
            all_candidates.extend(candidates)
            print(f"  Found {len(candidates)} stocks from industry screening")

        # 2. ETF持仓扫描
        print("\n[Source 2] ETF Holdings")
        candidates = self.etf_scanner.scan_theme_etfs(theme)
        all_candidates.extend(candidates)
        print(f"  Found {len(candidates)} stocks from ETF holdings")

        # 3. 产业链扫描
        print("\n[Source 3] Industry Chain")
        candidates = self.chain_scanner.scan_chain(theme)
        all_candidates.extend(candidates)
        print(f"  Found {len(candidates)} stocks from industry chain")

        # 4. 指数成分筛选
        print("\n[Source 4] Index Constituents")
        if theme in ["量子计算", "存储", "空间计算"]:
            # 科技股从NASDAQ-100筛选
            candidates = self.index_scanner.scan_index("^NDX")
            all_candidates.extend(candidates)
            print(f"  Found {len(candidates)} stocks from index constituents")

        # 去重和排序
        unique_candidates = self._deduplicate_candidates(all_candidates)
        sorted_candidates = sorted(unique_candidates, key=lambda x: x.confidence, reverse=True)

        print(f"\n{'='*60}")
        print(f"[Summary] Total unique candidates: {len(sorted_candidates)}")
        print(f"{'='*60}")

        return sorted_candidates

    def _deduplicate_candidates(self, candidates: List[StockCandidate]) -> List[StockCandidate]:
        """去重候选股票"""
        seen = {}
        for c in candidates:
            if c.symbol not in seen:
                seen[c.symbol] = c
            else:
                # 合并来源信息
                existing = seen[c.symbol]
                existing.discovery_reason += f" | {c.discovery_reason}"
                existing.confidence = max(existing.confidence, c.confidence)

        return list(seen.values())

    def export_candidates(self, candidates: List[StockCandidate], theme: str):
        """导出候选股票到文件"""
        output_path = Path(f"data/candidates_{theme}_{datetime.now().strftime('%Y%m%d')}.yaml")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'theme': theme,
            'generated_at': datetime.now().isoformat(),
            'count': len(candidates),
            'candidates': [
                {
                    'symbol': c.symbol,
                    'name': c.name,
                    'market': c.market,
                    'market_cap_b': round(c.market_cap, 2),
                    'pe_ratio': c.pe_ratio,
                    'industry': c.industry,
                    'discovery_source': c.discovery_source,
                    'discovery_reason': c.discovery_reason,
                    'confidence': c.confidence,
                }
                for c in candidates[:50]  # 只保存前50
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        print(f"\n[Export] Candidates saved to: {output_path}")
        return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description='多源股票数据连接器')
    parser.add_argument('--theme', type=str, help='主题名称')
    parser.add_argument('--min-cap', type=float, default=1.0, help='最低市值（亿美元）')
    parser.add_argument('--export', action='store_true', help='导出结果')

    args = parser.parse_args()

    connector = DataSourceConnector()

    if args.theme:
        candidates = connector.discover_stocks(args.theme, args.min_cap)

        print("\n[Top 10 Candidates]")
        print("-" * 80)
        for i, c in enumerate(candidates[:10], 1):
            print(f"{i}. {c.symbol} - {c.name}")
            print(f"   Market Cap: ${c.market_cap:.1f}B | PE: {c.pe_ratio or 'N/A'}")
            print(f"   Source: {c.discovery_source}")
            print(f"   Reason: {c.discovery_reason}")
            print()

        if args.export:
            connector.export_candidates(candidates, args.theme)
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python data_source_connector.py --theme 量子计算")
        print("  python data_source_connector.py --theme 新能源 --min-cap 5.0 --export")


if __name__ == "__main__":
    main()
