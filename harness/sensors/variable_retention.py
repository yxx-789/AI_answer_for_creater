"""
Harness传感器 - 变量保留检查
"""
import yaml
from typing import Dict, List, Tuple

class VariableRetentionSensor:
    """检查Skill修改后是否保留了关键变量"""

    def __init__(self):
        self.required_vars = [
            'raw_query',
            'user_id',
            'classification_id',
            'final_answer'
        ]

        self.critical_nodes = [
            'START',
            'END',
            'MSG_OUTPUT'
        ]

    def check(self, old_skill_path: str, new_skill_path: str) -> Tuple[bool, str]:
        """
        检查变量保留情况

        Returns:
            (is_valid, message)
        """
        with open(old_skill_path, 'r', encoding='utf-8') as f:
            old_skill = yaml.safe_load(f)

        with open(new_skill_path, 'r', encoding='utf-8') as f:
            new_skill = yaml.safe_load(f)

        # 1. 检查关键变量
        old_vars = self._extract_variables(old_skill)
        new_vars = self._extract_variables(new_skill)

        missing_vars = []
        for var in self.required_vars:
            if var in old_vars and var not in new_vars:
                missing_vars.append(var)

        if missing_vars:
            return False, f"❌ 丢失关键变量: {', '.join(missing_vars)}"

        # 2. 检查关键节点
        old_nodes = set(old_skill.get('nodes', {}).keys())
        new_nodes = set(new_skill.get('nodes', {}).keys())

        missing_nodes = []
        for node in self.critical_nodes:
            if node in old_nodes and node not in new_nodes:
                missing_nodes.append(node)

        if missing_nodes:
            return False, f"❌ 丢失关键节点: {', '.join(missing_nodes)}"

        # 3. 检查流程完整性
        if not self._check_flow_integrity(new_skill):
            return False, "❌ 流程不完整：缺少必要的节点连接"

        return True, "✅ 变量保留检查通过"

    def _extract_variables(self, skill: Dict) -> set:
        """提取Skill中使用的所有变量"""
        variables = set()

        nodes = skill.get('nodes', {})
        for node_id, node_config in nodes.items():
            # 从input_mapping提取
            input_mapping = node_config.get('input_mapping', {})
            variables.update(input_mapping.values())

            # 从output_mapping提取
            output_mapping = node_config.get('output_mapping', {})
            variables.update(output_mapping.keys())

            # 从模板中提取 {{variable}}
            if 'config' in node_config:
                template = node_config['config'].get('template', '')
                import re
                found = re.findall(r'\{\{(\w+)\}\}', template)
                variables.update(found)

        return variables

    def _check_flow_integrity(self, skill: Dict) -> bool:
        """检查流程完整性"""
        nodes = skill.get('nodes', {})

        # 必须有START和END
        if 'START' not in nodes or 'END' not in nodes:
            return False

        # 检查每个节点是否有下游连接（除END外）
        for node_id, node_config in nodes.items():
            node_type = node_config.get('type')
            if node_type == 'END':
                continue

            # IF节点：通过conditions或branches定义下游
            if node_type == 'IF':
                config = node_config.get('config', {})
                conditions = config.get('conditions', [])
                branches = config.get('branches', [])
                if not conditions and not branches:
                    print(f"  ⚠️ IF节点 {node_id} 缺少conditions或branches")
                    return False
                continue

            # INTENT节点：通过branches定义下游
            if node_type == 'INTENT':
                config = node_config.get('config', {})
                branches = config.get('branches', [])
                default_branch = config.get('default_branch')
                if not branches and not default_branch:
                    print(f"  ⚠️ INTENT节点 {node_id} 缺少branches或default_branch")
                    return False
                continue

            # ROUTE节点：通过status_routing定义下游
            if node_type == 'ROUTE':
                config = node_config.get('config', {})
                status_routing = config.get('status_routing', {})
                if not status_routing:
                    print(f"  ⚠️ ROUTE节点 {node_id} 缺少status_routing")
                    return False
                continue

            # 其他节点：通过next_nodes定义下游
            next_nodes = node_config.get('next_nodes', [])
            if not next_nodes:
                print(f"  ⚠️ 节点 {node_id} (type={node_type}) 缺少next_nodes")
                return False

        return True


# 测试
if __name__ == '__main__':
    sensor = VariableRetentionSensor()

    # 测试用例：保留变量
    print("测试1：保留关键变量")
    is_valid, msg = sensor.check('test_skill_old.yml', 'test_skill_new.yml')
    print(f"  结果: {msg}")

    # 测试用例：丢失变量
    print("\n测试2：丢失关键变量")
    # 这里应该测试失败的情况