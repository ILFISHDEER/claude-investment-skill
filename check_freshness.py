#!/usr/bin/env python3
"""
Investment Skill - 数据新鲜度检查脚本
功能：检查各数据文件的最后更新时间，提醒哪些数据已过期

使用方法：
    python check_freshness.py              # 检查所有数据
    python check_freshness.py --theme 孙哥方向  # 检查特定主题
    python check_freshness.py --report    # 生成过期数据报告

输出：
    控制台输出过期警告
    reports/数据新鲜度报告-{日期}.md
"""

import os
import sys
import yaml
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

# 数据新鲜度阈值（天）
FRESHNESS_THRESHOLDS = {
    'valuation.yaml': 7,        # 估值数据：7天内必须更新
    'tickers.yaml': 30,         # 股票清单：30天检查一次
    'catalysts.yaml': 14,       # 催化剂：14天内更新
    'etfs.yaml': 90,            # ETF数据：90天更新
    'core_logic': 90,           # 深度分析：90天更新
}

# 文件重要性等级
IMPORTANCE_LEVELS = {
    'valuation.yaml': '🔴 关键',      # 股价每天都在变
    'catalysts.yaml': '🟡 重要',      # 事件时间会变
    'tickers.yaml': '🟢 一般',        # 公司信息相对稳定
    'etfs.yaml': '🟢 一般',           # ETF结构稳定
    'core_logic': '🟡 重要',          # 季度更新即可
}


def 获取文件修改时间(文件路径):
    """获取文件最后修改时间"""
    try:
        mtime = os.path.getmtime(文件路径)
        return datetime.fromtimestamp(mtime)
    except FileNotFoundError:
        return None


def 计算天数差(时间1, 时间2):
    """计算两个时间之间的天数差"""
    return (时间2 - 时间1).days


def 判断新鲜度等级(文件类型, 天数):
    """判断数据新鲜度等级"""
    阈值 = FRESHNESS_THRESHOLDS.get(文件类型, 30)

    if 天数 <= 阈值:
        return '✅ 新鲜', '数据在有效期内'
    elif 天数 <= 阈值 * 2:
        return '⚠️ 警告', f'已过期{天数 - 阈值}天，建议更新'
    else:
        return '🚨 严重过期', f'已过期{天数 - 阈值}天，必须更新'


def 检查主题数据(主题名):
    """检查单个主题的数据新鲜度"""
    主题路径 = DATA_DIR / 主题名

    if not 主题路径.exists():
        print(f"❌ 主题不存在: {主题名}")
        return None

    检查结果 = []
    现在 = datetime.now()

    print(f"\n{'='*60}")
    print(f"📊 检查主题: {主题名}")
    print(f"{'='*60}")

    # 检查各类数据文件
    for 文件名, 阈值 in FRESHNESS_THRESHOLDS.items():
        if 文件名 == 'core_logic':
            # 检查core_logic目录
            core_logic_dir = 主题路径 / "core_logic"
            if core_logic_dir.exists():
                md_files = list(core_logic_dir.glob("*.md"))
                if md_files:
                    # 取最新的文件修改时间
                    最新时间 = max(获取文件修改时间(f) for f in md_files if 获取文件修改时间(f))
                    天数 = 计算天数差(最新时间, 现在)
                    状态, 说明 = 判断新鲜度等级('core_logic', 天数)

                    检查结果.append({
                        '文件': 'core_logic/*.md',
                        '类型': '深度分析',
                        '最后更新': 最新时间.strftime('%Y-%m-%d'),
                        '天数': 天数,
                        '阈值': 阈值,
                        '状态': 状态,
                        '说明': 说明,
                        '重要': IMPORTANCE_LEVELS['core_logic']
                    })

                    print(f"  {IMPORTANCE_LEVELS['core_logic']} core_logic/*.md: "
                          f"{状态} ({天数}天前)")
            continue

        文件路径 = 主题路径 / 文件名
        if 文件路径.exists():
            修改时间 = 获取文件修改时间(文件路径)
            天数 = 计算天数差(修改时间, 现在)
            状态, 说明 = 判断新鲜度等级(文件名, 天数)

            检查结果.append({
                '文件': 文件名,
                '类型': 文件名.replace('.yaml', ''),
                '最后更新': 修改时间.strftime('%Y-%m-%d'),
                '天数': 天数,
                '阈值': 阈值,
                '状态': 状态,
                '说明': 说明,
                '重要': IMPORTANCE_LEVELS.get(文件名, '🟢 一般')
            })

            print(f"  {IMPORTANCE_LEVELS.get(文件名, '🟢 一般')} {文件名}: "
                  f"{状态} ({天数}天前)")
        else:
            print(f"  ⚪ {文件名}: 文件不存在")

    return 检查结果


