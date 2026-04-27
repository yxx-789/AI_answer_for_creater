"""
变量管理器
负责对话过程中所有变量的存储、读取、映射
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import json
import re


@dataclass
class VariableManager:
    """
    变量管理器
    管理对话过程中的所有变量状态
    """
    # 变量存储
    variables: Dict[str, Any] = field(default_factory=dict)
    
    def set(self, name: str, value: Any):
        """设置变量值"""
        self.variables[name] = value
    
    def get(self, name: str, default: Any = None) -> Any:
        """获取变量值"""
        return self.variables.get(name, default)
    
    def set_batch(self, mapping: Dict[str, Any]):
        """批量设置变量"""
        self.variables.update(mapping)
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有变量"""
        return self.variables.copy()
    
    def resolve_value(self, value_template: str) -> str:
        """
        解析变量引用
        支持 {{variable}} 格式的变量插值
        
        Args:
            value_template: 包含变量占位符的字符串
        
        Returns:
            解析后的字符串
        """
        if not isinstance(value_template, str):
            return str(value_template)
        
        # 匹配 {{var}} 或 {{var.nested}}
        pattern = r'\{\{([^}]+)\}\}'
        
        def replace(match):
            var_path = match.group(1).strip()
            return str(self._resolve_path(var_path))
        
        return re.sub(pattern, replace, value_template)
    
    def _resolve_path(self, path: str) -> Any:
        """
        解析变量路径
        支持: var_name, var_name.field, var_name[0]
        """
        parts = re.split(r'\.|\[|\]', path)
        parts = [p for p in parts if p]  # 去除空字符串
        
        if not parts:
            return None
        
        # 获取根变量
        value = self.variables.get(parts[0])
        
        # 逐层访问
        for part in parts[1:]:
            if value is None:
                return None
            
            # 尝试字典访问
            if isinstance(value, dict):
                value = value.get(part)
            # 尝试列表索引
            elif isinstance(value, list) and part.isdigit():
                idx = int(part)
                value = value[idx] if idx < len(value) else None
            # 尝试对象属性
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
        
        return value
    
    def map_inputs(self, input_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        根据映射关系提取输入参数
        
        Args:
            input_mapping: {"参数名": "变量来源"}
            例如: {"query": "rewrite_query", "user_info": "user_list"}
        
        Returns:
            {"参数名": 实际值}
        """
        result = {}
        for param_name, var_source in input_mapping.items():
            result[param_name] = self._resolve_path(var_source)
        return result
    
    def apply_outputs(self, outputs: Dict[str, Any], output_mapping: Dict[str, str]):
        """
        应用节点输出到变量
        
        Args:
            outputs: {"输出名": 值}
            output_mapping: {"输出名": "存储变量名"}
            例如: {"output": "final_answer", "classification_id": "main_intent_id"}
        """
        print(f"[变量映射] outputs={outputs}, output_mapping={output_mapping}")
        for output_name, var_name in output_mapping.items():
            if output_name in outputs:
                self.variables[var_name] = outputs[output_name]
                print(f"[变量映射] {var_name} = {outputs[output_name]}")
    
    def evaluate_expression(self, expression: str) -> bool:
        """
        评估Python表达式（用于条件判断）
        
        Args:
            expression: Python表达式，可以引用变量
        
        Returns:
            表达式的布尔值
        """
        try:
            # 创建安全的执行环境
            safe_dict = self.variables.copy()
            # 添加常用函数和常量
            safe_dict['len'] = len
            safe_dict['str'] = str
            safe_dict['int'] = int
            safe_dict['float'] = float
            safe_dict['any'] = any
            safe_dict['all'] = all
            safe_dict['true'] = True
            safe_dict['false'] = False
            safe_dict['True'] = True
            safe_dict['False'] = False
            
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return bool(result)
        
        except Exception as e:
            print(f"表达式评估失败: {expression}, 错误: {e}")
            return False
    
    def to_json(self) -> str:
        """导出为JSON字符串"""
        return json.dumps(self.variables, ensure_ascii=False, indent=2)
    
    def from_json(self, json_str: str):
        """从JSON字符串导入"""
        self.variables = json.loads(json_str)
    
    def __repr__(self):
        return f"VariableManager(variables={len(self.variables)} items)"


# 使用示例
if __name__ == '__main__':
    # 创建变量管理器
    vm = VariableManager()
    
    # 设置变量
    vm.set("raw_query", "我的号被封了")
    vm.set("user_list", ["非鼓励层", "工时内", "用户账号状态:暂未发现异常"])
    vm.set("main_intent_id", "1")
    vm.set("api_result", {
        "code": 0,
        "data": {
            "conditionDescList": ["非鼓励层", "高权益"]
        }
    })
    
    # 测试变量插值
    print("=== 变量插值测试 ===")
    template = "用户问题：{{raw_query}}，意图ID：{{main_intent_id}}"
    print(f"模板: {template}")
    print(f"解析: {vm.resolve_value(template)}")
    
    # 测试路径解析
    print("\n=== 路径解析测试 ===")
    print(f"api_result.data.conditionDescList: {vm._resolve_path('api_result.data.conditionDescList')}")
    print(f"api_result.data.conditionDescList[0]: {vm._resolve_path('api_result.data.conditionDescList[0]')}")
    
    # 测试输入映射
    print("\n=== 输入映射测试 ===")
    input_mapping = {
        "query": "raw_query",
        "conditions": "api_result.data.conditionDescList"
    }
    print(f"映射: {vm.map_inputs(input_mapping)}")
    
    # 测试表达式评估
    print("\n=== 表达式评估测试 ===")
    expressions = [
        "main_intent_id == '1'",
        "'工时内' in user_list",
        "len(user_list) > 2",
        "any('权益' in item for item in user_list)"
    ]
    for expr in expressions:
        result = vm.evaluate_expression(expr)
        print(f"{expr} → {result}")
    
    # 测试输出映射
    print("\n=== 输出映射测试 ===")
    outputs = {
        "classification_id": "8",
        "output": "账号异常问题"
    }
    output_mapping = {
        "classification_id": "secondary_intent_id",
        "output": "classification_result"
    }
    vm.apply_outputs(outputs, output_mapping)
    print(f"应用后变量: {vm.get_all()}")
