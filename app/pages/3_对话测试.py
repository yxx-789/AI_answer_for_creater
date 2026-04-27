"""
对话测试页面（完整修复版）
"""

import streamlit as st
import json
import sys
import asyncio
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.config import TRACES_DIR, SCENARIOS_DIR
from config.models import MODELS, DEFAULT_MODEL, MODEL_GROUPS, MODEL_RECOMMENDATIONS

st.set_page_config(page_title="对话测试 - AI客服运营平台", page_icon="💬")

st.title("💬 对话测试")
st.markdown("实时测试AI客服效果，追踪执行链路")

st.divider()

TRACES_DIR.mkdir(parents=True, exist_ok=True)

# ── 模型选择 ──
st.subheader("🎛️ 模型配置")

col_model1, col_model2 = st.columns([2, 1])

with col_model1:
    # 模型分组选择
    selected_group = st.selectbox(
        "模型分组",
        list(MODEL_GROUPS.keys()),
        index=4  # 默认选择"其他"（包含 deepseek-v3.2）
    )
    
    # 该分组下的模型
    group_models = MODEL_GROUPS[selected_group]
    
    selected_model = st.selectbox(
        "选择模型",
        group_models,
        index=group_models.index(DEFAULT_MODEL) if DEFAULT_MODEL in group_models else 0
    )

with col_model2:
    # 模型推荐
    if selected_model in MODEL_RECOMMENDATIONS:
        st.info(f"💡 {MODEL_RECOMMENDATIONS[selected_model]}")
    else:
        st.info(f"💡 已选择: {selected_model}")

# 场景选择
st.divider()
st.subheader("📝 场景选择")

scenario_files = list(SCENARIOS_DIR.rglob("*.yml"))
if scenario_files:
    selected_scenario = st.selectbox(
        "选择场景",
        [str(f.relative_to(SCENARIOS_DIR)) for f in scenario_files],
        key="chat_scenario"
    )
else:
    st.warning("⚠️ 请先在场景配置中创建场景")
    selected_scenario = None

st.divider()

# ── 对话窗口 ──
col_chat, col_trace = st.columns([2, 1])

with col_chat:
    st.subheader("💬 对话窗口")
    
    # 初始化聊天历史
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []
    
    # 显示聊天历史
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state['chat_history']:
            if message['role'] == 'user':
                with st.chat_message("user"):
                    st.write(message['content'])
            else:
                with st.chat_message("assistant"):
                    st.write(message['content'])
                    if 'model' in message:
                        st.caption(f"模型: {message['model']}")
    
    # 输入框
    user_input = st.chat_input("输入您的问题...")
    
    if user_input and selected_scenario:
        # 添加用户消息
        st.session_state['chat_history'].append({
            'role': 'user',
            'content': user_input,
            'timestamp': datetime.now().isoformat()
        })
        
        # AI回复
        with st.chat_message("assistant"):
            with st.spinner(f"思考中... (模型: {selected_model})"):
                try:
                    # 导入引擎和解析器
                    from core.engine import DAGEngine
                    from core.yml_parser import YMLParser
                    
                    # 加载场景
                    scenario_path = SCENARIOS_DIR / selected_scenario
                    parser = YMLParser(str(SCENARIOS_DIR))
                    scenario = parser.parse_scenario(scenario_path)
                    
                    if not scenario:
                        raise ValueError(f"无法解析场景文件: {selected_scenario}")
                    
                    # 创建引擎实例
                    engine = DAGEngine()
                    
                    # 设置模型（通过全局配置）
                    import config.models
                    config.models.DEFAULT_MODEL = selected_model
                    
                    # 执行对话（正确传入字典参数）
                    async def run_scenario():
                        # ✅ 修复：传入字典格式的初始变量
                        initial_vars = {
                            "raw_query": user_input
                        }
                        result = await engine.execute_scenario(scenario, initial_vars)
                        return result
                    
                    # 运行异步任务
                    result = asyncio.run(run_scenario())
                    
                    # 提取回复
                    if result and 'final_answer' in result:
                        ai_response = result['final_answer']
                    elif result and 'response' in result:
                        ai_response = result['response']
                    else:
                        ai_response = "抱歉，我暂时无法回答这个问题。"
                    
                    st.write(ai_response)
                    st.caption(f"模型: {selected_model}")
                    
                    # 保存Trace
                    trace_data = {
                        'timestamp': datetime.now().isoformat(),
                        'scenario': selected_scenario,
                        'model': selected_model,
                        'user_input': user_input,
                        'ai_response': ai_response,
                        'nodes': result.get('trace_log', []) if result else [],
                        'success': True
                    }
                    
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    
                    ai_response = f"抱歉，处理您的请求时出现错误：{str(e)}"
                    st.write(ai_response)
                    st.caption(f"模型: {selected_model}")
                    
                    # 显示详细错误（调试用）
                    with st.expander("🐛 详细错误信息"):
                        st.code(error_detail)
                    
                    trace_data = {
                        'timestamp': datetime.now().isoformat(),
                        'scenario': selected_scenario,
                        'model': selected_model,
                        'user_input': user_input,
                        'error': str(e),
                        'error_detail': error_detail,
                        'success': False
                    }
        
        # 添加AI回复到历史
        st.session_state['chat_history'].append({
            'role': 'assistant',
            'content': ai_response,
            'model': selected_model,
            'timestamp': datetime.now().isoformat()
        })
        
        st.session_state['current_trace'] = trace_data
        
        # 保存Trace文件
        trace_file = TRACES_DIR / f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(trace_file, 'w', encoding='utf-8') as f:
            json.dump(trace_data, f, ensure_ascii=False, indent=2)
        
        st.rerun()

