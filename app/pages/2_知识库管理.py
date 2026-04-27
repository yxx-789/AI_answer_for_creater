"""
知识库管理页面（完整版 - 适配真实格式）
"""

import streamlit as st
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("/Users/xingyao/Desktop/ai-customer-service-platform-v2")
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.config import KNOWLEDGE_DIR

st.set_page_config(page_title="知识库管理 - AI客服运营平台", page_icon="📚")

st.title("📚 知识库管理")
st.markdown("管理知识条目，提升问答准确率")

st.divider()

KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

# 标签页
tab1, tab2, tab3 = st.tabs(["📋 知识列表", "➕ 添加知识", "🔍 检索测试"])

with tab1:
    st.subheader("📋 知识列表")
    
    # 获取所有知识库文件
    kb_files = list(KNOWLEDGE_DIR.glob("*.json"))
    
    # 过滤掉备份文件
    kb_files = [f for f in kb_files if 'backup' not in f.name and 'old' not in f.name]
    
    if not kb_files:
        st.warning("⚠️ 暂无知识库文件")
        
        # 提供初始化选项
        if st.button("初始化知识库", type="primary"):
            initial_data = {
                "documents": [
                    {
                        "id": "doc_001",
                        "title": "账号相关",
                        "keywords": ["账号", "封禁", "封号", "解封"],
                        "qa_pairs": [
                            {
                                "question": "账号被封了怎么办",
                                "answer": "创作者大人您好，账号被封禁通常是因为违反了平台规定。请您先查看站内信了解封禁原因，然后根据指引进行申诉。"
                            }
                        ]
                    }
                ]
            }
            
            kb_path = KNOWLEDGE_DIR / "default_kb.json"
            with open(kb_path, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)
            
            st.success("✅ 知识库已初始化！")
            st.rerun()
    else:
        # 选择知识库
        selected_kb = st.selectbox(
            "选择知识库",
            [f.name for f in kb_files],
            index=0
        )
        
        if selected_kb:
            kb_path = KNOWLEDGE_DIR / selected_kb
            
            try:
                with open(kb_path, 'r', encoding='utf-8') as f:
                    kb_data = json.load(f)
                
                # 适配两种格式
                documents = kb_data.get('documents', [])
                
                # 统计总数
                total_qa = sum(len(doc.get('qa_pairs', [])) for doc in documents)
                total_docs = len(documents)
                
                # 显示统计
                col1, col2, col3 = st.columns(3)
                col1.metric("文档数", total_docs)
                col2.metric("QA对数", total_qa)
                col3.metric("文件大小", f"{kb_path.stat().st_size / 1024:.1f} KB")
                
                st.divider()
                
                # 显示文档列表
                for doc_idx, doc in enumerate(documents):
                    doc_id = doc.get('id', f'doc_{doc_idx}')
                    doc_title = doc.get('title', '未命名文档')
                    qa_pairs = doc.get('qa_pairs', [])
                    keywords = doc.get('keywords', [])
                    
                    with st.expander(f"📄 **{doc_title}** ({len(qa_pairs)} 条QA)"):
                        # 文档信息
                        if keywords:
                            st.write(f"**关键词**: {', '.join(keywords[:10])}")
                        
                        st.divider()
                        
                        # QA对列表
                        for qa_idx, qa in enumerate(qa_pairs):
                            question = qa.get('question', '无问题')
                            answer = qa.get('answer', '无答案')
                            
                            st.write(f"**Q{qa_idx+1}:** {question}")
                            st.write(f"**A{qa_idx+1}:** {answer[:200]}{'...' if len(answer) > 200 else ''}")
                            
                            if qa_idx < len(qa_pairs) - 1:
                                st.divider()
            
            except Exception as e:
                st.error(f"❌ 读取知识库失败: {e}")