def 生成新鲜度报告(所有主题结果):
    """生成数据新鲜度报告"""
    日期 = datetime.now().strftime('%Y-%m-%d')
    报告路径 = REPORTS_DIR / f"数据新鲜度报告-{日期}.md"

    报告内容 = f"""# 数据新鲜度报告

**检查日期**: {日期}
**检查主题数**: {len(所有主题结果)}

---

## 执行摘要

"""

    # 统计
    总文件数 = 0
    新鲜数 = 0
    警告数 = 0
    过期数 = 0
    严重过期 = []

    for 主题, 结果列表 in 所有主题结果.items():
        for r in 结果列表:
            总文件数 += 1
            if '✅' in r['状态']:
                新鲜数 += 1
            elif '⚠️' in r['状态']:
                警告数 += 1
            else:
                过期数 += 1
                严重过期.append(r)

    报告内容 += f"""
| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 新鲜 | {新鲜数} | {新鲜数/总文件数*100:.1f}% |
| ⚠️ 警告 | {警告数} | {警告数/总文件数*100:.1f}% |
| 🚨 过期 | {过期数} | {过期数/总文件数*100:.1f}% |

**总体状态**: {'✅ 数据新鲜' if 过期数 == 0 else '⚠️ 需要更新' if 过期数 <= 3 else '🚨 严重过期，必须立即更新'}

---

## 🚨 严重过期数据（影响报告准确性）

"""

    if 严重过期:
        报告内容 += "| 文件 | 最后更新 | 已过期 | 影响 | 建议动作 |\n"
        报告内容 += "|------|----------|--------|------|----------|\n"
        for r in 严重过期:
            过期天数 = r['天数'] - r['阈值']
            影响 = '股价数据可能偏差20%+' if 'valuation' in r['文件'] else '催化剂时间可能已过期'
            建议 = '立即运行 update_data.py' if 'valuation' in r['文件'] else '人工检查更新'
            报告内容 += f"| {r['文件']} | {r['最后更新']} | {过期天数}天 | {影响} | {建议} |\n"
    else:
        报告内容 += "✅ 无严重过期数据\n"

    报告内容 += """

---

## 详细检查结果

"""

    for 主题, 结果列表 in 所有主题结果.items():
        报告内容 += f"\n### {主题}\n\n"
        报告内容 += "| 文件 | 最后更新 | 天数 | 状态 | 说明 |\n"
        报告内容 += "|------|----------|------|------|------|\n"

        for r in 结果列表:
            报告内容 += f"| {r['文件']} | {r['最后更新']} | {r['天数']} | {r['状态']} | {r['说明']} |\n"

    报告内容 += f"""

---

## 更新建议

### 立即执行（影响报告准确性）

```bash
# 更新股价数据（最关键）
python update_data.py

# 更新后重新检查
python check_freshness.py
```

### 本周内执行

```bash
# 健康检查（同时更新评分）
python maintenance.py --review monthly
```

### 本月内执行

- 检查 catalysts.yaml 中的事件时间是否过期
- 更新 core_logic/*.md 中的财务数据
- 检查 ETF 权重是否有变化

---

## 如何避免过时数据

### 最佳实践

1. **每次生成报告前**，先运行 `python check_freshness.py`
2. **看到 🚨 立即更新**，不要基于过期数据做决策
3. **设置提醒**：
   - 每周一：运行 update_data.py
   - 每月初：运行 check_freshness.py --report

### 数据更新优先级

| 优先级 | 文件 | 更新频率 | 影响 |
|--------|------|----------|------|
| 🔴 P0 | valuation.yaml | 每周 | 股价偏差直接影响估值 |
| 🟡 P1 | catalysts.yaml | 每两周 | 事件时间影响投资决策 |
| 🟢 P2 | core_logic/*.md | 每季度 | 基本面分析长期有效 |
| 🟢 P3 | tickers.yaml | 按需 | 公司信息相对稳定 |

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

    REPORTS_DIR.mkdir(exist_ok=True)
    with open(报告路径, 'w', encoding='utf-8') as f:
        f.write(报告内容)

    print(f"\n✅ 新鲜度报告已保存: {报告路径}")
    return 报告路径


def 主函数():
    """主入口"""
    args = sys.argv[1:]

    指定主题 = None
    生成报告 = '--report' in args

    if '--theme' in args:
        idx = args.index('--theme')
        if idx + 1 < len(args):
            指定主题 = args[idx + 1]

    print("🔍 Investment Skill 数据新鲜度检查")
    print(f"   检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   数据目录: {DATA_DIR}")

    所有主题结果 = {}

    if 指定主题:
        结果 = 检查主题数据(指定主题)
        if 结果:
            所有主题结果[指定主题] = 结果
    else:
        # 检查所有主题
        for 主题路径 in DATA_DIR.iterdir():
            if 主题路径.is_dir() and (主题路径 / 'tickers.yaml').exists():
                结果 = 检查主题数据(主题路径.name)
                if 结果:
                    所有主题结果[主题路径.name] = 结果

    # 检查是否有过期数据
    有过期 = False
    严重过期数 = 0

    for 主题, 结果列表 in 所有主题结果.items():
        for r in 结果列表:
            if '⚠️' in r['状态'] or '🚨' in r['状态']:
                有过期 = True
            if '🚨' in r['状态']:
                严重过期数 += 1

    print(f"\n{'='*60}")
    if 有过期:
        print("⚠️  发现过期数据，建议立即更新")
        print(f"   严重过期: {严重过期数} 个文件")
    else:
        print("✅ 所有数据新鲜，可以生成报告")
    print(f"{'='*60}")

    # 生成报告
    if 生成报告 or 严重过期数 > 0:
        报告路径 = 生成新鲜度报告(所有主题结果)

        if 严重过期数 > 0:
            print(f"\n🚨 警告: 有 {严重过期数} 个文件严重过期")
            print("   请立即运行: python update_data.py")
            print(f"   详细报告: {报告路径}")
            sys.exit(1)  # 返回错误码，阻止报告生成

    return 0 if not 有过期 else 1


if __name__ == '__main__':
    exit(主函数())
