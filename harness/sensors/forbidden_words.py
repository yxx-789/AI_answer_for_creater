"""
Harness传感器 - 禁止词检查
"""
import yaml
from typing import Dict, List, Tuple

class ForbiddenWordsSensor:
    """检查Skill中是否引入了禁止词"""

    def __init__(self):
        # 禁止词列表（示例）
        # 注意：以下词汇在特定上下文中是合理的业务术语，不应被禁止
        # "投诉/举报/曝光" 在高危言论识别场景中是合理关键词
        # "人工客服/转人工" 是正常业务词汇
        self.forbidden_words = [
            '绝对', '一定保证', '承诺解决',  # 过度承诺
            '赔偿', '退款保证', '补偿承诺',  # 过度承诺
        ]

        # 敏感词列表（需人工审核但不自动拒绝）
        self.sensitive_words = [
            '政治', '暴力', '色情', '违法'
        ]

    def check(self, skill_path: str) -> Tuple[bool, str, List[str]]:
        """
        检查禁止词

        Returns:
            (is_valid, message, found_words)
        """
        with open(skill_path, 'r', encoding='utf-8') as f:
            skill = yaml.safe_load(f)

        found_forbidden = []
        found_sensitive = []

        nodes = skill.get('nodes', {})
        for node_id, node_config in nodes.items():
            # 检查模板内容
            if 'config' in node_config:
                template = node_config['config'].get('template', '')
                system_prompt = node_config['config'].get('system_prompt', '')
                user_prompt = node_config['config'].get('user_prompt_template', '')

                # 合并所有文本
                all_text = f"{template} {system_prompt} {user_prompt}"

                # 检查禁止词
                for word in self.forbidden_words:
                    if word in all_text:
                        found_forbidden.append((node_id, word))

                # 检查敏感词
                for word in self.sensitive_words:
                    if word in all_text:
                        found_sensitive.append((node_id, word))

        # 生成报告
        if found_forbidden:
            words_str = ', '.join([f"{node}:{word}" for node, word in found_forbidden])
            return False, f"❌ 发现禁止词: {words_str}", found_forbidden

        if found_sensitive:
            words_str = ', '.join([f"{node}:{word}" for node, word in found_sensitive])
            return True, f"⚠️ 发现敏感词（需人工审核）: {words_str}", found_sensitive

        return True, "✅ 禁止词检查通过", []


# 测试
if __name__ == '__main__':
    sensor = ForbiddenWordsSensor()

    print("测试禁止词检查")
    is_valid, msg, words = sensor.check('test_skill.yml')
    print(f"  结果: {msg}")
    if words:
        print(f"  发现: {words}")