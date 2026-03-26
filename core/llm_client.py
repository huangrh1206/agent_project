import os
import time
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
            
            # 用于识别并截断 </think> 或 "Thinking Process:" 及其之前内容的逻辑
            found_end_tag = False
            full_buffer = ""
            
            # 定时器：限制思考时间，防止无限循环
            start_time = time.time()
            REASONING_TIMEOUT = 60 # 60秒硬性中断限制
            
            for chunk in response:
                delta = chunk.choices[0].delta
                
                # 1. 检查推理阶段是否耗时过长，无论是在原生字段还是内容流中
                if not found_end_tag:
                    if time.time() - start_time > REASONING_TIMEOUT:
                        msg = "⚠️ 思维推理耗时超过 60 秒，已强制中断该轮思考模式。"
                        print(f"\n{msg}")
                        log_markdown(f"> {msg}")
                        # 超时一刀切：丢弃缓冲区内容，假定思维已结束
                        collected_reasoning.append(full_buffer + " [思维超时中断]")
                        full_buffer = ""
                        found_end_tag = True
                        break # 中断当前流，后面交给 Agent 的兜底逻辑
                
                # 2. 优先处理标准的推理字段 (原生字段)
                reasoning_field = (
                    getattr(delta, 'reasoning_content', None) or 
                    getattr(delta, 'thinking_content', None) or 
                    getattr(delta, 'reasoning', None) or
                    getattr(delta, 'thought', None) or
                    getattr(delta, 'internal_thought', None)
                )
                if reasoning_field:
                    collected_reasoning.append(reasoning_field)
                    continue
                
                # 3. 处理内容中的思维链 (一刀切逻辑)
                content_chunk = delta.content or ""
                if content_chunk:
                    if not found_end_tag:
                        full_buffer += content_chunk
                        # 兼容多种思维终结或起始标识
                        if "</think>" in full_buffer:
                            # 找到终结符，切割内容
                            parts = full_buffer.split("</think>", 1)
                            # 之前的全部存入推理日志，移除可能的标识符
                            thought_part = parts[0].replace("<think>", "").replace("Thinking Process:", "").strip()
                            if thought_part:
                                collected_reasoning.append(thought_part)
                            
                            # 之后的部分才是真正的回答内容
                            answer_start = parts[1].lstrip()
                            if answer_start:
                                print(answer_start, end="", flush=True)
                                collected_content.append(answer_start)
                                yield answer_start
                            
                            found_end_tag = True
                            full_buffer = "" # 清空缓冲区
                    else:
                        # 已经跳过思维链，直接输出后续内容
                        print(content_chunk, end="", flush=True)
                        collected_content.append(content_chunk)
                        yield content_chunk
            
            # 兜底：如果整个流结束了还没找到 </think>，且 buffer 有内容
            if not found_end_tag and full_buffer:
                # 这种情况下模型可能没使用标准闭合标签，我们尝试手动清理常见的思维前缀
                clean_buffer = full_buffer.replace("<think>", "").replace("Thinking Process:", "").strip()
                if clean_buffer:
                    print(clean_buffer, end="", flush=True)
                    collected_content.append(clean_buffer)
                    yield clean_buffer
            
            print() # 换行
            
            # 日志记录完整的思考过程
            if collected_reasoning:
                reasoning_text = "".join(collected_reasoning).strip()
                if reasoning_text:
                    log_markdown(f"**LLM 思考过程**:\n{reasoning_text}")

            response_text = "".join(collected_content)
            log_markdown(f"**LLM 最终回答**:\n{response_text}")
            return response_text

        except Exception as e:
            error_msg = f"❌ 调用LLM API时发生错误: {e}"
            print(error_msg)
            log_markdown(f"**错误**: {error_msg}")
            return ""
