"""
DAG 执行引擎（健壮性增强版）
包含所有潜在问题的提前规避
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import json

from core.node_types import (
    Node, NodeType, Scenario,
    LLMConfig, IntentConfig, KnowledgeConfig, CodeConfig,
    APIConfig, MemoryConfig, ConditionConfig, MessageConfig, BarrierConfig,
    RouteConfig
)
from core.variable_manager import VariableManager

# 导入所有执行器
from core.node_executors.llm_executor import LLMExecutor
from core.node_executors.intent_executor import IntentExecutor
from core.node_executors.knowledge_executor import KnowledgeExecutor
from core.node_executors.code_executor import CodeExecutor
from core.node_executors.api_executor import APIExecutor
from core.node_executors.memory_executor import MemoryExecutor
from core.node_executors.message_executor import MessageExecutor
from core.node_executors.condition_executor import ConditionExecutor

import uuid
from datetime import datetime


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class ExecutionResult:
    """节点执行结果"""
    node_id: str
    status: ExecutionStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_ms: int = 0
    retry_count: int = 0


@dataclass
class ExecutionContext:
    """执行上下文"""
    scenario: Scenario
    variable_manager: VariableManager
    executed_nodes: Dict[str, ExecutionResult] = field(default_factory=dict)
    current_node_id: str = ""
    
    # 并行执行管理
    running_tasks: Dict[str, asyncio.Task] = field(default_factory=dict)
    completed_nodes: set = field(default_factory=set)
    
    # BARRIER节点防重复执行
    barrier_locks: Dict[str, asyncio.Lock] = field(default_factory=dict)
    barrier_executed: set = field(default_factory=set)
    
    # 链路追踪
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_log: List[Dict] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    # 健壮性增强：循环检测
    node_execution_count: Dict[str, int] = field(default_factory=dict)
    max_node_executions: int = 10  # 单个节点最大执行次数
    
    # 健壮性增强：总执行时间
    max_total_time: int = 300  # 最大总执行时间（秒）
    
    def log_trace(self, node_id: str, event: str, data: Dict = None):
        """记录链路追踪日志"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'trace_id': self.trace_id,
            'node_id': node_id,
            'event': event,
            'elapsed_ms': int((time.time() - self.start_time) * 1000),
            'data': data or {}
        }
        self.trace_log.append(entry)
        return entry
    
    def check_timeout(self) -> bool:
        """检查是否超时"""
        return (time.time() - self.start_time) > self.max_total_time
    
    def check_loop(self, node_id: str) -> bool:
        """检查是否有循环执行"""
        count = self.node_execution_count.get(node_id, 0) + 1
        self.node_execution_count[node_id] = count
        return count > self.max_node_executions
    
    def export_trace(self) -> Dict:
        """导出完整trace记录"""
        return {
            'trace_id': self.trace_id,
            'scene_id': self.scenario.scene_id,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'duration_ms': int((time.time() - self.start_time) * 1000),
            'nodes_executed': list(self.completed_nodes),
            'trace_log': self.trace_log,
            'final_variables': {
                k: v for k, v in self.variable_manager.get_all().items()
                if k in ['final_answer', 'transfer_flag', 'raw_query']
            }
        }


