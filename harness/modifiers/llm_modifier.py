"""
LLM 修改器 - 真正调用 LLM 生成修改建议（严格受控）
"""
import os
import yaml
import json
from pathlib import Path
from typing import Dict, Tuple, Optional
import sys

sys.path.insert(0, str(Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")))

from harness.permissions.permission_checker import PermissionChecker


class LLMModifier:
    """LLM 修改器 - 受控的 AI 修改生成
    
    运行模式：
    - 规则模式（默认）：不依赖外部模型，使用内置规则生成建议
    - LLM 模式：调用真实 LLM API 生成建议
    
    当前状态：
    - 规则模式：✅ 可用
    - LLM 模式：⚠️ 未启用（需要配置 API_KEY）
    """
    
    def __init__(
        self,
        permissions_path: str = 'harness/modification_permissions.yml'
    ):
        self.permission_checker = PermissionChecker(permissions_path)
        self.api_key = self._load_api_key()
        
        # 明确标识当前模式
        self.current_mode = 'LLM' if self.api_key else 'RULE'
        self.mode_description = {
            'RULE': '规则模式（不依赖外部模型）',
            'LLM': 'LLM 模式（调用真实模型）'
        }
    
    def _load_api_key(self) -> Optional[str]:
        """加载 API Key"""
        try:
            from config import API_KEY
            return API_KEY
        except ImportError:
            # 尝试从环境变量加载
            return os.getenv('OPENAI_API_KEY') or os.getenv('API_KEY')
    
    def generate_modification_suggestion(
        self,
        target_file: str,
        field_path: str,
        current_value: any,
        modification_goal: str,
        scenario_name: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        生成修改建议（而不是直接修改）
        
        Args:
            target_file: 目标文件
            field_path: 字段路径
            current_value: 当前值
            modification_goal: 修改目标
            scenario_name: 场景名称
        
        Returns:
            (success, result)
            result = {
                'suggestion': ...,
                'reason': ...,
                'new_value': ...,
                'allowed': True/False
            }
        """
        print()
        print("=" * 70)
        print("🤖 LLM 修改建议生成器")
        print("=" * 70)
        
        # Step 1: 权限预检查
        print("\n[Step 1] 权限预检查...")
        is_allowed, level, reason = self.permission_checker.check_file_permission(target_file)
        
        if not is_allowed:
            print(f"❌ 权限拒绝: {reason}")
            return False, {
                'allowed': False,
                'reason': f"权限拒绝: {reason}",
                'suggestion': None,
                'new_value': None
            }
        
        print(f"✅ 权限通过 (级别: {level})")
        
        # Step 2: 检查节点级权限（如果是修改场景文件）
        if scenario_name and field_path.startswith('nodes.'):
            keys = field_path.split('.')
            if len(keys) >= 2:
                node_name = keys[1]
                field_name = keys[-1]
                
                is_allowed, node_level, node_reason = self.permission_checker.check_node_permission(
                    scenario_name, node_name
                )
                
                if not is_allowed:
                    print(f"❌ 节点权限拒绝: {node_reason}")
                    return False, {
                        'allowed': False,
                        'reason': f"节点权限拒绝: {node_reason}",
                        'suggestion': None,
                        'new_value': None
                    }
                
                if node_level == 'L2':
                    is_allowed, field_reason = self.permission_checker.check_field_permission(
                        scenario_name, node_name, field_name
                    )
                    
                    if not is_allowed:
                        print(f"❌ 字段权限拒绝: {field_reason}")
                        return False, {
                            'allowed': False,
                            'reason': f"字段权限拒绝: {field_reason}",
                            'suggestion': None,
                            'new_value': None
                        }
        
        print(f"✅ 节点/字段权限检查通过")
        
        # Step 3: 生成修改建议
        print("\n[Step 2] 生成修改建议...")
        
        # 显示当前模式
        print(f"当前模式: {self.mode_description[self.current_mode]}")
        
        # 检查是否有 API Key
        if not self.api_key:
            print("⚠️ 未配置 API_KEY，使用规则模式")
            return self._generate_rule_based_suggestion(
                field_path, current_value, modification_goal
            )
        
        # 有 API Key，调用 LLM
        print("📡 调用 LLM 生成建议...")
        return self._call_llm_for_suggestion(
            target_file, field_path, current_value, modification_goal
        )
    
    def _generate_rule_based_suggestion(
        self,
        field_path: str,
        current_value: any,
        modification_goal: str
    ) -> Tuple[bool, Dict]:
        """基于规则的修改建议（无 LLM 时的备选方案）"""
        
        # 简单规则：temperature 调整
        if 'temperature' in field_path:
            if '降低随机性' in modification_goal or '更确定' in modification_goal:
                new_value = max(0.0, float(current_value) - 0.1)
                return True, {
                    'allowed': True,
                    'reason': f"降低 temperature 可减少输出随机性",
                    'suggestion': f"将 temperature 从 {current_value} 降低到 {new_value:.2f}",
                    'new_value': round(new_value, 2)
                }
            elif '提高多样性' in modification_goal or '更有创意' in modification_goal:
                new_value = min(1.0, float(current_value) + 0.1)
                return True, {
                    'allowed': True,
                    'reason': f"提高 temperature 可增加输出多样性",
                    'suggestion': f"将 temperature 从 {current_value} 提高到 {new_value:.2f}",
                    'new_value': round(new_value, 2)
                }
        
        # 默认：无建议
        return False, {
            'allowed': True,
            'reason': "未找到适用的修改规则",
            'suggestion': None,
            'new_value': None
        }
    
    def _call_llm_for_suggestion(
        self,
        target_file: str,
        field_path: str,
        current_value: any,
        modification_goal: str
    ) -> Tuple[bool, Dict]:
        """调用 LLM 生成修改建议"""
        
        try:
            # 使用百度千帆 API（OpenAI 兼容）
            from openai import OpenAI
            
            # 配置百度千帆端点
            base_url = os.getenv('OPENAI_BASE_URL', 'https://qianfan.baidubce.com/v2')
            
            client = OpenAI(
                api_key=self.api_key,
                base_url=base_url
            )
            
            prompt = f"""你是一个 AI 客服系统优化助手。现在需要修改一个配置字段。

目标文件: {target_file}
字段路径: {field_path}
当前值: {current_value}
修改目标: {modification_goal}

请分析并给出修改建议。要求：
1. 只能建议修改这个特定字段，不能建议修改其他字段
2. 必须给出具体的新值
3. 必须说明修改原因

请以 JSON 格式返回：
{{
  "reason": "修改原因",
  "suggestion": "修改建议的描述",
  "new_value": 新值
}}
"""
            
            response = client.chat.completions.create(
                model=os.getenv('MODEL_NAME', 'ernie-3.5-8k'),
                messages=[
                    {"role": "system", "content": "你是一个专业的 AI 配置优化助手，擅长调整 AI 客服系统参数。请用 JSON 格式返回结果。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # 解析 JSON
            # 尝试提取 JSON 块
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].split('```')[0].strip()
            
            result = json.loads(result_text)
            
            print(f"✅ LLM 建议生成成功")
            print(f"   原因: {result.get('reason', 'N/A')}")
            print(f"   建议: {result.get('suggestion', 'N/A')}")
            print(f"   新值: {result.get('new_value', 'N/A')}")
            
            return True, {
                'allowed': True,
                'reason': result.get('reason', ''),
                'suggestion': result.get('suggestion', ''),
                'new_value': result.get('new_value')
            }
            
        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            print("   回退到规则模式...")
            return self._generate_rule_based_suggestion(
                field_path, current_value, modification_goal
            )
    
    def get_mode_info(self) -> Dict:
        """
        获取当前模式信息
        
        Returns:
            {
                'current_mode': 'RULE' | 'LLM',
                'description': '...',
                'llm_available': True | False,
                'switch_instructions': '...'
            }
        """
        return {
            'current_mode': self.current_mode,
            'description': self.mode_description[self.current_mode],
            'llm_available': self.api_key is not None,
            'switch_instructions': (
                "切换到 LLM 模式需要：\n"
                "1. 在 config.py 中设置 API_KEY = 'your-api-key'\n"
                "2. 或设置环境变量 OPENAI_API_KEY 或 API_KEY\n"
                "3. 可选：设置 OPENAI_BASE_URL 指向兼容的 API 端点\n"
                "4. 可选：设置 MODEL_NAME 指定模型名称（默认 gpt-3.5-turbo）"
            ),
            'permission_control': (
                "LLM 修改器的权限控制：\n"
                "1. 所有修改建议生成前，必须通过 PermissionChecker 检查\n"
                "2. 只能对指定文件（target_file）和指定字段（field_path）生成建议\n"
                "3. LLM 无法绕过权限直接修改文件\n"
                "4. 如果 LLM 调用失败，自动回退到规则模式"
            )
        }


# 测试
if __name__ == '__main__':
    print("测试 LLM 修改器")
    
    modifier = LLMModifier()
    
    # 测试1：尝试生成不允许文件的修改建议
    print("\n" + "=" * 70)
    print("测试1：尝试为禁止文件生成修改建议")
    print("=" * 70)
    success, result = modifier.generate_modification_suggestion(
        target_file='core/engine.py',
        field_path='test_field',
        current_value='test',
        modification_goal='测试'
    )
    print(f"\n结果: {'✅ 成功' if success else '❌ 失败'}")
    print(f"详情: {result}")
    
    # 测试2：为允许文件生成修改建议（使用规则）
    print("\n" + "=" * 70)
    print("测试2：为允许文件生成修改建议（规则模式）")
    print("=" * 70)
    success, result = modifier.generate_modification_suggestion(
        target_file='scenarios/bailing/main_flow.yml',
        field_path='nodes.INTENT_MAIN.config.temperature',
        current_value=0.01,
        modification_goal='降低随机性，让输出更确定',
        scenario_name='main_flow'
    )
    print(f"\n结果: {'✅ 成功' if success else '❌ 失败'}")
    print(f"详情: {result}")
