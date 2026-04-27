"""
核心模块初始化
"""

from core.node_types import (
    NodeType, Node, NodeConfig, Scenario, ContextVariable,
    LLMConfig, IntentConfig, KnowledgeConfig, CodeConfig,
    APIConfig, MemoryConfig, ConditionConfig, MessageConfig, BarrierConfig,
    PreCondition, Branch, ConditionRule
)
from core.variable_manager import VariableManager
from core.engine import DAGEngine, ExecutionContext, ExecutionResult, ExecutionStatus

__all__ = [
    # 节点类型
    'NodeType', 'Node', 'NodeConfig', 'Scenario', 'ContextVariable',
    
    # 配置类
    'LLMConfig', 'IntentConfig', 'KnowledgeConfig', 'CodeConfig',
    'APIConfig', 'MemoryConfig', 'ConditionConfig', 'MessageConfig', 'BarrierConfig',
    
    # 辅助类
    'PreCondition', 'Branch', 'ConditionRule',
    
    # 变量管理
    'VariableManager',
    
    # 执行引擎
    'DAGEngine', 'ExecutionContext', 'ExecutionResult', 'ExecutionStatus',
]
