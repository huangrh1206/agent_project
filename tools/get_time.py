import datetime

# 依照约定定义工具三要素
tool_name = "get_current_time"
tool_desc = "获取当前系统的具体日期和时间。无需任何输入参数。"

def tool_func(input_str: str = None) -> str:
    """
    返回当前系统时间。
    """
    now = datetime.datetime.now()
    return f"📅 当前系统具体时间是: {now.strftime('%Y-%m-%d %H:%M:%S')}"
