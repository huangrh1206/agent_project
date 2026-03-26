import os
import json
import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS

from core.llm_client import HelloAgentsLLM
from core.reactagent import ReActAgent
from core.fastagent import FastAgent
from core.planandsolveagent import PlanAndSolveAgent
from core.reflectionagent import ReflectionAgent
from core.utils import log_markdown
from core.register_all_tools import register_all_tools

from werkzeug.utils import secure_filename

# 1. 配置加载与初始化
load_dotenv()

# Web 服务配置
app = Flask(__name__, static_folder='gemini-chat-ui')
CORS(app)

# 文件上传配置
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 2. 静态页面路由
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件到服务器"""
    if 'file' not in request.files:
        return jsonify({"error": "没有文件被上传"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "文件名不能为空"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        # 加上时间戳防止重名
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # 返回绝对路径，供 WordParser 使用
        return jsonify({
            "message": "文件上传成功",
            "filename": filename,
            "abs_path": os.path.abspath(file_path)
        })

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

# 3. 对话接口 (支持 SSE 流式返回)
@app.route('/api/chat', methods=['POST'])
def chat():
    """
    接收用户消息，启动 Agent 执行流并返回分步推理日志。
    """
    data = request.json
    question = data.get('question', '')
    enable_thinking = data.get('enable_thinking', False)
    
    if not question:
        return jsonify({"answer": "请输入您的问题。"})
    
    print(f"📡 收到新对话请求: {question} (思考模式: {enable_thinking})")
    
    def generate():
        # 获取 Agent 类型，默认为 Fast
        agent_type = data.get('agent_type', 'Fast')
        
        client = HelloAgentsLLM(enable_thinking=enable_thinking)
        
        # 根据选择的 Agent 类型选择框架
        if agent_type == "ReAct":
            tool_executor = register_all_tools()
            agent = ReActAgent(client, tool_executor)
        elif agent_type == "Plan&Solve":
            agent = PlanAndSolveAgent(client)
        elif agent_type == "Reflection":
            agent = ReflectionAgent(client)
        else: # Fast
            agent = FastAgent(client)
        print(f"(Agent框架: {agent_type})")
        # 记录会话日志
        log_markdown(f"# 前端对话会话 - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_markdown(f"**问题**: {question}")
        
        # 迭代 Agent 生成器并流式推送事件给前端
        for event in agent.run(question):
            yield f"data: {json.dumps(event)}\n\n"

    return Response(stream_with_context(generate()), content_type='text/event-stream')

# 4. 程序启动入口
if __name__ == '__main__':
    print("🚀 正在启动轻量化模块化的 Gemini 聊天后端...")
    print("👉 请在浏览器中打开: http://localhost:5556")
    
    # debug=True: 代码修改和保存后会自动热重载
    app.run(host='0.0.0.0', port=5556, debug=True)