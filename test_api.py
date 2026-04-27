#!/usr/bin/env python3
"""
API调用测试脚本
验证API配置是否正确（支持测试不同模型）
"""

import sys
import json
from pathlib import Path

# 添加项目路径
ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import requests
from config.api_config import API_KEY, API_URL
from config.models import MODELS, DEFAULT_MODEL


def test_api(model: str = None):
    """测试API调用"""
    print("🧪 API调用测试")
    print("=" * 50)
    
    # 使用指定模型或默认模型
    test_model = model or DEFAULT_MODEL
    
    # 1. 检查配置
    print("\n📋 配置信息:")
    print(f"  API_URL: {API_URL}")
    print(f"  API_KEY: {API_KEY[:20]}...")
    print(f"  测试模型: {test_model}")
    
    # 2. 构建请求
    print("\n🔨 构建请求...")
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {API_KEY}'
    }
    
    payload = {
        "model": test_model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "你好，请简单介绍一下你自己（一句话）"}
        ]
    }
    
    print(f"  Headers: Content-Type, Authorization")
    print(f"  Payload: model={test_model}, messages=2条")
    
    # 3. 发送请求
    print("\n🌐 发送请求...")
    
    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,  # 直接传字典
            timeout=30
        )
        
        print(f"  状态码: {response.status_code}")
        
        response.raise_for_status()
        
        # 4. 解析响应
        result = response.json()
        
        print("\n✅ API调用成功！")
        print(f"\n📝 模型: {test_model}")
        
        # 5. 提取回复
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            print(f"\n💬 AI回复:\n{content}")
        
        return True
    
    except requests.exceptions.Timeout:
        print(f"\n❌ API调用超时")
        return False
    
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ API调用失败: {e}")
        
        if e.response:
            print(f"\n📄 错误响应:")
            print(e.response.text)
        
        return False
    
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        return False


def test_all_models():
    """测试所有模型"""
    print("\n🧪 测试所有模型")
    print("=" * 50)
    
    success_count = 0
    failed_models = []
    
    for model in MODELS[:3]:  # 只测试前3个模型，避免太慢
        print(f"\n测试模型: {model}")
        print("-" * 40)
        
        if test_api(model):
            success_count += 1
        else:
            failed_models.append(model)
    
    print("\n" + "=" * 50)
    print(f"📊 测试结果: {success_count}/{len(MODELS[:3])} 成功")
    
    if failed_models:
        print(f"\n❌ 失败的模型: {', '.join(failed_models)}")
    
    return success_count > 0


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="API测试工具")
    parser.add_argument('--model', type=str, help='指定测试的模型')
    parser.add_argument('--all', action='store_true', help='测试所有模型（前3个）')
    
    args = parser.parse_args()
    
    if args.all:
        success = test_all_models()
    else:
        success = test_api(args.model)
    
    if success:
        print("\n" + "=" * 50)
        print("✅ API配置正确，可以使用！")
        print("\n下一步: 运行 streamlit run app/main.py")
    else:
        print("\n" + "=" * 50)
        print("❌ API配置有误，请检查 config/api_config.py")
    
    sys.exit(0 if success else 1)
