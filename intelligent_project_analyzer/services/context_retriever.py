"""
上下文检索服务

功能：
1. 关键词匹配
2. 语义相似度检索
3. 章节结构化提取
"""

from typing import Dict, Any, List
from loguru import logger
import re


class ContextRetriever:
    """
    上下文检索服务
    
    功能：
    1. 关键词匹配
    2. 章节结构化提取
    3. 相关性评分
    """
    
    def retrieve(
        self,
        query: str,
        context: 'ConversationContext',
        intent: str,
        top_k: int = 3
    ) -> Dict[str, Any]:
        """
        检索相关上下文
        
        Args:
            query: 用户查询
            context: 对话上下文
            intent: 用户意图
            top_k: 返回最相关的K个章节
        
        Returns:
            {
                "sections": [
                    {
                        "id": "chapter_3",
                        "title": "设计方案",
                        "content": "...",
                        "relevance_score": 0.85
                    }
                ],
                "metadata": {...}
            }
        """
        logger.info(f"Retrieving context for query: {query[:50]}...")
        
        # 1. 提取关键词
        keywords = self._extract_keywords(query)
        logger.debug(f"Extracted keywords: {keywords}")
        
        # 2. 从报告中提取所有章节
        all_sections = self._extract_sections_from_report(
            context.final_report
        )
        
        # 3. 计算相关性分数
        scored_sections = []
        for section in all_sections:
            score = self._calculate_relevance_score(
                section=section,
                keywords=keywords,
                query=query
            )
            scored_sections.append({
                **section,
                "relevance_score": score
            })
        
        # 4. 排序并返回top_k
        scored_sections.sort(key=lambda x: x["relevance_score"], reverse=True)
        top_sections = scored_sections[:top_k]
        
        logger.info(f"Retrieved {len(top_sections)} relevant sections")
        
        return {
            "sections": top_sections,
            "metadata": {
                "total_sections": len(all_sections),
                "keywords": keywords
            }
        }
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取查询关键词"""
        # 使用正则表达式提取中文词汇（2-10个字）
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,10}', query)
        
        # 去重并过滤常见停用词
        stopwords = {'什么', '怎么', '如何', '能否', '可以', '是否', '为什么', '哪些', '怎样'}
        keywords = [kw for kw in set(keywords) if kw not in stopwords]
        
        return keywords
    
    def _extract_sections_from_report(
        self,
        report: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """从报告中提取所有章节"""
        sections = []
        
        # 执行摘要
        if "executive_summary" in report:
            exec_summary = report["executive_summary"]
            content_parts = []
            
            if isinstance(exec_summary, dict):
                if "key_recommendations" in exec_summary:
                    content_parts.append(f"核心建议：{exec_summary['key_recommendations']}")
                if "key_findings" in exec_summary:
                    content_parts.append(f"主要发现：{exec_summary['key_findings']}")
                content = "\n".join(content_parts) if content_parts else str(exec_summary)
            else:
                content = str(exec_summary)
            
            sections.append({
                "id": "executive_summary",
                "title": "执行摘要",
                "content": content
            })
        
        # 各个章节
        if "sections" in report:
            for section_id, section_data in report["sections"].items():
                if isinstance(section_data, dict):
                    title = section_data.get("title", section_id)
                    content = section_data.get("content", "")
                    
                    # 如果content是dict，尝试提取主要字段
                    if isinstance(content, dict):
                        content_str = "\n".join([
                            f"{k}: {v}" for k, v in content.items()
                            if isinstance(v, (str, int, float))
                        ])
                    else:
                        content_str = str(content)
                    
                    sections.append({
                        "id": section_id,
                        "title": title,
                        "content": content_str
                    })
        
        # 需求分析
        if "requirements_analysis" in report:
            req_analysis = report["requirements_analysis"]
            sections.append({
                "id": "requirements_analysis",
                "title": "需求分析",
                "content": str(req_analysis)
            })
        
        logger.debug(f"Extracted {len(sections)} sections from report")
        return sections
    
    def _calculate_relevance_score(
        self,
        section: Dict[str, Any],
        keywords: List[str],
        query: str
    ) -> float:
        """计算章节与查询的相关性分数"""
        score = 0.0
        content = section.get("content", "").lower()
        title = section.get("title", "").lower()
        query_lower = query.lower()
        
        # 标题完全匹配查询关键部分（高分）
        for keyword in keywords:
            if keyword in title:
                score += 0.5
        
        # 内容包含关键词（中分）
        for keyword in keywords:
            count = content.count(keyword)
            if count > 0:
                score += 0.1 * min(count, 5)  # 最多计5次
        
        # 查询原文出现在内容中（高分）
        if query_lower in content:
            score += 0.3
        
        # 归一化到[0, 1]
        return min(score, 1.0)
