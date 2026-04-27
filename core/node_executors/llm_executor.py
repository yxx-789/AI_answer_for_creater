"""
LLM 节点执行器
负责调用大模型API（支持动态模型选择）
"""

import json
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass

from core.node_executors.base import BaseExecutor
from core.node_types import Node, LLMConfig
from core.variable_manager import VariableManager


@dataclass
class LLMClient:
    """大模型客户端配置"""
    api_url: str = "https://qianfan.baidubce.com/v2/chat/completions"
    api_key: str = ""
    timeout: int = 30


class LLMExecutor(BaseExecutor):
    """LLM节点执行器"""
    
    def __init__(self, client: LLMClient = None, use_mock: bool = False):
        """
        初始化
        
        Args:
            client: LLM客户端配置
            use_mock: 是否使用Mock模式（开发测试用）
        """
        self.client = client or LLMClient()
        self.use_mock = use_mock
    
    async def execute(self, node: Node, var_manager: VariableManager) -> Dict[str, Any]:
        """执行LLM节点"""
        config: LLMConfig = node.config
        
        # 解析prompt模板
        system_prompt = self.resolve_template(config.system_prompt, var_manager)
        user_prompt = self.resolve_template(config.user_prompt_template, var_manager)
        
        # 调试：打印完整prompt
        print(f"\n[LLM Prompt] 节点={node.node_id}")
        print(f"  System: {system_prompt[:150]}...")
        print(f"  User: {user_prompt[:200]}...")
        print()
        
        # 从配置文件读取API配置
        try:
            import sys
            from pathlib import Path
            ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")
            if str(ROOT_DIR) not in sys.path:
                sys.path.insert(0, str(ROOT_DIR))
            
            from config.api_config import API_KEY, API_URL
            from config.models import DEFAULT_MODEL
            
            if API_KEY:
                self.client.api_key = API_KEY
                self.client.api_url = API_URL
            
            # 优先使用全局配置的模型（用户在UI中选择的）
            if not config.model_id or config.model_id == "qwen3.5-27b":
                config.model_id = DEFAULT_MODEL
        
        except ImportError as e:
            print(f"⚠️ 无法导入API配置: {e}")
            pass
        
        if self.client.api_key and not self.use_mock:
            return await self._real_call(config, system_prompt, user_prompt)
        else:
            return await self._mock_call(config, system_prompt, user_prompt)
    
    async def _real_call(
        self, 
        config: LLMConfig, 
        system_prompt: str, 
        user_prompt: str
    ) -> Dict[str, Any]:
        """真实调用千帆API"""
        
        print(f"[真实LLM] 模型: {config.model_id}")
        print(f"  System: {system_prompt[:80]}...")
        print(f"  User: {user_prompt[:80]}...")
        
        # 构建请求头
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.client.api_key}'
        }
        
        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 构建请求体
        payload = {
            "model": config.model_id,
            "messages": messages
        }
        
        # 添加可选参数
        if hasattr(config, 'temperature') and config.temperature:
            payload["temperature"] = config.temperature
        
        if hasattr(config, 'max_tokens') and config.max_tokens:
            payload["max_tokens"] = config.max_tokens
        
        try:
            # 使用 requests.post 调用
            response = requests.post(
                self.client.api_url,
                headers=headers,
                json=payload,  # 直接传字典，requests 会自动序列化
                timeout=self.client.timeout
            )
            
            print(f"  [HTTP状态码] {response.status_code}")
            
            response.raise_for_status()
            result = response.json()
            
            # 提取输出
            output = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            print(f"  [API返回] {output[:100]}...")
            
            # 根据output_parser处理
            return self._parse_output(output, config.output_parser)
        
        except requests.exceptions.Timeout:
            print(f"  ❌ LLM调用超时")
            return {"output": "", "error": "请求超时"}
        
        except requests.exceptions.HTTPError as e:
            print(f"  ❌ LLM调用失败: {e}")
            if e.response:
                print(f"  [错误响应] {e.response.text[:200]}")
            return {"output": "", "error": f"HTTP错误: {e}"}
        
        except Exception as e:
            print(f"  ❌ LLM调用失败: {e}")
            return {"output": "", "error": str(e)}
    
    async def _mock_call(
        self, 
        config: LLMConfig, 
        system_prompt: str, 
        user_prompt: str
    ) -> Dict[str, Any]:
        """Mock调用（开发测试用）"""
        
        print(f"[MOCK LLM] 模型: {config.model_id}")
        print(f"  System: {system_prompt[:100]}...")
        print(f"  User: {user_prompt[:100]}...")
        
        # Mock逻辑
        mock_output = self._generate_mock_output(system_prompt, user_prompt, config)
        
        print(f"  [Mock输出] {mock_output}")
        return self._parse_output(mock_output, config.output_parser)
    
    def _generate_mock_output(self, system_prompt: str, user_prompt: str, config: LLMConfig) -> str:
        """生成Mock输出"""
        
        # 语义完整性检查
        if "语义完整" in system_prompt or "语义完整性" in system_prompt:
            return "1"
        
        # Query改写
        elif "改写助手" in system_prompt or "改写为" in system_prompt:
            if "用户输入：" in user_prompt:
                return user_prompt.split("用户输入：")[-1].split("\n")[0]
            return "我的百家号被封了怎么办"
        
        # 主意图识别
        elif "意图识别助手" in system_prompt and "分类规则" in system_prompt:
            return "1"
        
        # 二级意图识别
        elif "二级意图识别" in system_prompt:
            return "8"
        
        # 账号异常识别
        elif "账号异常" in system_prompt and "判断用户" in system_prompt:
            return "1"
        
        # 高危言论
        elif "高危言论" in system_prompt:
            return "-1"
        
        # 情绪检查
        elif "情绪分析" in system_prompt or "纯情绪" in system_prompt:
            return "-1"
        
        # JSON格式输出
        elif config.output_parser == "json":
            return json.dumps({
                "answer": "这是Mock回复内容",
                "knowledge_indexes": "1,2"
            }, ensure_ascii=False)
        
        # 分类任务
        elif config.output_parser == "classification":
            return "1"
        
        # 默认文本任务
        else:
            return "这是Mock回复内容，帮助您解决问题。"
    
    def _parse_output(self, output: str, parser: str) -> Dict[str, Any]:
        """解析LLM输出"""
        
        if parser == "json":
            try:
                parsed = json.loads(output)
                return {"output": output, "parsed": parsed}
            except:
                return {"output": output, "parsed": {}}
        
        elif parser == "classification":
            # 分类任务，提取数字
            import re
            match = re.search(r'[-]?\d+', output)
            classification_id = match.group() if match else "-1"
            return {"output": classification_id, "classification_id": classification_id}
        
        else:
            # 文本任务，直接返回
            return {"output": output}
