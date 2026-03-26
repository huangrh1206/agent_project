from core.llm_client import HelloAgentsLLM
from core.utils import log_markdown

class FastAgent:
    def __init__(self, llm_client: HelloAgentsLLM):
        self.llm_client = llm_client

    def run(self, question: str):
        """
        运行快速智能体（直接回答，无需思考过程和工具调用）。
        """
        # 1. 格式化提示词
        prompt = FAST_PROMPT_TEMPLATE.format(question=question)
        messages = [{"role": "user", "content": prompt}]

        # 2. 直接调用LLM进行响应
        full_response = ""
        # 遍历 LLM 返回的内容块（目前 think 会自动过滤掉推理/思考内容）
        for chunk in self.llm_client.think(messages=messages):
            full_response += chunk
            yield {"type": "chunk", "content": chunk}
        
        # 3. 返回最终答案
        if full_response:
            log_markdown(f"### 🎉 快速回答\n\n{full_response}")
            yield {"type": "answer", "content": full_response}
        else:
            yield {"type": "error", "content": "未能生成有效回答。"}

FAST_PROMPT_TEMPLATE = """
你是一个高效且直接的AI助手。你的任务是直接回答用户的问题。
要求：
1. 不要输出你的思考过程（Thought）。
2. 不要尝试调用任何工具（Action）。
3. 不要使用任何特殊的格式，直接给出最终答案。

用户提问：{question}
"""