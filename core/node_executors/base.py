"""
节点执行器基类
所有节点执行器的抽象基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from core.variable_manager import VariableManager
from core.node_types import Node


class BaseExecutor(ABC):
    """节点执行器基类"""
    
    @abstractmethod
    async def execute(self, node: Node, var_manager: VariableManager) -> Dict[str, Any]:
        """
        执行节点
        
        Args:
            node: 节点对象
            var_manager: 变量管理器
        
        Returns:
            执行结果 {"output_name": value, ...}
        """
        pass
    
    def resolve_template(self, template: str, var_manager: VariableManager) -> str:
        """解析模板中的变量"""
        # 调试：打印解析前后的变量
        import re
        vars_in_template = re.findall(r'\{\{([^}]+)\}\}', template)
        if vars_in_template:
            print(f"  [模板变量] 需要解析: {vars_in_template}")
            for var_name in vars_in_template:
                value = var_manager.get(var_name.strip())
                print(f"    {var_name.strip()} = {value}")
        
        result = var_manager.resolve_value(template)
        print(f"  [解析结果] '{result[:100]}...'\n")
        return result
