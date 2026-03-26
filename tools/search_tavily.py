from tavily import TavilyClient
from dotenv import load_dotenv
import os

load_dotenv()

tool_name = "TavilySearch"
tool_desc = "塔维利网页搜索引擎。当你需要回答关于时事、事实以及在你的知识库中找不到的信息时，优先使用此工具。"

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
client = TavilyClient(TAVILY_API_KEY)


def clean_results(results):
    """
    保护逻辑：如果 URL 超过 1000 个字符，且大于此长度可能为垃圾数据，直接截断。
    """
    for res in results:
        url = res.get('url', '')
        if url and len(url) > 1000:
            res['url'] = url[:100] + "...(数据异常已截断)"
    return results


def tool_func(query: str) -> str:
    """
    执行塔维利网页搜索。
    """
    try:
        response = client.search(
            query=query,
            search_depth="advanced"
        )
        
        # 处理搜索结果，防止极端数据撑爆 LLM 上下文
        if isinstance(response, dict) and 'results' in response:
            clean_results(response['results'])
            
        return response
    except Exception as e:
        return f"塔维利搜索失败: {str(e)}"
