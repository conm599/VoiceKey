import os
import json
import requests
from typing import Dict, List, Optional, Callable
from datetime import datetime
import uuid
import re


def estimate_tokens(text: str) -> int:
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars * 0.5)


class ChatSession:
    def __init__(self, session_id: str = None, title: str = ""):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.title = title or f"对话 {datetime.now().strftime('%m-%d %H:%M')}"
        self.messages: List[Dict] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def add_message(self, role: str, content: str):
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "tokens": estimate_tokens(content)
        }
        self.messages.append(message)
        self.updated_at = datetime.now().isoformat()
        if role == "user" and not self.title:
            self.title = content[:20] + ("..." if len(content) > 20 else "")
    
    def get_total_tokens(self) -> int:
        return sum(msg.get("tokens", 0) for msg in self.messages)
    
    def get_messages_for_api(self) -> List[Dict]:
        return [{"role": msg["role"], "content": msg["content"]} for msg in self.messages]
    
    def trim_old_messages(self, max_tokens: int = 7000):
        while self.get_total_tokens() > max_tokens and len(self.messages) >= 2:
            self.messages.pop(0)
            if self.messages:
                self.messages.pop(0)
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChatSession':
        session = cls(data.get("session_id"), data.get("title", ""))
        session.messages = data.get("messages", [])
        session.created_at = data.get("created_at", datetime.now().isoformat())
        session.updated_at = data.get("updated_at", datetime.now().isoformat())
        return session


class ChatManager:
    MAX_TOKENS = 7000
    
    def __init__(self, history_dir: str = None):
        if history_dir is None:
            history_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_history")
        self.history_dir = history_dir
        self.sessions_file = os.path.join(history_dir, "sessions.json")
        self.sessions: Dict[str, ChatSession] = {}
        self.current_session_id: Optional[str] = None
        self._ensure_dir()
        self.load_sessions()
    
    def _ensure_dir(self):
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)
    
    def load_sessions(self):
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for session_data in data.get("sessions", []):
                        session = ChatSession.from_dict(session_data)
                        self.sessions[session.session_id] = session
                    self.current_session_id = data.get("current_session_id")
            except (json.JSONDecodeError, IOError):
                self.sessions = {}
        
        if not self.sessions:
            self.create_new_session()
    
    def save_sessions(self):
        try:
            data = {
                "sessions": [session.to_dict() for session in self.sessions.values()],
                "current_session_id": self.current_session_id
            }
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[ERROR] 保存对话列表失败: {e}")
    
    def create_new_session(self, title: str = "") -> ChatSession:
        session = ChatSession(title=title)
        self.sessions[session.session_id] = session
        self.current_session_id = session.session_id
        self.save_sessions()
        return session
    
    def get_current_session(self) -> Optional[ChatSession]:
        if self.current_session_id and self.current_session_id in self.sessions:
            return self.sessions[self.current_session_id]
        return None
    
    def switch_session(self, session_id: str) -> Optional[ChatSession]:
        if session_id in self.sessions:
            self.current_session_id = session_id
            self.save_sessions()
            return self.sessions[session_id]
        return None
    
    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.current_session_id == session_id:
                if self.sessions:
                    self.current_session_id = list(self.sessions.keys())[0]
                else:
                    self.create_new_session()
            self.save_sessions()
    
    def get_session_list(self) -> List[Dict]:
        result = []
        for session in sorted(self.sessions.values(), key=lambda s: s.updated_at, reverse=True):
            result.append({
                "id": session.session_id,
                "title": session.title,
                "message_count": len(session.messages),
                "updated_at": session.updated_at
            })
        return result
    
    def add_message_to_current(self, role: str, content: str):
        session = self.get_current_session()
        if session:
            session.add_message(role, content)
            session.trim_old_messages(self.MAX_TOKENS)
            self.save_sessions()
    
    def clear_current_session(self):
        session = self.get_current_session()
        if session:
            session.messages = []
            self.save_sessions()


