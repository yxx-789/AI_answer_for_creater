"""
INTENT 节点执行器
负责意图识别，支持前置条件 + LLM分类
"""

from typing import Dict, Any, Optional
from core.node_executors.base import BaseExecutor
from core.node_types import Node, IntentConfig
from core.variable_manager import VariableManager


class IntentExecutor(BaseExecutor):
    """INTENT节点执行器"""
    
    def __init__(self, llm_client=None, use_mock: bool = False):
        """
        初始化
        
        Args:
            llm_client: 大模型客户端（已废弃，直接使用LLMExecutor）
            use_mock: 是否使用Mock模式（已废弃，强制使用真实API）
        """
        # 强制不使用Mock
        self.llm_client = llm_client
        self.use_mock = False  # 强制使用真实API

    async def execute(self, node: Node, var_manager: VariableManager) -> Dict[str, Any]:
        """执行INTENT节点"""
        config: IntentConfig = node.config
        
        print(f"\n[INTENT] 节点={node.node_id}")
        
        # 1. 先检查前置条件（优先级高于LLM）
        print(f"[INTENT] 检查 {len(config.pre_conditions)} 个前置条件...")
        for pre_cond in sorted(config.pre_conditions, key=lambda x: x.priority):
            try:
                result = var_manager.evaluate_expression(pre_cond.expression)
                print(f"  [{pre_cond.id}] {pre_cond.name}: {pre_cond.expression} → {result}")
                if result:
                    print(f"  ✅ 前置条件命中: {pre_cond.name} → {pre_cond.target_node}")
                    return {
                        "classification_id": pre_cond.id,  # 返回前置条件ID
                        "_next_node": pre_cond.target_node,
                        "_matched_by": "pre_condition"
                    }
            except Exception as e:
                print(f"  ⚠️ 前置条件评估失败: {e}")
                continue
        
        # 2. 前置条件都不命中，调用LLM分类
        print(f"[INTENT] 前置条件未命中，调用LLM分类...")
        classification_id = await self._llm_classify(config, var_manager, node)
        
        # 根据分类结果找分支
        next_node = self._find_branch(config, classification_id)
        
        print(f"[INTENT] 分类结果: {classification_id} → {next_node}")
        
        return {
            "classification_id": classification_id,
            "_next_node": next_node,
            "_matched_by": "llm"
        }
    
    async def _llm_classify(self, config: IntentConfig, var_manager: VariableManager, node: Node) -> str:
        """调用LLM进行分类"""
        
        # 解析prompt模板
        system_prompt = self.resolve_template(config.system_prompt, var_manager)
        user_prompt = self.resolve_template(config.user_prompt_template, var_manager)
        
        print(f"[INTENT LLM] System: {system_prompt[:100]}...")
        print(f"[INTENT LLM] User: {user_prompt[:100]}...")
        
        # 调用真实LLM API
        try:
            from core.node_executors.llm_executor import LLMExecutor
            from core.node_types import Node as TempNode, LLMConfig
            
            # 创建LLM执行器
            llm_executor = LLMExecutor(use_mock=False)  # 强制使用真实API
            
            # 创建临时LLM节点
            temp_node = TempNode(
                node_id=f"{node.node_id}_llm_temp",
                node_type="LLM",
                config=LLMConfig(
                    model_id=config.model_id,
                    system_prompt=system_prompt,
                    user_prompt_template=user_prompt,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    history_rounds=getattr(config, 'history_rounds', 0),
                    output_parser="classification"  # 分类任务
                )
            )
            
            # 执行LLM调用
            result = await llm_executor.execute(temp_node, var_manager)
            
            classification_id = result.get("classification_id", "-1")
            print(f"[INTENT LLM] API返回: {classification_id}")
            
            return classification_id
            
        except Exception as e:
            print(f"[INTENT LLM] ❌ LLM调用失败: {e}")
            import traceback
            traceback.print_exc()
            # 失败时返回默认值
            return "-1"
    
    def _find_branch(self, config: IntentConfig, classification_id: str) -> str:
        """根据分类ID找分支"""
        for branch in config.branches:
            if branch.key == classification_id:
                return branch.target_node
        
        # 没找到，返回默认分支
        return config.default_branch