class DAGEngine:
    """
    DAG 执行引擎（健壮性增强版）
    """
    
    # 健壮性配置
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 1.0  # 重试延迟（秒）
    NODE_TIMEOUT = 60  # 单个节点超时（秒）
    SCENARIO_TIMEOUT = 300  # 场景总超时（秒）
    
    def __init__(self, executors: Dict[NodeType, Any] = None, use_mock: bool = False):
        """初始化引擎"""
        self.executors = executors or {}
        self.use_mock = use_mock
        
        # 注册默认执行器
        if not self.executors:
            self._register_default_executors()
        
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        self.permission_checker = None
    
    def _register_default_executors(self):
        """注册默认执行器"""
        executors_map = [
            (NodeType.LLM, LLMExecutor, "LLM"),
            (NodeType.INTENT, IntentExecutor, "Intent"),
            (NodeType.KNOWLEDGE, KnowledgeExecutor, "Knowledge"),
            (NodeType.CODE, CodeExecutor, "Code"),
            (NodeType.API, APIExecutor, "API"),
            (NodeType.MEMORY, MemoryExecutor, "Memory"),
            (NodeType.MESSAGE, MessageExecutor, "Message"),
            (NodeType.IF, ConditionExecutor, "IF"),
        ]
        
        for node_type, executor_class, name in executors_map:
            try:
                if node_type == NodeType.LLM:
                    self.executors[node_type] = executor_class(use_mock=self.use_mock)
                elif node_type == NodeType.API:
                    self.executors[node_type] = executor_class(timeout=30)
                else:
                    self.executors[node_type] = executor_class()
                print(f"[ENGINE] ✅ {name}执行器已注册")
            except Exception as e:
                print(f"[ENGINE] ⚠️ {name}执行器注册失败: {e}")
    
    async def execute_scenario(
        self,
        scenario: Scenario,
        initial_variables: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """执行场景（健壮性增强版）"""
        
        # 初始化上下文
        ctx = ExecutionContext(
            scenario=scenario,
            variable_manager=VariableManager(),
            max_total_time=self.SCENARIO_TIMEOUT
        )
        
        # 初始化 context_variables 的默认值
        if scenario.context_variables:
            default_vars = {}
            for var_name, var_def in scenario.context_variables.items():
                if var_def.default is not None:
                    default_val = var_def.default
                    # 解析 JSON 字符串
                    if isinstance(default_val, str):
                        if default_val.startswith('[') or default_val.startswith('{'):
                            try:
                                default_val = json.loads(default_val)
                            except:
                                pass
                    default_vars[var_name] = default_val
            
            if default_vars:
                ctx.variable_manager.set_batch(default_vars)
                print(f"[ENGINE] 已初始化 {len(default_vars)} 个默认变量")
        
        # 设置初始变量
        if initial_variables:
            ctx.variable_manager.set_batch(initial_variables)
        
        # 记录场景开始
        ctx.log_trace(scenario.entry_node, 'scenario_start', {
            'scene_id': scenario.scene_id,
            'entry_node': scenario.entry_node,
            'node_count': len(scenario.nodes)
        })
        
        try:
            # 从入口节点开始执行（带超时保护）
            await asyncio.wait_for(
                self._execute_from_node(ctx, scenario.entry_node),
                timeout=self.SCENARIO_TIMEOUT
            )
            
            # 记录场景完成
            ctx.log_trace('', 'scenario_complete', {
                'nodes_executed': len(ctx.completed_nodes),
                'duration_ms': int((time.time() - ctx.start_time) * 1000)
            })
            
            # 保存 trace
            trace = ctx.export_trace()
            self._save_trace(trace)
            
            return {
                "status": "success",
                "variables": ctx.variable_manager.get_all(),
                "executed_nodes": list(ctx.completed_nodes),
                "final_answer": ctx.variable_manager.get("final_answer", ""),
                "transfer_flag": ctx.variable_manager.get("transfer_flag", False),
                "trace": trace,
                "trace_log": ctx.trace_log
            }
        
        except asyncio.TimeoutError:
            error_msg = f"场景执行超时（>{self.SCENARIO_TIMEOUT}秒）"
            print(f"[ERROR] {error_msg}")
            
            self._save_bad_case(ctx, 'scenario_timeout', {
                'error': error_msg,
                'nodes_executed': len(ctx.completed_nodes)
            })
            
            return {
                "status": "timeout",
                "error": error_msg,
                "executed_nodes": list(ctx.completed_nodes),
                "final_answer": ctx.variable_manager.get("final_answer", "抱歉，处理超时，请稍后重试。")
            }
        
        except Exception as e:
            error_msg = f"场景执行异常: {str(e)}"
            print(f"[ERROR] {error_msg}")
            
            self._save_bad_case(ctx, 'scenario_exception', {
                'error': error_msg,
                'exception_type': type(e).__name__
            })
            
            return {
                "status": "error",
                "error": error_msg,
                "executed_nodes": list(ctx.completed_nodes),
                "final_answer": "抱歉，系统出现异常，请稍后重试。"
            }
    
    async def _execute_from_node(self, ctx: ExecutionContext, node_id: str):
        """从指定节点开始执行（健壮性增强版）"""
        
        # 健壮性检查1：节点是否存在
        if node_id not in ctx.scenario.nodes:
            print(f"[ERROR] 节点 {node_id} 不存在")
            return
        
        # 健壮性检查2：是否已执行过
        if node_id in ctx.completed_nodes:
            return
        
        # 健壮性检查3：循环检测
        if ctx.check_loop(node_id):
            print(f"[ERROR] 检测到循环执行: {node_id}（已执行 {ctx.node_execution_count[node_id]} 次）")
            self._save_bad_case(ctx, 'loop_detected', {
                'node_id': node_id,
                'execution_count': ctx.node_execution_count[node_id]
            })
            return
        
        # 健壮性检查4：总超时检测
        if ctx.check_timeout():
            print(f"[ERROR] 场景执行超时")
            return
        
        # 获取节点
        node = ctx.scenario.nodes[node_id]
        
        # 执行节点（带重试）
        result = await self._execute_node_with_retry(ctx, node)
        
        # 记录执行结果
        ctx.executed_nodes[node_id] = result
        
        # 只有成功才标记为完成
        if result.status == ExecutionStatus.SUCCESS:
            ctx.completed_nodes.add(node_id)
        
        # 记录节点执行日志
        ctx.log_trace(node_id, 'node_complete', {
            'status': result.status.value,
            'outputs': result.outputs,
            'duration_ms': result.duration_ms,
            'retry_count': result.retry_count
        })
        
        # 如果执行失败，记录 bad case
        if result.status in [ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT]:
            self._save_bad_case(ctx, 'node_failed', {
                'node_id': node_id,
                'node_type': node.node_type.value,
                'error': result.error,
                'retry_count': result.retry_count
            })
        
        # 获取下一步节点
        next_node_ids = self._get_next_nodes(ctx, node, result)
        
        # 递归执行下一步节点
        for next_node_id in next_node_ids:
            await self._execute_from_node(ctx, next_node_id)
    
    async def _execute_node_with_retry(self, ctx: ExecutionContext, node: Node) -> ExecutionResult:
        """执行节点（带重试机制）"""
        
        for retry_count in range(self.MAX_RETRIES + 1):
            try:
                # 带超时的节点执行
                result = await asyncio.wait_for(
                    self._execute_node(ctx, node),
                    timeout=self.NODE_TIMEOUT
                )
                
                result.retry_count = retry_count
                
                # 成功则返回
                if result.status == ExecutionStatus.SUCCESS:
                    return result
                
                # 失败但不可重试的错误
                if result.error and "not found" in result.error.lower():
                    return result
                
                # 可以重试的错误
                if retry_count < self.MAX_RETRIES:
                    print(f"[RETRY] 节点 {node.node_id} 执行失败，{self.RETRY_DELAY}秒后重试（{retry_count + 1}/{self.MAX_RETRIES}）")
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    return result
            
            except asyncio.TimeoutError:
                error_msg = f"节点执行超时（>{self.NODE_TIMEOUT}秒）"
                print(f"[ERROR] {error_msg}")
                
                if retry_count < self.MAX_RETRIES:
                    print(f"[RETRY] 节点 {node.node_id} 执行超时，{self.RETRY_DELAY}秒后重试（{retry_count + 1}/{self.MAX_RETRIES}）")
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    return ExecutionResult(
                        node_id=node.node_id,
                        status=ExecutionStatus.TIMEOUT,
                        error=error_msg,
                        retry_count=retry_count
                    )
            
            except Exception as e:
                error_msg = f"节点执行异常: {str(e)}"
                print(f"[ERROR] {error_msg}")
                
                if retry_count < self.MAX_RETRIES:
                    print(f"[RETRY] 节点 {node.node_id} 执行异常，{self.RETRY_DELAY}秒后重试（{retry_count + 1}/{self.MAX_RETRIES}）")
                    await asyncio.sleep(self.RETRY_DELAY)
                else:
                    return ExecutionResult(
                        node_id=node.node_id,
                        status=ExecutionStatus.FAILED,
                        error=error_msg,
                        retry_count=retry_count
                    )
        
        # 不应该到达这里
        return ExecutionResult(
            node_id=node.node_id,
            status=ExecutionStatus.FAILED,
            error="Unknown error"
        )
    
    async def _execute_node(self, ctx: ExecutionContext, node: Node) -> ExecutionResult:
        """执行单个节点"""
        print(f"[执行] 节点={node.node_id}, 类型={node.node_type.value}")
        
        start_time = time.time()
        
        try:
            # 特殊处理：START节点
            if node.node_type == NodeType.START:
                print(f"[START] {node.node_id} 开始执行")
                duration_ms = int((time.time() - start_time) * 1000)
                return ExecutionResult(
                    node_id=node.node_id,
                    status=ExecutionStatus.SUCCESS,
                    outputs={},
                    duration_ms=duration_ms
                )
            
            # 特殊处理：END节点
            if node.node_type == NodeType.END:
                print(f"[END] {node.node_id} 执行结束")
                duration_ms = int((time.time() - start_time) * 1000)
                return ExecutionResult(
                    node_id=node.node_id,
                    status=ExecutionStatus.SUCCESS,
                    outputs={},
                    duration_ms=duration_ms
                )
            
            # 特殊处理：BARRIER节点
            if node.node_type == NodeType.BARRIER:
                print(f"[BARRIER] {node.node_id} 开始执行")
                return await self._execute_barrier(ctx, node)
            
            # 特殊处理：ROUTE节点
            if node.node_type == NodeType.ROUTE:
                print(f"[ROUTE] {node.node_id} 开始执行")
                return await self._execute_route_node(ctx, node)
            
            # 获取执行器
            executor = self.executors.get(node.node_type)
            
            if not executor:
                return ExecutionResult(
                    node_id=node.node_id,
                    status=ExecutionStatus.FAILED,
                    error=f"未找到执行器: {node.node_type}"
                )
            
            # 执行节点
            outputs = await executor.execute(node, ctx.variable_manager)
            
            # 应用输出映射
            if node.output_mapping:
                ctx.variable_manager.apply_outputs(outputs, node.output_mapping)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return ExecutionResult(
                node_id=node.node_id,
                status=ExecutionStatus.SUCCESS,
                outputs=outputs,
                duration_ms=duration_ms
            )
        
        except Exception as e:
            print(f"[ERROR] 节点 {node.node_id} 执行失败: {e}")
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                node_id=node.node_id,
                status=ExecutionStatus.FAILED,
                error=str(e),
                duration_ms=duration_ms
            )
    
    async def _execute_barrier(self, ctx: ExecutionContext, node: Node) -> ExecutionResult:
        """执行BARRIER节点"""
        if node.node_id in ctx.barrier_executed:
            return ExecutionResult(
                node_id=node.node_id,
                status=ExecutionStatus.SUCCESS,
                outputs={}
            )
        
        if node.node_id not in ctx.barrier_locks:
            ctx.barrier_locks[node.node_id] = asyncio.Lock()
        
        async with ctx.barrier_locks[node.node_id]:
            if node.node_id in ctx.barrier_executed:
                return ExecutionResult(
                    node_id=node.node_id,
                    status=ExecutionStatus.SUCCESS,
                    outputs={}
                )
            
            # 等待所有前置节点完成
            wait_for = node.wait_for or []
            for dep_node_id in wait_for:
                while dep_node_id not in ctx.completed_nodes:
                    await asyncio.sleep(0.1)
            
            ctx.barrier_executed.add(node.node_id)
            
            return ExecutionResult(
                node_id=node.node_id,
                status=ExecutionStatus.SUCCESS,
                outputs={}
            )
    
    async def _execute_route_node(self, ctx: ExecutionContext, node: Node) -> ExecutionResult:
        """执行ROUTE节点"""
        config: RouteConfig = node.config
        
        agent_name = config.agent_name
        agent_input = ctx.variable_manager.map_inputs(config.input_mapping)
        
        agent_result = await self._execute_agent(agent_name, agent_input, ctx)
        
        if config.output_mapping:
            ctx.variable_manager.apply_outputs(agent_result, config.output_mapping)
        
        return ExecutionResult(
            node_id=node.node_id,
            status=ExecutionStatus.SUCCESS,
            outputs=agent_result
        )
    
    async def _execute_agent(self, agent_name: str, agent_input: Dict[str, Any], ctx: ExecutionContext) -> Dict[str, Any]:
        """执行子Agent"""
        from pathlib import Path
        
        agent_paths = [
            Path(f"data/scenarios/{agent_name}.yml"),
            Path(f"data/scenarios/agents/{agent_name}.yml"),
            Path(f"scenarios/{agent_name}.yml"),
            Path(f"scenarios/agents/{agent_name}.yml"),
        ]
        
        agent_file = None
        for path in agent_paths:
            if path.exists():
                agent_file = path
                break
        
        if not agent_file:
            print(f"[AGENT] 未找到Agent配置: {agent_name}")
            return {"error": f"Agent not found: {agent_name}"}
        
        try:
            from core.yml_parser import YMLParser
            parser = YMLParser(str(agent_file.parent))
            agent_scenario = parser.parse_scenario(agent_file)
            
            if not agent_scenario:
                return {"error": f"Failed to load agent: {agent_name}"}
            
            agent_engine = DAGEngine(executors=self.executors, use_mock=self.use_mock)
            result = await agent_engine.execute_scenario(agent_scenario, agent_input)
            
            return result
        
        except Exception as e:
            print(f"[AGENT] Agent执行失败: {e}")
            return {"error": str(e)}
    
    def _get_next_nodes(self, ctx: ExecutionContext, node: Node, result: ExecutionResult) -> List[str]:
        """获取下一步节点"""
        if result.status != ExecutionStatus.SUCCESS:
            return []
        
        # 特殊处理 IF 节点
        if node.node_type == NodeType.IF:
            next_node = result.outputs.get('next_node', '') or result.outputs.get('_next_node', '')
            if next_node:
                return [next_node]
            return []
        
        # 特殊处理 INTENT 节点
        if node.node_type == NodeType.INTENT:
            next_node = result.outputs.get('next_node', '') or result.outputs.get('_next_node', '')
            if next_node:
                return [next_node]
            if node.next_nodes:
                return node.next_nodes if isinstance(node.next_nodes, list) else [node.next_nodes]
            return []
        
        next_nodes = node.next_nodes
        
        if not next_nodes:
            return []
        
        if isinstance(next_nodes, list):
            return next_nodes
        
        if isinstance(next_nodes, dict):
            branch_key = result.outputs.get('output', '')
            if branch_key in next_nodes:
                return [next_nodes[branch_key]]
            if 'default' in next_nodes:
                return [next_nodes['default']]
            return []
        
        return [next_nodes]
    
    def _save_trace(self, trace: Dict):
        """保存trace到文件"""
        from pathlib import Path
        
        traces_dir = Path('traces')
        traces_dir.mkdir(exist_ok=True)
        
        trace_file = traces_dir / f"{trace['trace_id'][:8]}.json"
        
        with open(trace_file, 'w', encoding='utf-8') as f:
            json.dump(trace, f, ensure_ascii=False, indent=2)
        
        print(f"[TRACE] 已保存trace: {trace_file}")
    
    def _save_bad_case(self, ctx: ExecutionContext, case_type: str, details: Dict):
        """保存bad case到文件"""
        from pathlib import Path
        
        bad_cases_dir = Path('bad_cases')
        bad_cases_dir.mkdir(exist_ok=True)
        
        bad_case = {
            'timestamp': datetime.now().isoformat(),
            'trace_id': ctx.trace_id,
            'case_type': case_type,
            'details': details,
            'variables': {
                k: v for k, v in ctx.variable_manager.get_all().items()
                if k in ['raw_query', 'final_answer', 'transfer_flag']
            }
        }
        
        bad_case_file = bad_cases_dir / f"{case_type}_{uuid.uuid4().hex[:8]}.json"
        
        with open(bad_case_file, 'w', encoding='utf-8') as f:
            json.dump(bad_case, f, ensure_ascii=False, indent=2)
        
        print(f"[BAD_CASE] 已保存bad case: {bad_case_file}")
