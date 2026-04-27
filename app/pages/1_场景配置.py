"""
场景配置管理页面（完整版 - 流程图与代码联动）
"""

import streamlit as st
import yaml
import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.config import SCENARIOS_DIR

st.set_page_config(page_title="场景配置 - AI客服运营平台", page_icon="⚙️")

st.title("⚙️ 场景配置管理")
st.markdown("在线编辑和管理对话场景配置")

st.divider()

SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

# 左侧：场景列表
col_list, col_editor = st.columns([1, 3])

with col_list:
    st.subheader("📁 场景列表")
    
    # 获取所有场景文件
    scenario_files = list(SCENARIOS_DIR.rglob("*.yml"))
    
    # 初始化选择状态
    if 'selected_scenario' not in st.session_state:
        if scenario_files:
            st.session_state['selected_scenario'] = str(scenario_files[0].relative_to(SCENARIOS_DIR))
        else:
            st.session_state['selected_scenario'] = None
    
    # 场景选择
    scenario_options = [str(f.relative_to(SCENARIOS_DIR)) for f in scenario_files]
    
    if scenario_options:
        selected_scenario = st.selectbox(
            "选择场景",
            scenario_options,
            index=scenario_options.index(st.session_state['selected_scenario']) if st.session_state['selected_scenario'] in scenario_options else 0
        )
        st.session_state['selected_scenario'] = selected_scenario
    else:
        selected_scenario = None
        st.info("暂无场景文件，请新建场景")
    
    # 操作按钮
    st.divider()
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("➕ 新建场景", use_container_width=True):
            st.session_state['show_new_scenario'] = True
    
    with col_btn2:
        if st.button("📥 导入场景", use_container_width=True):
            st.session_state['show_import'] = True

