"""
模块独立性测试脚本
验证删除任一模块后，其他模块仍能正常运行

用法:
    python check_module_independence.py                    # 测试所有模块
    python check_module_independence.py --exclude 15-产业链全景图谱  # 测试删除特定模块
    python check_module_independence.py --check-links      # 检查模块间交叉引用
"""

import os
import sys
import re
import yaml
from pathlib import Path
from typing import List, Dict, Set, Tuple


class ModuleIndependenceChecker:
    """模块独立性检查器"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.modules_dir = self.project_root / "modules"
        self.config_file = self.project_root / "config.yaml"
        self.dependency_rules_file = self.project_root / "dependency-rules.yaml"

        self.modules: Dict[str, Dict] = {}
        self.config: Dict = {}
        self.dependency_rules: Dict = {}

    def load_config(self) -> bool:
        """加载主配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            return True
        except Exception as e:
            print(f"❌ 无法加载config.yaml: {e}")
            return False

    def load_dependency_rules(self) -> bool:
        """加载依赖规则文件"""
        try:
            with open(self.dependency_rules_file, 'r', encoding='utf-8') as f:
                self.dependency_rules = yaml.safe_load(f)
            return True
        except Exception as e:
            print(f"⚠️ 无法加载dependency-rules.yaml: {e}")
            self.dependency_rules = {}
            return False

    def parse_module_frontmatter(self, file_path: Path) -> Dict:
        """解析模块文件的frontmatter"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 提取frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2]
                    return {
                        'frontmatter': frontmatter or {},
                        'body': body,
                        'file': file_path.name
                    }
            return {'frontmatter': {}, 'body': content, 'file': file_path.name}
        except Exception as e:
            print(f"⚠️ 无法解析 {file_path}: {e}")
            return {'frontmatter': {}, 'body': '', 'file': file_path.name}

    def load_all_modules(self) -> None:
        """加载所有模块"""
        if not self.modules_dir.exists():
            print(f"❌ 模块目录不存在: {self.modules_dir}")
            return

        for md_file in self.modules_dir.glob("*.md"):
            module_name = md_file.stem
            # 跳过模板文件
            if module_name == "00-模板":
                continue

            module_data = self.parse_module_frontmatter(md_file)
            self.modules[module_name] = module_data

        print(f"✅ 加载了 {len(self.modules)} 个模块")

    def check_frontmatter_completeness(self) -> List[str]:
        """检查frontmatter完整性"""
        issues = []
        required_fields = ['module', 'version', 'description', 'dependencies']
        optional_fields = ['last_updated', 'data_access', 'interface']

        for module_name, module_data in self.modules.items():
            fm = module_data.get('frontmatter', {})

            # 检查必需字段
            for field in required_fields:
                if field not in fm:
                    issues.append(f"❌ {module_name}: 缺少必需字段 '{field}'")

            # 警告可选字段
            for field in optional_fields:
                if field not in fm:
                    issues.append(f"⚠️  {module_name}: 建议添加字段 '{field}'")

        return issues

    def check_implicit_dependencies(self) -> List[str]:
        """检查隐式依赖（模块内容中直接引用其他模块）"""
        issues = []
        module_names = set(self.modules.keys())

        # 定义隐式引用模式
        reference_patterns = [
            r'如[\s]*([^\s]+模块|[^\s]+层)[\s]*所述',  # "如XX模块所述"
            r'参见[\s]*([^\s]+模块|[^\s]+层)',       # "参见XX模块"
            r'来自[\s]*([^\s]+模块|[^\s]+层)',        # "来自XX模块"
            r'根据[\s]*([^\s]+模块|[^\s]+层)',        # "根据XX模块"
        ]

        for module_name, module_data in self.modules.items():
            body = module_data.get('body', '')
            declared_deps = module_data.get('frontmatter', {}).get('dependencies', [])

            for pattern in reference_patterns:
                matches = re.finditer(pattern, body, re.IGNORECASE)
                for match in matches:
                    referenced = match.group(1)
                    # 检查是否是模块引用
                    for other_module in module_names:
                        if other_module in referenced and other_module != module_name:
                            # 检查是否已声明依赖
                            if other_module not in declared_deps:
                                issues.append(
                                    f"⚠️  {module_name}: 隐式引用 '{other_module}' 但未在dependencies中声明"
                                )

        return issues

    def check_data_isolation(self) -> List[str]:
        """检查数据隔离（模块是否只访问声明的数据）"""
        issues = []

        for module_name, module_data in self.modules.items():
            fm = module_data.get('frontmatter', {})
            body = module_data.get('body', '')

            # 检查是否声明了data_access
            data_access = fm.get('data_access', {})
            declared_reads = set(data_access.get('reads', []))

            # 在内容中查找数据文件引用
            data_file_patterns = [
                r'valuation\.yaml',
                r'tickers\.yaml',
                r'catalysts\.yaml',
                r'etfs\.yaml',
            ]

            for pattern in data_file_patterns:
                if re.search(pattern, body):
                    file_name = pattern.replace(r'\.', '.')
                    # 检查是否已声明
                    if not any(file_name in declared for declared in declared_reads):
                        issues.append(
                            f"⚠️  {module_name}: 使用数据文件 '{file_name}' 但未在data_access.reads中声明"
                        )

        return issues

    def check_module_deletion_impact(self, exclude_module: str) -> Tuple[bool, List[str]]:
        """检查删除某个模块后的影响"""
        issues = []

        # 找到依赖该模块的其他模块
        for module_name, module_data in self.modules.items():
            if module_name == exclude_module:
                continue

            deps = module_data.get('frontmatter', {}).get('dependencies', [])
            if exclude_module in deps:
                issues.append(
                    f"❌ 删除 {exclude_module} 会导致 {module_name} 无法运行（依赖未满足）"
                )

        # 检查dependency-rules.yaml
        if self.dependency_rules:
            requires = self.dependency_rules.get('requires', [])
            for rule in requires:
                before = rule.get('before', '')
                after = rule.get('after', '')
                if exclude_module == after:
                    issues.append(
                        f"❌ 删除 {exclude_module} 违反依赖规则: {before} 依赖它"
                    )

        return len(issues) == 0, issues

    def check_cross_references(self) -> List[str]:
        """检查模块间的交叉引用是否通过接口"""
        issues = []

        for module_name, module_data in self.modules.items():
            fm = module_data.get('frontmatter', {})
            interface = fm.get('interface', {})

            # 检查是否声明了输入输出接口
            if not interface:
                issues.append(
                    f"⚠️  {module_name}: 未声明interface（input/output），建议添加"
                )
            else:
                if 'input' not in interface:
                    issues.append(f"⚠️  {module_name}: 未声明interface.input")
                if 'output' not in interface:
                    issues.append(f"⚠️  {module_name}: 未声明interface.output")

        return issues

    def generate_impact_matrix(self) -> Dict[str, Dict]:
        """生成模块删除影响矩阵"""
        matrix = {}

        for module_name in self.modules.keys():
            can_delete, issues = self.check_module_deletion_impact(module_name)

            # 计算风险等级
            risk_level = "🟢 低"
            if not can_delete:
                risk_level = "🔴 高"
            elif any("隐式引用" in i for i in issues):
                risk_level = "🟡 中"

            matrix[module_name] = {
                'can_delete': can_delete,
                'direct_impact': len([i for i in issues if '删除' in i]),
                'indirect_impact': len([i for i in issues if '依赖' in i]),
                'risk_level': risk_level,
                'issues': issues
            }

        return matrix

    def print_report(self, impact_matrix: Dict = None) -> None:
        """打印测试报告"""
        print("\n" + "=" * 60)
        print("模块独立性测试报告")
        print("=" * 60)

        # Frontmatter检查
        print("\n## 1. Frontmatter完整性检查")
        frontmatter_issues = self.check_frontmatter_completeness()
        if frontmatter_issues:
            for issue in frontmatter_issues:
                print(f"  {issue}")
        else:
            print("  ✅ 所有模块frontmatter完整")

        # 隐式依赖检查
        print("\n## 2. 隐式依赖检查")
        implicit_issues = self.check_implicit_dependencies()
        if implicit_issues:
            for issue in implicit_issues:
                print(f"  {issue}")
        else:
            print("  ✅ 未发现隐式依赖")

        # 数据隔离检查
        print("\n## 3. 数据隔离检查")
        data_issues = self.check_data_isolation()
        if data_issues:
            for issue in data_issues:
                print(f"  {issue}")
        else:
            print("  ✅ 数据访问边界清晰")

        # 接口声明检查
        print("\n## 4. 接口声明检查")
        interface_issues = self.check_cross_references()
        if interface_issues:
            for issue in interface_issues:
                print(f"  {issue}")
        else:
            print("  ✅ 所有模块声明了输入输出接口")

        # 删除影响矩阵
        if impact_matrix:
            print("\n## 5. 模块删除影响矩阵")
            print(f"\n  {'模块':<25} {'风险等级':<10} {'直接影响':<10} {'间接影响':<10}")
            print("  " + "-" * 60)
            for module_name, data in sorted(impact_matrix.items()):
                print(f"  {module_name:<25} {data['risk_level']:<10} {data['direct_impact']:<10} {data['indirect_impact']:<10}")

        print("\n" + "=" * 60)

    def run_all_tests(self, exclude_module: str = None) -> bool:
        """运行所有测试"""
        print(f"开始模块独立性测试...")
        print(f"项目根目录: {self.project_root.absolute()}")

        # 加载配置
        if not self.load_config():
            return False

        self.load_dependency_rules()
        self.load_all_modules()

        if not self.modules:
            print("❌ 未找到任何模块")
            return False

        # 如果指定了排除模块，只测试该模块
        if exclude_module:
            print(f"\n测试删除模块: {exclude_module}")
            can_delete, issues = self.check_module_deletion_impact(exclude_module)

            if can_delete:
                print(f"✅ 可以安全删除 {exclude_module}")
                return True
            else:
                print(f"❌ 删除 {exclude_module} 存在风险:")
                for issue in issues:
                    print(f"  - {issue}")
                return False

        # 运行完整测试
        impact_matrix = self.generate_impact_matrix()
        self.print_report(impact_matrix)

        # 统计问题数量
        total_issues = (
            len(self.check_frontmatter_completeness()) +
            len(self.check_implicit_dependencies()) +
            len(self.check_data_isolation()) +
            len(self.check_cross_references())
        )

        # 检查是否有高风险模块
        high_risk_modules = [
            m for m, d in impact_matrix.items()
            if d['risk_level'] == "🔴 高"
        ]

        print(f"\n## 总结")
        print(f"  - 发现问题数: {total_issues}")
        print(f"  - 高风险模块数: {len(high_risk_modules)}")

        if high_risk_modules:
            print(f"  - 高风险模块: {', '.join(high_risk_modules)}")

        if total_issues == 0 and not high_risk_modules:
            print("\n✅ 所有模块独立性测试通过！")
            return True
        else:
            print("\n⚠️ 存在模块化问题，建议修复")
            return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description='模块独立性测试工具')
    parser.add_argument('--exclude', type=str, help='测试删除指定模块')
    parser.add_argument('--check-links', action='store_true', help='只检查模块间链接')
    parser.add_argument('--project-root', type=str, default='.', help='项目根目录')

    args = parser.parse_args()

    checker = ModuleIndependenceChecker(args.project_root)

    if args.check_links:
        checker.load_config()
        checker.load_dependency_rules()
        checker.load_all_modules()
        issues = checker.check_implicit_dependencies()
        if issues:
            print("发现隐式依赖:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("✅ 未发现隐式依赖")
        return

    success = checker.run_all_tests(args.exclude)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
