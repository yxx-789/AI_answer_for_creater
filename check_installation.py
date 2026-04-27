#!/usr/bin/env python3
"""
安装验证脚本 - 检查项目是否正确安装
"""

import os
import sys
from pathlib import Path

# 项目路径
PROJECT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")

def check_installation():
    """检查安装状态"""
    print("🔍 AI客服运营平台 - 安装验证")
    print("=" * 50)
    
    errors = []
    warnings = []
    
    # 1. 检查项目目录
    print("\n📁 检查项目目录...")
    if not PROJECT_DIR.exists():
        errors.append(f"❌ 项目目录不存在: {PROJECT_DIR}")
    else:
        print(f"✅ 项目目录存在: {PROJECT_DIR}")
    
    # 2. 检查Python版本
    print("\n🐍 检查Python版本...")
    py_version = sys.version_info
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 8):
        errors.append(f"❌ Python版本过低: {sys.version}")
    else:
        print(f"✅ Python版本: {sys.version.split()[0]}")
    
    # 3. 检查依赖
    print("\n📦 检查依赖...")
    required_packages = ['streamlit', 'yaml', 'pandas', 'plotly']
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} 已安装")
        except ImportError:
            errors.append(f"❌ {package} 未安装")
    
    # 4. 检查数据目录
    print("\n📂 检查数据目录...")
    data_dirs = [
        "data/scenarios/bailing",
        "data/knowledge",
        "data/traces",
        "data/bad_cases"
    ]
    
    for dir_path in data_dirs:
        full_path = PROJECT_DIR / dir_path
        if full_path.exists():
            print(f"✅ {dir_path} 存在")
        else:
            warnings.append(f"⚠️ {dir_path} 不存在，将自动创建")
    
    # 5. 检查配置文件
    print("\n⚙️ 检查配置文件...")
    
    # 主配置
    main_config = PROJECT_DIR / "config" / "config.py"
    if main_config.exists():
        print(f"✅ 主配置文件存在")
    else:
        errors.append(f"❌ 主配置文件不存在: config/config.py")
    
    # API配置
    api_config = PROJECT_DIR / "config" / "api_config.py"
    if api_config.exists():
        print(f"✅ API配置文件存在")
        
        # 检查是否配置了API_KEY
        with open(api_config, 'r') as f:
            content = f.read()
            if 'your-api-key' in content or 'API_KEY = ""' in content:
                warnings.append("⚠️ API_KEY 未配置，请运行 python3 setup_config.py")
    else:
        warnings.append("⚠️ API配置文件不存在，请运行 python3 setup_config.py")
    
    # 6. 检查核心文件
    print("\n🔧 检查核心文件...")
    core_files = [
        "app/main.py",
        "core/engine.py",
        "core/yml_parser.py"
    ]
    
    for file_path in core_files:
        full_path = PROJECT_DIR / file_path
        if full_path.exists():
            print(f"✅ {file_path} 存在")
        else:
            errors.append(f"❌ {file_path} 不存在")
    
    # 7. 检查场景文件
    print("\n📝 检查场景文件...")
    scenario_file = PROJECT_DIR / "data/scenarios/bailing/main_flow.yml"
    if scenario_file.exists():
        print(f"✅ 场景文件存在")
    else:
        warnings.append(f"⚠️ 场景文件不存在: {scenario_file}")
    
    # 8. 检查知识库
    print("\n📚 检查知识库...")
    kb_file = PROJECT_DIR / "data/knowledge/account_kb.json"
    if kb_file.exists():
        print(f"✅ 知识库文件存在")
    else:
        warnings.append(f"⚠️ 知识库文件不存在: {kb_file}")
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 验证结果")
    print("=" * 50)
    
    if not errors and not warnings:
        print("✅ 所有检查通过！可以启动平台")
        print("\n运行命令:")
        print("  streamlit run app/main.py")
        return True
    
    if errors:
        print("\n❌ 错误:")
        for error in errors:
            print(f"  {error}")
    
    if warnings:
        print("\n⚠️ 警告:")
        for warning in warnings:
            print(f"  {warning}")
    
    if not errors:
        print("\n✅ 无致命错误，可以启动平台")
        print("\n运行命令:")
        print("  streamlit run app/main.py")
        return True
    else:
        print("\n❌ 存在致命错误，请修复后重试")
        return False

if __name__ == "__main__":
    success = check_installation()
    sys.exit(0 if success else 1)
