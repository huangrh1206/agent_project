import ast
import re
from core.llm_client import HelloAgentsLLM
from core.utils import log_markdown

# 增强的规划器 Prompt，引入工具意识和时间意识
PLANNER_PROMPT_TEMPLATE = """
你是一个顶级的AI规划专家。你的任务是将用户提出的复杂问题分解成一个由多个简单步骤组成的行动计划。
请确保计划中的每个步骤都是一个独立的、可执行的子任务，并且严格按照逻辑顺序排列。

# 可用工具:
{tools}

# 时效性原则:
- 如果用户的问题涉及具体的时间点（如“今天”、“现在”、“本周”等），或者涉及需要实时查询的信息（如天气、新闻），你的**第一步**必须是调用 `get_current_time` 工具来获取当前的时间。
- 根据当前时间，再安排后续的搜索或分析任务。

# 输出格式:
你的输出必须且只能是一个Python列表，每个元素都是一个描述单个任务步骤的字符串。
严禁输出任何列表之外的解释。

例如:
```python
["get_current_time[]", "search_tavily[查询2024年3月26日的新闻]", "总结新闻内容"]
```

问题: {question}

请严格按照以下格式输出你的计划:
```python
["步骤1", "步骤2", "步骤3", ...]
```
"""

class Planner:
    def __init__(self, llm_client, tool_executor=None):
        self.llm_client = llm_client
        self.tool_executor = tool_executor

    def plan(self, question: str) -> list[str]:
        """
        根据用户问题生成一个行动计划。
        """
        tools_desc = self.tool_executor.getAvailableTools() if self.tool_executor else "无可用工具"
        prompt = PLANNER_PROMPT_TEMPLATE.format(
            question=question,
            tools=tools_desc
        )
        
        messages = [{"role": "user", "content": prompt}]
        log_markdown("--- 正在生成计划 ---")
        
        # 收集完整回应
        response_text = ""
        for chunk in self.llm_client.think(messages=messages):
            response_text += chunk
        
        log_markdown(f"✅ 计划已生成:\n{response_text}")
        
        try:
            # 找到代码块并解析
            plan_str = re.search(r"```python\s*(.*?)```", response_text, re.DOTALL).group(1).strip()
            plan = ast.literal_eval(plan_str)
            return plan if isinstance(plan, list) else []
        except Exception as e:
            log_markdown(f"❌ 解析计划失败: {e}")
            # 备选解析：简单提取每一行
            return []

EXECUTOR_PROMPT_TEMPLATE = """
你是一位顶级的AI执行专家。你的任务是严格按照给定的计划，一步步地解决问题。
你将收到原始问题、完整的计划、以及到目前为止已经完成的步骤和结果。
请你专注于解决“当前步骤”。

# 可用工具:
{tools}

# 解决原则:
1. 如果“当前步骤”是一个简单的描述符，你可以直接通过推理得出结论。
2. 如果“当前步骤”包含一个工具名称（如 ToolName[input]），你必须生成 Action 来调用它。
3. 请严格按照以下格式进行回应:

Thought: 你的思考过程。
Action: 你决定采取的行动，格式为 `ToolName[input]`。如果没有工具调用，则不填写此项。

# 原始问题:
{question}

# 完整计划:
{plan}

# 历史步骤与结果:
{history}

# 当前步骤:
{current_step}

请开始回应:
"""