with col_trace:
    st.subheader("📍 执行链路")
    
    if 'current_trace' in st.session_state:
        trace = st.session_state['current_trace']
        
        # 显示模型信息
        if 'model' in trace:
            st.info(f"🎯 模型: {trace['model']}")
        
        # 显示执行链路
        nodes = trace.get('nodes', [])
        if nodes:
            for idx, node in enumerate(nodes):
                col_node, col_time = st.columns([3, 1])
                
                with col_node:
                    status_icon = "✅" if trace.get('success') else "❌"
                    node_id = node.get('node_id', 'N/A') if isinstance(node, dict) else str(node)
                    st.write(f"{status_icon} **{node_id}**")
                
                with col_time:
                    elapsed = node.get('elapsed_ms', 0) if isinstance(node, dict) else 0
                    st.caption(f"{elapsed}ms")
                
                if idx < len(nodes) - 1:
                    st.write("⬇️")
        
        st.divider()
        
        with st.expander("📊 详细信息"):
            st.json(trace)
    
    else:
        st.info("👆 开始对话后，这里会显示执行链路")

# 操作按钮
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state['chat_history'] = []
        if 'current_trace' in st.session_state:
            del st.session_state['current_trace']
        st.rerun()

with col2:
    if st.button("📥 导出对话", use_container_width=True):
        if st.session_state['chat_history']:
            chat_export = json.dumps(st.session_state['chat_history'], ensure_ascii=False, indent=2)
            st.download_button(
                label="下载对话记录",
                data=chat_export,
                file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

with col3:
    if st.button("🚫 标记Bad Case", use_container_width=True):
        if st.session_state['chat_history'] and 'current_trace' in st.session_state:
            bad_case = {
                'timestamp': datetime.now().isoformat(),
                'model': selected_model,
                'chat_history': st.session_state['chat_history'],
                'trace': st.session_state['current_trace'],
                'reason': '手动标记'
            }
            
            bad_case_file = Path(ROOT_DIR) / "data" / "bad_cases" / f"bad_case_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            bad_case_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(bad_case_file, 'w', encoding='utf-8') as f:
                json.dump(bad_case, f, ensure_ascii=False, indent=2)
            
            st.success("✅ 已标记为Bad Case")

st.divider()
st.caption(f"💡 当前模型: {selected_model} | 对话会自动保存Trace，可在运营看板中查看分析")