# 右侧：场景编辑器
with col_editor:
    # 新建场景表单
    if st.session_state.get('show_new_scenario'):
        st.subheader("➕ 新建场景")
        
        with st.form("new_scenario_form"):
            new_name = st.text_input("场景名称（不含.yml）", placeholder="例如：main_flow")
            new_dir = st.text_input("场景目录（可选）", placeholder="例如：bailing")
            
            template = st.select_slider(
                "场景模板",
                options=["空白场景", "基础流程", "客服场景"],
                value="空白场景"
            )
            
            # 生成YAML模板
            if template == "空白场景":
                new_yaml = """metadata:
  scene_id: demo_scene
  scene_name: 演示场景
  version: 1.0.0

nodes:
  START:
    type: start
    next_nodes: [END]
  
  END:
    type: end
"""
            elif template == "基础流程":
                new_yaml = """metadata:
  scene_id: basic_flow
  scene_name: 基础对话流程
  version: 1.0.0

context_variables:
  raw_query:
    type: String
    source: user_input

nodes:
  START:
    type: start
    next_nodes: [LLM]
  
  LLM:
    type: llm
    config:
      model_id: deepseek-v3.2
      system_prompt: "你是一个智能客服助手"
      user_prompt_template: "用户问题：{{raw_query}}"
    next_nodes: [END]
  
  END:
    type: end
"""
            else:
                new_yaml = """metadata:
  scene_id: customer_service
  scene_name: 客服对话场景
  version: 1.0.0

context_variables:
  raw_query:
    type: String
    source: user_input

nodes:
  START:
    type: start
    next_nodes: [INTENT]
  
  INTENT:
    type: intent
    config:
      model_id: deepseek-v3.2
      system_prompt: "你是一个意图识别助手"
      user_prompt_template: "用户输入：{{raw_query}}"
      branches:
        - key: "账号"
          name: "账号问题"
          target_node: "ACCOUNT_AGENT"
        - key: "审核"
          name: "审核问题"
          target_node: "KNOWLEDGE"
      default_branch: "LLM"
    next_nodes: [ACCOUNT_AGENT, KNOWLEDGE, LLM]
  
  ACCOUNT_AGENT:
    type: route
    config:
      agent_name: penalty_agent
    next_nodes: [END]
  
  KNOWLEDGE:
    type: knowledge
    config:
      knowledge_base_id: account_kb
    next_nodes: [END]
  
  LLM:
    type: llm
    config:
      model_id: deepseek-v3.2
      system_prompt: "你是百灵平台的AI客服助手"
      user_prompt_template: "用户问题：{{raw_query}}"
    next_nodes: [END]
  
  END:
    type: end
"""
            
            new_yaml_content = st.text_area("YAML内容", value=new_yaml, height=300)
            
            col_submit, col_cancel = st.columns(2)
            
            with col_submit:
                submitted = st.form_submit_button("✅ 创建场景", type="primary", use_container_width=True)
            
            with col_cancel:
                cancelled = st.form_submit_button("❌ 取消", use_container_width=True)
            
            if submitted and new_name:
                try:
                    yaml.safe_load(new_yaml_content)
                    
                    if new_dir:
                        scenario_path = SCENARIOS_DIR / new_dir / f"{new_name}.yml"
                    else:
                        scenario_path = SCENARIOS_DIR / f"{new_name}.yml"
                    
                    scenario_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(scenario_path, 'w', encoding='utf-8') as f:
                        f.write(new_yaml_content)
                    
                    st.success(f"✅ 场景 {new_name}.yml 创建成功！")
                    st.session_state['show_new_scenario'] = False
                    st.session_state['selected_scenario'] = str(scenario_path.relative_to(SCENARIOS_DIR))
                    st.rerun()
                
                except yaml.YAMLError as e:
                    st.error(f"❌ YAML格式错误: {e}")
            
            if cancelled:
                st.session_state['show_new_scenario'] = False
                st.rerun()
    
    # 导入场景
    elif st.session_state.get('show_import'):
        st.subheader("📥 导入场景")
        
        uploaded_file = st.file_uploader("上传YAML文件", type=['yml', 'yaml'])
        
        if uploaded_file:
            file_content = uploaded_file.read().decode('utf-8')
            st.text_area("文件内容预览", value=file_content, height=200)
            
            col_import, col_cancel = st.columns(2)
            
            with col_import:
                if st.button("✅ 确认导入", type="primary", use_container_width=True):
                    try:
                        yaml.safe_load(file_content)
                        
                        save_path = SCENARIOS_DIR / uploaded_file.name
                        with open(save_path, 'w', encoding='utf-8') as f:
                            f.write(file_content)
                        
                        st.success(f"✅ 已导入: {uploaded_file.name}")
                        st.session_state['show_import'] = False
                        st.rerun()
                    
                    except yaml.YAMLError as e:
                        st.error(f"❌ YAML格式错误: {e}")
            
            with col_cancel:
                if st.button("❌ 取消", use_container_width=True):
                    st.session_state['show_import'] = False
                    st.rerun()
    
    # 编辑现有场景
    elif selected_scenario:
        st.subheader(f"📝 编辑: {selected_scenario}")
        
        scenario_path = SCENARIOS_DIR / selected_scenario
        
        try:
            with open(scenario_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()
            
            # 解析YAML
            data = yaml.safe_load(yaml_content)
            
            # 初始化编辑内容
            if 'edited_yaml' not in st.session_state:
                st.session_state['edited_yaml'] = yaml_content
            
            # 显示视图切换
            view_mode = st.radio(
                "视图模式",
                ["📊 流程图", "💻 代码"],
                horizontal=True
            )
            
            st.divider()
            
            # 解析节点（支持两种格式）
            nodes_data = data.get('nodes', {}) if data else {}
            
            # 统计信息
            if nodes_data:
                st.info(f"📊 节点数: {len(nodes_data)}")
            
            if view_mode == "📊 流程图":
                # 流程图可视化
                st.subheader("📊 场景流程图")
                
                if nodes_data:
                    # 绘制流程图（使用文本+图形）
                    st.markdown("#### 节点流程")
                    
                    # 节点类型样式
                    node_styles = {
                        'start': ('🟢', '开始'),
                        'end': ('🔴', '结束'),
                        'llm': ('🔵', 'LLM'),
                        'intent': ('🟡', '意图'),
                        'route': ('🟣', '子链路'),
                        'knowledge': ('🟠', '知识库'),
                        'api': ('⚪', 'API'),
                        'code': ('⚫', '代码'),
                        'message': ('🔵', '消息'),
                        'barrier': ('🔶', '汇聚'),
                        'if': ('🔷', '条件'),
                    }
                    
                    # 显示节点
                    for node_id, node_data in nodes_data.items():
                        if isinstance(node_data, dict):
                            node_type = node_data.get('type', 'unknown')
                            next_nodes = node_data.get('next_nodes', [])
                            
                            # 获取样式
                            style = node_styles.get(node_type, ('⚪', node_type))
                            
                            # 显示节点
                            col_node, col_next = st.columns([1, 2])
                            
                            with col_node:
                                st.markdown(f"**{style[0]} {node_id}**")
                                st.caption(f"类型: {style[1]}")
                            
                            with col_next:
                                if next_nodes:
                                    if isinstance(next_nodes, list):
                                        next_str = " → ".join(next_nodes)
                                    elif isinstance(next_nodes, dict):
                                        next_str = " | ".join([f"{k}→{v}" for k, v in next_nodes.items()])
                                    else:
                                        next_str = str(next_nodes)
                                    st.write(f"→ {next_str}")
                                
                                # 显示子链路信息
                                if node_type == 'route' and isinstance(node_data.get('config'), dict):
                                    agent_name = node_data['config'].get('agent_name', '')
                                    if agent_name:
                                        st.info(f"🔗 子链路: {agent_name}")
                            
                            st.divider()
                    
                    # 节点统计
                    st.subheader("📊 节点统计")
                    
                    node_types_count = {}
                    for node_id, node_data in nodes_data.items():
                        if isinstance(node_data, dict):
                            node_type = node_data.get('type', 'unknown')
                            node_types_count[node_type] = node_types_count.get(node_type, 0) + 1
                    
                    cols = st.columns(len(node_types_count))
                    for idx, (ntype, count) in enumerate(node_types_count.items()):
                        style = node_styles.get(ntype, ('⚪', ntype))
                        cols[idx].metric(f"{style[0]} {style[1]}", count)
                
                else:
                    st.warning("⚠️ 场景文件格式不正确或无节点")
            
            else:  # 代码视图
                # 编辑器（联动更新）
                edited_yaml = st.text_area(
                    "YAML编辑器",
                    st.session_state.get('edited_yaml', yaml_content),
                    height=400,
                    key="yaml_editor",
                    on_change=lambda: st.session_state.update({'edited_yaml': st.session_state.yaml_editor})
                )
                
                # 操作按钮
                col_save, col_test, col_rollback, col_delete = st.columns(4)
                
                with col_save:
                    if st.button("💾 保存", use_container_width=True, type="primary"):
                        try:
                            yaml.safe_load(edited_yaml)
                            
                            # 备份原文件
                            backup_path = scenario_path.with_suffix('.yml.backup')
                            with open(backup_path, 'w', encoding='utf-8') as f:
                                f.write(yaml_content)
                            
                            # 保存新文件
                            with open(scenario_path, 'w', encoding='utf-8') as f:
                                f.write(edited_yaml)
                            
                            # 更新session state
                            st.session_state['edited_yaml'] = edited_yaml
                            
                            st.success("✅ 保存成功！已自动备份")
                            st.rerun()
                        
                        except yaml.YAMLError as e:
                            st.error(f"❌ YAML格式错误: {e}")
                
                with col_test:
                    if st.button("🧪 测试场景", use_container_width=True):
                        st.session_state['test_scenario'] = selected_scenario
                        st.switch_page("pages/3_对话测试.py")
                
                with col_rollback:
                    backup_path = scenario_path.with_suffix('.yml.backup')
                    if backup_path.exists():
                        if st.button("⏪ 回滚", use_container_width=True):
                            with open(backup_path, 'r', encoding='utf-8') as f:
                                backup_content = f.read()
                            
                            with open(scenario_path, 'w', encoding='utf-8') as f:
                                f.write(backup_content)
                            
                            st.session_state['edited_yaml'] = backup_content
                            st.success("✅ 已回滚到上一版本")
                            st.rerun()
                
                with col_delete:
                    if st.button("🗑️ 删除", use_container_width=True):
                        scenario_path.unlink()
                        st.success(f"✅ 已删除: {selected_scenario}")
                        st.session_state['selected_scenario'] = None
                        st.rerun()
        
        except Exception as e:
            st.error(f"❌ 读取文件失败: {e}")
    
    else:
        st.info("👈 请从左侧选择一个场景进行编辑，或新建场景")

# 页脚
st.divider()
st.caption("💡 提示：流程图显示节点类型和子链路 | 代码视图可编辑YAML并实时更新流程图")
