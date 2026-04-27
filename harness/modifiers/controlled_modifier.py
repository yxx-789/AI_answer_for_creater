"""
受控修改器 - 真正使用权限检查的修改器
不破坏原有 skill_modifier.py，而是新增
"""
import yaml
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
import sys

sys.path.insert(0, str(Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")))

from harness.permissions.permission_checker import PermissionChecker
from harness.sensors.variable_retention import VariableRetentionSensor
from harness.sensors.forbidden_words import ForbiddenWordsSensor
from harness.evals.simple_eval_checker import SimpleEvalChecker
from harness.validators.main_flow_validator import MainFlowValidator


class ControlledModifier:
    """受控修改器 - 真正的权限控制 + 回滚机制 + 主链路验证"""
    
    def __init__(
        self,
        target_file: str,
        permissions_path: str = 'harness/modification_permissions.yml'
    ):
        self.target_file = Path(target_file)
        self.permission_checker = PermissionChecker(permissions_path)
        self.backup_dir = Path('backups')
        self.backup_dir.mkdir(exist_ok=True)
        self.last_backup_path: Optional[Path] = None
        
        # 传感器
        self.var_sensor = VariableRetentionSensor()
        self.word_sensor = ForbiddenWordsSensor()
        
        # Eval 检查器
        self.eval_checker = SimpleEvalChecker()
        
        # 主链路验证器
        self.validator = MainFlowValidator()
    
    def check_permission(self) -> Tuple[bool, str]:
        """检查是否有权限修改目标文件"""
        return self.permission_checker.check_file_permission(str(self.target_file))
    
    def set_eval_force_fail(self, should_fail: bool, reason: str = ""):
        """设置 eval 强制失败（用于演示）"""
        self.eval_checker.set_force_fail(should_fail, reason)
    
    def backup(self) -> Path:
        """备份文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.backup_dir / f'{self.target_file.stem}_{timestamp}{self.target_file.suffix}'
        shutil.copy(self.target_file, backup_path)
        self.last_backup_path = backup_path
        print(f"✅ 已备份到 {backup_path}")
        return backup_path
    
    def rollback(self) -> bool:
        """回滚到最后一次备份"""
        if not self.last_backup_path or not self.last_backup_path.exists():
            print("❌ 没有可回滚的备份")
            return False
        
        shutil.copy(self.last_backup_path, self.target_file)
        print(f"✅ 已回滚到 {self.last_backup_path}")
        
        # 验证回滚是否成功
        with open(self.last_backup_path, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        with open(self.target_file, 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        if backup_content == current_content:
            print("✅ 回滚验证成功：文件内容已恢复")
            return True
        else:
            print("❌ 回滚验证失败：文件内容不匹配")
            return False
    
    def rollback_with_validation(self) -> Dict:
        """
        回滚并验证主链路
        
        Returns:
            {
                'rollback_executed_successfully': bool,  # 回滚动作是否成功
                'rollback_validation_passed': bool,       # 回滚后主链路验证是否通过
                'message': str,                            # 结果消息
                'alert_level': str                        # 告警等级：'none' / 'warning' / 'critical'
            }
        """
        result = {
            'rollback_executed_successfully': False,
            'rollback_validation_passed': False,
            'message': '',
            'alert_level': 'none'
        }
        
        print("\n[回滚] 执行回滚...")
        rollback_success = self.rollback()
        
        if not rollback_success:
            # 场景1：回滚动作本身失败
            result['message'] = "回滚动作失败"
            result['alert_level'] = 'critical'
            print("❌ 回滚失败")
            return result
        
        result['rollback_executed_successfully'] = True
        
        print("\n[回滚后主链路验证]")
        is_passed, msg, _ = self.validator.validate_after_rollback()
        
        if not is_passed:
            # 场景2：回滚成功，但主链路验证失败
            result['message'] = f"回滚成功，但主链路验证失败: {msg}"
            result['alert_level'] = 'critical'
            print("⚠️ 警告：回滚后主链路验证失败！")
            print(f"   原因: {msg}")
            print("   需要人工介入检查系统状态")
            return result
        
        # 场景3：回滚成功，主链路验证也成功
        result['rollback_validation_passed'] = True
        result['message'] = "回滚成功，主链路正常"
        result['alert_level'] = 'none'
        print("✅ 回滚后主链路验证通过")
        return result
    
    def _handle_rollback(self, error_msg: str) -> Tuple[bool, str]:
        """
        处理回滚并返回统一的失败结果
        
        Args:
            error_msg: 错误消息
        
        Returns:
            (success, message)
        """
        rollback_result = self.rollback_with_validation()
        
        if not rollback_result['rollback_executed_successfully']:
            # 回滚动作失败 - 最高告警等级
            return False, f"{error_msg}，且回滚失败（需要人工介入）"
        elif not rollback_result['rollback_validation_passed']:
            # 回滚成功但主链路验证失败 - 高告警等级
            return False, f"{error_msg}，已回滚但主链路验证失败（需要人工检查）"
        else:
            # 回滚成功且主链路验证通过
            return False, f"{error_msg}，已回滚"
    
    def validate_yaml(self) -> Tuple[bool, str]:
        """验证 YAML 语法"""
        try:
            with open(self.target_file, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            return True, "YAML 语法正确"
        except yaml.YAMLError as e:
            return False, f"YAML 语法错误: {e}"
    
    def run_sensors(self, backup_path: Path) -> Tuple[bool, str]:
        """运行所有传感器检查"""
        # 变量保留检查
        try:
            is_valid, msg = self.var_sensor.check(str(backup_path), str(self.target_file))
            if not is_valid:
                return False, f"变量保留检查失败: {msg}"
        except Exception as e:
            return False, f"变量保留检查异常: {e}"
        
        # 禁止词检查
        try:
            result = self.word_sensor.check(str(self.target_file))
            # 禁止词传感器返回 3 个值
            if isinstance(result, tuple) and len(result) == 3:
                is_valid, msg, found_words = result
            elif isinstance(result, tuple):
                is_valid, msg = result[0], result[1] if len(result) > 1 else 'Unknown'
            else:
                is_valid, msg = result, 'Unknown'
            
            if not is_valid:
                return False, f"禁止词检查失败: {msg}"
        except Exception as e:
            return False, f"禁止词检查异常: {e}"
        
        return True, "所有传感器检查通过"
    
    def modify_field(
        self,
        field_path: str,
        new_value: any,
        scenario_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        修改指定字段
        
        标准流程：
        1. 修改前主链路验证
        2. 权限检查
        3. 备份
        4. 读取文件
        5. 节点权限检查
        6. 执行修改
        7. 写入文件
        8. YAML 语法验证
        9. 传感器检查
        10. Eval 评估
        11. 修改后主链路验证
        12. 成功保留
        
        任何步骤失败则回滚，回滚后再次验证主链路
        
        Args:
            field_path: 字段路径，如 "nodes.INTENT_MAIN.config.temperature"
            new_value: 新值
            scenario_name: 场景名称（用于节点级权限检查）
        
        Returns:
            (success, message)
        """
        print()
        print("=" * 70)
        print(f"🔧 开始修改: {self.target_file.name}")
        print("=" * 70)
        
        # Step 1: 修改前主链路验证
        print("\n[Step 1] 修改前主链路验证...")
        is_passed, msg, _ = self.validator.validate_before_modify()
        if not is_passed:
            print(f"❌ 主链路验证失败，终止修改")
            print(f"   原因: {msg}")
            return False, f"修改前主链路验证失败: {msg}"
        
        # Step 2: 检查文件级权限
        print("\n[Step 2] 检查文件级权限...")
        is_allowed, level, reason = self.check_permission()
        
        if not is_allowed:
            print(f"❌ 权限拒绝: {reason}")
            return False, f"权限拒绝: {reason}"
        
        print(f"✅ 权限通过 (级别: {level})")
        print(f"   原因: {reason}")
        
        # Step 3: 备份
        print("\n[Step 3] 备份当前文件...")
        backup_path = self.backup()
        
        # Step 4: 读取文件
        print("\n[Step 4] 读取文件内容...")
        try:
            with open(self.target_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 读取失败: {e}")
            return self._handle_rollback(f"读取失败: {e}")
        
        # Step 5: 解析字段路径并检查节点权限
        print("\n[Step 5] 解析字段路径并检查权限...")
        keys = field_path.split('.')
        
        # 如果是修改节点，检查节点级权限
        if len(keys) >= 2 and keys[0] == 'nodes' and scenario_name:
            node_name = keys[1]
            field_name = keys[-1]  # 最后一个key是字段名
            
            # 检查节点权限
            is_allowed, node_level, node_reason = self.permission_checker.check_node_permission(
                scenario_name, node_name
            )
            
            if not is_allowed:
                print(f"❌ 节点权限拒绝: {node_reason}")
                return self._handle_rollback(f"节点权限拒绝: {node_reason}")
            
            # 如果是 L2 权限，检查字段权限
            if node_level == 'L2':
                is_allowed, field_reason = self.permission_checker.check_field_permission(
                    scenario_name, node_name, field_name
                )
                
                if not is_allowed:
                    print(f"❌ 字段权限拒绝: {field_reason}")
                    return self._handle_rollback(f"字段权限拒绝: {field_reason}")
                
                print(f"✅ 字段权限通过: {field_reason}")
            else:
                print(f"✅ 节点权限通过 (级别: {node_level})")
        
        # Step 6: 修改字段
        print(f"\n[Step 6] 修改字段: {field_path}")
        try:
            current = data
            for key in keys[:-1]:
                if key not in current:
                    print(f"❌ 字段路径不存在: {key}")
                    return self._handle_rollback(f"字段路径不存在: {key}")
                current = current[key]
            
            old_value = current[keys[-1]]
            current[keys[-1]] = new_value
            
            print(f"   旧值: {old_value}")
            print(f"   新值: {new_value}")
        except Exception as e:
            print(f"❌ 修改失败: {e}")
            return self._handle_rollback(f"修改失败: {e}")
        
        # Step 7: 写入文件
        print("\n[Step 7] 写入文件...")
        try:
            with open(self.target_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
            print("✅ 文件已写入")
        except Exception as e:
            print(f"❌ 写入失败: {e}")
            return self._handle_rollback(f"写入失败: {e}")
        
        # Step 8: 验证 YAML 语法
        print("\n[Step 8] 验证 YAML 语法...")
        is_valid, msg = self.validate_yaml()
        if not is_valid:
            print(f"❌ {msg}")
            return self._handle_rollback(msg)
        print(f"✅ {msg}")
        
        # Step 9: 运行传感器
        print("\n[Step 9] 运行传感器检查...")
        is_valid, msg = self.run_sensors(backup_path)
        if not is_valid:
            print(f"❌ {msg}")
            return self._handle_rollback(msg)
        print(f"✅ {msg}")
        
        # Step 10: Eval 评估
        print("\n[Step 10] 运行 Eval 评估...")
        is_passed, msg, details = self.eval_checker.evaluate(
            str(self.target_file),
            field_path,
            new_value
        )
        if not is_passed:
            print(f"❌ {msg}")
            return self._handle_rollback(msg)
        print(f"✅ {msg}")
        
        # Step 11: 修改后主链路验证
        print("\n[Step 11] 修改后主链路验证...")
        is_passed, msg, _ = self.validator.validate_after_modify()
        if not is_passed:
            print(f"❌ 修改后主链路验证失败")
            print(f"   原因: {msg}")
            return self._handle_rollback(f"修改后主链路验证失败: {msg}")
        
        # Step 12: 成功
        print()
        print("=" * 70)
        print("✅ 修改成功并保留")
        print("=" * 70)
        return True, "修改成功"
