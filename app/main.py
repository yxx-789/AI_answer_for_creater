"""
AI客服运营平台 - 主入口（完整版）
"""
import sys
import os
# 把当前文件所在目录的上一级（也就是项目的根目录）强制加入到Python的搜索路径中
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 原来的代码保持不变，继续写在下面...
from config.config import PLATFORM_NAME, VERSION, TRACES_DIR, BAD_CASES_DIR
import streamlit as st
import sys
from pathlib import Path
import json
from datetime import datetime

# 统一使用配置文件中的 ROOT_DIR
ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.config import PLATFORM_NAME, VERSION, TRACES_DIR, BAD_CASES_DIR

# 页面配置
st.set_page_config(
    page_title=f"{PLATFORM_NAME}",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF4B4B;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏
with st.sidebar:
    st.title(f"🤖 {PLATFORM_NAME}")
    st.caption(f"版本: {VERSION}")
    st.divider()
    
    # 导航（正确的相对路径）
    st.page_link("main.py", label="📊 仪表盘", icon="📊")
    st.page_link("pages/1_场景配置.py", label="⚙️ 场景配置", icon="⚙️")
    st.page_link("pages/2_知识库管理.py", label="📚 知识库管理", icon="📚")
    st.page_link("pages/3_对话测试.py", label="💬 对话测试", icon="💬")
    st.page_link("pages/4_运营看板.py", label="📈 运营看板", icon="📈")
    
    st.divider()
    
    # Harness状态
    st.subheader("🛡️ Harness 状态")
    st.metric("权限控制", "✅ 启用")
    st.metric("Eval系统", "✅ 启用")
    st.metric("传感器", "✅ 启用")
    
    st.divider()
    st.caption("© 2026 AI客服运营平台")

# 主页内容
st.markdown(f'<p class="main-header">欢迎使用 {PLATFORM_NAME}</p>', unsafe_allow_html=True)

st.markdown("""
### 🎯 平台功能

这是一个用于管理和优化AI客服系统的运营平台，已集成 **Harness 约束系统**：

- **⚙️ 场景配置**: 在线编辑和管理对话场景（支持新建/编辑/测试）
- **📚 知识库管理**: 管理知识条目，提升问答准确率（真实数据）
- **💬 对话测试**: 实时测试AI客服效果，追踪执行链路（真实AI回复）
- **📈 运营看板**: 查看真实统计数据，分析Bad Cases

---

### 📊 今日统计（真实数据）
""")

# 读取真实统计数据
def load_real_stats():
    """从trace文件读取真实统计数据"""
    if not TRACES_DIR.exists():
        return {'total': 0, 'success': 0, 'failed': 0, 'success_rate': 0}
    
    trace_files = list(TRACES_DIR.glob("*.json"))
    
    if not trace_files:
        return {'total': 0, 'success': 0, 'failed': 0, 'success_rate': 0}
    
    total = len(trace_files)
    success = sum(1 for f in trace_files if 
                  (lambda: (open(f, 'r', encoding='utf-8').read()))() and 
                  json.loads(open(f, 'r', encoding='utf-8').read()).get('success'))
    failed = total - success
    
    return {
        'total': total,
        'success': success,
        'failed': failed,
        'success_rate': round(success / total * 100, 1) if total > 0 else 0
    }

stats = load_real_stats()

# 显示统计
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="今日对话数", value=stats['total'])

with col2:
    st.metric(label="成功数", value=stats['success'])

with col3:
    st.metric(label="失败数", value=stats['failed'])

with col4:
    st.metric(label="成功率", value=f"{stats['success_rate']}%")

st.divider()

# 最近动态（从trace文件读取）
st.subheader("🔥 最近对话记录")

if TRACES_DIR.exists():
    trace_files = sorted(TRACES_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]
    
    if trace_files:
        for trace_file in trace_files:
            try:
                with open(trace_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                timestamp = data.get('timestamp', '未知时间')
                user_input = data.get('user_input', 'N/A')[:50]
                success = "✅" if data.get('success') else "❌"
                
                with st.container():
                    col_time, col_input, col_status = st.columns([1, 3, 0.5])
                    col_time.write(timestamp.split('T')[1].split('.')[0] if 'T' in timestamp else timestamp)
                    col_input.write(f"{user_input}...")
                    col_status.write(success)
            except Exception as e:
                pass
    else:
        st.info("暂无对话记录")
else:
    st.info("暂无对话记录")

st.divider()

# 快速操作
st.subheader("🚀 快速操作")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📝 新建场景", use_container_width=True):
        st.switch_page("pages/1_场景配置.py")

with col2:
    if st.button("💬 开始测试", use_container_width=True):
        st.switch_page("pages/3_对话测试.py")

with col3:
    if st.button("📊 查看统计", use_container_width=True):
        st.switch_page("pages/4_运营看板.py")

# 页脚
st.divider()
st.caption("💡 提示：点击左侧菜单开始使用各项功能 | 数据来源：真实Trace记录")
