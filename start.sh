#!/bin/bash

echo "🚀 AI客服运营平台 v2.0 启动脚本"
echo "================================"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3，请先安装 Python"
    exit 1
fi

echo "✅ Python 版本: $(python3 --version)"

# 检查依赖
echo ""
echo "📦 检查依赖..."
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "⚠️ Streamlit 未安装，正在安装..."
    pip3 install -r requirements.txt
fi

# 检查 requests 库
if ! python3 -c "import requests" 2>/dev/null; then
    echo "⚠️ requests 未安装，正在安装..."
    pip3 install requests
fi

# 初始化数据目录
echo ""
echo "📁 初始化数据目录..."
mkdir -p data/scenarios/bailing/agents
mkdir -p data/knowledge
mkdir -p data/traces
mkdir -p data/bad_cases

# 检查API配置
echo ""
echo "⚙️ 检查API配置..."
if [ ! -f "config/api_config.py" ]; then
    echo "⚠️ API配置文件不存在"
    echo ""
    echo "请运行配置向导："
    echo "  python3 setup_config.py"
    echo ""
    echo "或手动创建 config/api_config.py"
    exit 1
fi

# 测试API（可选）
echo ""
read -p "是否测试API连接？(y/n): " test_api
if [ "$test_api" = "y" ] || [ "$test_api" = "Y" ]; then
    echo "🧪 测试API连接..."
    python3 test_api.py
    
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ API测试失败，请检查配置"
        exit 1
    fi
fi

echo ""
echo "🌐 启动平台..."
echo "访问地址: http://localhost:8501"
echo ""
echo "💡 提示：按 Ctrl+C 停止服务"
echo ""

# 启动Streamlit
streamlit run app/main.py --server.port 8501 --server.address localhost
