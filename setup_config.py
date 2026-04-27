#!/usr/bin/env python3
"""
配置向导 - 首次使用配置
自动创建API配置文件
"""

import os
import sys
from pathlib import Path

# 项目路径
ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")

def setup_api_config():
    """配置API密钥"""
    config_file = ROOT_DIR / "config" / "api_config.py"
    
    if config_file.exists():
        print("✅ 配置文件已存在")
        
        # 询问是否重新配置
        choice = input("是否重新配置？(y/n): ").strip().lower()
        if choice != 'y':
            print("配置保持不变")
            return
    
    print("\n🔧 API配置向导")
    print("=" * 50)
    print("\n请按提示输入配置信息：")
    print()
    
    # API_KEY
    print("1. API_KEY")
    print("   格式: bce-v3/ALTAK-...")
    api_key = input("   请输入API_KEY: ").strip()
    
    if not api_key:
        print("\n⚠️ API_KEY 不能为空")
        return
    
    # API_URL
    print("\n2. API_URL")
    print("   默认: https://qianfan.baidubce.com/v2/chat/completions")
    api_url = input("   请输入API_URL (回车使用默认): ").strip()
    
    if not api_url:
        api_url = "https://qianfan.baidubce.com/v2/chat/completions"
    
    # 模型名称
    print("\n3. 模型名称")
    print("   默认: deepseek-v3.1-250821")
    model = input("   请输入模型名称 (回车使用默认): ").strip()
    
    if not model:
        model = "deepseek-v3.1-250821"
    
    # 确认配置
    print("\n" + "=" * 50)
    print("📋 配置确认:")
    print(f"  API_KEY: {api_key[:30]}...")
    print(f"  API_URL: {api_url}")
    print(f"  MODEL: {model}")
    print()
    
    confirm = input("确认配置？(y/n): ").strip().lower()
    
    if confirm != 'y':
        print("❌ 配置已取消")
        return
    
    # 生成配置文件
    config_content = f'''# API配置文件

API_KEY = "{api_key}"
API_URL = "{api_url}"
DEFAULT_MODEL = "{model}"

# 请求配置
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# 请求头
HEADERS = {{
    'Content-Type': 'application/json',
}}
'''
    
    # 写入文件
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"\n✅ 配置文件已创建: {config_file}")
    print("\n下一步:")
    print("  1. 测试API: python3 test_api.py")
    print("  2. 启动平台: streamlit run app/main.py")


def quick_setup():
    """快速配置（使用预设值）"""
    print("\n🚀 快速配置模式")
    print("=" * 50)
    
    config_file = ROOT_DIR / "config" / "api_config.py"
    
    # 使用预设值
    config_content = '''# API配置文件

API_KEY = "bce-v3/ALTAK-vnASNnJZQkPchN6JShUdi/38e23c1484e3b2ab42e15dd596dc85fd4328caf4"
API_URL = "https://qianfan.baidubce.com/v2/chat/completions"
DEFAULT_MODEL = "deepseek-v3.1-250821"

# 请求配置
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# 请求头
HEADERS = {
    'Content-Type': 'application/json',
}
'''
    
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print("✅ 已使用预设值创建配置文件")
    print(f"   文件位置: {config_file}")
    print("\n预设值:")
    print("  API_KEY: bce-v3/ALTAK-vnASNnJZQkPchN6JShUdi/...")
    print("  API_URL: https://qianfan.baidubce.com/v2/chat/completions")
    print("  MODEL: deepseek-v3.1-250821")
    print("\n下一步:")
    print("  python3 test_api.py")


if __name__ == "__main__":
    print("🔧 AI客服运营平台 - 配置向导")
    print("=" * 50)
    print()
    print("请选择配置方式：")
    print("  1. 交互式配置（推荐）")
    print("  2. 快速配置（使用预设值）")
    print()
    
    choice = input("请输入选项 (1/2): ").strip()
    
    if choice == '1':
        setup_api_config()
    elif choice == '2':
        quick_setup()
    else:
        print("❌ 无效选项")
