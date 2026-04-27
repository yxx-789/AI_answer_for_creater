#!/usr/bin/env python3
"""
本地测试脚本 - 测试对话功能
"""

import sys
import asyncio
from pathlib import Path

# 设置路径
ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")
sys.path.insert(0, str(ROOT_DIR))

from core.engine import DAGEngine
from core.yml_parser import YMLParser

async def test_simple_conversation():
    """测试简化场景"""
    print("=" * 60)
    print("🧪 测试简化场景")
    print("=" * 60)
    
    # 加载简化场景
    scenarios_dir = ROOT_DIR / "data" / "scenarios"
    parser = YMLParser(str(scenarios_dir))
    scenario = parser.parse_scenario(scenarios_dir / "test_simple.yml")
    
    if not scenario:
        print("❌ 场景加载失败")
        return False
    
    print(f"✅ 场景加载成功: {scenario.scene_name}")
    print(f"   节点数: {len(scenario.nodes)}")
    
    # 创建引擎
    engine = DAGEngine()
    
    # 测试问题
    test_questions = [
        "你好",
        "我的账号怎么了？",
        "为什么我的账号被莫名其妙封禁了？",
        "别搞笑了好吗？"
    ]
    
    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"📝 测试问题: {question}")
        print(f"{'='*60}")
        
        try:
            # 执行对话
            initial_vars = {"raw_query": question}
            result = await engine.execute_scenario(scenario, initial_vars)
            
            # 提取回复
            final_answer = result.get("final_answer", "")
            
            print(f"✅ 执行成功")
            print(f"💬 回复: {final_answer}")
            
            if not final_answer:
                print("⚠️ 警告: 回复为空")
                return False
        
        except Exception as e:
            print(f"❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_simple_conversation())
    sys.exit(0 if success else 1)