with tab2:
    st.subheader("➕ 添加知识")
    
    kb_files = list(KNOWLEDGE_DIR.glob("*.json"))
    kb_files = [f for f in kb_files if 'backup' not in f.name and 'old' not in f.name]
    
    if not kb_files:
        st.warning("⚠️ 请先在知识列表中初始化知识库")
    else:
        selected_kb = st.selectbox("选择知识库", [f.name for f in kb_files], key="add_kb_select")
        
        with st.form("add_knowledge_form"):
            # 选择文档或新建
            kb_path = KNOWLEDGE_DIR / selected_kb
            with open(kb_path, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
            
            documents = kb_data.get('documents', [])
            doc_options = ["新建文档"] + [doc.get('title', '未命名') for doc in documents]
            
            selected_doc_option = st.selectbox("选择文档", doc_options)
            
            if selected_doc_option == "新建文档":
                doc_title = st.text_input("文档标题", placeholder="例如：账号相关")
                doc_keywords = st.text_input("关键词（逗号分隔）", placeholder="账号, 封禁, 解封")
            
            question = st.text_input("问题 *", placeholder="用户可能问的问题")
            answer = st.text_area("答案 *", placeholder="标准答案", height=150)
            
            submitted = st.form_submit_button("✅ 添加知识", type="primary")
            
            if submitted:
                if question and answer:
                    try:
                        with open(kb_path, 'r', encoding='utf-8') as f:
                            kb_data = json.load(f)
                        
                        documents = kb_data.get('documents', [])
                        
                        # 创建新的QA对
                        new_qa = {
                            "question": question,
                            "answer": answer
                        }
                        
                        if selected_doc_option == "新建文档":
                            # 创建新文档
                            new_doc = {
                                "id": f"doc_{len(documents)+1:03d}",
                                "title": doc_title or "未命名文档",
                                "keywords": [k.strip() for k in doc_keywords.split(',')] if doc_keywords else [],
                                "qa_pairs": [new_qa]
                            }
                            documents.append(new_doc)
                        else:
                            # 添加到现有文档
                            doc_idx = doc_options.index(selected_doc_option) - 1
                            if 'qa_pairs' not in documents[doc_idx]:
                                documents[doc_idx]['qa_pairs'] = []
                            documents[doc_idx]['qa_pairs'].append(new_qa)
                        
                        kb_data['documents'] = documents
                        
                        with open(kb_path, 'w', encoding='utf-8') as f:
                            json.dump(kb_data, f, ensure_ascii=False, indent=2)
                        
                        st.success("✅ 知识添加成功！")
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ 添加失败: {e}")
                else:
                    st.warning("⚠️ 问题和答案为必填项")

with tab3:
    st.subheader("🔍 检索测试")
    
    kb_files = list(KNOWLEDGE_DIR.glob("*.json"))
    kb_files = [f for f in kb_files if 'backup' not in f.name and 'old' not in f.name]
    
    if not kb_files:
        st.warning("⚠️ 暂无知识库")
    else:
        selected_kb = st.selectbox("选择知识库", [f.name for f in kb_files], key="search_kb_select")
        
        query = st.text_input("输入测试问题", placeholder="如：我的账号被封了怎么办？")
        
        if st.button("🔍 测试检索", type="primary"):
            if query:
                kb_path = KNOWLEDGE_DIR / selected_kb
                
                with open(kb_path, 'r', encoding='utf-8') as f:
                    kb_data = json.load(f)
                
                documents = kb_data.get('documents', [])
                
                # 搜索匹配
                results = []
                query_lower = query.lower()
                
                for doc in documents:
                    doc_title = doc.get('title', '')
                    keywords = doc.get('keywords', [])
                    qa_pairs = doc.get('qa_pairs', [])
                    
                    for qa in qa_pairs:
                        question = qa.get('question', '')
                        answer = qa.get('answer', '')
                        
                        score = 0
                        
                        # 问题匹配
                        if query_lower in question.lower():
                            score += 10
                        
                        # 答案匹配
                        if query_lower in answer.lower():
                            score += 5
                        
                        # 关键词匹配
                        for keyword in keywords:
                            if keyword.lower() in query_lower:
                                score += 3
                        
                        if score > 0:
                            results.append({
                                'doc_title': doc_title,
                                'question': question,
                                'answer': answer,
                                'score': score
                            })
                
                # 排序
                results.sort(key=lambda x: x['score'], reverse=True)
                
                if results:
                    st.success(f"✅ 找到 {len(results)} 条相关知识")
                    
                    for idx, result in enumerate(results[:10], 1):
                        with st.expander(f"#{idx} - 匹配度: {result['score']} - {result['doc_title']}"):
                            st.write(f"**问题**: {result['question']}")
                            st.write(f"**答案**: {result['answer'][:300]}{'...' if len(result['answer']) > 300 else ''}")
                else:
                    st.warning("⚠️ 未找到相关知识，可能需要添加新知识")
            else:
                st.warning("⚠️ 请输入测试问题")

st.divider()
st.caption("💡 提示：知识库数据存储在 data/knowledge/ 目录下")
