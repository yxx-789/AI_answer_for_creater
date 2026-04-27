"""
简单的 Eval 检查器 - 用于验证修改效果
"""
import yaml
from pathlib import Path
from typing import Tuple, Dict, Optional


class SimpleEvalChecker:
    """
    简单的 Eval 检查器
    
    用于验证修改后的场景是否能正常工作
    当前实现使用规则检查，未来可扩展为真实场景执行评估
    """
    
    def __init__(self):
        self.evaluation_rules = {
            # 规则1：temperature 不能超过 1.0
            'temperature_range': {
                'field': 'nodes.INTENT_MAIN.config.temperature',
                'condition': lambda x: 0.0 <= x <= 1.0,
                'message': 'temperature 必须在 [0.0, 1.0] 范围内'
            },
            # 规则2：temperature 不能是负数（演示用）
            'temperature_positive': {
                'field': 'nodes.INTENT_MAIN.config.temperature',
                'condition': lambda x: x >= 0.0,
                'message': 'temperature 不能是负数'
            }
        }
        
        # 可以通过参数控制 eval 是否失败（用于演示）
        self.force_fail = False
        self.force_fail_reason = "强制 eval 失败（演示用）"
    
    def set_force_fail(self, should_fail: bool, reason: str = ""):
        """设置强制失败（用于演示）"""
        self.force_fail = should_fail
        if reason:
            self.force_fail_reason = reason
    
    def evaluate(
        self,
        scenario_path: str,
        modified_field: Optional[str] = None,
        new_value: Optional[any] = None
    ) -> Tuple[bool, str, Dict]:
        """
        评估修改效果
        
        Args:
            scenario_path: 场景文件路径
            modified_field: 修改的字段路径
            new_value: 新值
        
        Returns:
            (is_passed, message, details)
        """
        print()
        print("=" * 70)
        print("📊 Eval 评估启动")
        print("=" * 70)
        print(f"场景文件: {scenario_path}")
        if modified_field:
            print(f"修改字段: {modified_field}")
            print(f"新值: {new_value}")
        
        details = {
            'scenario_path': scenario_path,
            'modified_field': modified_field,
            'new_value': new_value,
            'rules_checked': 0,
            'rules_passed': 0,
            'rules_failed': [],
            'force_fail': self.force_fail
        }
        
        # 检查是否强制失败
        if self.force_fail:
            print()
            print(f"❌ Eval 评估失败: {self.force_fail_reason}")
            details['rules_failed'].append(self.force_fail_reason)
            return False, self.force_fail_reason, details
        
        # 加载场景文件
        try:
            with open(scenario_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 场景文件加载失败: {e}")
            return False, f"场景文件加载失败: {e}", details
        
        # 运行评估规则
        print()
        print("运行评估规则...")
        
        for rule_name, rule_config in self.evaluation_rules.items():
            field_path = rule_config['field']
            condition = rule_config['condition']
            message = rule_config['message']
            
            # 如果修改的字段与规则相关，才检查
            if modified_field and field_path != modified_field:
                continue
            
            details['rules_checked'] += 1
            
            # 提取字段值
            try:
                keys = field_path.split('.')
                current = data
                for key in keys:
                    current = current[key]
                field_value = current
            except (KeyError, TypeError):
                print(f"  ⚠️ 规则 '{rule_name}': 字段不存在，跳过")
                continue
            
            # 检查条件
            try:
                is_passed = condition(field_value)
            except Exception as e:
                print(f"  ❌ 规则 '{rule_name}': 检查异常 - {e}")
                details['rules_failed'].append(f"{rule_name}: {e}")
                continue
            
            if is_passed:
                print(f"  ✅ 规则 '{rule_name}': 通过")
                details['rules_passed'] += 1
            else:
                print(f"  ❌ 规则 '{rule_name}': 失败 - {message}")
                details['rules_failed'].append(f"{rule_name}: {message}")
        
        # 判断是否通过
        is_passed = len(details['rules_failed']) == 0 and details['rules_checked'] > 0
        
        print()
        if is_passed:
            print(f"✅ Eval 评估通过 ({details['rules_passed']}/{details['rules_checked']} 规则通过)")
            return True, "Eval 评估通过", details
        else:
            print(f"❌ Eval 评估失败 ({len(details['rules_failed'])} 个规则失败)")
            return False, f"Eval 评估失败: {'; '.join(details['rules_failed'])}", details


# 测试
if __name__ == '__main__':
    checker = SimpleEvalChecker()
    
    print("测试1：正常评估")
    is_passed, msg, details = checker.evaluate(
        'scenarios/bailing/main_flow.yml',
        'nodes.INTENT_MAIN.config.temperature',
        0.5
    )
    print(f"\n结果: {'✅ 通过' if is_passed else '❌ 失败'}")
    print(f"消息: {msg}")
    
    print("\n" + "=" * 70)
    print("测试2：强制失败")
    checker.set_force_fail(True, "演示 eval 失败回滚")
    is_passed, msg, details = checker.evaluate(
        'scenarios/bailing/main_flow.yml',
        'nodes.INTENT_MAIN.config.temperature',
        0.5
    )
    print(f"\n结果: {'✅ 通过' if is_passed else '❌ 失败'}")
    print(f"消息: {msg}")
