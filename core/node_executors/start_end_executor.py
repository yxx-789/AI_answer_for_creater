"""
START/END 节点执行器
处理流程的入口和出口
"""

from typing import Dict, Any
from core.node_executors.base import BaseExecutor
from core.node_types import Node
from core.variable_manager import VariableManager


class StartEndExecutor(BaseExecutor):
    """START/END节点执行器"""
    
    async def execute(self, node: Node, var_manager: VariableManager) -> Dict[str, Any]:
        """执行START/END节点"""
        # START节点：初始化流程
        if node.node_type.value == "START":
            return {
                "status": "started",
                "message": "流程开始"
            }
        
        # END节点：结束流程
        if node.node_type.value == "END":
            return {
                "status": "ended",
                "message": "流程结束"
            }
        
        return {"status": "unknown"}