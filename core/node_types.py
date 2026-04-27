"""
节点类型定义
基于百灵AI客服系统文档的8种标准化节点类型
"""

from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


class NodeType(Enum):
    """节点类型枚举"""
    START = "START"           # 入口节点
    LLM = "LLM"               # 大模型调用
    INTENT = "INTENT"         # 意图识别（LLM + 分类 + 前置条件）
    KNOWLEDGE = "KNOWLEDGE"   # 知识库检索
    CODE = "CODE"             # Python代码执行
    IF = "IF"                 # 条件分支
    API = "API"               # 外部HTTP调用
    MEMORY = "MEMORY"         # 记忆变量读写
    MESSAGE = "MESSAGE"       # 消息输出
    BARRIER = "BARRIER"       # 汇聚点（等待并行分支）
    END = "END"               # 结束节点
    ROUTE = "ROUTE"           # 路由节点（调用Agent）


@dataclass
class PreCondition:
    """前置条件（用于INTENT节点，优先级高于LLM分类）"""
    id: str
    name: str
    expression: str                    # Python表达式
    target_node: str                   # 命中后跳转的节点
    description: str = ""
    priority: int = 999                # 优先级，数字越小越优先


@dataclass
class Branch:
    """分支定义"""
    key: str                           # 分支标识（如意图ID）
    name: str                          # 分支名称
    target_node: str                   # 目标节点ID


@dataclass
class ConditionRule:
    """条件规则（用于IF节点）"""
    expression: str                    # Python表达式
    target_node: str                   # 目标节点
    description: str = ""


@dataclass
class NodeConfig:
    """节点配置基类"""
    pass


@dataclass
class LLMConfig(NodeConfig):
    """LLM节点配置"""
    model_id: str
    system_prompt: str
    user_prompt_template: str
    temperature: float = 0.1
    max_tokens: int = 500
    history_rounds: int = 0            # 传递多少轮历史，0=不传
    output_parser: str = "text"        # text | json | classification


@dataclass
class IntentConfig(NodeConfig):
    """INTENT节点配置"""
    model_id: str
    system_prompt: str
    user_prompt_template: str
    temperature: float = 0.01          # 意图识别通常用低温度
    max_tokens: int = 10
    history_rounds: int = 0
    output_parser: str = "classification"
    pre_conditions: List[PreCondition] = field(default_factory=list)
    branches: List[Branch] = field(default_factory=list)
    default_branch: str = ""


@dataclass
class KnowledgeConfig(NodeConfig):
    """KNOWLEDGE节点配置"""
    knowledge_base_id: str
    strategy: str = "hybrid"           # hybrid | semantic | keyword
    reranker: str = ""
    reranker_threshold: float = 0.44
    recall_count: int = 5
    query_source: str = ""             # 哪个变量作为检索query


@dataclass
class CodeConfig(NodeConfig):
    """CODE节点配置"""
    function_name: str                 # 映射到Python函数名
    input_mapping: Dict[str, str] = field(default_factory=dict)    # 参数名 → 变量来源
    output_mapping: Dict[str, str] = field(default_factory=dict)   # 输出名 → 存储变量名


@dataclass
class APIConfig(NodeConfig):
    """API节点配置"""
    url: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    body_template: Dict[str, Any] = field(default_factory=dict)
    timeout_sec: int = 5
    mock_response: Optional[Dict] = None


@dataclass
class MemoryConfig(NodeConfig):
    """MEMORY节点配置"""
    operation: str                     # read | write
    variables: List[str] = field(default_factory=list)


@dataclass
class ConditionConfig(NodeConfig):
    """IF节点配置"""
    conditions: List[ConditionRule] = field(default_factory=list)


@dataclass
class MessageConfig(NodeConfig):
    """MESSAGE节点配置"""
    template: str                      # 支持变量插值 {{var}}
    message_type: str = "text"         # text | card | transfer


@dataclass
class EndConfig(NodeConfig):
    """END节点配置"""
    status: str = "resolved"           # resolved | unresolved | transfer
    final_answer: str = ""


@dataclass
class BarrierConfig(NodeConfig):
    """BARRIER节点配置"""
    wait_for: List[str] = field(default_factory=list)  # 等待哪些节点完成


@dataclass
class RouteConfig(NodeConfig):
    """ROUTE节点配置（调用Agent）"""
    agent_name: str                    # Agent名称
    input_mapping: Dict[str, str] = field(default_factory=dict)    # 参数名 → 变量来源
    output_mapping: Dict[str, str] = field(default_factory=dict)   # 输出名 → 存储变量名
    status_routing: Dict[str, str] = field(default_factory=dict)   # status → 下一个节点ID


@dataclass
class Node:
    """
    节点定义
    所有节点类型的统一数据结构
    """
    node_id: str
    node_type: NodeType
    config: NodeConfig
    description: str = ""
    
    # 输出映射
    output_mapping: Dict[str, str] = field(default_factory=dict)
    
    # 下游节点
    next_nodes: List[str] = field(default_factory=list)
    
    # 并行标记
    parallel: bool = False             # 是否并行执行多个下游节点
    
    # 汇聚标记
    wait_for: List[str] = field(default_factory=list)  # 等待哪些节点完成


@dataclass
class ContextVariable:
    """上下文变量定义"""
    name: str
    var_type: str                      # String | Integer | Boolean | Object | ArrayString | ArrayObject
    source: str = "user_input"         # user_input | system | api
    default: Any = None


@dataclass
class Scenario:
    """
    场景定义
    一个完整的对话流程
    """
    scene_id: str
    scene_name: str
    version: str
    description: str
    
    # 上下文变量
    context_variables: Dict[str, ContextVariable] = field(default_factory=dict)
    
    # DAG节点
    nodes: Dict[str, Node] = field(default_factory=dict)
    
    # 入口节点
    entry_node: str = "START"
    
    # 知识库引用
    knowledge_refs: List[str] = field(default_factory=list)
    
    # 原始YML数据
    raw_data: Dict = None
