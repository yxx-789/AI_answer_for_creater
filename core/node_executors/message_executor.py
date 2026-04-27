"""
MESSAGE 节点执行器
负责消息输出
"""

from typing import Dict, Any
from core.node_executors.base import BaseExecutor
from core.node_types import Node, MessageConfig
from core.variable_manager import VariableManager


class MessageExecutor(BaseExecutor):
    """MESSAGE节点执行器"""
    
    async def execute(self, node: Node, var_manager: VariableManager) -> Dict[str, Any]:
        """执行MESSAGE节点"""
        config: MessageConfig = node.config
        
        # 解析模板中的变量
        resolved_message = self.resolve_template(config.template, var_manager)
        
        return {
            "template_output": resolved_message,
            "message_type": config.message_type
        }
