import pkgutil
import importlib
import tools
import traceback
from core.utils import log_markdown
from core.reactagent import ToolExecutor

def register_all_tools():
    """
    自动注册 tools 包下的所有工具
    """
    registered_names = set() # 用于检查重名
    executor = ToolExecutor()
    log_markdown("# 正在注册工具...")
    # 1. 遍历 tools 包下的所有模块
    for _, module_name, is_pkg in pkgutil.iter_modules(tools.__path__):
        if is_pkg: 
            continue  # 跳过子文件夹
        
        full_module_name = f"tools.{module_name}"
        
        try:
            # 2. 动态导入模块
            # 如果模块内部有语法错误或 import 错误，这里会抛出异常
            module = importlib.import_module(full_module_name)
            
            # 3. 校验约定的工具属性
            required_attrs = ["tool_name", "tool_desc", "tool_func"]
            if all(hasattr(module, attr) for attr in required_attrs):
                
                t_name = module.tool_name
                
                # 安全检查：防止重名工具覆盖
                if t_name in registered_names:
                    log_markdown(f"⚠️ 跳过 {module_name}: 工具名称 '{t_name}' 已被占用")
                    continue

                # 4. 执行注册
                executor.registerTool(
                    t_name,
                    module.tool_desc,
                    module.tool_func
                )
                
                registered_names.add(t_name)
                log_markdown(f"✅ 成功加载: {module_name} -> [{t_name}]")
            else:
                log_markdown(f"ℹ️ 忽略模块 {module_name}: 缺少 tool_name/desc/func 约定")

        except Exception as e:
            # 关键：捕获所有导入或注册过程中的错误
            log_markdown(f"❌ 加载工具模块 [{module_name}] 出错!")
            # 打印简短错误信息
            log_markdown(f"   错误类型: {type(e).__name__}: {e}")
            # 如果需要调试详细堆栈，可以取消下面这一行的注释：
            # traceback.print_exc() 
            continue # 继续加载下一个工具，不中断程序

    log_markdown(f"\n🚀 工具初始化完成，共成功注册 {len(registered_names)} 个工具。")
    return executor