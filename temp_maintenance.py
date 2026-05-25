#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
临时文件维护脚本 (Temp Maintenance)

功能：
1. 清理过期的临时文件
2. 归档历史执行记录
3. 列出所有执行记录
4. 验证执行记录完整性

用法：
    python temp_maintenance.py --cleanup --days 7      # 清理7天前的临时文件
    python temp_maintenance.py --archive --days 30   # 归档30天前的记录
    python temp_maintenance.py --list                # 列出所有执行记录
    python temp_maintenance.py --verify <execution_id> # 验证执行记录
"""

import os
import sys
import shutil
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional


def parse_execution_dir_name(dir_name: str) -> Optional[Tuple[str, datetime]]:
    """
    解析执行目录名

    Args:
        dir_name: 目录名 (如: physical_ai_20260524_221530_a3f2b1c8)

    Returns:
        (theme, timestamp) 或 None
    """
    parts = dir_name.split('_')
    if len(parts) < 4:
        return None

    try:
        # 主题可能是多段的 (如: sun_ge_direction)
        theme_parts = []
        date_idx = -1
        for i, part in enumerate(parts):
            if len(part) == 8 and part.isdigit():  # YYYYMMDD
                date_idx = i
                break
            theme_parts.append(part)

        if date_idx == -1 or date_idx + 2 > len(parts):
            return None

        theme = '_'.join(theme_parts)
        date_str = parts[date_idx]
        time_str = parts[date_idx + 1]

        timestamp = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
        return theme, timestamp
    except (ValueError, IndexError):
        return None


def cleanup_temp_files(project_root: Path, days: int = 7, dry_run: bool = False) -> dict:
    """
    清理过期的临时文件

    Args:
        project_root: 项目根目录
        days: 保留天数
        dry_run: 仅预览不执行

    Returns:
        统计信息
    """
    temp_base = project_root / ".agent_temp"
    if not temp_base.exists():
        return {"cleaned": 0, "skipped": 0, "errors": 0, "total_size": 0}

    cutoff_date = datetime.now() - timedelta(days=days)

    stats = {"cleaned": 0, "skipped": 0, "errors": 0, "total_size": 0}

    print(f"[TempMaintenance] 清理 {days} 天前的临时文件...")
    print(f"  截止日期: {cutoff_date.strftime('%Y-%m-%d')}")
    print(f"  模式: {'预览' if dry_run else '执行'}\n")

    for item in temp_base.iterdir():
        if not item.is_dir():
            continue

        parsed = parse_execution_dir_name(item.name)
        if not parsed:
            print(f"  [跳过] 无法解析: {item.name}")
            stats["skipped"] += 1
            continue

        theme, timestamp = parsed

        if timestamp < cutoff_date:
            # 计算目录大小
            dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())

            if dry_run:
                print(f"  [预览] 将删除: {item.name}")
                print(f"         主题: {theme}, 时间: {timestamp.strftime('%Y-%m-%d %H:%M')}")
                print(f"         大小: {dir_size / 1024 / 1024:.2f} MB")
            else:
                try:
                    shutil.rmtree(item)
                    print(f"  [已删除] {item.name} ({dir_size / 1024 / 1024:.2f} MB)")
                    stats["total_size"] += dir_size
                    stats["cleaned"] += 1
                except Exception as e:
                    print(f"  [错误] 无法删除 {item.name}: {e}")
                    stats["errors"] += 1
        else:
            print(f"  [保留] {item.name} ({theme}, {timestamp.strftime('%Y-%m-%d')})")
            stats["skipped"] += 1

    return stats


def archive_executions(project_root: Path, days: int = 30) -> Optional[Path]:
    """
    归档历史执行记录

    Args:
        project_root: 项目根目录
        days: 归档多少天前的记录

    Returns:
        归档文件路径
    """
    temp_base = project_root / ".agent_temp"
    archive_dir = project_root / ".agent_temp_archive"

    if not temp_base.exists():
        return None

    archive_dir.mkdir(exist_ok=True)

    cutoff_date = datetime.now() - timedelta(days=days)
    archive_file = archive_dir / f"executions_{datetime.now().strftime('%Y%m%d')}.zip"

    print(f"[TempMaintenance] 归档 {days} 天前的执行记录...")
    print(f"  目标: {archive_file}\n")

    archived_count = 0

    with zipfile.ZipFile(archive_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in temp_base.iterdir():
            if not item.is_dir():
                continue

            parsed = parse_execution_dir_name(item.name)
            if not parsed:
                continue

            _, timestamp = parsed

            if timestamp < cutoff_date:
                # 压缩整个目录
                for file in item.rglob('*'):
                    if file.is_file():
                        arcname = f"{item.name}/{file.relative_to(item)}"
                        zf.write(file, arcname)

                archived_count += 1
                print(f"  [归档] {item.name}")

    if archived_count == 0:
        archive_file.unlink()  # 删除空归档
        print("  没有需要归档的记录")
        return None

    print(f"\n  已归档 {archived_count} 个执行记录")
    print(f"  归档文件: {archive_file}")
    print(f"  大小: {archive_file.stat().st_size / 1024 / 1024:.2f} MB")

    return archive_file


def list_executions(project_root: Path, theme: Optional[str] = None, limit: int = 20) -> List[Tuple[str, datetime, Path]]:
    """
    列出执行记录

    Args:
        project_root: 项目根目录
        theme: 主题筛选
        limit: 返回数量限制

    Returns:
        [(execution_id, timestamp, path), ...]
    """
    temp_base = project_root / ".agent_temp"
    if not temp_base.exists():
        return []

    executions = []

    for item in temp_base.iterdir():
        if not item.is_dir():
            continue

        parsed = parse_execution_dir_name(item.name)
        if not parsed:
            continue

        dir_theme, timestamp = parsed

        if theme and dir_theme != theme.replace("/", "_").replace(" ", "_").replace("-", "_"):
            continue

        executions.append((item.name, timestamp, item))

    # 按时间倒序
    executions.sort(key=lambda x: x[1], reverse=True)

    return executions[:limit]


def verify_execution(project_root: Path, execution_id: str) -> dict:
    """
    验证执行记录的完整性

    Args:
        project_root: 项目根目录
        execution_id: 执行ID

    Returns:
        验证结果
    """
    temp_dir = project_root / ".agent_temp" / execution_id

    result = {
        "exists": temp_dir.exists(),
        "execution_id": execution_id,
        "outputs": 0,
        "instructions": 0,
        "metadata": False,
        "missing_agents": []
    }

    if not temp_dir.exists():
        return result

    # 检查元数据
    metadata_file = temp_dir / "_metadata.yaml"
    result["metadata"] = metadata_file.exists()

    # 统计文件
    for file in temp_dir.glob("*_output.md"):
        result["outputs"] += 1

    for file in temp_dir.glob("*_instructions.md"):
        result["instructions"] += 1

    # 检查期望的Agent输出
    expected_agents = [
        "00-市场情绪分析Agent", "01-市场环境扫描Agent", "02-核心投资哲学Agent",
        "03-产业链拆解Agent", "04-铲子股筛选Agent", "05-护城河评估Agent",
        "06-催化剂日历Agent", "07-中美对比矩阵Agent", "08-风险矩阵与对冲Agent",
        "09-组合构建Agent", "10-实操指南Agent", "11-动态跟踪机制Agent",
        "12-预测与实际对比Agent", "13-ETF备选与核心逻辑Agent",
        "14-深度核心逻辑摘要Agent", "15-产业链全景图谱Agent", "16-供应链分析Agent"
    ]

    for agent in expected_agents:
        output_file = temp_dir / f"{agent}_output.md"
        if not output_file.exists():
            result["missing_agents"].append(agent)

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description='临时文件维护脚本')
    parser.add_argument('--cleanup', action='store_true', help='清理过期临时文件')
    parser.add_argument('--days', type=int, default=7, help='保留天数（默认7天）')
    parser.add_argument('--dry-run', action='store_true', help='预览模式（不实际删除）')
    parser.add_argument('--archive', action='store_true', help='归档历史执行记录')
    parser.add_argument('--archive-days', type=int, default=30, help='归档多少天前的记录')
    parser.add_argument('--list', action='store_true', help='列出执行记录')
    parser.add_argument('--theme', type=str, help='主题筛选')
    parser.add_argument('--limit', type=int, default=20, help='列出数量限制')
    parser.add_argument('--verify', type=str, help='验证指定执行ID的完整性')
    parser.add_argument('--project-root', type=str, default='.', help='项目根目录')

    args = parser.parse_args()

    project_root = Path(args.project_root)

    if args.cleanup:
        stats = cleanup_temp_files(project_root, args.days, args.dry_run)
        print(f"\n[TempMaintenance] 清理完成:")
        print(f"  已清理: {stats['cleaned']} 个目录")
        print(f"  已跳过: {stats['skipped']} 个目录")
        print(f"  错误: {stats['errors']} 个")
        if stats['total_size'] > 0:
            print(f"  释放空间: {stats['total_size'] / 1024 / 1024:.2f} MB")

    elif args.archive:
        archive_file = archive_executions(project_root, args.archive_days)
        if archive_file:
            print(f"\n[TempMaintenance] 归档完成: {archive_file}")

    elif args.list:
        executions = list_executions(project_root, args.theme, args.limit)
        if not executions:
            print("[TempMaintenance] 没有找到执行记录")
            return

        print(f"[TempMaintenance] 执行记录列表 ({len(executions)} 条):\n")
        print(f"{'执行ID':<50} {'主题':<20} {'时间':<20}")
        print("-" * 90)

        for exec_id, timestamp, path in executions:
            theme = exec_id.split('_')[0] if '_' in exec_id else 'unknown'
            time_str = timestamp.strftime('%Y-%m-%d %H:%M')
            print(f"{exec_id:<50} {theme:<20} {time_str:<20}")

    elif args.verify:
        result = verify_execution(project_root, args.verify)
        print(f"[TempMaintenance] 验证结果:\n")
        print(f"  执行ID: {result['execution_id']}")
        print(f"  目录存在: {'是' if result['exists'] else '否'}")
        print(f"  元数据: {'有' if result['metadata'] else '无'}")
        print(f"  输出文件: {result['outputs']}")
        print(f"  指令文件: {result['instructions']}")

        if result['missing_agents']:
            print(f"\n  缺失的Agent ({len(result['missing_agents'])} 个):")
            for agent in result['missing_agents']:
                print(f"    - {agent}")
        else:
            print(f"\n  所有Agent输出完整")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
