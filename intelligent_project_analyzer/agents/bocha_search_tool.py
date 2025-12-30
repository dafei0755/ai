"""
博查搜索工具 (v7.105)

✅ 状态: 已修复并完整集成博查Web Search API

博查是中文AI搜索引擎，专注于中文内容搜索
适用场景：中文项目、国内市场调研、中文案例研究

📊 API配置:
- 域名: https://api.bocha.cn
- 端点: /v1/web-search
- 文档: https://bocha-ai.feishu.cn/wiki/HmtOw1z6vik14Fkdu5uc9VaInBb
- 获取密钥: https://open.bocha.cn

✅ 实现状态:
- ✅ 配置系统完整
- ✅ 工具框架就绪
- ✅ Web Search API 集成完成
- ✅ 响应解析适配博查返回格式

修复记录:
- v7.105 (2025-12-30): 修复域名 api.bochaai.com → api.bocha.cn
- v7.105: 修复端点 /chat/completions → /v1/web-search
- v7.105: 修复请求格式为博查Web Search API标准
- v7.105: 修复响应解析（code: 200 vs 0）
"""

from typing import Optional, Dict, Any
from loguru import logger
from intelligent_project_analyzer.settings import settings


class BochaSearchTool:
    """
    博查搜索工具
    
    使用博查AI搜索引擎进行中文内容搜索
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.bocha.cn", default_count: int = 5, timeout: int = 30):
        """
        初始化博查搜索工具
        
        Args:
            api_key: 博查API密钥
            base_url: 博查API地址
            default_count: 默认搜索结果数量
            timeout: 请求超时时间(秒)
        """
        self.api_key = api_key
        self.base_url = base_url
        self.default_count = default_count
        self.timeout = timeout
        
    def search(self, query: str, count: Optional[int] = None) -> Dict[str, Any]:
        """
        执行搜索
        
        Args:
            query: 搜索关键词
            count: 返回结果数量（可选，默认使用default_count）
            
        Returns:
            搜索结果字典
        """
        try:
            import httpx
            
            result_count = count or self.default_count
            freshness = getattr(settings.bocha, 'freshness', 'oneYear')
            
            logger.info(f"🔍 博查搜索: query='{query}', count={result_count}")
            
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 🔥 v7.105: 调用博查Web Search API（官方文档）
            search_url = f"{self.base_url}/v1/web-search"
            payload = {
                "query": query,
                "freshness": "oneYear",  # 搜索时间范围
                "count": result_count,
                "summary": True  # 显示摘要
            }
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(search_url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"📥 博查API响应成功")
                    
                    # 🔥 v7.105: 解析博查Web Search API响应格式
                    results = []
                    
                    # 博查API返回格式: {code: 200, log_id, msg, data: {webPages: {value: [...]}}}
                    # 注意：code是HTTP状态码200，不是0
                    if isinstance(data, dict) and data.get('code') == 200:
                        web_data = data.get('data', {})
                        web_pages = web_data.get('webPages', {})
                        page_values = web_pages.get('value', [])
                        
                        for item in page_values[:result_count]:
                            results.append({
                                'title': item.get('name', ''),
                                'url': item.get('url', ''),
                                'snippet': item.get('snippet', ''),
                                'summary': item.get('summary', ''),  # 完整摘要
                                'siteName': item.get('siteName', ''),
                                'datePublished': item.get('datePublished', '')
                            })
                    
                    logger.info(f"✅ 博查搜索成功: 返回 {len(results)} 条结果")
                    return {
                        "success": True,
                        "query": query,
                        "results": results,
                        "count": len(results)
                    }
                else:
                    error_msg = f"API返回错误 {response.status_code}"
                    logger.error(f"❌ 博查搜索失败: {error_msg}")
                    logger.debug(f"响应内容: {response.text[:200]}")
                    
                    return {
                        "success": False,
                        "message": f"{error_msg}。请检查API配置。",
                        "query": query,
                        "results": []
                    }
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP错误 {e.response.status_code}"
            logger.error(f"❌ 博查搜索失败: {error_msg}")
            logger.debug(f"响应: {e.response.text[:150]}")
            return {
                "success": False,
                "message": error_msg,
                "query": query,
                "results": []
            }
        except httpx.RequestError as e:
            error_msg = f"网络请求失败: {str(e)}"
            logger.error(f"❌ 博查搜索失败: {error_msg}")
            return {
                "success": False,
                "message": error_msg,
                "query": query,
                "results": []
            }
        except Exception as e:
            logger.error(f"❌ 博查搜索失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"搜索失败: {str(e)}",
                "query": query,
                "results": []
            }
    
    def __call__(self, query: str) -> str:
        """
        LangChain工具接口
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索结果（字符串格式）
        """
        result = self.search(query)
        
        if not result["success"]:
            return f"搜索失败: {result['message']}"
        
        if not result["results"]:
            return "未找到相关结果"
        
        # 格式化输出
        output = f"博查搜索结果 (关键词: {query}):\n\n"
        for i, item in enumerate(result["results"], 1):
            output += f"{i}. {item.get('title', '无标题')}\n"
            output += f"   摘要: {item.get('snippet', '无摘要')}\n"
            output += f"   链接: {item.get('url', '无链接')}\n\n"
        
        return output


def create_bocha_search_tool_from_settings() -> Optional[BochaSearchTool]:
    """
    从全局配置创建博查搜索工具
    
    Returns:
        BochaSearchTool实例，如果配置不完整则返回None
    """
    if not settings.bocha.enabled:
        logger.info("博查搜索未启用")
        return None
    
    if not settings.bocha.api_key or settings.bocha.api_key == "your_bocha_api_key_here":
        logger.warning("⚠️ 博查API密钥未配置")
        return None
    
    logger.info(f"✅ 创建博查搜索工具: base_url={settings.bocha.base_url}, count={settings.bocha.default_count}")
    
    return BochaSearchTool(
        api_key=settings.bocha.api_key,
        base_url=settings.bocha.base_url,
        default_count=settings.bocha.default_count,
        timeout=settings.bocha.timeout
    )
