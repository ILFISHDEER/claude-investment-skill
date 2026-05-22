#!/usr/bin/env python3
"""
Investment Skill - 股票库维护脚本
功能：定期评估股票池健康度，生成剔除/纳入建议

使用方法：
    python maintenance.py --review monthly      # 月度健康检查
    python maintenance.py --review quarterly   # 季度审议（生成剔除/纳入建议）
    python maintenance.py --direction quantum  # 单个方向深度评估
    python maintenance.py --dry-run            # 预览模式，不写入文件

输出：
    reports/健康检查-{日期}.md     - 月度评分报告
    reports/季度审议-{季度}.md      - 季度剔除/纳入建议
    changelog.yaml                    - 变更记录
    watchlist.yaml                    - 观察名单
"""

import yfinance as yf
import yaml
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Windows编码修复
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"

# 确保报告目录存在
REPORTS_DIR.mkdir(exist_ok=True)


def 读取YAML(路径):
    """读取YAML文件"""
    try:
        with open(路径, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def 写入YAML(数据, 路径):
    """写入YAML文件"""
    with open(路径, 'w', encoding='utf-8') as f:
        yaml.dump(数据, f, allow_unicode=True, sort_keys=False)


def 转为原生类型(值):
    """将numpy类型转为Python原生类型"""
    if 值 is None:
        return None
    if hasattr(值, 'item'):
        return 值.item()
    if isinstance(值, dict):
        return {k: 转为原生类型(v) for k, v in 值.items()}
    if isinstance(值, list):
        return [转为原生类型(v) for v in 值]
    return 值


class 股票评估器:
    """股票评分系统"""

    def __init__(self):
        self.基准表现 = {}  # 缓存行业基准表现

    def 获取股票数据(self, 代码):
        """获取股票完整数据"""
        try:
            ticker = yf.Ticker(代码)
            info = ticker.info
            hist = ticker.history(period="1y")

            if len(hist) < 30:
                return None

            当前价格 = hist['Close'].iloc[-1]
            一年前价格 = hist['Close'].iloc[0]
            一年涨幅 = (当前价格 - 一年前价格) / 一年前价格 * 100

            # 计算波动率
            日收益率 = hist['Close'].pct_change().dropna()
            波动率 = 日收益率.std() * (252 ** 0.5) * 100  # 年化波动率

            # 计算最大回撤
            历史最高 = hist['Close'].expanding().max()
            回撤 = (hist['Close'] - 历史最高) / 历史最高 * 100
            最大回撤 = 回撤.min()

            return {
                'code': 代码,
                'name': info.get('shortName', 'N/A'),
                'price': round(当前价格, 2),
                'yoy_return': round(一年涨幅, 2),
                'volatility': round(波动率, 2),
                'max_drawdown': round(最大回撤, 2),
                'pe': info.get('trailingPE') or info.get('forwardPE'),
                'pb': info.get('priceToBook'),
                'ps': info.get('priceToSalesTrailing12Months'),
                'market_cap': info.get('marketCap'),
                'revenue_growth': info.get('revenueGrowth'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
            }
        except Exception as e:
            print(f"  ⚠️  {代码}: 获取失败 ({str(e)[:50]})")
            return None

    def 计算价格表现分(self, 数据, 行业基准):
        """价格表现评分（20分）"""
        涨幅 = 数据['yoy_return']

        if 涨幅 > 100:  # 翻倍
            return 20
        elif 涨幅 > 50:
            return 18
        elif 涨幅 > 30:
            return 15
        elif 涨幅 > 10:
            return 12
        elif 涨幅 > 0:
            return 8
        elif 涨幅 > -20:
            return 5
        elif 涨幅 > -40:
            return 2
        else:
            return 0

    def 计算估值健康分(self, 数据):
        """估值健康评分（20分）"""
        pe = 数据.get('pe')

        if pe is None:
            return 10  # 无PE数据给中性分

        # 科技股PE容忍度较高
        if pe < 0:  # 亏损
            return 2
        elif pe < 15:  # 低估
            return 18
        elif pe < 30:  # 合理
            return 15
        elif pe < 50:  # 偏高
            return 10
        elif pe < 100:  # 高估值
            return 6
        else:  # 泡沫
            return 3

    def 计算财务质量分(self, 数据):
        """财务质量评分（20分）"""
        营收增速 = 数据.get('revenue_growth')

        if 营收增速 is None:
            return 10

        营收增速 = 营收增速 * 100 if 营收增速 < 1 else 营收增速

        if 营收增速 > 100:  # 爆发式增长
            return 20
        elif 营收增速 > 50:
            return 18
        elif 营收增速 > 30:
            return 15
        elif 营收增速 > 15:
            return 12
        elif 营收增速 > 0:
            return 8
        elif 营收增速 > -10:
            return 4
        else:
            return 0

    def 计算技术地位分(self, 数据, 公司信息):
        """技术地位评分（20分）- 基于市值和行业地位"""
        市值 = 数据.get('market_cap')

        if 市值 is None:
            return 10

        # 转换为亿美元
        市值亿 = 市值 / 1e9

        if 市值亿 > 1000:  # 万亿市值（英伟达、苹果）
            return 20
        elif 市值亿 > 500:
            return 18
        elif 市值亿 > 100:  # 大蓝筹
            return 15
        elif 市值亿 > 50:
            return 12
        elif 市值亿 > 10:  # 中型
            return 10
        elif 市值亿 > 5:
            return 7
        else:  # 小盘股
            return 5

    def 计算综合评分(self, 数据, 公司信息):
        """计算总分"""
        价格分 = self.计算价格表现分(数据, None)
        估值分 = self.计算估值健康分(数据)
        财务分 = self.计算财务质量分(数据)
        技术分 = self.计算技术地位分(数据, 公司信息)

        # 催化剂和风险分默认为中性（需人工判断）
        催化剂分 = 5  # 默认5分（10分制）
        风险分 = 5     # 默认5分（10分制）

        总分 = (价格分 + 估值分 + 财务分 + 技术分) * 1.0 + (催化剂分 + 风险分) * 1.0

        return {
            'total': round(总分, 1),
            'price': 价格分,
            'valuation': 估值分,
            'financial': 财务分,
            'technology': 技术分,
            'catalyst': 催化剂分,
            'risk': 风险分,
        }

    def 评分等级(self, 总分):
        """根据总分评定等级"""
        if 总分 >= 90:
            return 'A+', '核心仓位'
        elif 总分 >= 80:
            return 'A', '标准持仓'
        elif 总分 >= 70:
            return 'B', '观察改进'
        elif 总分 >= 60:
            return 'C', '⚠️ 黄色预警'
        else:
            return 'D', '🚨 红色预警'


def 月度健康检查(主题名, dry_run=False):
    """执行月度健康检查"""
    print(f"\n{'='*60}")
    print(f"📊 月度健康检查: {主题名}")
    print(f"{'='*60}")

    评估器 = 股票评估器()
    主题路径 = DATA_DIR / 主题名
    tickers文件 = 主题路径 / "tickers.yaml"

    if not tickers文件.exists():
        print(f"❌ 未找到 {主题名}/tickers.yaml")
        return

    tickers = 读取YAML(tickers文件)
    评分结果 = []
    红灯预警 = []
    黄灯预警 = []

    for 方向, 公司列表 in tickers.items():
        print(f"\n【{方向}】")
        for 公司 in 公司列表:
            代码 = 公司.get('code', '')
            公司名 = 公司.get('name', '')
            状态 = 公司.get('status', '')

            if not 代码 or 代码 == 'N/A' or 状态 != '上市':
                continue

            print(f"  评估 {公司名} ({代码})...", end=' ')

            数据 = 评估器.获取股票数据(代码)
            if 数据 is None:
                print("❌ 数据获取失败")
                continue

            评分 = 评估器.计算综合评分(数据, 公司)
            等级, 建议 = 评估器.评分等级(评分['total'])

            结果 = {
                'direction': 方向,
                'name': 公司名,
                'code': 代码,
                'score': 评分['total'],
                'grade': 等级,
                'suggestion': 建议,
                'details': 评分,
                'data': 数据,
            }
            评分结果.append(结果)

            if 等级 == 'D':
                红灯预警.append(结果)
                print(f"🚨 D级 {评分['total']}分")
            elif 等级 == 'C':
                黄灯预警.append(结果)
                print(f"⚠️ C级 {评分['total']}分")
            else:
                print(f"✅ {等级}级 {评分['total']}分")

    # 生成报告
    生成健康检查报告(主题名, 评分结果, 红灯预警, 黄灯预警, dry_run)

    return 评分结果


def 生成健康检查报告(主题名, 全部结果, 红灯, 黄灯, dry_run):
    """生成月度健康检查报告"""
    日期 = datetime.now().strftime('%Y-%m-%d')
    报告路径 = REPORTS_DIR / f"健康检查-{日期}.md"

    报告内容 = f"""# 股票库健康检查报告

**检查日期**: {日期}
**主题**: {主题名}
**覆盖股票**: {len(全部结果)} 只

---

## 评分概览

| 等级 | 数量 | 说明 |
|------|------|------|
| A+ (90-100) | {len([x for x in 全部结果 if x['grade'] == 'A+'])} | 核心仓位 |
| A (80-89) | {len([x for x in 全部结果 if x['grade'] == 'A'])} | 标准持仓 |
| B (70-79) | {len([x for x in 全部结果 if x['grade'] == 'B'])} | 观察改进 |
| C (60-69) | {len(黄灯)} | ⚠️ 黄色预警 |
| D (<60) | {len(红灯)} | 🚨 红色预警 |

---

## 🚨 红灯预警（强制剔除候选）

"""

    if 红灯:
        报告内容 += "| 方向 | 公司 | 代码 | 评分 | 主要问题 |\n"
        报告内容 += "|------|------|------|------|----------|\n"
        for r in 红灯:
            问题 = []
            if r['data']['yoy_return'] < -40:
                问题.append(f"年跌幅{r['data']['yoy_return']:.1f}%")
            if r['details']['valuation'] < 5:
                问题.append("估值泡沫")
            if r['details']['financial'] < 5:
                问题.append("财务恶化")
            问题描述 = "、".join(问题) if 问题 else "综合评分低"
            报告内容 += f"| {r['direction']} | {r['name']} | {r['code']} | {r['score']} | {问题描述} |\n"
    else:
        报告内容 += "✅ 无红灯预警\n"

    报告内容 += "\n---\n\n## ⚠️ 黄灯预警（观察名单）\n\n"

    if 黄灯:
        报告内容 += "| 方向 | 公司 | 代码 | 评分 | 建议 |\n"
        报告内容 += "|------|------|------|------|------|\n"
        for r in 黄灯:
            报告内容 += f"| {r['direction']} | {r['name']} | {r['code']} | {r['score']} | 下季度若仍<70分则剔除 |\n"
    else:
        报告内容 += "✅ 无黄灯预警\n"

    报告内容 += "\n---\n\n## 📈 详细评分\n\n"
    报告内容 += "| 方向 | 公司 | 代码 | 总分 | 价格 | 估值 | 财务 | 技术 | 年涨幅 |\n"
    报告内容 += "|------|------|------|------|------|------|------|------|--------|\n"

    # 按评分排序
    排序结果 = sorted(全部结果, key=lambda x: x['score'], reverse=True)
    for r in 排序结果:
        d = r['details']
        涨幅 = r['data']['yoy_return']
        涨幅显示 = f"{涨幅:.1f}%" if 涨幅 else "N/A"
        报告内容 += f"| {r['direction']} | {r['name']} | {r['code']} | **{r['score']}** | {d['price']} | {d['valuation']} | {d['financial']} | {d['technology']} | {涨幅显示} |\n"

    报告内容 += "\n---\n\n## 下一步动作\n\n"
    报告内容 += f"1. **立即关注**: {len(红灯)} 只红灯股票，考虑是否触发强制剔除条件\n"
    报告内容 += f"2. **持续观察**: {len(黄灯)} 只黄灯股票，下月重新评估\n"
    报告内容 += f"3. **季度审议**: 基于本报告和下月数据，季度末执行正式剔除/纳入\n\n"
    报告内容 += f"---\n*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    if not dry_run:
        with open(报告路径, 'w', encoding='utf-8') as f:
            f.write(报告内容)
        print(f"\n✅ 报告已保存: {报告路径}")
    else:
        print(f"\n👁️ 预览模式，未保存报告")
        print(报告内容[:500] + "...")


def 季度审议(主题名, dry_run=False):
    """执行季度审议，生成剔除/纳入建议"""
    print(f"\n{'='*60}")
    print(f"📋 季度审议: {主题名}")
    print(f"{'='*60}")

    # 先执行健康检查获取评分
    评分结果 = 月度健康检查(主题名, dry_run=True)

    剔除建议 = [r for r in 评分结果 if r['grade'] in ['C', 'D']]

    print(f"\n📊 季度审议结果:")
    print(f"  - 总评估数: {len(评分结果)}")
    print(f"  - 剔除候选: {len(剔除建议)}")
    print(f"  - 核心持仓(A+): {len([r for r in 评分结果 if r['grade'] == 'A+'])}")

    # 生成季度审议报告
    季度 = f"{datetime.now().year}-Q{(datetime.now().month-1)//3 + 1}"
    报告路径 = REPORTS_DIR / f"季度审议-{季度}.md"

    报告内容 = f"""# 季度审议报告

**审议季度**: {季度}
**主题**: {主题名}
**审议日期**: {datetime.now().strftime('%Y-%m-%d')}

---

## 一、剔除建议

基于季度评分和表现，以下股票建议剔除：

"""

    if 剔除建议:
        报告内容 += "| 方向 | 公司 | 代码 | 评分 | 剔除理由 | 建议替代 |\n"
        报告内容 += "|------|------|------|------|----------|----------|\n"
        for r in 剔除建议:
            理由 = f"连续评分{r['grade']}级({r['score']}分)，跑输基准"
            报告内容 += f"| {r['direction']} | {r['name']} | {r['code']} | {r['score']} | {理由} | 待研究 |\n"
    else:
        报告内容 += "✅ 本季度无剔除建议\n"

    报告内容 += """
---

## 二、纳入建议

### 候选池（需进一步研究）

| 方向 | 潜在标的 | 代码 | 纳入理由 | 研究状态 |
|------|----------|------|----------|----------|
| 示例 | FormFactor | FORM | 量子测试设备铲子股 | 待研究 |

### 纳入标准检查
- [ ] 市值门槛达标（美股>$10B，A股>¥10B）
- [ ] 技术稀缺性验证
- [ ] 财务数据审查
- [ ] 技术路线确认

---

## 三、组合优化建议

1. **权重调整**: 基于评分结果，建议增加A+级股票权重
2. **行业平衡**: 检查7大方向权重分布
3. **中美配比**: 当前美股/A股占比分析

---

## 四、执行清单

**剔除执行**:
- [ ] 从 tickers.yaml 移除
- [ ] 记录到 changelog.yaml
- [ ] 更新 valuation.yaml

**纳入执行**:
- [ ] 添加到 tickers.yaml
- [ ] 初始评分录入
- [ ] 加入监控列表

---
*审议完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    if not dry_run:
        with open(报告路径, 'w', encoding='utf-8') as f:
            f.write(报告内容)
        print(f"\n✅ 季度审议报告已保存: {报告路径}")

    return 剔除建议


def 主函数():
    """主入口"""
    args = sys.argv[1:]

    dry_run = '--dry-run' in args
    review_type = 'monthly'  # 默认月度
    direction = None

    if '--review' in args:
        idx = args.index('--review')
        if idx + 1 < len(args):
            review_type = args[idx + 1]

    if '--direction' in args:
        idx = args.index('--direction')
        if idx + 1 < len(args):
            direction = args[idx + 1]

    # 默认主题
    主题 = direction if direction else "孙哥方向"

    print(f"🔧 Investment Skill 股票库维护")
    print(f"   模式: {'预览' if dry_run else '正式'}")
    print(f"   检查类型: {review_type}")
    print(f"   主题: {主题}")

    if review_type == 'monthly':
        月度健康检查(主题, dry_run)
    elif review_type == 'quarterly':
        季度审议(主题, dry_run)
    else:
        print(f"❌ 未知检查类型: {review_type}")
        print("   可用: monthly, quarterly")
        sys.exit(1)


if __name__ == '__main__':
    主函数()
