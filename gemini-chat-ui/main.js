const sidebar = document.getElementById('sidebar');
const menuToggle = document.getElementById('menuToggle');
const greetingScreen = document.getElementById('greetingScreen');
const chatArea = document.getElementById('chatArea');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');
const menuBtn = document.getElementById('menuBtn');
const fileInput = document.getElementById('fileInput');
const attachBtn = document.getElementById('attachBtn');
const filePreview = document.getElementById('filePreview');
const searchBox = document.getElementById('searchBox');

let uploadedFiles = []; // 保存已上传文件信息的数组
const userMessageText = document.getElementById('userMessageText');
const aiResponseContainer = document.getElementById('aiResponseContainer');

// Toggle Sidebar
menuToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    if (sidebar.classList.contains('collapsed')) {
        sidebar.style.width = '70px';
        document.querySelectorAll('.sidebar span, .sidebar-title').forEach(el => el.style.display = 'none');
    } else {
        sidebar.style.width = '280px';
        setTimeout(() => {
            document.querySelectorAll('.sidebar span, .sidebar-title').forEach(el => el.style.display = 'inline');
        }, 100);
    }
});

// --- 文件上传逻辑 ---

// 点击附件图标触发文件选择
attachBtn.addEventListener('click', () => fileInput.click());

// 处理文件选择
fileInput.addEventListener('change', (e) => {
    handleFiles(e.target.files);
    fileInput.value = ''; // 清空选择器以便重选相同文件
});

// 拖拽上传支持
searchBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    searchBox.style.borderColor = 'var(--accent-blue)';
    searchBox.style.backgroundColor = 'rgba(75, 144, 255, 0.05)';
});

searchBox.addEventListener('dragleave', (e) => {
    e.preventDefault();
    searchBox.style.borderColor = 'var(--border-color)';
    searchBox.style.backgroundColor = 'transparent';
});

searchBox.addEventListener('drop', (e) => {
    e.preventDefault();
    searchBox.style.borderColor = 'var(--border-color)';
    searchBox.style.backgroundColor = 'transparent';
    handleFiles(e.dataTransfer.files);
});

async function handleFiles(files) {
    if (!files || files.length === 0) return;
    
    for (let file of files) {
        const ext = file.name.toLowerCase();
        if (!ext.endsWith('.docx') && !ext.endsWith('.pdf')) {
            alert(`忽略文件 ${file.name}: 目前仅支持 .docx 和 .pdf 文档。`);
            continue;
        }
        await uploadFile(file);
    }
}

async function uploadFile(file) {
    // 1. 创建 UI 药丸（Loading 状态）
    const pillId = 'pill-' + Math.random().toString(36).substr(2, 9);
    const pill = document.createElement('div');
    pill.className = 'file-pill';
    pill.id = pillId;
    pill.innerHTML = `
        <i class="ri-loader-4-line ri-spin"></i>
        <span>正在上传 ${file.name}...</span>
    `;
    filePreview.appendChild(pill);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        if (response.ok) {
            // 2. 更新药丸状态（成功）
            uploadedFiles.push({ name: file.name, path: result.abs_path, id: pillId });
            const isPdf = file.name.toLowerCase().endsWith('.pdf');
            const iconClass = isPdf ? 'ri-file-pdf-2-line' : 'ri-file-word-line';
            
            pill.innerHTML = `
                <i class="${iconClass}"></i>
                <span>${file.name}</span>
                <i class="ri-close-line remove-file" onclick="removeUploadedFile('${pillId}')"></i>
            `;
            checkSendBtnVisibility();
        } else {
            pill.innerHTML = `<span style="color: #ff5546;">失败: ${result.error}</span>`;
            setTimeout(() => pill.remove(), 3000);
        }
    } catch (error) {
        console.error('Upload Error:', error);
        pill.innerHTML = `<span style="color: #ff5546;">网络错误</span>`;
        setTimeout(() => pill.remove(), 3000);
    }
}

function removeUploadedFile(pillId) {
    uploadedFiles = uploadedFiles.filter(f => f.id !== pillId);
    const pill = document.getElementById(pillId);
    if (pill) pill.remove();
    checkSendBtnVisibility();
}

function clearFiles() {
    uploadedFiles = [];
    filePreview.innerHTML = '';
}

