import re
import json
from typing import Dict, Any, List
from core.llm_client import HelloAgentsLLM
from core.utils import log_markdown

REACT_PROMPT_TEMPLATE = """
请注意，你是一个有能力调用外部工具的智能助手。

# 可用工具:
{tools}

# 时效性原则:
- 如果用户的问题涉及具体的时间点（如“今天”、“现在”、“本周”等），或者涉及需要实时查询的信息（如天气、新闻），你的**第一步**必须是调用 `get_current_time` 工具来获取当前的时间。
- 根据获取到的当前时间，再进行后续的行动。

# 回应格式:
请严格按照以下格式进行回应:

Thought: 你的思考过程，用于分析问题、拆解任务和规划下一步行动。
Action: 你决定采取的行动，必须是以下格式之一:
- `{{tool_name}}[{{tool_input}}]`:调用一个可用工具。
- `Finish[最终答案]`:当你认为已经获得最终答案时。
- 当你收集到足够的信息，能够回答用户的最终问题时，你必须在Action:字段后使用 Finish[最终答案] 来输出最终答案。

现在，请开始解决以下问题:
Question: {question}
History: {history}
"""

class ToolExecutor:
    """
    负责管理和执行工具。
    """
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}

    def registerTool(self, name: str, description: str, func: callable):
        """
        向执行器中注册一个新工具。
        """
        if name in self.tools:
            print(f"警告:工具 '{name}' 已存在，将被覆盖。")
        self.tools[name] = {"description": description, "func": func}
        msg = f"工具 '{name}' 已注册。"
        print(msg)
        log_markdown(f"- {msg}")

    def getTool(self, name: str) -> callable:
        """
        根据名称获取工具执行函数。
        """
        return self.tools.get(name, {}).get("func")

    def getAvailableTools(self) -> str:
        """
        获取所有可用工具描述。
        """
        return "\n".join([f"- {name}: {info['description']}" for name, info in self.tools.items()])


class ReActAgent:
    def __init__(self, llm_client: HelloAgentsLLM, tool_executor: ToolExecutor, max_steps: int = 5):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.max_steps = max_steps
        self.history = []

    def run(self, question: str):
        """
        运行ReAct智能体（生成器模式，支持流式交互）。
        """
        self.history = [] # 每次运行时重置历史
        current_step = 0

        while current_step < self.max_steps:
            current_step += 1
            step_header = f"--- 第 {current_step} 步 ---"
            print(step_header)
            log_markdown(f"## {step_header}")
            
            # 1. 格式化提示词
            tools_desc = self.tool_executor.getAvailableTools()
            history_str = "\n".join(self.history)
            prompt = REACT_PROMPT_TEMPLATE.format(
                tools=tools_desc,
                question=question,
                history=history_str
            )

            # 2. 调用LLM进行流式思考
            messages = [{"role": "user", "content": prompt}]
            
            # 使用列表来累积响应内容，以便后续解析
            full_response_parts = []
            
            # 我们实时 yield token 给前端显示目前的思考状态
            # 在没有解析出 Action 之前，默认都当做思维链输出
            for chunk in self.llm_client.think(messages=messages):
                full_response_parts.append(chunk)
                # 实时推送每个 token 到前端展示目前的进展
                yield {"type": "chunk", "content": chunk}
            
            response_text = "".join(full_response_parts)
            
            if not response_text:
                yield {"type": "error", "content": "LLM未能返回有效响应。"}
                break

            # 3. 解析LLM全量输出，判断并执行后续逻辑
            thought, action = self._parse_output(response_text)
            
            if thought:
                print(f"思考: {thought}")

            if not action:
                print("警告:未能解析出有效的Action，流程终止。")
                break

            if action.startswith("Finish"):
                match = re.search(r"Finish\[(.*)\]", action, re.DOTALL)
                if match:
                    final_answer = match.group(1)
                else:
                    final_answer = action.replace("Finish", "").strip("[]: \n")
                
                print(f"🎉 最终答案: {final_answer}")
                log_markdown(f"### 🎉 最终答案\n\n{final_answer}")
                yield {"type": "answer", "content": final_answer}
                return

            tool_name, tool_input = self._parse_action(action)
            if not tool_name or not tool_input:
                continue

            print(f"🎬 行动: {tool_name}[{tool_input}]")
            log_markdown(f"**行动**: `{tool_name}[{tool_input}]`")
            yield {"type": "action", "content": f"{tool_name}[{tool_input}]"}
            
            tool_function = self.tool_executor.getTool(tool_name)
            if not tool_function:
                observation = f"错误:未找到名为 '{tool_name}' 的工具。"
            else:
                observation = tool_function(tool_input)
                
            print(f"👀 观察: {observation}")
            log_markdown(f"**观察**:\n\n{observation}")
            yield {"type": "observation", "content": observation}
            
            self.history.append(f"Action: {action}")
            self.history.append(f"Observation: {observation}")

        print("已达到最大步数，流程终止。")
        yield {"type": "error", "content": "已达到最大步数，流程终止。"}

    def _parse_output(self, text: str):
        """解析LLM输出 Thought 和 Action。"""
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str):
        """解析Action 提取工具名称和输入。"""
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None
