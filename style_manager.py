#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风格管理器 (Style Manager)

功能：
1. 管理配置值到风格文件的映射
2. 加载风格指南内容
3. 提取风格关键要求（语气、句式、结构）
4. 为Agent生成风格指令

用法：
    from style_manager import StyleManager

    sm = StyleManager()
    style_guide = sm.get_style_guide("专业投研风")
    agent_instructions = sm.get_agent_style_instructions("专业投研风", depth="L2")
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class StyleProfile:
    """风格配置"""
    name: str
    file_name: str
    positioning: str
    best_depths: List[str]
    tone: str
    sentence_pattern: str
    structure: str
    min_dimensions: int
    maxLength: Optional[int] = None


class StyleManager:
    """风格管理器"""

    # 配置值到文件名的映射（支持多种写法）
    STYLE_MAPPING = {
        # 专业投行/投研类
        "专业投行风": "专业投行风.md",
        "专业投研风": "专业投行风.md",  # 映射到同一个文件
        "投研风": "专业投行风.md",
        "投行风": "专业投行风.md",

        # 科普类
        "散户科普风": "散户科普风.md",
        "科普风": "散户科普风.md",
        "口语化风": "口语化风.md",

        # PPT类
        "路演PPT风": "路演PPT风.md",
        "PPT风": "路演PPT风.md",
        "路演风": "路演PPT风.md",

        # 社交媒体类
        "社交媒体风": "社交媒体风.md",
        "社媒风": "社交媒体风.md",
        "微博风": "社交媒体风.md",
        "朋友圈风": "社交媒体风.md",

        # 新闻类
        "新闻快讯风": "新闻快讯风.md",
        "新闻风": "新闻快讯风.md",
        "快讯风": "新闻快讯风.md",

        # 内部类
        "内部备忘录风": "内部备忘录风.md",
        "备忘录风": "内部备忘录风.md",
        "内部风": "内部备忘录风.md",

        # 学术类
        "学术论文风": "学术论文风.md",
        "学术风": "学术论文风.md",
        "论文风": "学术论文风.md",

        # 叙事类
        "故事叙事风": "故事叙事风.md",
        "故事风": "故事叙事风.md",
        "叙事风": "故事叙事风.md",

        # FAQ类
        "FAQ问答风": "FAQ问答风.md",
        "问答风": "FAQ问答风.md",
        "FAQ风": "FAQ问答风.md",

        # 对比类
        "对比分析风": "对比分析风.md",
        "对比风": "对比分析风.md",
        "分析风": "对比分析风.md",
    }

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.styles_dir = self.project_root / "styles"
        self._style_cache: Dict[str, str] = {}
        self._profile_cache: Dict[str, StyleProfile] = {}

    def resolve_style_file(self, style_name: str) -> Optional[str]:
        """
        解析风格名称到文件路径

        Args:
            style_name: 配置中的风格名称（如"专业投研风"）

        Returns:
            文件路径或None
        """
        # 1. 直接查映射表
        if style_name in self.STYLE_MAPPING:
            file_name = self.STYLE_MAPPING[style_name]
            file_path = self.styles_dir / file_name
            if file_path.exists():
                return str(file_path)

        # 2. 尝试直接匹配文件（加.md后缀）
        direct_path = self.styles_dir / f"{style_name}.md"
        if direct_path.exists():
            return str(direct_path)

        # 3. 尝试模糊匹配（去掉"风"字）
        if style_name.endswith("风"):
            base_name = style_name[:-1]
            for mapped_name, file_name in self.STYLE_MAPPING.items():
                if base_name in mapped_name or mapped_name.replace("风", "") in base_name:
                    file_path = self.styles_dir / file_name
                    if file_path.exists():
                        return str(file_path)

        # 4. 默认回退到专业投行风
        default_path = self.styles_dir / "专业投行风.md"
        if default_path.exists():
            print(f"[StyleManager] 警告: 未找到风格'{style_name}'，使用默认风格")
            return str(default_path)

        return None

    def load_style_guide(self, style_name: str) -> str:
        """
        加载风格指南内容

        Args:
            style_name: 风格名称

        Returns:
            风格指南完整内容
        """
        # 缓存检查
        if style_name in self._style_cache:
            return self._style_cache[style_name]

        file_path = self.resolve_style_file(style_name)
        if not file_path:
            return self._get_default_style_guide()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self._style_cache[style_name] = content
                return content
        except Exception as e:
            print(f"[StyleManager] 错误: 无法加载风格文件: {e}")
            return self._get_default_style_guide()

    def parse_style_profile(self, style_name: str) -> StyleProfile:
        """
        解析风格配置文件，提取关键属性

        Args:
            style_name: 风格名称

        Returns:
            StyleProfile对象
        """
        if style_name in self._profile_cache:
            return self._profile_cache[style_name]

        content = self.load_style_guide(style_name)

        # 解析 frontmatter（如果有）
        profile = StyleProfile(
            name=style_name,
            file_name=self.resolve_style_file(style_name) or "",
            positioning="",
            best_depths=[],
            tone="",
            sentence_pattern="",
            structure="",
            min_dimensions=6
        )

        # 提取定位
        pos_match = re.search(r'## 定位\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if pos_match:
            profile.positioning = pos_match.group(1).strip()

        # 提取最佳深度
        depth_match = re.search(r'## 篇幅匹配\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if depth_match:
            depth_text = depth_match.group(1)
            # 提取 ✅ 最适合 或 ⚠️ 勉强可接受 或 ❌ 完全不推荐
            if 'L0' in depth_text and ('✅' in depth_text or '适合' in depth_text):
                profile.best_depths.append('L0')
            if 'L1' in depth_text and ('✅' in depth_text or '适合' in depth_text):
                profile.best_depths.append('L1')
            if 'L2' in depth_text and ('✅' in depth_text or '适合' in depth_text):
                profile.best_depths.append('L2')
            if 'L3' in depth_text and ('✅' in depth_text or '适合' in depth_text):
                profile.best_depths.append('L3')
            if 'L4' in depth_text and ('✅' in depth_text or '适合' in depth_text):
                profile.best_depths.append('L4')

        # 提取语气特征
        tone_match = re.search(r'## 语气特征\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if tone_match:
            profile.tone = tone_match.group(1).strip()

        # 提取句式特征
        sent_match = re.search(r'## 句式特征\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if sent_match:
            profile.sentence_pattern = sent_match.group(1).strip()

        # 提取结构特征
        struct_match = re.search(r'## 结构特征\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if struct_match:
            profile.structure = struct_match.group(1).strip()

        # 提取最小维度要求
        dim_match = re.search(r'## 禁用\s*\n.*?维度太少.*?至少(\d+)个', content, re.DOTALL)
        if dim_match:
            profile.min_dimensions = int(dim_match.group(1))

        self._profile_cache[style_name] = profile
        return profile

    def get_agent_style_instructions(self, style_name: str, depth: str = "L3") -> str:
        """
        为Agent生成风格指令

        Args:
            style_name: 风格名称
            depth: 报告深度（L0-L4）

        Returns:
            Agent风格指令
        """
        profile = self.parse_style_profile(style_name)
        content = self.load_style_guide(style_name)

        # 提取关键部分
        instructions = f"""## 写作风格要求

**风格名称**: {style_name}
**风格定位**: {profile.positioning or '专业投资分析'}

### 语气要求
{profile.tone or '- 专业、客观、理性'}

### 句式要求
{profile.sentence_pattern or '- 清晰简洁，避免冗长'}

### 结构要求
{profile.structure or '- 按模块模板结构输出'}

### 深度适配
当前报告深度: **{depth}**
"""

        # 添加深度特定的要求
        depth_specific = self._get_depth_specific_requirements(style_name, depth)
        if depth_specific:
            instructions += f"\n### 深度特定要求\n{depth_specific}\n"

        # 提取禁用事项
        forbidden_match = re.search(r'## 禁用\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if forbidden_match:
            instructions += f"\n### 禁用事项（必须遵守）\n{forbidden_match.group(1).strip()}\n"

        # 提取必用结构
        required_match = re.search(r'## 必用结构\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if required_match:
            instructions += f"\n### 必用结构（必须包含）\n{required_match.group(1).strip()}\n"

        return instructions

    def _get_depth_specific_requirements(self, style_name: str, depth: str) -> str:
        """获取深度特定要求"""
        content = self.load_style_guide(style_name)

        # 查找篇幅标准表格
        length_match = re.search(r'## 篇幅标准\s*\n\|[^\n]+\|[^\n]+\|[^\n]+\|[^\n]+\|\n\|[-:\s\|]+\|[^\n]*\n((?:\|[^\n]+\|[^\n]+\|[^\n]+\|[^\n]+\|[^\n]*\n)+)', content)

        requirements = []

        if length_match:
            table_content = length_match.group(1)
            for line in table_content.strip().split('\n'):
                if depth in line:
                    # 解析该行
                    cols = [c.strip() for c in line.split('|')]
                    if len(cols) >= 4:
                        requirements.append(f"- 字数要求: {cols[3]}")

        # 根据风格添加特定要求
        style_requirements = {
            "社交媒体风": {
                "L0": "- 使用emoji表情\n- 15-30字\n- 带话题标签",
                "L1": "- 多用emoji\n- 300-500字\n- 短句为主\n- 易转发"
            },
            "新闻快讯风": {
                "L0": "- 一句话快讯\n- 5W1H要素\n- 客观陈述",
                "L1": "- 倒金字塔结构\n- 300-600字\n- 引用信源"
            },
            "内部备忘录风": {
                "L1": "- TO/FROM/DATE/RE\n- 结论先行\n- Bullet points为主",
                "L2": "- 带责任人DDL\n- checkbox行动项\n- 800-1200字"
            },
            "学术论文风": {
                "L3": "- 完整6章结构\n- 方法论章节\n- 8000-15000字",
                "L4": "- 参考文献\n- 稳健性检验\n- 20000字+"
            },
            "FAQ问答风": {
                "L1": "- 3-5个问题\n- 由浅入深\n- 50-100字/答案",
                "L2": "- 8-12个问题\n- 100-200字/答案"
            },
            "对比分析风": {
                "L2": "- 6-10个对比维度\n- 并排对比表\n- 综合评分表"
            }
        }

        # 查找匹配的风格要求
        for style_key, depths in style_requirements.items():
            if style_key in style_name or style_name in style_key:
                if depth in depths:
                    requirements.append(depths[depth])
                break

        return '\n'.join(requirements) if requirements else ""

    def _get_default_style_guide(self) -> str:
        """默认风格指南"""
        return """## 定位
专业投资分析风格

## 语气特征
- 专业、客观、理性
- 基于数据和逻辑
- 明确给出结论

## 句式特征
- 简洁清晰
- 避免口语化
- 多用数据和指标

## 结构特征
- 按模块模板结构
- 表格优先
- 层次分明
"""

    def validate_style_depth(self, style_name: str, depth: str) -> Tuple[bool, str]:
        """
        验证风格是否适合指定深度

        Returns:
            (是否适合, 建议信息)
        """
        content = self.load_style_guide(style_name)

        # 查找篇幅匹配部分
        depth_section = re.search(r'## 篇幅匹配\s*\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
        if not depth_section:
            return True, "未找到深度匹配信息"

        depth_text = depth_section.group(1)
        depth_line = None

        for line in depth_text.split('\n'):
            if depth in line:
                depth_line = line
                break

        if not depth_line:
            return True, f"未找到{depth}的配置"

        if '❌' in depth_line or '完全不推荐' in depth_line:
            return False, f"❌ 风格'{style_name}'完全不推荐用于{depth}深度"
        elif '⚠️' in depth_line or '勉强' in depth_line:
            return True, f"⚠️ 风格'{style_name}'用于{depth}深度效果可能不佳"
        elif '✅' in depth_line:
            if '最适合' in depth_line or '次适合' in depth_line:
                return True, f"✅ 风格'{style_name}'非常适合{depth}深度"
            else:
                return True, f"✅ 风格'{style_name}'适合{depth}深度"

        return True, "配置不明确"

    def list_available_styles(self) -> List[Dict]:
        """列出所有可用风格"""
        styles = []
        for style_file in self.styles_dir.glob("*.md"):
            if style_file.name == "风格选择指南.md":
                continue
            style_name = style_file.stem
            profile = self.parse_style_profile(style_name)
            styles.append({
                "name": style_name,
                "positioning": profile.positioning,
                "best_depths": profile.best_depths,
                "file": str(style_file)
            })
        return styles


def main():
    """命令行测试"""
    sm = StyleManager()

    print("=" * 60)
    print("风格管理器测试")
    print("=" * 60)

    # 测试加载风格
    test_styles = [
        "专业投研风",
        "社交媒体风",
        "内部备忘录风",
        "学术论文风",
        "FAQ问答风"
    ]

    for style in test_styles:
        print(f"\n{'='*60}")
        print(f"测试风格: {style}")
        print('='*60)

        # 验证风格和深度
        for depth in ['L0', 'L1', 'L2', 'L3', 'L4']:
            ok, msg = sm.validate_style_depth(style, depth)
            print(f"  {depth}: {msg}")

        # 生成Agent指令
        instructions = sm.get_agent_style_instructions(style, depth='L2')
        print(f"\nAgent指令预览 (前500字符):")
        print(instructions[:500] + "...")


if __name__ == '__main__':
    main()
