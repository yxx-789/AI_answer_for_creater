"""
IF 节点执行器
负责条件分支判断
"""

from typing import Dict, Any
from core.node_executors.base import BaseExecutor
from core.node_types import Node, ConditionConfig
from core.variable_manager import VariableManager


class ConditionExecutor(BaseExecutor):
    """IF节点执行器"""
    
    async def execute(self, node: Node, var_manager: VariableManager) -> Dict[str, Any]:
        """执行IF节点"""
        config: ConditionConfig = node.config
        
        # 遍历条件规则
        for rule in config.conditions:
            # 评估表达式
            if var_manager.evaluate_expression(rule.expression):
                print(f"条件命中: {rule.description or rule.expression} → {rule.target_node}")
                return {
                    "next_node": rule.target_node,
                    "matched_condition": rule.description
                }
        
        # 没有匹配的条件，返回空
        print(f"IF节点 {node.node_id} 没有匹配的条件")
        return {
            "next_node": "",
            "matched_condition": None
        }
