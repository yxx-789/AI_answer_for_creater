"""
CODE 节点执行器
负责执行 Python 代码函数
"""

from typing import Dict, Any, Callable
import inspect

from core.node_executors.base import BaseExecutor
from core.node_types import Node, CodeConfig
from core.variable_manager import VariableManager

# 导入业务函数模块，自动注册其中的函数
import code_functions.bailing_functions as bailing_functions


class CodeExecutor(BaseExecutor):
    """CODE 节点执行器"""

    def __init__(self, function_registry: Dict[str, Callable] = None):
        """
        初始化

        Args:
            function_registry: 函数名 -> 函数对象的映射
        """
        self.function_registry = function_registry or {}

        # 注册内置函数
        self._register_builtin_functions()

        # 自动注册业务函数
        self._register_bailing_functions()

    def register_function(self, name: str, func: Callable):
        """注册函数"""
        self.function_registry[name] = func

    def _register_builtin_functions(self):
        """注册内置函数"""
        self.register_function("passthrough", passthrough)
        self.register_function("merge_query", merge_query)
        self.register_function("parse_talk_context", parse_talk_context)
        self.register_function("generate_extra_prompt", generate_extra_prompt)
        self.register_function("fill_query_with_info", fill_query_with_info)

    def _register_bailing_functions(self):
        """自动注册 bailing_functions.py 中的全部函数"""
        for name, func in inspect.getmembers(bailing_functions, inspect.isfunction):
            if name.startswith("_"):
                continue
            self.register_function(name, func)

    async def execute(self, node: Node, var_manager: VariableManager) -> Dict[str, Any]:
        """执行 CODE 节点"""
        config: CodeConfig = node.config

        # 获取函数
        func = self.function_registry.get(config.function_name)

        if not func:
            raise ValueError(f"函数未注册: {config.function_name}")

        # 提取输入参数
        inputs = var_manager.map_inputs(config.input_mapping)

        # 执行函数
        print(f"执行函数: {config.function_name}({inputs})")
        result = func(**inputs)

        # 如果返回 None，返回空字典
        if result is None:
            return {}

        # 如果返回字典，直接返回
        if isinstance(result, dict):
            return result

        # 其他类型，包装为 {"output": result}
        return {"output": result}


# ============================================================
# 内置代码函数
# ============================================================

def passthrough(value: Any) -> Any:
    """透传函数"""
    return value


def merge_query(img_query: str = "", no_img_query: str = "") -> str:
    """合并图片 query 和文字 query"""
    return img_query or no_img_query or ""


def parse_talk_context(talk_context_str: str = "[]") -> Dict[str, Any]:
    """
    解析 talk_context JSON 字符串

    Returns:
        {
            "count_map": {"1": 5, "2": 2},
            "last_id": "1",
            "continuity_count": 3
        }
    """
    import json
    from collections import Counter

    try:
        talk_context = json.loads(talk_context_str) if talk_context_str else []
    except Exception:
        talk_context = []

    if not talk_context:
        return {
            "count_map": {},
            "last_id": "",
            "continuity_count": 0
        }

    # 统计各意图出现次数
    count_map = dict(Counter(talk_context))

    # 获取最后的意图 ID
    last_id = talk_context[-1] if talk_context else ""

    # 统计连续相同意图次数
    continuity_count = 0
    for i in range(len(talk_context) - 1, -1, -1):
        if talk_context[i] == last_id:
            continuity_count += 1
        else:
            break

    return {
        "count_map": count_map,
        "last_id": last_id,
        "continuity_count": continuity_count
    }


def generate_extra_prompt(user_list: list) -> str:
    """生成额外 prompt（非工时时补充提示）"""
    if any("非工时" in str(item) for item in user_list):
        return "现在处于非工作时间。"
    return ""


def fill_query_with_info(
    rewrite_query: str,
    user_list: list,
    semantic_complete: str,
    extra_prompt: str
) -> Dict[str, str]:
    """
    生成两个版本的 query
    """
    if semantic_complete == "0":
        # 语义不完整，不改写
        return {
            "query_with_info": rewrite_query,
            "query_without_info": rewrite_query
        }

    # 语义完整，拼接用户信息
    user_info = " ".join([str(item) for item in user_list if item])
    query_with_info = f"{user_info} {rewrite_query} {extra_prompt}".strip()

    return {
        "query_with_info": query_with_info,
        "query_without_info": rewrite_query
    }


# 使用示例
if __name__ == '__main__':
    # 创建执行器
    executor = CodeExecutor()

    # 测试
    import asyncio

    async def test():
        from core.node_types import Node, CodeConfig
        from core.variable_manager import VariableManager

        vm = VariableManager()
        vm.set("talk_context_str", '["1", "1", "1", "2", "1"]')

        node = Node(
            node_id="test",
            node_type="CODE",
            config=CodeConfig(
                function_name="parse_talk_context",
                input_mapping={"talk_context_str": "talk_context_str"}
            )
        )

        result = await executor.execute(node, vm)
        print(f"结果: {result}")

    asyncio.run(test())