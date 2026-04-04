import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from typing import Optional, Dict, List

from voice_to_text.modules.chat import SparkChatAPI


class ChatWindow:
    def __init__(self, parent: Optional[tk.Tk] = None, chat_api: Optional[SparkChatAPI] = None):
        self.parent = parent
        self.chat_api = chat_api
        self.window: Optional[tk.Toplevel] = None
        self.is_sending = False
    
    def show(self):
        if self.window is not None and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
        
        self._create_window()
    
    def _create_window(self):
        self.window = tk.Toplevel(self.parent) if self.parent else tk.Tk()
        self.window.title("星火大模型对话")
        self.window.geometry("650x550")
        self.window.minsize(450, 350)
        
        self._create_widgets()
        self._refresh_session_list()
        self._load_current_session()
        
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        session_frame = ttk.Frame(main_frame)
        session_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(session_frame, text="对话:").pack(side=tk.LEFT)
        
        self.session_var = tk.StringVar()
        self.session_combo = ttk.Combobox(session_frame, textvariable=self.session_var, state="readonly", width=30)
        self.session_combo.pack(side=tk.LEFT, padx=5)
        self.session_combo.bind("<<ComboboxSelected>>", self._on_session_selected)
        
        self.new_session_btn = ttk.Button(session_frame, text="新建", command=self._create_new_session, width=6)
        self.new_session_btn.pack(side=tk.LEFT, padx=2)
        
        self.delete_session_btn = ttk.Button(session_frame, text="删除", command=self._delete_current_session, width=6)
        self.delete_session_btn.pack(side=tk.LEFT, padx=2)
        
        self.clear_btn = ttk.Button(session_frame, text="清空", command=self._clear_chat, width=6)
        self.clear_btn.pack(side=tk.RIGHT)
        
        self.chat_display = scrolledtext.ScrolledText(
            main_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("", 10),
            height=20
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.chat_display.tag_configure("user", foreground="#0066cc")
        self.chat_display.tag_configure("assistant", foreground="#333333")
        self.chat_display.tag_configure("error", foreground="#cc0000")
        self.chat_display.tag_configure("system", foreground="#888888")
        
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.input_text = tk.Text(input_frame, height=3, font=("", 10), wrap=tk.WORD)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.input_text.bind("<Control-Return>", lambda e: self._send_message())
        
        self.send_button = ttk.Button(input_frame, text="发送", command=self._send_message, width=8)
        self.send_button.pack(side=tk.RIGHT, fill=tk.Y)
        
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="gray")
        self.status_label.pack(side=tk.LEFT)
        
        self.token_label = ttk.Label(status_frame, text="Token: 0/7000", foreground="gray")
        self.token_label.pack(side=tk.RIGHT)
        
        hint_label = ttk.Label(status_frame, text="Ctrl+Enter发送", foreground="gray")
        hint_label.pack(side=tk.RIGHT, padx=10)
    
    def _refresh_session_list(self):
        if not self.chat_api:
            return
        
        sessions = self.chat_api.get_session_list()
        session_options = []
        self._session_map = {}
        
        for session in sessions:
            display_text = f"{session['title']} ({session['message_count']}条)"
            session_options.append(display_text)
            self._session_map[display_text] = session['id']
        
        self.session_combo['values'] = session_options
        
        current = self.chat_api.get_current_session()
        if current:
            for display_text, session_id in self._session_map.items():
                if session_id == current.session_id:
                    self.session_var.set(display_text)
                    break
    
    def _on_session_selected(self, event=None):
        selected = self.session_var.get()
        if selected and selected in self._session_map:
            session_id = self._session_map[selected]
            self.chat_api.switch_session(session_id)
            self._load_current_session()
    
    def _load_current_session(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
        if not self.chat_api:
            return
        
        session = self.chat_api.get_current_session()
        if session:
            for msg in session.messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                self._append_message(role, content)
            
            self._update_token_count()
    
    def _update_token_count(self):
        if self.chat_api:
            session = self.chat_api.get_current_session()
            if session:
                tokens = session.get_total_tokens()
                self.token_label.config(text=f"Token: {tokens}/7000")
                return
        self.token_label.config(text="Token: 0/7000")
    
    def _append_message(self, role: str, content: str):
        self.chat_display.config(state=tk.NORMAL)
        
        if role == "user":
            self.chat_display.insert(tk.END, "你: ", "user")
            self.chat_display.insert(tk.END, f"{content}\n\n", "user")
        elif role == "assistant":
            self.chat_display.insert(tk.END, "星火: ", "assistant")
            self.chat_display.insert(tk.END, f"{content}\n\n", "assistant")
        else:
            self.chat_display.insert(tk.END, f"{content}\n\n", "system")
        
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def _append_streaming(self, content: str):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, content, "assistant")
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)
    
    def _create_new_session(self):
        if not self.chat_api:
            return
        
        self.chat_api.create_new_session()
        self._refresh_session_list()
        self._load_current_session()
        self.status_var.set("已创建新对话")
    
    def _delete_current_session(self):
        if not self.chat_api:
            return
        
        current = self.chat_api.get_current_session()
        if not current:
            return
        
        if messagebox.askyesno("确认", f"确定要删除对话 \"{current.title}\" 吗？"):
            self.chat_api.delete_session(current.session_id)
            self._refresh_session_list()
            self._load_current_session()
            self.status_var.set("对话已删除")
    
    def _send_message(self):
        if self.is_sending:
            return
        
        message = self.input_text.get("1.0", tk.END).strip()
        if not message:
            return
        
        if not self.chat_api:
            messagebox.showerror("错误", "聊天API未初始化")
            return
        
        self.is_sending = True
        self.send_button.config(state=tk.DISABLED)
        self.input_text.delete("1.0", tk.END)
        self.status_var.set("正在思考...")
        
        self._append_message("user", message)
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "星火: ", "assistant")
        self.chat_display.config(state=tk.DISABLED)
        
        def do_send():
            result = self.chat_api.chat_stream(message, self._on_stream_chunk)
            self.window.after(0, lambda: self._on_send_complete(result))
        
        threading.Thread(target=do_send, daemon=True).start()
    
    def _on_stream_chunk(self, chunk: str):
        if self.window and self.window.winfo_exists():
            self.window.after(0, lambda: self._append_streaming(chunk))
    
    def _on_send_complete(self, result: Dict):
        self.is_sending = False
        self.send_button.config(state=tk.NORMAL)
        
        if result.get("success", False):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, "\n\n")
            self.chat_display.config(state=tk.DISABLED)
            self.status_var.set("就绪")
            self._refresh_session_list()
            self._update_token_count()
        else:
            error = result.get("error", "发送失败")
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"\n[错误: {error}]\n\n", "error")
            self.chat_display.config(state=tk.DISABLED)
            self.status_var.set(f"错误: {error}")
    
    def _clear_chat(self):
        if not self.chat_api:
            return
        
        if messagebox.askyesno("确认", "确定要清空当前对话记录吗？"):
            self.chat_api.clear_current_session()
            self._load_current_session()
            self.status_var.set("对话已清空")
    
    def _on_close(self):
        if self.window:
            self.window.destroy()
            self.window = None
    
    def set_chat_api(self, chat_api: SparkChatAPI):
        self.chat_api = chat_api
