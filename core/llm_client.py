import os
from typing import List, Dict, Generator
from openai import OpenAI
from core.utils import log_markdown

class HelloAgentsLLM:
    """
    为对话应用定制的LLM客户端。
    它用于调用任何兼容OpenAI接口的服务，并可以记录流式响应。支持全量返回或流式生成（Generator）。
    """
    def __init__(self, model: str = None, apiKey: str = None, baseUrl: str = None, timeout: int = None, enable_thinking: bool = False):
        """
        初始化客户端。优先使用传入参数，如果未提供，则从环境变量加载。
        """
        self.model = model or os.getenv("LLM_MODEL_ID")
        apiKey = apiKey or os.getenv("LLM_API_KEY")
        baseUrl = baseUrl or os.getenv("LLM_BASE_URL")
        timeout = timeout or int(os.getenv("LLM_TIMEOUT", 60))
        self.enable_thinking = enable_thinking
        
        if not all([self.model, apiKey, baseUrl]):
            raise ValueError("模型ID、API密钥和服务地址必须被提供或在.env文件中定义。")

        self.client = OpenAI(api_key=apiKey, base_url=baseUrl, timeout=timeout)

    def think(self, messages: List[Dict[str, str]], temperature: float = 0) -> Generator[str, None, str]:
        """
        调用 LLM 并在生成的过程中 yield 每一个内容块 (chunk)。
        在此过程中会自动识别并分离大模型的思考/推理轨迹（reasoning_content）。
        """
        print(f"🧠 正在调用 {self.model} 模型 (思考模式: {self.enable_thinking})...")
        log_markdown(f"### 🧠 调用 {self.model} 模型 (思考模式: {self.enable_thinking})")
        
        try:
            # 某些模型可能需要特定的参数来开启或关闭思考逻辑
            extra_body = {
                "top_k": 20,
                "chat_template_kwargs": {"enable_thinking": self.enable_thinking},
            }
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
                extra_body=extra_body,
            )
            
            collected_content = []
            collected_reasoning = []
            
            for chunk in response:
                # 打印原始 chunk 以识别可能的推理字段（调试用）
                # print(f"DEBUG CHUNK: {chunk}")
                
                delta = chunk.choices[0].delta
                
                # 处理专门的推理字段 (如 DeepSeek, Qwen, 以及其他兼容接口)
                # 尝试捕获所有可能的推理字段名
                reasoning = (
                    getattr(delta, 'reasoning_content', None) or 
                    getattr(delta, 'thinking_content', None) or 
                    getattr(delta, 'reasoning', None) or
                    getattr(delta, 'thought', None) or
                    getattr(delta, 'internal_thought', None)
                )
                
                if reasoning:
                    collected_reasoning.append(reasoning)
                    continue
                
                # 处理主回复内容
                content = delta.content or ""
                if content:
                    print(content, end="", flush=True)
                    collected_content.append(content)
                    yield content # 实时 yield 给 Agent
            
            print() # 换行
            
            # 日志记录完整的思考过程和最终回答
            if collected_reasoning:
                reasoning_text = "".join(collected_reasoning)
                log_markdown(f"**LLM 思考过程**:\n{reasoning_text}")

            response_text = "".join(collected_content)
            log_markdown(f"**LLM 最终回答**:\n{response_text}")
            return response_text

        except Exception as e:
            error_msg = f"❌ 调用LLM API时发生错误: {e}"
            print(error_msg)
            log_markdown(f"**错误**: {error_msg}")
            return ""
