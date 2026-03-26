# 🤖 My AI Agent

一个基于 Python 开发的轻量级、插件化 AI Agent 助手。支持动态加载工具集，能够自主思考、联网搜索并解析本地文档。

## ✨ 核心特性

- **插件化工具注册**：无需修改主逻辑，只需在 `tools` 目录下新建 Python 文件即可自动识别并注册工具。
- **Web 搜索能力**：集成 Tavily/SerpApi，智能提取网页答案与知识图谱。
- **多格式文档解析**：
  - 支持 `.docx` 和旧版 `.doc` Word 文档解析。
  - 支持 `.pdf` 提取，并内置 GPU 加速的 EasyOCR 补丁，可精准识别扫描版图片文档。

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/huangrh1206/agent_project.git
cd agent_project
```

### 2. 配置环境
推荐使用 Python 3.10+。
```bash
# 创建并激活虚拟环境
python -m venv agentenv
agentenv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量
在项目根目录创建 `.env` 文件，并填入你的 API Keys：
```env
LLM_API_KEY=your_llm_api_key
LLM_MODEL_ID=your_llm_model_id
LLM_BASE_URL=your_llm_base_url
# SERPAPI和Tavily是联网搜索工具，需要注册账号申请apikey，否则无法联网搜索
SERPAPI_API_KEY=your_serpapi_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### 4. 运行 Agent
```bash
python main.py
```

## 🛠️ 工具箱目录 (Tools)
- `search_tavily.py`: 联网搜索引擎。
- `search_google.py`: 联网搜索引擎。
- `word_parser.py`: Word 文档解析器。
- `pdf_parser.py`: PDF 文本与图像 OCR 提取器。