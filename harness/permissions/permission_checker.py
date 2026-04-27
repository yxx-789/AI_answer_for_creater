"""
权限检查器 - 真正读取并执行 modification_permissions.yml
"""
import yaml
from pathlib import Path
from typing import Dict, Tuple, Optional


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, permissions_path: str = 'harness/modification_permissions.yml'):
        self.permissions_path = Path(permissions_path)
        self.permissions = self._load_permissions()
    
    def _load_permissions(self) -> Dict:
        """加载权限配置"""
        if not self.permissions_path.exists():
            raise FileNotFoundError(f"权限配置文件不存在: {self.permissions_path}")
        
        with open(self.permissions_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def check_file_permission(self, file_path: str) -> Tuple[bool, str, str]:
        """
        检查文件是否允许被修改
        
        Returns:
            (is_allowed, permission_level, reason)
        """
        file_path = Path(file_path)
        file_str = str(file_path)
        
        # 1. 检查是否是核心代码文件（Python）
        if file_path.suffix == '.py':
            # core/ 目录下的所有文件禁止修改
            if 'core/' in file_str or file_path.parts[-2] == 'core':
                return False, 'L3', "禁止修改核心执行器代码（core/ 目录）"
            
            # config.py 禁止修改
            if file_path.name == 'config.py':
                return False, 'L3', "禁止修改配置文件（config.py）"
            
            # optimizer/ 目录下的修改器本身需要保护
            if 'optimizer/' in file_str and 'skill_modifier' in file_str:
                return False, 'L3', "禁止修改修改器本身（skill_modifier.py）"
        
        # 2. 检查 YML 场景文件
        if file_path.suffix in ['.yml', '.yaml']:
            # scenarios/ 目录下的文件需要检查场景级权限
            if 'scenarios/' in file_str:
                # 提取场景名称
                scenario_name = file_path.stem
                return self._check_scenario_permission(scenario_name)
        
        # 3. knowledge/ 目录允许修改（L1权限）
        if 'knowledge' in file_str or 'knowledge_base' in file_str:
            return True, 'L1', "知识库文件允许修改"
        
        # 4. 默认：未知文件类型，不允许修改
        return False, 'L3', f"未知文件类型，不允许修改: {file_path.name}"
    
    def _check_scenario_permission(self, scenario_name: str) -> Tuple[bool, str, str]:
        """
        检查场景级权限
        
        Returns:
            (is_allowed, permission_level, reason)
        """
        scenarios = self.permissions.get('scenarios', {})
        
        # 如果场景在配置中，返回具体权限
        if scenario_name in scenarios:
            scenario_config = scenarios[scenario_name]
            return True, 'L1', f"场景 '{scenario_name}' 允许修改"
        
        # 默认：允许修改场景文件（但要经过节点级检查）
        return True, 'L2', f"场景 '{scenario_name}' 允许修改（需节点级权限检查）"
    
    def check_node_permission(
        self, 
        scenario_name: str, 
        node_name: str
    ) -> Tuple[bool, str, str]:
        """
        检查节点级权限
        
        Returns:
            (is_allowed, permission_level, reason)
        """
        # 检查全局保护节点
        global_config = self.permissions.get('global', {})
        protected_nodes = global_config.get('protected_nodes', [])
        
        if node_name in protected_nodes:
            return False, 'L3', f"节点 '{node_name}' 是全局保护节点，禁止修改"
        
        # 检查场景级节点权限
        scenarios = self.permissions.get('scenarios', {})
        if scenario_name in scenarios:
            scenario_config = scenarios[scenario_name]
            nodes = scenario_config.get('nodes', {})
            
            if node_name in nodes:
                node_config = nodes[node_name]
                permission = node_config.get('permission', 'L2')
                reason = node_config.get('reason', '')
                
                if permission == 'L3':
                    return False, 'L3', f"节点 '{node_name}' 禁止修改: {reason}"
                elif permission == 'L2':
                    return True, 'L2', f"节点 '{node_name}' 限制修改: 只能修改参数"
                else:  # L1
                    return True, 'L1', f"节点 '{node_name}' 允许修改"
        
        # 默认：允许修改，但需要经过其他检查
        return True, 'L2', f"节点 '{node_name}' 允许修改（需其他检查）"
    
    def check_field_permission(
        self,
        scenario_name: str,
        node_name: str,
        field_name: str
    ) -> Tuple[bool, str]:
        """
        检查字段级权限（针对 L2 权限节点）
        
        Returns:
            (is_allowed, reason)
        """
        scenarios = self.permissions.get('scenarios', {})
        
        if scenario_name in scenarios:
            nodes = scenarios[scenario_name].get('nodes', {})
            
            if node_name in nodes:
                node_config = nodes[node_name]
                permission = node_config.get('permission', 'L2')
                
                if permission == 'L3':
                    return False, "节点禁止修改"
                
                if permission == 'L2':
                    allowed = node_config.get('allowed_modifications', [])
                    forbidden = node_config.get('forbidden_modifications', [])
                    
                    if field_name in forbidden:
                        return False, f"字段 '{field_name}' 禁止修改"
                    
                    if allowed and field_name not in allowed:
                        return False, f"字段 '{field_name}' 不在允许修改列表中"
        
        return True, f"字段 '{field_name}' 允许修改"


# 测试
if __name__ == '__main__':
    checker = PermissionChecker()
    
    print("=" * 70)
    print("权限检查器测试")
    print("=" * 70)
    
    # 测试1：尝试修改核心文件
    print("\n测试1：尝试修改 core/engine.py")
    is_allowed, level, reason = checker.check_file_permission('core/engine.py')
    print(f"  结果: {'✅ 允许' if is_allowed else '❌ 拒绝'}")
    print(f"  权限级别: {level}")
    print(f"  原因: {reason}")
    
    # 测试2：尝试修改场景文件
    print("\n测试2：尝试修改 scenarios/bailing/main_flow.yml")
    is_allowed, level, reason = checker.check_file_permission('scenarios/bailing/main_flow.yml')
    print(f"  结果: {'✅ 允许' if is_allowed else '❌ 拒绝'}")
    print(f"  权限级别: {level}")
    print(f"  原因: {reason}")
    
    # 测试3：尝试修改知识库
    print("\n测试3：尝试修改 knowledge_base/account_kb.json")
    is_allowed, level, reason = checker.check_file_permission('knowledge_base/account_kb.json')
    print(f"  结果: {'✅ 允许' if is_allowed else '❌ 拒绝'}")
    print(f"  权限级别: {level}")
    print(f"  原因: {reason}")
    
    # 测试4：检查节点权限
    print("\n测试4：检查 START 节点权限")
    is_allowed, level, reason = checker.check_node_permission('article_offline', 'START')
    print(f"  结果: {'✅ 允许' if is_allowed else '❌ 拒绝'}")
    print(f"  权限级别: {level}")
    print(f"  原因: {reason}")
    
    # 测试5：检查字段权限
    print("\n测试5：检查 KB_SEARCH_MAIN 节点的 knowledge_base_id 字段")
    is_allowed, reason = checker.check_field_permission('article_offline', 'KB_SEARCH_MAIN', 'knowledge_base_id')
    print(f"  结果: {'✅ 允许' if is_allowed else '❌ 拒绝'}")
    print(f"  原因: {reason}")
