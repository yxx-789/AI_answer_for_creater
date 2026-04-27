"""
KNOWLEDGE 节点执行器
负责知识库检索（支持多种检索策略）
"""

import json
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import httpx

from core.node_executors.base import BaseExecutor
from core.node_types import Node, KnowledgeConfig
from core.variable_manager import VariableManager


@dataclass
class KnowledgeResult:
    """知识库检索结果"""
    id: str
    question: str          # 列1：问题
    answer: str            # 列2：答案/处置手册
    category_id: str       # 列3：分类ID
    fast_transfer: int     # 列4：快转人工标记
    score: float           # 相关性得分
    metadata: Dict = None


class KnowledgeExecutor(BaseExecutor):
    """KNOWLEDGE节点执行器"""
    
    def __init__(self, use_mock: bool = True):
        """
        初始化
        
        Args:
            use_mock: 是否使用Mock模式
        """
        self.use_mock = use_mock
        self.knowledge_bases = {}  # 知识库缓存
    
    def load_knowledge_base_from_json(self, kb_id: str, json_path: str):
        """
        从JSON文件加载知识库
        
        Args:
            kb_id: 知识库ID
            json_path: JSON文件路径
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                kb_data = json.load(f)
            
            # 转换为知识列表格式
            knowledge_list = []
            
            for doc in kb_data.get('documents', []):
                doc_title = doc.get('title', '')
                doc_keywords = doc.get('keywords', [])
                doc_content = doc.get('full_content', '')
                
                # 为每个问答对创建知识条目
                for qa in doc.get('qa_pairs', []):
                    knowledge_list.append({
                        'question': qa.get('question', ''),
                        'answer': qa.get('answer', ''),
                        'category_id': doc_title,
                        'fast_transfer': 0,
                        'keywords': doc_keywords,
                        'metadata': {
                            'document_id': doc.get('id', ''),
                            'document_title': doc_title
                        }
                    })
            
            # 注册知识库
            self.register_knowledge_base(kb_id, knowledge_list)
            print(f"✓ 知识库 {kb_id} 加载成功: {len(knowledge_list)} 条")
            
        except Exception as e:
            print(f"✗ 知识库加载失败: {e}")
    
    def register_knowledge_base(self, kb_id: str, knowledge_list: List[Dict]):
        """
        注册知识库
        
        Args:
            kb_id: 知识库ID
            knowledge_list: 知识列表，每个元素包含：
                - question: 问题
                - answer: 答案
                - category_id: 分类ID
                - fast_transfer: 快转人工标记
        """
        self.knowledge_bases[kb_id] = knowledge_list
    
    async def execute(self, node: Node, var_manager: VariableManager) -> Dict[str, Any]:
        """执行KNOWLEDGE节点"""
        config: KnowledgeConfig = node.config
        
        # 获取检索query
        query = var_manager.get(config.query_source, "")
        
        if not query:
            return {"results": [], "error": "query为空"}
        
        # 判断是否使用Mock
        if self.use_mock:
            results = await self._mock_search(config, query)
        else:
            results = await self._real_search(config, query)
        
        # 后处理：提取URL、生成知识列表
        processed = self._postprocess_results(results, query)
        
        return processed
    
    async def _mock_search(
        self, 
        config: KnowledgeConfig, 
        query: str
    ) -> List[KnowledgeResult]:
        """Mock检索（使用本地知识库）"""
        
        print(f"[MOCK KNOWLEDGE] 知识库: {config.knowledge_base_id}")
        print(f"  Query: {query}")
        print(f"  策略: {config.strategy}, 召回数: {config.recall_count}")
        
        # 检查知识库是否已加载
        kb_id = config.knowledge_base_id
        if kb_id not in self.knowledge_bases:
            # 尝试从默认路径加载
            import os
            default_path = f"knowledge_base/{kb_id}.json"
            if os.path.exists(default_path):
                self.load_knowledge_base_from_json(kb_id, default_path)
            else:
                print(f"  ⚠️ 知识库 {kb_id} 未找到，使用空结果")
                return []
        
        # 获取知识库
        knowledge_list = self.knowledge_bases.get(kb_id, [])
        if not knowledge_list:
            print(f"  ⚠️ 知识库 {kb_id} 为空")
            return []
        
        # 改进的检索算法：多维度评分
        results = []
        query_lower = query.lower()
        query_keywords = [kw for kw in query_lower.split() if len(kw) > 1]
        
        for item in knowledge_list:
            question = item.get('question', '')
            answer = item.get('answer', '')
            keywords = item.get('keywords', [])
            
            # 多维度相关性计算
            score = 0.0
            score_details = []
            
            # 1. 完全匹配（权重最高）
            if query_lower == question.lower():
                score = 0.99
                score_details.append("完全匹配")
            # 2. 问题包含查询（权重高）
            elif query_lower in question.lower():
                score = 0.90
                score_details.append("问题包含查询")
            # 3. 查询包含问题核心词（权重较高）
            elif question.lower() in query_lower:
                score = 0.85
                score_details.append("查询包含问题")
            else:
                # 多维度评分
                
                # 3.1 关键词覆盖率
                if query_keywords:
                    matched_in_question = sum(1 for kw in query_keywords if kw in question.lower())
                    matched_in_answer = sum(1 for kw in query_keywords if kw in answer.lower())
                    
                    question_coverage = matched_in_question / len(query_keywords)
                    answer_coverage = matched_in_answer / len(query_keywords)
                    
                    # 问题的权重高于答案
                    keyword_score = question_coverage * 0.6 + answer_coverage * 0.3
                    
                    if keyword_score > 0:
                        score_details.append(f"关键词覆盖: {keyword_score:.2f}")
                
                # 3.2 知识库关键词匹配
                if keywords:
                    keyword_match = sum(1 for kw in keywords if kw.lower() in query_lower)
                    keyword_score_boost = (keyword_match / len(keywords)) * 0.2
                    
                    if keyword_score_boost > 0:
                        score_details.append(f"知识库关键词: +{keyword_score_boost:.2f}")
                
                # 3.3 特殊模式匹配
                # 问答型："如何..."、"怎么..."、"为什么..."
                question_patterns = ['如何', '怎么', '为什么', '什么', '怎样', '能否', '可以']
                if any(pattern in query_lower for pattern in question_patterns):
                    if any(pattern in question.lower() for pattern in question_patterns):
                        score += 0.1
                        score_details.append("问答模式匹配")
                
                # 3.4 计算最终得分
                if not score_details:
                    # 没有任何匹配
                    continue
                else:
                    # 综合评分
                    base_score = 0.3
                    if 'keyword_score' in locals() and keyword_score > 0:
                        base_score += keyword_score
                    if 'keyword_score_boost' in locals() and keyword_score_boost > 0:
                        base_score += keyword_score_boost
                    
                    score = min(base_score, 0.89)  # 最高不超过0.89（低于完全匹配）
            
            if score > 0.3:  # 阈值：相关度 > 0.3
                results.append(KnowledgeResult(
                    id=item.get('id', ''),
                    question=question,
                    answer=answer,
                    category_id=item.get('category_id', ''),
                    fast_transfer=item.get('fast_transfer', 0),
                    score=score,
                    metadata=item.get('metadata')
                ))
        
        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)
        
        print(f"  ✓ 检索到 {len(results)} 条相关知识")
        if results:
            best = results[0]
            detail_str = f" ({', '.join(score_details)})" if score_details else ""
            print(f"  Top 1: {best.question[:50]}... (score: {best.score:.2f}{detail_str})")
        
        return results[:config.recall_count]
    
    async def _real_search(
        self, 
        config: KnowledgeConfig, 
        query: str
    ) -> List[KnowledgeResult]:
        """真实检索知识库平台"""
        
        # TODO: 对接真实的知识库平台API
        # 例如：百度智能云知识库、Elasticsearch等
        
        return []
    
    def _postprocess_results(
        self, 
        results: List[KnowledgeResult], 
        query: str
    ) -> Dict[str, Any]:
        """
        知识库后处理
        
        参考《百灵AI客服系统.docx》中的"知识库后置参数汇总处理"节点：
        1. 提取URL链接 → 替换为短标记[链接X]
        2. 给每条知识加[知识库索引:X]标记
        3. 生成两个版本：
           - knowledge_list_for_llm: 精简版（给LLM参考）
           - knowledge_raw: 完整版
        4. 提取分类ID、快转人工标记
        """
        
        if not results:
            return {
                "results": [],
                "knowledge_list": "",
                "knowledge_raw": "",
                "link_map": {},
                "question_category_ids": "",
                "fast_transfer": 0
            }
        
        link_map = {}  # URL → 短标记
        link_counter = 0
        knowledge_list = []
        category_ids = []
        fast_transfer_flag = 0
        
        for idx, result in enumerate(results):
            # 提取URL并替换
            answer_text = result.answer
            urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', answer_text)
            
            for url in urls:
                if url not in link_map:
                    link_counter += 1
                    link_map[url] = f"[链接{link_counter}]"
                
                # 替换URL为短标记
                answer_text = answer_text.replace(url, link_map[url])
            
            # 添加知识索引标记
            knowledge_entry = f"[知识库索引:{idx+1}]\n问题：{result.question}\n答案：{answer_text}"
            knowledge_list.append(knowledge_entry)
            
            # 收集分类ID
            if result.category_id:
                category_ids.append(result.category_id)
            
            # 检查快转人工标记
            if result.fast_transfer == 1:
                fast_transfer_flag = 1
        
        return {
            "results": results,
            "knowledge_list": "\n\n".join(knowledge_list),
            "knowledge_raw": json.dumps([r.__dict__ for r in results], ensure_ascii=False),
            "link_map": link_map,
            "question_category_ids": ",".join(category_ids),
            "fast_transfer": fast_transfer_flag,
            "match_success": 1 if results else 0
        }


# 使用示例
if __name__ == '__main__':
    import asyncio
    
    async def test():
        # 创建执行器
        executor = KnowledgeExecutor(use_mock=True)
        
        # 创建变量管理器
        vm = VariableManager()
        vm.set("search_query", "账号被封了怎么办")
        
        # 创建节点
        from core.node_types import KnowledgeConfig
        
        node = Node(
            node_id="test_kb",
            node_type="KNOWLEDGE",
            config=KnowledgeConfig(
                knowledge_base_id="bailing_bjh_app",
                strategy="hybrid",
                recall_count=5,
                query_source="search_query"
            )
        )
        
        # 执行
        result = await executor.execute(node, vm)
        print(f"\n检索结果数: {len(result['results'])}")
        print(f"知识列表:\n{result['knowledge_list'][:200]}...")
        print(f"链接映射: {result['link_map']}")
        print(f"快转人工: {result['fast_transfer']}")
    
    asyncio.run(test())
