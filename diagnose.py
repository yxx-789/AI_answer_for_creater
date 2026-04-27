#!/usr/bin/env python3
"""
快速诊断脚本 - 检查项目配置和依赖
"""

import sys
from pathlib import Path

ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")

def check_project():
    """检查项目完整性"""
    print("🔍 AI客服运营平台 - 快速诊断")
    print("=" * 60)
    
    issues = []
    
    # 1. 检查目录结构
    print("\n📁 检查目录结构...")
    required_dirs = [
        "app/pages",
        "core",
        "core/node_executors",
        "config",
        "data/scenarios",
        "data/knowledge",
        "data/traces",
        "data/bad_cases",
        "code_functions"
    ]
    
    for dir_path in required_dirs:
        full_path = ROOT_DIR / dir_path
        if full_path.exists():
            print(f"  ✅ {dir_path}")
        else:
            print(f"  ❌ {dir_path} - 不存在")
            issues.append(f"缺失目录: {dir_path}")
    
    # 2. 检查关键文件
    print("\n📄 检查关键文件...")
    required_files = [
        "app/main.py",
        "config/config.py",
        "config/api_config.py",
        "config/models.py",
        "core/engine.py",
        "core/yml_parser.py",
        "core/node_executors/llm_executor.py",
        "code_functions/bailing_functions.py",
        "data/scenarios/test_simple.yml"
    ]
    
    for file_path in required_files:
        full_path = ROOT_DIR / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - 不存在")
            issues.append(f"缺失文件: {file_path}")
    
    # 3. 检查API配置
    print("\n⚙️ 检查API配置...")
    try:
        sys.path.insert(0, str(ROOT_DIR))
        from config.api_config import API_KEY, API_URL
        from config.models import MODELS, DEFAULT_MODEL
        
        if API_KEY and len(API_KEY) > 20:
            print(f"  ✅ API_KEY: {API_KEY[:20]}...")
        else:
            print(f"  ❌ API_KEY 未配置")
            issues.append("API_KEY 未配置")
        
        print(f"  ✅ API_URL: {API_URL}")
        print(f"  ✅ 默认模型: {DEFAULT_MODEL}")
        print(f"  ✅ 可用模型: {len(MODELS)} 个")
    
    except Exception as e:
        print(f"  ❌ 配置加载失败: {e}")
        issues.append(f"配置加载失败: {e}")
    
    # 4. 检查场景文件
    print("\n📝 检查场景文件...")
    scenarios_dir = ROOT_DIR / "data" / "scenarios"
    scenario_files = list(scenarios_dir.glob("**/*.yml"))
    
    if scenario_files:
        print(f"  ✅ 找到 {len(scenario_files)} 个场景文件")
        for sf in scenario_files[:5]:
            print(f"     - {sf.relative_to(scenarios_dir)}")
    else:
        print(f"  ❌ 未找到场景文件")
        issues.append("未找到场景文件")
    
    # 5. 测试场景解析
    print("\n🔧 测试场景解析...")
    try:
        from core.yml_parser import YMLParser
        
        parser = YMLParser(str(scenarios_dir))
        test_scenario = parser.parse_scenario(scenarios_dir / "test_simple.yml")
        
        if test_scenario:
            print(f"  ✅ 场景解析成功: {test_scenario.scene_name}")
            print(f"     节点数: {len(test_scenario.nodes)}")
            print(f"     入口节点: {test_scenario.entry_node}")
        else:
            print(f"  ❌ 场景解析失败")
            issues.append("场景解析失败")
    
    except Exception as e:
        print(f"  ❌ 场景解析错误: {e}")
        issues.append(f"场景解析错误: {e}")
    
    # 6. 测试引擎初始化
    print("\n🚀 测试引擎初始化...")
    try:
        from core.engine import DAGEngine
        engine = DAGEngine()
        print(f"  ✅ 引擎初始化成功")
    except Exception as e:
        print(f"  ❌ 引擎初始化失败: {e}")
        issues.append(f"引擎初始化失败: {e}")
    
    # 总结
    print("\n" + "=" * 60)
    if issues:
        print(f"❌ 发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n请修复上述问题后再测试")
        return False
    else:
        print("✅ 所有检查通过！")
        print("\n可以开始测试:")
        print("  python3 test_local.py")
        return True

if __name__ == "__main__":
    success = check_project()
    sys.exit(0 if success else 1)
