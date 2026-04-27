#!/usr/bin/env python3
"""
完整测试脚本 - 测试所有场景文件
"""

import sys
import asyncio
from pathlib import Path

ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")
sys.path.insert(0, str(ROOT_DIR))

from core.engine import DAGEngine
from core.yml_parser import YMLParser

async def test_all_scenarios():
    """测试所有场景文件"""
    print("=" * 70)
    print("🧪 测试所有场景文件")
    print("=" * 70)
    
    scenarios_dir = ROOT_DIR / "data" / "scenarios"
    parser = YMLParser(str(scenarios_dir))
    
    # 测试简化场景
    print("\n📋 测试1: test_simple.yml (简化场景)")
    print("-" * 70)
    
    simple_scenario = parser.parse_scenario(scenarios_dir / "test_simple.yml")
    
    if not simple_scenario or len(simple_scenario.nodes) == 0:
        print("❌ 简化场景加载失败")
        return False
    
    print(f"✅ 场景加载成功: {simple_scenario.scene_name}")
    print(f"   节点数: {len(simple_scenario.nodes)}")
    print(f"   入口节点: {simple_scenario.entry_node}")
    
    # 测试问题
    test_questions = [
        "你好",
        "我的账号怎么了？",
        "为什么我的账号被莫名其妙封禁了？",
        "别搞笑了好吗？"
    ]
    
    engine = DAGEngine()
    success_count = 0
    
    for idx, question in enumerate(test_questions, 1):
        print(f"\n   测试问题 {idx}: {question}")
        
        try:
            initial_vars = {"raw_query": question}
            result = await engine.execute_scenario(simple_scenario, initial_vars)
            
            final_answer = result.get("final_answer", "")
            
            if final_answer:
                print(f"   ✅ 回复: {final_answer[:60]}...")
                success_count += 1
            else:
                print(f"   ❌ 回复为空")
        
        except Exception as e:
            print(f"   ❌ 执行失败: {e}")
    
    print(f"\n   📊 测试结果: {success_count}/{len(test_questions)} 成功")
    
    if success_count != len(test_questions):
        print("\n❌ 简化场景测试未完全通过")
        return False
    
    # 测试完整场景（只验证加载）
    print("\n" + "=" * 70)
    print("📋 测试2: bailing/main_flow.yml (完整场景 - 仅加载)")
    print("-" * 70)
    
    try:
        main_scenario = parser.parse_scenario(scenarios_dir / "bailing" / "main_flow.yml")
        
        if not main_scenario or len(main_scenario.nodes) == 0:
            print("❌ 完整场景加载失败")
            return False
        
        print(f"✅ 场景加载成功: {main_scenario.scene_name}")
        print(f"   节点数: {len(main_scenario.nodes)}")
        print(f"   入口节点: {main_scenario.entry_node}")
        
        # 显示部分节点
        print(f"   前5个节点:")
        for idx, node_id in enumerate(list(main_scenario.nodes.keys())[:5], 1):
            node = main_scenario.nodes[node_id]
            print(f"      {idx}. {node_id} ({node.node_type.value})")
    
    except Exception as e:
        print(f"❌ 完整场景加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试子Agent
    print("\n" + "=" * 70)
    print("📋 测试3: bailing/agents/penalty_agent.yml (子Agent - 仅加载)")
    print("-" * 70)
    
    try:
        agent_scenario = parser.parse_scenario(scenarios_dir / "bailing" / "agents" / "penalty_agent.yml")
        
        if not agent_scenario or len(agent_scenario.nodes) == 0:
            print("❌ 子Agent加载失败")
            return False
        
        print(f"✅ Agent加载成功: {agent_scenario.scene_name}")
        print(f"   节点数: {len(agent_scenario.nodes)}")
        print(f"   入口节点: {agent_scenario.entry_node}")
    
    except Exception as e:
        print(f"❌ 子Agent加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 总结
    print("\n" + "=" * 70)
    print("✅ 所有测试通过！")
    print("=" * 70)
    print("\n✅ 简化场景: 4/4 测试通过")
    print("✅ 完整场景: 加载成功")
    print("✅ 子Agent: 加载成功")
    print("\n🎉 平台已准备就绪！")
    print("\n启动Web平台:")
    print("  bash start.sh")
    print("\n访问:")
    print("  http://localhost:8501")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_all_scenarios())
    sys.exit(0 if success else 1)
