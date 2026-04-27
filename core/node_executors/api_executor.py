"""
API 节点执行器
负责外部HTTP调用，支持Mock降级
"""

import json
import httpx
from typing import Dict, Any, Optional
from dataclasses import dataclass

from core.node_executors.base import BaseExecutor
from core.node_types import Node, APIConfig
from core.variable_manager import VariableManager


class APIExecutor(BaseExecutor):
    """API节点执行器"""
    
    def __init__(self, timeout: int = 10):
        """
        初始化
        
        Args:
            timeout: 请求超时时间（秒）
        """
        self.timeout = timeout
    
    async def execute(self, node: Node, var_manager: VariableManager) -> Dict[str, Any]:
        """执行API节点"""
        config: APIConfig = node.config
        
        # 解析URL和Body中的变量
        url = self.resolve_template(config.url, var_manager)
        body = self._resolve_body(config.body_template, var_manager)
        
        # 判断是否有Mock数据
        if config.mock_response is not None:
            print(f"[MOCK API] {config.method} {url}")
            print(f"  Body: {json.dumps(body, ensure_ascii=False)[:100]}...")
            return self._process_response(config.mock_response, node.output_mapping)
        
        # 真实调用
        try:
            result = await self._real_call(config, url, body)
            return self._process_response(result, node.output_mapping)
        
        except Exception as e:
            print(f"API调用失败: {e}")
            # 如果有Mock数据，降级使用
            if config.mock_response is not None:
                print("  降级使用Mock数据")
                return self._process_response(config.mock_response, node.output_mapping)
            
            return {"error": str(e)}
    
    def _resolve_body(self, body_template: Dict, var_manager: VariableManager) -> Dict:
        """
        解析Body模板中的变量
        
        支持嵌套字典和列表
        """
        if not body_template:
            return {}
        
        def resolve_value(value):
            if isinstance(value, str):
                return self.resolve_template(value, var_manager)
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            else:
                return value
        
        return resolve_value(body_template)
    
    async def _real_call(
        self, 
        config: APIConfig, 
        url: str, 
        body: Dict
    ) -> Dict[str, Any]:
        """真实HTTP调用"""
        
        headers = config.headers or {}
        headers.setdefault("Content-Type", "application/json")
        
        timeout = config.timeout_sec or self.timeout
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            if config.method.upper() == "GET":
                response = await client.get(url, headers=headers, params=body)
            else:  # POST
                response = await client.post(url, headers=headers, json=body)
            
            response.raise_for_status()
            return response.json()
    
    def _process_response(
        self, 
        response: Dict[str, Any], 
        output_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        处理API响应
        
        根据output_mapping提取响应数据
        例如：{"condition_desc_list": "data.conditionDescList"}
        表示从response['data']['conditionDescList']提取，存储到condition_desc_list
        """
        result = {"raw_response": response}
        
        for output_name, path in output_mapping.items():
            # 解析路径（如 data.conditionDescList）
            value = self._extract_by_path(response, path)
            result[output_name] = value
        
        return result
    
    def _extract_by_path(self, data: Dict, path: str) -> Any:
        """
        根据路径提取数据
        
        Args:
            data: 响应数据
            path: 路径，如 "data.conditionDescList" 或 "data.items[0].id"
        """
        if not path:
            return None
        
        parts = path.split(".")
        value = data
        
        for part in parts:
            if value is None:
                return None
            
            # 处理数组索引
            if "[" in part and "]" in part:
                # 提取键名和索引
                match = part.split("[")
                key = match[0]
                index = int(match[1].rstrip("]"))
                
                if key:
                    value = value.get(key)
                if isinstance(value, list) and index < len(value):
                    value = value[index]
                else:
                    return None
            else:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
        
        return value


# 使用示例
if __name__ == '__main__':
    import asyncio
    
    async def test():
        # 创建执行器
        executor = APIExecutor()
        
        # 创建变量管理器
        vm = VariableManager()
        vm.set("conversation_id", "test_conv_123")
        vm.set("condition_ids", [2296, 2049])
        
        # 创建节点（使用Mock）
        from core.node_types import APIConfig
        
        node = Node(
            node_id="test_api",
            node_type="API",
            config=APIConfig(
                url="https://ufosdk.baidu.com/connector/checkCondition",
                method="POST",
                body_template={
                    "conditionIds": "{{condition_ids}}",
                    "conversationId": "{{conversation_id}}"
                },
                timeout_sec=5,
                mock_response={
                    "code": 0,
                    "data": {
                        "conditionDescList": ["非鼓励层", "工时内", "非黑名单"],
                        "conditionIdList": [2296, 2049]
                    }
                }
            ),
            output_mapping={
                "condition_desc_list": "data.conditionDescList",
                "condition_id_list": "data.conditionIdList"
            }
        )
        
        # 执行
        result = await executor.execute(node, vm)
        print(f"\n结果:")
        print(f"  condition_desc_list: {result.get('condition_desc_list')}")
        print(f"  condition_id_list: {result.get('condition_id_list')}")
    
    asyncio.run(test())
