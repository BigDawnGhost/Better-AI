import os
from openai import OpenAI
import json


class Bot:
    def __init__(self):
        self.HISTORY_FILE = './conversation_history.json'
        self.MAX_HISTORY = 100

    def base(self):
        messages = [{"role": "system", "content": '你是一个AI助手'}]
        return messages

    def load_history(self):
        """从本地加载历史记录，出错则返回空"""
        if not os.path.exists(self.HISTORY_FILE):
            return []
        try:
            with open(self.HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ 警告：历史记录文件格式错误，已忽略。")
            return []

    def save_history(self, history):
        """保存历史记录，仅保留最近 self.MAX_HISTORY 条"""
        history = history[-self.MAX_HISTORY:]
        history_dict = [msg if isinstance(msg, dict) else msg.model_dump() for msg in history]
        with open(self.HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_dict, f, ensure_ascii=False, indent=2)

    def deepseek(self, text,key):
        client = OpenAI(api_key=key, base_url="https://api.deepseek.com")
        user_message = {"role": "user", "content": ''.join(text)}
        # 加载历史记录
        history = self.load_history()
        # 获取初始 prompt 和新输入
        messages = self.base() + history
        messages.append(user_message)

        # 改为流式请求
        stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True,
        )

        full_response = []
        print("AI: ", end="", flush=True)
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response.append(content)

        message_content = "".join(full_response)
        message = {"role": "assistant", "content": message_content}

        # 保存历史（追加用户输入和回复）
        history.append(user_message)
        history.append(message)
        self.save_history(history)

        return message_content

with open('key','r') as f:
    key = f.read()
cat = Bot()
res = cat.deepseek(input("You: "),key)
