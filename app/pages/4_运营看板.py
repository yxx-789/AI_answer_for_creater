"""
运营看板页面（完整版 - 显示真实数据）
"""

import streamlit as st
import json
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.config import TRACES_DIR, BAD_CASES_DIR

st.set_page_config(page_title="运营看板 - AI客服运营平台", page_icon="📈", layout="wide")

st.title("📈 运营看板")
st.markdown("查看真实统计数据，分析运营效果")

st.divider()

# 读取真实统计数据
def load_real_stats():
    traces_dir = TRACES_DIR
    if not traces_dir.exists():
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'success_rate': 0,
            'daily_stats': []
        }
    
    trace_files = list(traces_dir.glob("*.json"))
    
    if not trace_files:
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'success_rate': 0,
            'daily_stats': []
        }
    
    total = len(trace_files)
    success = 0
    failed = 0
    
    for trace_file in trace_files:
        try:
            with open(trace_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('success'):
                success += 1
            else:
                failed += 1
        except:
            pass
    
    return {
        'total': total,
        'success': success,
        'failed': failed,
        'success_rate': round(success / total * 100, 1) if total > 0 else 0,
        'daily_stats': []
    }

stats = load_real_stats()

# 第一行：关键指标
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="对话总数",
        value=stats['total']
    )

with col2:
    st.metric(
        label="成功数",
        value=stats['success']
    )

with col3:
    st.metric(
        label="失败数",
        value=stats['failed']
    )

with col4:
    st.metric(
        label="成功率",
        value=f"{stats['success_rate']}%"
    )

st.divider()

# 第二行：Trace列表和Bad Cases
col_traces, col_badcases = st.columns([1, 1])

with col_traces:
    st.subheader("📁 最近对话记录")
    
    traces_dir = TRACES_DIR
    if traces_dir.exists():
        trace_files = sorted(traces_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]
        
        if trace_files:
            for trace_file in trace_files:
                try:
                    with open(trace_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    timestamp = data.get('timestamp', '未知时间')
                    user_input = data.get('user_input', 'N/A')[:40]
                    success = "✅" if data.get('success') else "❌"
                    
                    with st.container():
                        col_time, col_input, col_status = st.columns([1, 3, 0.5])
                        col_time.caption(timestamp.split('T')[1].split('.')[0] if 'T' in timestamp else timestamp)
                        col_input.write(f"{user_input}...")
                        col_status.write(success)
                except:
                    pass
        else:
            st.info("暂无对话记录")
    else:
        st.info("暂无对话记录")

with col_badcases:
    st.subheader("🔥 Bad Cases")
    
    bad_cases_dir = BAD_CASES_DIR
    if bad_cases_dir.exists():
        bad_case_files = sorted(bad_cases_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]
        
        if bad_case_files:
            for idx, bad_case_file in enumerate(bad_case_files, 1):
                try:
                    with open(bad_case_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    timestamp = data.get('timestamp', '未知时间')
                    reason = data.get('reason', '未知原因')
                    
                    with st.expander(f"#{idx} - {timestamp.split('T')[1].split('.')[0] if 'T' in timestamp else timestamp}"):
                        st.write(f"**原因**: {reason}")
                        
                        if data.get('chat_history'):
                            st.write("**对话历史**:")
                            for msg in data['chat_history'][-2:]:  # 显示最后2条
                                st.write(f"- {msg['role']}: {msg['content'][:50]}...")
                
                except Exception as e:
                    pass
        else:
            st.info("暂无Bad Case")
    else:
        st.info("暂无Bad Case")

st.divider()

# 第三行：Harness 状态
st.subheader("🛡️ Harness 约束系统状态")

col_h1, col_h2, col_h3 = st.columns(3)

with col_h1:
    st.metric("权限控制", "✅ 启用")
    st.caption("三级权限：L1/L2/L3")

with col_h2:
    st.metric("Eval系统", "✅ 启用")
    st.caption("触发评估 + 事实边界评估")

with col_h3:
    st.metric("传感器", "✅ 启用")
    st.caption("结构检查 + 变量检查 + 内容检查")

st.divider()

# 页脚
st.caption("💡 数据来源：真实Trace记录 | 数据存储在 data/traces/ 和 data/bad_cases/ 目录")
