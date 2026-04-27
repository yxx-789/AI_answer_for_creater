"""
YML 场景解析器
负责读取和解析 scenarios/ 目录下的 YML 文件
"""

import os
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from core.node_types import (
    NodeType, Node, Scenario, ContextVariable,
    LLMConfig, IntentConfig, KnowledgeConfig, CodeConfig,
    APIConfig, MemoryConfig, ConditionConfig, MessageConfig, BarrierConfig,
    RouteConfig, PreCondition, Branch, ConditionRule, EndConfig
)


class YMLParser:
    """YML解析器"""
    
    def __init__(self, scenarios_dir: str = "scenarios"):
        """
        初始化解析器
        
        Args:
            scenarios_dir: 场景文件目录
        """
        self.scenarios_dir = Path(scenarios_dir)
        self.scenarios: Dict[str, Scenario] = {}
    
    def load_all_scenarios(self) -> Dict[str, Scenario]:
        """加载所有场景文件（支持递归加载子目录）"""
        if not self.scenarios_dir.exists():
            print(f"警告：场景目录不存在 {self.scenarios_dir}")
            return {}
        
        # 递归查找所有YML文件
        yml_files = list(self.scenarios_dir.glob("**/*.yml"))
        
        for yml_file in yml_files:
            try:
                scenario = self.parse_scenario(yml_file)
                if scenario:
                    self.scenarios[scenario.scene_id] = scenario
                    print(f"✓ 加载场景: {scenario.scene_name} ({scenario.scene_id})")
            except Exception as e:
                print(f"✗ 解析失败 {yml_file}: {e}")
        
        print(f"\n总计加载 {len(self.scenarios)} 个场景")
        return self.scenarios
    
    def parse_scenario(self, yml_path: Path) -> Optional[Scenario]:
        """解析单个场景文件"""
        with open(yml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data:
            return None
        
        # 解析metadata
        metadata = data.get('metadata', {})
        
        # 解析context_variables
        context_variables = {}
        for var_name, var_data in data.get('context_variables', {}).items():
            context_variables[var_name] = ContextVariable(
                name=var_name,
                var_type=var_data.get('type', 'String'),
                source=var_data.get('source', 'user_input'),
                default=var_data.get('default')
            )
        
        # 解析nodes
        nodes = {}
        for node_id, node_data in data.get('nodes', {}).items():
            node = self._parse_node(node_id, node_data)
            if node:
                nodes[node_id] = node
        
        # P0修复：查找入口节点
        entry_node = "START"
        if "START" not in nodes and "AGENT_START" in nodes:
            entry_node = "AGENT_START"
        
        return Scenario(
            scene_id=metadata.get('scene_id', 'unknown'),
            scene_name=metadata.get('scene_name', '未命名场景'),
            version=metadata.get('version', '1.0.0'),
            description=metadata.get('description', ''),
            context_variables=context_variables,
            nodes=nodes,
            entry_node=entry_node,
            knowledge_refs=metadata.get('knowledge_refs', []),
            raw_data=data
        )
    
    def _parse_node(self, node_id: str, node_data: Dict) -> Optional[Node]:
        """解析单个节点"""
        node_type_str = node_data.get('type', 'MESSAGE')
        
        try:
            node_type = NodeType(node_type_str)
        except ValueError:
            print(f"未知节点类型: {node_type_str}")
            return None
        
        # 解析config
        config = self._parse_config(node_type, node_data.get('config', {}))
        
        # START节点默认配置
        if node_type == NodeType.START and not config:
            config = MessageConfig(template="")
        
        # END节点默认配置
        if node_type == NodeType.END and not config:
            config = EndConfig(status='resolved')
        
        # 解析next_nodes
        next_nodes = node_data.get('next_nodes', [])
        if isinstance(next_nodes, str):
            next_nodes = [next_nodes]
        
        return Node(
            node_id=node_id,
            node_type=node_type,
            config=config,
            description=node_data.get('description', ''),
            output_mapping=node_data.get('output_mapping', {}),
            next_nodes=next_nodes,
            parallel=node_data.get('parallel', False),
            wait_for=node_data.get('wait_for', [])
        )
    
    def _parse_config(self, node_type: NodeType, config_data: Dict) -> Any:
        """解析节点配置"""
        
        if node_type == NodeType.LLM:
            return LLMConfig(
                model_id=config_data.get('model_id', ''),
                system_prompt=config_data.get('system_prompt', ''),
                user_prompt_template=config_data.get('user_prompt_template', ''),
                temperature=config_data.get('temperature', 0.1),
                max_tokens=config_data.get('max_tokens', 500),
                history_rounds=config_data.get('history_rounds', 0),
                output_parser=config_data.get('output_parser', 'text')
            )
        
        elif node_type == NodeType.INTENT:
            # 解析前置条件
            pre_conditions = []
            for pre_data in config_data.get('pre_conditions', []):
                pre_conditions.append(PreCondition(
                    id=pre_data.get('id', ''),
                    name=pre_data.get('name', ''),
                    expression=pre_data.get('expression', ''),
                    target_node=pre_data.get('target_node', ''),
                    description=pre_data.get('description', ''),
                    priority=pre_data.get('priority', 999)
                ))
            
            # 解析分支
            branches = []
            for branch_data in config_data.get('branches', []):
                branches.append(Branch(
                    key=branch_data.get('key', ''),
                    name=branch_data.get('name', ''),
                    target_node=branch_data.get('target_node', '')
                ))
            
            return IntentConfig(
                model_id=config_data.get('model_id', ''),
                system_prompt=config_data.get('system_prompt', ''),
                user_prompt_template=config_data.get('user_prompt_template', ''),
                temperature=config_data.get('temperature', 0.01),
                max_tokens=config_data.get('max_tokens', 10),
                history_rounds=config_data.get('history_rounds', 0),
                output_parser=config_data.get('output_parser', 'classification'),
                pre_conditions=pre_conditions,
                branches=branches,
                default_branch=config_data.get('default_branch', '')
            )
        
        elif node_type == NodeType.KNOWLEDGE:
            return KnowledgeConfig(
                knowledge_base_id=config_data.get('knowledge_base_id', ''),
                strategy=config_data.get('strategy', 'hybrid'),
                reranker=config_data.get('reranker', ''),
                reranker_threshold=config_data.get('reranker_threshold', 0.44),
                recall_count=config_data.get('recall_count', 5),
                query_source=config_data.get('query_source', '')
            )
        
        elif node_type == NodeType.CODE:
            return CodeConfig(
                function_name=config_data.get('function_name', ''),
                input_mapping=config_data.get('input_mapping', {}),
                output_mapping=config_data.get('output_mapping', {})
            )
        
        elif node_type == NodeType.API:
            return APIConfig(
                url=config_data.get('url', ''),
                method=config_data.get('method', 'POST'),
                headers=config_data.get('headers', {}),
                body_template=config_data.get('body_template', {}),
                timeout_sec=config_data.get('timeout_sec', 5),
                mock_response=config_data.get('mock_response')
            )
        
        elif node_type == NodeType.MEMORY:
            return MemoryConfig(
                operation=config_data.get('operation', 'read'),
                variables=config_data.get('variables', [])
            )
        
        elif node_type == NodeType.IF:
            conditions = []
            for cond_data in config_data.get('conditions', []):
                conditions.append(ConditionRule(
                    expression=cond_data.get('expression', ''),
                    target_node=cond_data.get('target_node', ''),
                    description=cond_data.get('description', '')
                ))
            return ConditionConfig(conditions=conditions)
        
        elif node_type == NodeType.MESSAGE:
            return MessageConfig(
                template=config_data.get('template', ''),
                message_type=config_data.get('message_type', 'text')
            )
        
        elif node_type == NodeType.BARRIER:
            return BarrierConfig(
                wait_for=config_data.get('wait_for', [])
            )
        
        elif node_type == NodeType.ROUTE:
            return RouteConfig(
                agent_name=config_data.get('agent_name', ''),
                input_mapping=config_data.get('input_mapping', {}),
                output_mapping=config_data.get('output_mapping', {}),
                status_routing=config_data.get('status_routing', {})
            )
        
        elif node_type == NodeType.END:
            # P0修复：解析END节点的status
            return EndConfig(
                status=config_data.get('status', 'resolved'),
                final_answer=config_data.get('final_answer', '')
            )
        
        else:
            return None
    
    def get_scenario(self, scene_id: str) -> Optional[Scenario]:
        """获取指定场景"""
        return self.scenarios.get(scene_id)


# 使用示例
if __name__ == '__main__':
    parser = YMLParser(scenarios_dir="scenarios")
    scenarios = parser.load_all_scenarios()
    
    print("\n" + "=" * 60)
    for scene_id, scenario in scenarios.items():
        print(f"场景: {scenario.scene_name} ({scene_id})")
        print(f"  节点数: {len(scenario.nodes)}")
        print(f"  变量数: {len(scenario.context_variables)}")
