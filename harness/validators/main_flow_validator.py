"""
主链路验证器 - 可被代码调用的验证模块
"""
import subprocess
import sys
from pathlib import Path
from typing import Tuple, List, Dict
from datetime import datetime


class MainFlowValidator:
    """
    主链路验证器
    
    将 verify_main_flow.sh 的验证逻辑封装成可被代码调用的模块
    """
    
    def __init__(self, script_path: str = 'verify_main_flow.sh'):
        self.script_path = Path(script_path)
        self.last_results = []
    
    def validate(self, stage: str = "unknown") -> Tuple[bool, str, Dict]:
        """
        执行主链路验证
        
        Args:
            stage: 当前阶段（如 "before"、"after"、"after_rollback"）
        
        Returns:
            (is_passed, summary, structured_result)
        """
        timestamp = datetime.now().isoformat()
        
        structured_result = {
            'stage': stage,
            'is_passed': False,
            'pass_count': 0,
            'fail_count': 0,
            'exit_code': -1,
            'timestamp': timestamp,
            'summary': '',
            'details': []
        }
        
        print()
        print("=" * 70)
        print(f"🔍 主链路验证 [{stage}]")
        print("=" * 70)
        
        # 执行验证脚本
        try:
            result = subprocess.run(
                ['bash', str(self.script_path)],
                capture_output=True,
                text=True,
                cwd=Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2"),
                timeout=60
            )
            
            output = result.stdout
            self.last_results = output.split('\n')
            
            # 解析结果
            is_passed = result.returncode == 0
            structured_result['exit_code'] = result.returncode
            structured_result['is_passed'] = is_passed
            
            # 提取通过/失败数量
            pass_count, fail_count = self._extract_counts(output)
            structured_result['pass_count'] = pass_count
            structured_result['fail_count'] = fail_count
            
            # 提取摘要
            summary = self._extract_summary(output)
            structured_result['summary'] = summary
            
            if is_passed:
                print(f"✅ 主链路验证通过 [{stage}]")
            else:
                print(f"❌ 主链路验证失败 [{stage}]")
            
            print(f"   {summary}")
            
            return is_passed, summary, structured_result
            
        except subprocess.TimeoutExpired:
            msg = "验证超时"
            print(f"❌ 主链路验证超时 [{stage}]")
            structured_result['summary'] = msg
            return False, msg, structured_result
        except Exception as e:
            msg = f"验证异常: {e}"
            print(f"❌ 主链路验证异常 [{stage}]: {e}")
            structured_result['summary'] = msg
            return False, msg, structured_result
    
    def _extract_counts(self, output: str) -> Tuple[int, int]:
        """提取通过和失败数量"""
        pass_count = 0
        fail_count = 0
        
        for line in output.split('\n'):
            if '通过:' in line:
                try:
                    pass_count = int(line.split('通过:')[1].strip())
                except:
                    pass
            if '失败:' in line:
                try:
                    fail_count = int(line.split('失败:')[1].strip())
                except:
                    pass
        
        return pass_count, fail_count
    
    def _extract_summary(self, output: str) -> str:
        """提取验证结果摘要"""
        pass_count = 0
        fail_count = 0
        
        for line in output.split('\n'):
            if '通过:' in line:
                try:
                    pass_count = int(line.split('通过:')[1].strip())
                except:
                    pass
            if '失败:' in line:
                try:
                    fail_count = int(line.split('失败:')[1].strip())
                except:
                    pass
        
        # 生成有信息量的摘要
        if fail_count == 0:
            return f"主链路验证通过：{pass_count}/{pass_count}"
        else:
            return f"主链路验证失败：{pass_count}/{pass_count + fail_count}（{fail_count}项失败）"
    
    def validate_before_modify(self) -> Tuple[bool, str]:
        """修改前验证"""
        return self.validate("修改前")
    
    def validate_after_modify(self) -> Tuple[bool, str]:
        """修改后验证"""
        return self.validate("修改后")
    
    def validate_after_rollback(self) -> Tuple[bool, str]:
        """回滚后验证"""
        return self.validate("回滚后")


# 测试
if __name__ == '__main__':
    print("测试主链路验证器")
    
    validator = MainFlowValidator()
    
    # 测试修改前验证
    is_passed, summary, _ = validator.validate_before_modify()
    print(f"\n结果: {'✅ 通过' if is_passed else '❌ 失败'}")
    print(f"摘要: {summary}")