class Plan_Executor:
    def __init__(self, llm_client, tool_executor=None):
        self.llm_client = llm_client
        self.tool_executor = tool_executor

    def execute(self, question: str, plan: list[str]):
        """
        根据计划，逐步执行并解决问题（生成器模式）。
        """
        history = "" 
        tools_desc = self.tool_executor.getAvailableTools() if self.tool_executor else "无可用工具"
        
        print("\n--- 正在执行计划 ---")
        
        for i, step in enumerate(plan):
            yield {"type": "action", "content": f"第 {i+1} 步: {step}"}
            print(f"\n-> 正在执行步骤 {i+1}/{len(plan)}: {step}")
            
            prompt = EXECUTOR_PROMPT_TEMPLATE.format(
                question=question,
                plan=plan,
                history=history if history else "无",
                current_step=step,
                tools=tools_desc
            )
            
            messages = [{"role": "user", "content": prompt}]
            
            full_response = ""
            for chunk in self.llm_client.think(messages=messages):
                full_response += chunk
                yield {"type": "chunk", "content": chunk}
            
            # 尝试解析 Thought 和 Action
            thought, action = self._parse_output(full_response)
            
            step_result = ""
            if action and self.tool_executor:
                # 如果有 Action：执行工具
                tool_name, tool_input = self._parse_action(action)
                if tool_name:
                    yield {"type": "action", "content": f"调用工具 {tool_name}[{tool_input}]"}
                    tool_func = self.tool_executor.getTool(tool_name)
                    if tool_func:
                        observation = tool_func(tool_input)
                    else:
                        observation = f"错误: 工具 '{tool_name}' 未找到。"
                    
                    yield {"type": "observation", "content": observation}
                    step_result = f"Thought: {thought}\nAction: {action}\nObservation: {observation}"
                else:
                    step_result = f"Thought: {thought}\nResult: {full_response}"
            else:
                step_result = f"Thought: {thought}\nResult: {full_response}"

            # 更新历史
            history += f"步骤 {i+1}: {step}\n回复: {step_result}\n\n"
            print(f"✅ 步骤 {i+1} 已完成。")

        # 返回最终整合结果
        return full_response

    def _parse_output(self, text: str):
        thought_match = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", text, re.DOTALL)
        action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else text
        action = action_match.group(1).strip() if action_match else None
        return thought, action

    def _parse_action(self, action_text: str):
        match = re.match(r"(\w+)\[(.*)\]", action_text, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, None

class PlanAndSolveAgent:
    def __init__(self, llm_client, tool_executor=None):
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.planner = Planner(self.llm_client, tool_executor)
        self.executor = Plan_Executor(self.llm_client, tool_executor)

    def run(self, question: str):
        log_markdown(f"\n--- 开始处理问题 ---\n问题: {question}")
        yield {"type": "chunk", "content": "🤔 正在为您的问题制定详细计划...\n"}

        # 1. 规划
        plan = self.planner.plan(question)
        if not plan:
            yield {"type": "error", "content": "无法生成有效的行动计划。"}
            return

        # 2. 执行计划并获取过程数据
        history_trace = ""
        exec_gen = self.executor.execute(question, plan)
        try:
            while True:
                event = next(exec_gen)
                yield event
                if event["type"] == "chunk":
                     history_trace += event["content"]
        except StopIteration as e:
             history_trace = e.value
        
        # 3. 强制汇总最终结论 (由于执行器每步可能只输出局部结果，这里做总和)
        yield {"type": "action", "content": "🏁 计划执行完毕，正在为您汇总最终结论..."}
        
        summary_prompt = f"【系统指令：强制总结】\n请根据以下所有步骤的执行历史，为原始问题提供一个完整、最终的答案。不要展开思考过程，不要再调用工具，直接给出清晰的结论。\n\n原始问题：{question}\n\n执行详情如下：\n{history_trace}"
        
        # 暂时关闭思考，快速生成结论
        original_think_state = self.llm_client.enable_thinking
        self.llm_client.enable_thinking = False
        
        final_summary = ""
        for chunk in self.llm_client.think(messages=[{"role": "user", "content": summary_prompt}]):
            final_summary += chunk
            yield {"type": "chunk", "content": chunk}
        
        self.llm_client.enable_thinking = original_think_state
        
        log_markdown(f"\n--- 任务完成 ---\n最终汇总答案: {final_summary}")
        yield {"type": "answer", "content": final_summary}