class SparkChatAPI:
    CHAT_SYSTEM_PROMPT = """你是星火大模型，一个友好、专业的AI助手。你可以帮助用户解答问题、提供建议、进行对话交流。

请用简洁、清晰的语言回答用户的问题。如果不确定答案，请诚实告知。"""

    def __init__(self, api_url: str, api_password: str, model: str = "lite"):
        self.api_url = api_url.rstrip('/')
        self.api_password = api_password
        self.model = model
        self.timeout = 60
        self.chat_manager: Optional[ChatManager] = None
    
    def init_chat_manager(self, history_dir: str = None):
        self.chat_manager = ChatManager(history_dir)
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_password}",
            "Content-Type": "application/json"
        }
    
    def create_new_session(self, title: str = "") -> Dict:
        if self.chat_manager is None:
            self.init_chat_manager()
        session = self.chat_manager.create_new_session(title)
        return {"success": True, "session_id": session.session_id, "title": session.title}
    
    def switch_session(self, session_id: str) -> Dict:
        if self.chat_manager is None:
            self.init_chat_manager()
        session = self.chat_manager.switch_session(session_id)
        if session:
            return {"success": True, "session_id": session.session_id, "title": session.title}
        return {"success": False, "error": "会话不存在"}
    
    def delete_session(self, session_id: str) -> Dict:
        if self.chat_manager is None:
            self.init_chat_manager()
        self.chat_manager.delete_session(session_id)
        return {"success": True}
    
    def get_session_list(self) -> List[Dict]:
        if self.chat_manager is None:
            self.init_chat_manager()
        return self.chat_manager.get_session_list()
    
    def get_current_session(self) -> Optional[ChatSession]:
        if self.chat_manager is None:
            self.init_chat_manager()
        return self.chat_manager.get_current_session()
    
    def chat(self, user_message: str) -> Dict:
        result = {
            "success": False,
            "text": "",
            "error": ""
        }

        if not user_message or not user_message.strip():
            result["error"] = "消息为空"
            return result

        if self.chat_manager is None:
            self.init_chat_manager()
        
        self.chat_manager.add_message_to_current("user", user_message)
        
        session = self.chat_manager.get_current_session()
        messages = [{"role": "system", "content": self.CHAT_SYSTEM_PROMPT}]
        messages.extend(session.get_messages_for_api())

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                response_data = response.json()
                choices = response_data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    assistant_message = message.get("content", "")
                    self.chat_manager.add_message_to_current("assistant", assistant_message)
                    result["success"] = True
                    result["text"] = assistant_message
                else:
                    result["error"] = "API返回数据格式错误"
            elif response.status_code == 401:
                result["error"] = "认证失败: API Password 无效或已过期"
            elif response.status_code == 429:
                result["error"] = "请求过于频繁,请稍后再试"
            elif response.status_code >= 500:
                result["error"] = f"服务器错误: {response.status_code}"
            else:
                try:
                    error_data = response.json()
                    result["error"] = error_data.get("error", {}).get("message", f"请求失败: {response.status_code}")
                except Exception:
                    result["error"] = f"请求失败: {response.status_code}"

        except requests.exceptions.Timeout:
            result["error"] = "请求超时,请检查网络连接"
        except requests.exceptions.ConnectionError:
            result["error"] = "网络连接失败,请检查网络设置"
        except requests.exceptions.RequestException as e:
            result["error"] = f"请求异常: {str(e)}"
        except Exception as e:
            result["error"] = f"未知错误: {str(e)}"

        return result
    
    def chat_stream(self, user_message: str, callback: Callable[[str], None]) -> Dict:
        result = {
            "success": False,
            "text": "",
            "error": ""
        }

        if not user_message or not user_message.strip():
            result["error"] = "消息为空"
            return result

        if self.chat_manager is None:
            self.init_chat_manager()
        
        self.chat_manager.add_message_to_current("user", user_message)
        
        session = self.chat_manager.get_current_session()
        messages = [{"role": "system", "content": self.CHAT_SYSTEM_PROMPT}]
        messages.extend(session.get_messages_for_api())

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": True
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
                stream=True
            )

            if response.status_code == 200:
                full_content = ""
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data_str = line[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        full_content += content
                                        if callback:
                                            callback(content)
                            except json.JSONDecodeError:
                                continue
                
                self.chat_manager.add_message_to_current("assistant", full_content)
                result["success"] = True
                result["text"] = full_content
            elif response.status_code == 401:
                result["error"] = "认证失败: API Password 无效或已过期"
            elif response.status_code == 429:
                result["error"] = "请求过于频繁,请稍后再试"
            elif response.status_code >= 500:
                result["error"] = f"服务器错误: {response.status_code}"
            else:
                try:
                    error_data = response.json()
                    result["error"] = error_data.get("error", {}).get("message", f"请求失败: {response.status_code}")
                except Exception:
                    result["error"] = f"请求失败: {response.status_code}"

        except requests.exceptions.Timeout:
            result["error"] = "请求超时,请检查网络连接"
        except requests.exceptions.ConnectionError:
            result["error"] = "网络连接失败,请检查网络设置"
        except requests.exceptions.RequestException as e:
            result["error"] = f"请求异常: {str(e)}"
        except Exception as e:
            result["error"] = f"未知错误: {str(e)}"

        return result
    
    def clear_current_session(self):
        if self.chat_manager:
            self.chat_manager.clear_current_session()
    
    def get_history_count(self) -> int:
        if self.chat_manager and self.chat_manager.get_current_session():
            return len(self.chat_manager.get_current_session().messages)
        return 0
