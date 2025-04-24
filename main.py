from flask import Flask, render_template_string, request, Response, jsonify
import os
import json
from openai import OpenAI

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>DeepSeek Chat</title>
    <style>
        body { 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px; 
            font-family: Arial, sans-serif;
            background-color: #f9f9f9;
        }
        .chat-container { 
            border: 1px solid #ddd; 
            border-radius: 10px; 
            padding: 20px; 
            margin-bottom: 20px; 
            background-color: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .message { 
            margin: 15px 0; 
            padding: 12px; 
            border-radius: 8px; 
            position: relative;
        }
        .user { 
            background: #e3f2fd; 
            margin-left: 20px;
            margin-right: 5px;
        }
        .assistant { 
            background: #f5f5f5; 
            margin-right: 20px;
            margin-left: 5px;
        }
        .controls { 
            visibility: hidden;
            position: absolute;
            right: 10px;
            top: 10px;
        }
        .message:hover .controls {
            visibility: visible;
        }
        .controls button { 
            padding: 3px 8px; 
            margin-left: 5px;
            background-color: transparent;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        .controls button:hover {
            background-color: #f0f0f0;
        }
        #input-area { 
            display: flex; 
            gap: 10px; 
            margin-top: 20px;
        }
        #user-input { 
            flex: 1; 
            padding: 12px; 
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        #send-btn { 
            padding: 10px 20px; 
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: background-color 0.2s;
        }
        #send-btn:hover {
            background-color: #0d8bf2;
        }
        #send-btn:disabled {
            background-color: #b0b0b0;
        }
        .content {
            white-space: pre-wrap;
            word-break: break-word;
        }
        .edit-mode textarea {
            width: 100%;
            min-height: 80px;
            margin-bottom: 10px;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-family: inherit;
            font-size: 14px;
        }
        .edit-buttons {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }
        .edit-buttons button {
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
        }
        .save-btn {
            background-color: #4CAF50;
            color: white;
            border: none;
        }
        .cancel-btn {
            background-color: #f5f5f5;
            border: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div id="history">
            {% for msg in history %}
            <div class="message {{ msg.role }}">
                <div class="content">{{ msg.content }}</div>
                <div class="controls">
                    <button onclick="editMessage({{ loop.index0 }})">编辑</button>
                    <button onclick="deleteMessage({{ loop.index0 }})">删除</button>
                </div>
            </div>
            {% endfor %}
        </div>
        <div id="input-area">
            <input type="text" id="user-input" placeholder="输入消息...">
            <button id="send-btn" onclick="sendMessage()">发送</button>
        </div>
    </div>

    <script>
        let currentResponse = null;

        async function sendMessage() {
            const input = document.getElementById('user-input');
            const message = input.value.trim();
            if (!message) return;

            input.disabled = true;
            document.getElementById('send-btn').disabled = true;

            // 添加用户消息
            addMessage('user', message);
            input.value = '';

            // 创建等待助理消息的占位
            currentResponse = addMessage('assistant', '...');

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let responseText = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    responseText += chunk;
                    currentResponse.querySelector('.content').textContent = responseText;
                    currentResponse.scrollIntoView({ behavior: 'smooth' });
                }
            } catch (error) {
                currentResponse.querySelector('.content').textContent = '请求失败: ' + error.message;
            }

            input.disabled = false;
            document.getElementById('send-btn').disabled = false;
            currentResponse = null;
            refreshHistory();
        }

        function addMessage(role, content) {
            const historyDiv = document.getElementById('history');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            messageDiv.innerHTML = `
                <div class="content">${content}</div>
                <div class="controls">
                    <button onclick="editMessageUI(this)">编辑</button>
                    <button onclick="deleteMessage(this)">删除</button>
                </div>
            `;
            historyDiv.appendChild(messageDiv);
            messageDiv.scrollIntoView({ behavior: 'smooth' });
            return messageDiv;
        }

        function editMessageUI(button) {
            const messageDiv = button.closest('.message');
            const contentDiv = messageDiv.querySelector('.content');
            const originalContent = contentDiv.textContent;

            // Replace content with textarea for editing
            messageDiv.classList.add('edit-mode');
            contentDiv.innerHTML = `
                <textarea>${originalContent}</textarea>
                <div class="edit-buttons">
                    <button class="cancel-btn" onclick="cancelEdit(this, '${originalContent.replace(/'/g, "\\'")}')">取消</button>
                    <button class="save-btn" onclick="saveEdit(this)">保存</button>
                </div>
            `;

            // Focus and select text in textarea
            const textarea = contentDiv.querySelector('textarea');
            textarea.focus();
            textarea.select();
        }

        function cancelEdit(button, originalContent) {
            const messageDiv = button.closest('.message');
            const contentDiv = messageDiv.querySelector('.content');
            contentDiv.innerHTML = originalContent;
            messageDiv.classList.remove('edit-mode');
        }

        async function saveEdit(button) {
            const messageDiv = button.closest('.message');
            const contentDiv = messageDiv.querySelector('.content');
            const textarea = contentDiv.querySelector('textarea');
            const newContent = textarea.value.trim();

            const index = Array.from(messageDiv.parentNode.children).indexOf(messageDiv);
            await fetch('/history', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: index, content: newContent })
            });

            refreshHistory();
        }

        async function editMessage(index) {
            const messages = document.querySelectorAll('.message');
            if (index < messages.length) {
                const button = messages[index].querySelector('.controls button');
                editMessageUI(button);
            }
        }

        async function deleteMessage(buttonOrIndex) {
            let index;

            if (typeof buttonOrIndex === 'number') {
                index = buttonOrIndex;
            } else {
                const messageDiv = buttonOrIndex.closest('.message');
                index = Array.from(messageDiv.parentNode.children).indexOf(messageDiv);
            }

            // Delete without confirmation
            await fetch('/history', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: index })
            });

            refreshHistory();
        }

        async function refreshHistory() {
            const response = await fetch('/history');
            const history = await response.json();
            document.getElementById('history').innerHTML = history.map(msg => `
                <div class="message ${msg.role}">
                    <div class="content">${msg.content}</div>
                    <div class="controls">
                        <button onclick="editMessageUI(this)">编辑</button>
                        <button onclick="deleteMessage(this)">删除</button>
                    </div>
                </div>
            `).join('');
        }

        document.getElementById('user-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
'''

class ChatHistory:
    def __init__(self):
        self.HISTORY_FILE = 'conversation_history.json'
        self.MAX_HISTORY = 100

    def load(self):
        if not os.path.exists(self.HISTORY_FILE):
            return []
        try:
            with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def save(self, history):
        with open(self.HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history[-self.MAX_HISTORY:], f, ensure_ascii=False, indent=2)


class ChatBot:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.system_prompt = {"role": "system", "content": "你是一个重口情色小说家"}

    def generate_response(self, messages):
        stream = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[self.system_prompt] + messages,
            stream=True,
            temperature=1.5,
            max_tokens=5000
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

app = Flask(__name__)
@app.route('/')
def index():
    history = history_manager.load()
    return render_template_string(HTML_TEMPLATE, history=history)


@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    history = history_manager.load()

    # 保存用户消息
    history.append({"role": "user", "content": user_message})
    history_manager.save(history)

    def generate():
        full_response = []
        for chunk in bot.generate_response(history):
            full_response.append(chunk)
            yield chunk

        # 保存完整回复
        history.append({"role": "assistant", "content": ''.join(full_response)})
        history_manager.save(history)

    return Response(generate(), mimetype='text/plain')


@app.route('/history', methods=['GET', 'PUT', 'DELETE'])
def manage_history():
    history = history_manager.load()

    if request.method == 'PUT':
        data = request.json
        index = data.get('index')
        if 0 <= index < len(history):
            history[index]['content'] = data.get('content')
            history_manager.save(history)

    elif request.method == 'DELETE':
        index = request.json.get('index')
        if 0 <= index < len(history):
            del history[index]
            history_manager.save(history)

    return jsonify(history)


if __name__ == '__main__':
    history_manager = ChatHistory()
    with open('key', 'r') as f:
        bot = ChatBot(f.read().strip())
    app.run(debug=True,port=5000)