// 扩展发送按钮显示逻辑：如果没有文字但有文件，也允许点击发送
function checkSendBtnVisibility() {
    if (userInput.value.trim() !== '' || uploadedFiles.length > 0) {
        sendBtn.style.display = 'flex';
    } else {
        sendBtn.style.display = 'none';
    }
}

userInput.addEventListener('input', checkSendBtnVisibility);
// 将原本的 userInput.addEventListener('input', ...) 修改为调用此函数即可。

// Set input from cards
function setInput(text) {
    userInput.value = text;
    checkSendBtnVisibility();
    onSent();
}

// Send Message
async function onSent() {
    const text = userInput.value.trim();
    if (!text) return;

    // Get selected agent type and thinking state from UI
    const agentType = document.getElementById('agentSelector').value;
    const enableThinking = document.getElementById('thinkingToggle').checked;

    // Combine text with uploaded file paths for the agent
    let promptText = text;
    if (uploadedFiles.length > 0) {
        promptText += "\n\n[文件上下文信息]:\n" + uploadedFiles.map(f => `文件: ${f.name}, 路径: ${f.path}`).join("\n");
    }

    // UI Updates
    greetingScreen.style.display = 'none';
    chatArea.style.display = 'block';
    userMessageText.innerText = text;
    userInput.value = '';
    sendBtn.style.display = 'none';
    
    // Clear file preview after sending
    clearFiles();

    // Reset Chat Area
    aiResponseContainer.innerHTML = `
        <div class="loader" id="mainLoader">
            <hr><hr><hr>
        </div>
        <div id="stepsContainer" style="font-size: 14px; color: var(--text-secondary); margin-bottom: 15px;"></div>
        <div id="finalAnswer" class="markdown-body" style="font-size: 17px; line-height: 1.8;"></div>
    `;

    const stepsContainer = document.getElementById('stepsContainer');
    const finalAnswer = document.getElementById('finalAnswer');
    const mainLoader = document.getElementById('mainLoader');

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                question: promptText,
                agent_type: agentType,
                enable_thinking: enableThinking
            }),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let fullAnswer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const event = JSON.parse(line.slice(6));
                        
                        if (event.type === 'chunk') {
                            // Real-time chunk display (token-by-token)
                            let currentStepText = document.getElementById('currentStepInProgress');
                            if (!currentStepText) {
                                currentStepText = document.createElement('div');
                                currentStepText.id = 'currentStepInProgress';
                                currentStepText.style.color = '#8ab4f8';
                                currentStepText.style.fontStyle = 'italic';
                                currentStepText.style.marginBottom = '10px';
                                stepsContainer.appendChild(currentStepText);
                            }
                            currentStepText.innerText += event.content;
                        } else if (event.type === 'thought') {
                            // Step finished, could clean up currentStepInProgress if desired
                        } else if (event.type === 'action') {
                            const prog = document.getElementById('currentStepInProgress');
                            if (prog) prog.id = ''; // Finalize current step's chunk container
                            stepsContainer.innerHTML += `<p style="margin-bottom: 5px;">🎬 <strong>行动:</strong> <code>${event.content}</code></p>`;
                        } else if (event.type === 'observation') {
                            stepsContainer.innerHTML += `<p style="margin-bottom: 10px; color: #888;">👀 <strong>观察:</strong> ${event.content.substring(0, 100)}...</p>`;
                        } else if (event.type === 'answer') {
                            mainLoader.style.display = 'none';
                            const prog = document.getElementById('currentStepInProgress');
                            if (prog) prog.remove();
                            
                            fullAnswer = event.content;
                            finalAnswer.innerHTML = marked.parse(fullAnswer);
                        } else if (event.type === 'error') {
                            mainLoader.style.display = 'none';
                            finalAnswer.innerHTML = `<p style="color: #ff5546;">❌ ${event.content}</p>`;
                        }
                    } catch (e) {
                        console.error("Error parsing JSON:", e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error:', error);
        mainLoader.style.display = 'none';
        aiResponseContainer.innerHTML = `<p style="color: #ff5546;">抱歉，连接服务器时出错。请确保 backend 服务已启动。</p>`;
    }
}

sendBtn.addEventListener('click', onSent);

userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        onSent();
    }
});

// New Chat Button
document.getElementById('newChat').addEventListener('click', () => {
    greetingScreen.style.display = 'block';
    chatArea.style.display = 'none';
    userInput.value = '';
    sendBtn.style.display = 'none';
});
