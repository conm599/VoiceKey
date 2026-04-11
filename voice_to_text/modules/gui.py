import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from pynput import keyboard
import threading
import os
import pyperclip
from voice_to_text.modules.config import Config
from voice_to_text.modules.api_client import SiliconFlowAPI, SparkAPI
from voice_to_text.modules.local_whisper import LocalWhisperManager, MODELS_INFO, get_available_devices, get_compute_type_options
from voice_to_text.modules.chat_window import ChatWindow
from voice_to_text.modules.chat import SparkChatAPI

AUDIO_FORMATS = [
    ("音频文件", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.wma *.webm"),
    ("MP3 文件", "*.mp3"),
    ("WAV 文件", "*.wav"),
    ("M4A 文件", "*.m4a"),
    ("FLAC 文件", "*.flac"),
    ("所有文件", "*.*")
]


class SettingsWindow:
    def __init__(self, app):
        self.app = app
        self.config = Config.get_instance()
        self.whisper_manager = LocalWhisperManager.get_instance()
        
        self.window = tk.Toplevel()
        self.window.title("语音转文字 - 设置")
        self.window.geometry("600x1000")
        self.window.resizable(True, True)
        
        self.capturing_hotkey = False
        self.hotkey_listener = None
        self.pressed_keys = set()
        self.selected_audio_file = None
        self.is_converting = False
        
        self.setup_ui()
        self.load_config()
        self.setup_window_close()
        self.refresh_model_status()
        
    def setup_ui(self):
        # 创建滚动框架
        self.canvas = tk.Canvas(self.window)
        self.scrollbar = ttk.Scrollbar(self.window, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        
        self.main_frame = ttk.Frame(self.scrollable_frame, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.main_frame.columnconfigure(0, weight=1)
        
        self.create_recognition_mode_section()
        self.create_streaming_section()
        self.create_local_model_section()
        self.create_chinese_mode_section()
        self.create_cloud_api_section()
        self.create_llm_polish_section()
        self.create_hotkey_section()
        self.create_input_mode_section()
        self.create_audio_settings_section()
        self.create_file_upload_section()
        self.create_buttons()
        self.create_status_bar()
        
    def create_recognition_mode_section(self):
        mode_frame = ttk.LabelFrame(self.main_frame, text="识别模式", padding="10")
        mode_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        mode_frame.columnconfigure(1, weight=1)
        
        self.recognition_mode_var = tk.StringVar(value="cloud")
        
        ttk.Radiobutton(
            mode_frame, text="云端识别 (需要网络和 API Key)", 
            variable=self.recognition_mode_var, value="cloud",
            command=self.on_recognition_mode_change
        ).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        ttk.Radiobutton(
            mode_frame, text="本地识别 (无需网络，隐私安全)", 
            variable=self.recognition_mode_var, value="local",
            command=self.on_recognition_mode_change
        ).grid(row=1, column=0, sticky=tk.W, pady=2)
        
    def create_streaming_section(self):
        streaming_frame = ttk.LabelFrame(self.main_frame, text="流式识别设置", padding="10")
        streaming_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.enable_streaming_recognition_var = tk.BooleanVar(value=False)
        self.enable_streaming_recognition_check = ttk.Checkbutton(
            streaming_frame, text="启用流式识别 (实时识别语音片段)",
            variable=self.enable_streaming_recognition_var
        )
        self.enable_streaming_recognition_check.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        chunk_frame = ttk.Frame(streaming_frame)
        chunk_frame.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        ttk.Label(chunk_frame, text="识别片段时长 (秒):").pack(side=tk.LEFT, padx=(0, 5))
        
        self.streaming_chunk_duration_var = tk.DoubleVar(value=3.0)
        self.streaming_chunk_duration_spinbox = ttk.Spinbox(
            chunk_frame, from_=1.0, to=10.0, increment=0.5,
            textvariable=self.streaming_chunk_duration_var, width=8
        )
        self.streaming_chunk_duration_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(chunk_frame, text="(推荐: 2-5秒)", foreground="gray").pack(side=tk.LEFT)
        
        streaming_hint_label = ttk.Label(
            streaming_frame,
            text="注: 流式识别仅在直接输入模式下可用，需要持续的网络连接或本地模型",
            foreground="gray"
        )
        streaming_hint_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        
    def create_local_model_section(self):
        self.local_frame = ttk.LabelFrame(self.main_frame, text="本地模型设置", padding="10")
        self.local_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        self.local_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.local_frame, text="选择模型:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        model_select_frame = ttk.Frame(self.local_frame)
        model_select_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)
        
        self.model_var = tk.StringVar(value="base")
        self.model_combo = ttk.Combobox(
            model_select_frame, textvariable=self.model_var,
            values=list(MODELS_INFO.keys()), state="readonly", width=15
        )
        self.model_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        self.download_button = ttk.Button(model_select_frame, text="下载模型", command=self.download_model, width=12)
        self.download_button.pack(side=tk.LEFT)
        
        self.model_info_label = ttk.Label(self.local_frame, text="", foreground="gray")
        self.model_info_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        device_frame = ttk.Frame(self.local_frame)
        device_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(device_frame, text="计算设备:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.available_devices = get_available_devices()
        device_names = [d["name"] for d in self.available_devices]
        
        self.device_var = tk.StringVar(value="CPU")
        self.device_combo = ttk.Combobox(
            device_frame, textvariable=self.device_var,
            values=device_names, state="readonly", width=25
        )
        self.device_combo.pack(side=tk.LEFT, padx=5)
        self.device_combo.bind('<<ComboboxSelected>>', self.on_device_select)
        
        ttk.Label(device_frame, text="计算类型:").pack(side=tk.LEFT, padx=(10, 5))
        
        self.compute_type_var = tk.StringVar(value="int8")
        self.compute_type_combo = ttk.Combobox(
            device_frame, textvariable=self.compute_type_var,
            values=["int8", "float16", "float32"], state="readonly", width=10
        )
        self.compute_type_combo.pack(side=tk.LEFT, padx=5)
        
        cpu_frame = ttk.Frame(self.local_frame)
        cpu_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=2)
        
        ttk.Label(cpu_frame, text="CPU 线程数:").pack(side=tk.LEFT, padx=(0, 5))
        
        import multiprocessing
        max_threads = multiprocessing.cpu_count()
        
        self.cpu_threads_var = tk.IntVar(value=min(4, max_threads))
        self.cpu_threads_spinbox = ttk.Spinbox(
            cpu_frame, from_=1, to=max_threads,
            textvariable=self.cpu_threads_var, width=5
        )
        self.cpu_threads_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(cpu_frame, text=f"(最大: {max_threads})").pack(side=tk.LEFT)
        
        self.model_status_label = ttk.Label(self.local_frame, text="", foreground="blue")
        self.model_status_label.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(self.local_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.progress_label = ttk.Label(self.local_frame, text="")
        self.progress_label.grid(row=6, column=0, columnspan=2, sticky=tk.W)
        
        self.model_combo.bind('<<ComboboxSelected>>', self.on_model_select)
        
    def create_chinese_mode_section(self):
        chinese_frame = ttk.LabelFrame(self.main_frame, text="中文输出模式", padding="10")
        chinese_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.chinese_mode_var = tk.StringVar(value="simplified")
        
        ttk.Radiobutton(
            chinese_frame, text="简体中文", 
            variable=self.chinese_mode_var, value="simplified"
        ).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        ttk.Radiobutton(
            chinese_frame, text="繁体中文", 
            variable=self.chinese_mode_var, value="traditional"
        ).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        hint_label = ttk.Label(
            chinese_frame, 
            text="选择识别结果的中文输出格式（需要安装 opencc: pip install opencc）",
            foreground="gray"
        )
        hint_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        
    def create_cloud_api_section(self):
        self.cloud_frame = ttk.LabelFrame(self.main_frame, text="云端 API 设置", padding="10")
        self.cloud_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=5)
        self.cloud_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.cloud_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.api_key_entry = ttk.Entry(self.cloud_frame, width=40, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
        
        self.show_key_var = tk.BooleanVar(value=False)
        self.show_key_check = ttk.Checkbutton(
            self.cloud_frame, text="显示 API Key", variable=self.show_key_var,
            command=self.toggle_key_visibility
        )
        self.show_key_check.grid(row=1, column=0, columnspan=2, pady=2)
        
        self.test_button = ttk.Button(self.cloud_frame, text="测试连接", command=self.test_api_connection)
        self.test_button.grid(row=2, column=0, columnspan=2, pady=10)
        
    def create_llm_polish_section(self):
        self.llm_polish_frame = ttk.LabelFrame(self.main_frame, text="大模型润色", padding="10")
        self.llm_polish_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=5)
        self.llm_polish_frame.columnconfigure(1, weight=1)
        
        self.enable_llm_polish_var = tk.BooleanVar(value=False)
        self.enable_llm_polish_check = ttk.Checkbutton(
            self.llm_polish_frame, text="启用大模型润色 (识别后自动修正错别字和常识错误)",
            variable=self.enable_llm_polish_var
        )
        self.enable_llm_polish_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        ttk.Label(self.llm_polish_frame, text="API Password:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.spark_api_password_entry = ttk.Entry(self.llm_polish_frame, width=40, show="*")
        self.spark_api_password_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2, padx=5)
        
        self.show_spark_key_var = tk.BooleanVar(value=False)
        self.show_spark_key_check = ttk.Checkbutton(
            self.llm_polish_frame, text="显示 API Password", variable=self.show_spark_key_var,
            command=self.toggle_spark_key_visibility
        )
        self.show_spark_key_check.grid(row=2, column=0, columnspan=2, pady=2)
        
        ttk.Label(self.llm_polish_frame, text="润色模式:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.polish_mode_var = tk.StringVar(value="correct")
        polish_mode_frame = ttk.Frame(self.llm_polish_frame)
        polish_mode_frame.grid(row=3, column=1, sticky=tk.W, pady=2, padx=5)
        
        ttk.Radiobutton(
            polish_mode_frame, text="修正模式", variable=self.polish_mode_var, value="correct"
        ).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(
            polish_mode_frame, text="润色模式", variable=self.polish_mode_var, value="embellish"
        ).pack(side=tk.LEFT)
        
        mode_hint_label = ttk.Label(
            self.llm_polish_frame,
            text="修正模式: 仅修正明显错误 | 润色模式: 优化语句表达 (温度0.2)",
            foreground="gray"
        )
        mode_hint_label.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.test_spark_button = ttk.Button(self.llm_polish_frame, text="测试星火API连接", command=self.test_spark_api_connection)
        self.test_spark_button.grid(row=5, column=0, columnspan=2, pady=5)
        
        self.enable_stream_output_var = tk.BooleanVar(value=True)
        self.enable_stream_output_check = ttk.Checkbutton(
            self.llm_polish_frame, text="流式输出 (直接输入模式下实时显示润色结果)",
            variable=self.enable_stream_output_var
        )
        self.enable_stream_output_check.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        stream_hint_label = ttk.Label(
            self.llm_polish_frame,
            text="注: 粘贴模式不支持流式输出，仅直接输入模式可用",
            foreground="gray"
        )
        stream_hint_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        chat_frame = ttk.Frame(self.llm_polish_frame)
        chat_frame.grid(row=8, column=0, columnspan=2, pady=10)
        
        self.open_chat_button = ttk.Button(chat_frame, text="打开对话窗口", command=self.open_chat_window)
        self.open_chat_button.pack(side=tk.LEFT, padx=(0, 10))
        
        chat_hint_label = ttk.Label(chat_frame, text="与星火大模型进行对话交流", foreground="gray")
        chat_hint_label.pack(side=tk.LEFT)
        
        self.chat_window = None
        self.chat_api = None
        
    def toggle_spark_key_visibility(self):
        if self.show_spark_key_var.get():
            self.spark_api_password_entry.config(show="")
        else:
            self.spark_api_password_entry.config(show="*")
            
    def test_spark_api_connection(self):
        api_password = self.spark_api_password_entry.get().strip()
        
        if not api_password:
            messagebox.showwarning("警告", "请输入 API Password")
            return
        
        self.test_spark_button.config(state="disabled")
        self.status_var.set("正在测试星火API连接...")
        
        def do_test():
            spark_api = SparkAPI(
                api_url="https://spark-api-open.xf-yun.com/v1/chat/completions",
                api_password=api_password
            )
            success, message = spark_api.test_connection()
            self.window.after(0, lambda: self.on_test_spark_complete(success, message))
        
        threading.Thread(target=do_test, daemon=True).start()
    
    def on_test_spark_complete(self, success: bool, message: str):
        self.test_spark_button.config(state="normal")
        self.status_var.set(message)
        
        if success:
            messagebox.showinfo("成功", message)
        else:
            messagebox.showerror("失败", message)
    
    def open_chat_window(self):
        api_password = self.spark_api_password_entry.get().strip()
        
        if not api_password:
            messagebox.showwarning("警告", "请先输入 API Password")
            return
        
        if self.chat_api is None:
            self.chat_api = SparkChatAPI(
                api_url="https://spark-api-open.xf-yun.com/v1/chat/completions",
                api_password=api_password,
                model="lite"
            )
        else:
            self.chat_api.api_password = api_password
        
        if self.chat_window is None:
            self.chat_window = ChatWindow(self.window, self.chat_api)
        
        self.chat_window.show()
        
    def create_hotkey_section(self):
        hotkey_frame = ttk.LabelFrame(self.main_frame, text="热键配置", padding="10")
        hotkey_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=5)
        hotkey_frame.columnconfigure(1, weight=1)
        
        ttk.Label(hotkey_frame, text="当前热键:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.hotkey_label = ttk.Label(hotkey_frame, text="", width=20)
        self.hotkey_label.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)
        
        self.set_hotkey_button = ttk.Button(hotkey_frame, text="设置新热键", command=self.start_hotkey_capture)
        self.set_hotkey_button.grid(row=1, column=0, pady=5)
        
        self.hotkey_hint_label = ttk.Label(hotkey_frame, text="", foreground="gray")
        self.hotkey_hint_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        
    def create_input_mode_section(self):
        mode_frame = ttk.LabelFrame(self.main_frame, text="输入模式", padding="10")
        mode_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.input_mode_var = tk.StringVar(value="paste")
        
        ttk.Radiobutton(
            mode_frame, text="粘贴模式 (剪贴板 + Ctrl+V)", 
            variable=self.input_mode_var, value="paste"
        ).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        ttk.Radiobutton(
            mode_frame, text="直接输入模式 (pynput 原生输入)", 
            variable=self.input_mode_var, value="direct"
        ).grid(row=1, column=0, sticky=tk.W, pady=2)
    
    def create_audio_settings_section(self):
        audio_frame = ttk.LabelFrame(self.main_frame, text="录音设置", padding="10")
        audio_frame.grid(row=8, column=0, sticky=(tk.W, tk.E), pady=5)
        audio_frame.columnconfigure(1, weight=1)
        
        ttk.Label(audio_frame, text="静音检测阈值:").grid(row=0, column=0, sticky=tk.W, pady=2)
        
        threshold_frame = ttk.Frame(audio_frame)
        threshold_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)
        
        self.silence_threshold_var = tk.IntVar(value=500)
        self.silence_threshold_scale = ttk.Scale(
            threshold_frame, from_=100, to=2000, 
            variable=self.silence_threshold_var, orient=tk.HORIZONTAL, length=200
        )
        self.silence_threshold_scale.pack(side=tk.LEFT, padx=5)
        
        self.silence_threshold_label = ttk.Label(threshold_frame, text="500", width=5)
        self.silence_threshold_label.pack(side=tk.LEFT)
        
        self.silence_threshold_scale.configure(command=self._update_threshold_label)
        
        ttk.Label(audio_frame, text="静音停止时间 (秒):").grid(row=1, column=0, sticky=tk.W, pady=2)
        
        silence_frame = ttk.Frame(audio_frame)
        silence_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)
        
        self.silence_duration_var = tk.DoubleVar(value=2.0)
        self.silence_duration_scale = ttk.Scale(
            silence_frame, from_=0.5, to=5.0, 
            variable=self.silence_duration_var, orient=tk.HORIZONTAL, length=200
        )
        self.silence_duration_scale.pack(side=tk.LEFT, padx=5)
        
        self.silence_duration_label = ttk.Label(silence_frame, text="2.0", width=5)
        self.silence_duration_label.pack(side=tk.LEFT)
        
        self.silence_duration_scale.configure(command=self._update_silence_label)
        
        ttk.Label(audio_frame, text="采样率 (Hz):").grid(row=2, column=0, sticky=tk.W, pady=2)
        
        sample_frame = ttk.Frame(audio_frame)
        sample_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2)
        
        self.sample_rate_var = tk.IntVar(value=16000)
        sample_rate_combo = ttk.Combobox(
            sample_frame, textvariable=self.sample_rate_var,
            values=[8000, 16000, 22050, 44100, 48000], state="readonly", width=10
        )
        sample_rate_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(sample_frame, text="(推荐: 16000)", foreground="gray").pack(side=tk.LEFT)
        
        ttk.Label(audio_frame, text="最大录音时长 (秒):").grid(row=3, column=0, sticky=tk.W, pady=2)
        
        max_frame = ttk.Frame(audio_frame)
        max_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=2)
        
        self.max_duration_var = tk.IntVar(value=60)
        self.max_duration_spinbox = ttk.Spinbox(
            max_frame, from_=10, to=300, 
            textvariable=self.max_duration_var, width=8
        )
        self.max_duration_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(max_frame, text="(10-300秒)", foreground="gray").pack(side=tk.LEFT)
    
    def _update_threshold_label(self, value):
        self.silence_threshold_label.config(text=f"{int(float(value))}")
    
    def _update_silence_label(self, value):
        self.silence_duration_label.config(text=f"{float(value):.1f}")
    
    def create_file_upload_section(self):
        file_frame = ttk.LabelFrame(self.main_frame, text="音频文件转文字", padding="10")
        file_frame.grid(row=9, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        file_frame.columnconfigure(0, weight=1)
        file_frame.rowconfigure(3, weight=1)
        
        select_frame = ttk.Frame(file_frame)
        select_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        select_frame.columnconfigure(1, weight=1)
        
        ttk.Label(select_frame, text="选择文件:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.file_path_var = tk.StringVar(value="")
        self.file_path_entry = ttk.Entry(select_frame, textvariable=self.file_path_var, state="readonly")
        self.file_path_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        self.browse_button = ttk.Button(select_frame, text="浏览", command=self.browse_audio_file, width=8)
        self.browse_button.grid(row=0, column=2, padx=5)
        
        convert_frame = ttk.Frame(file_frame)
        convert_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.convert_button = ttk.Button(convert_frame, text="开始转换", command=self.convert_audio_file, width=12)
        self.convert_button.pack(side=tk.LEFT, padx=5)
        
        self.file_progress_var = tk.DoubleVar(value=0)
        self.file_progress_bar = ttk.Progressbar(convert_frame, variable=self.file_progress_var, maximum=100, length=200)
        self.file_progress_bar.pack(side=tk.LEFT, padx=5)
        
        self.file_progress_label = ttk.Label(convert_frame, text="")
        self.file_progress_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(file_frame, text="转换结果:").grid(row=2, column=0, sticky=tk.W, pady=(10, 2))
        
        result_frame = ttk.Frame(file_frame)
        result_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=2)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        self.result_text = scrolledtext.ScrolledText(result_frame, height=6, wrap=tk.WORD)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        copy_frame = ttk.Frame(file_frame)
        copy_frame.grid(row=4, column=0, sticky=tk.E, pady=5)
        
        self.copy_result_button = ttk.Button(copy_frame, text="复制结果", command=self.copy_result, width=10)
        self.copy_result_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_result_button = ttk.Button(copy_frame, text="清空", command=self.clear_result, width=8)
        self.clear_result_button.pack(side=tk.RIGHT, padx=5)
        
    def create_buttons(self):
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=10, column=0, pady=10)
        
        self.save_button = ttk.Button(button_frame, text="保存", command=self.save_config, width=12)
        self.save_button.grid(row=0, column=0, padx=5)
        
        self.reset_button = ttk.Button(button_frame, text="重置为默认", command=self.reset_to_default, width=12)
        self.reset_button.grid(row=0, column=1, padx=5)
        
        self.close_button = ttk.Button(button_frame, text="关闭", command=self.on_close, width=12)
        self.close_button.grid(row=0, column=2, padx=5)
        
    def create_status_bar(self):
        self.status_var = tk.StringVar(value="就绪")
        self.status_bar = ttk.Label(
            self.window, textvariable=self.status_var,
            relief=tk.SUNKEN, anchor=tk.W, padding="2"
        )
        self.status_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
    def setup_window_close(self):
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def on_recognition_mode_change(self):
        mode = self.recognition_mode_var.get()
        if mode == "local":
            self.cloud_frame.grid_remove()
            self.local_frame.grid()
            self.refresh_model_status()
        else:
            self.local_frame.grid_remove()
            self.cloud_frame.grid()
    
    def on_model_select(self, event=None):
        model_name = self.model_var.get()
        info = MODELS_INFO.get(model_name, {})
        self.model_info_label.config(
            text=f"{info.get('name', '')} | 大小: {info.get('size', '')} | 内存: {info.get('vram', '')}"
        )
        self.refresh_model_status()
    
    def on_device_select(self, event=None):
        device_name = self.device_var.get()
        for device in self.available_devices:
            if device["name"] == device_name:
                backend = device.get("backend", "cpu")
                if backend == "cuda":
                    self.compute_type_combo.config(values=["int8", "float16", "float32"])
                    self.compute_type_var.set("float16")
                elif backend == "directml":
                    self.compute_type_combo.config(values=["float16", "float32"])
                    self.compute_type_var.set("float16")
                else:
                    self.compute_type_combo.config(values=["int8", "float32"])
                    self.compute_type_var.set("int8")
                break
    
    def refresh_model_status(self):
        downloaded = self.whisper_manager.get_downloaded_models()
        current = self.whisper_manager.get_current_model()
        selected = self.model_var.get()
        
        status_parts = []
        if downloaded:
            status_parts.append(f"已下载: {', '.join(downloaded)}")
        else:
            status_parts.append("未下载任何模型")
        
        if current:
            status_parts.append(f"当前加载: {current}")
        elif self.whisper_manager.is_model_loaded():
            status_parts.append("模型已加载")
        
        if selected in downloaded:
            self.download_button.config(text="加载模型")
            if not current or current != selected:
                status_parts.append(f"点击'加载模型'加载 {selected}")
        else:
            self.download_button.config(text="下载模型")
        
        self.model_status_label.config(text=" | ".join(status_parts))
    
    def download_model(self):
        model_name = self.model_var.get()
        
        if self.whisper_manager.is_downloading:
            messagebox.showwarning("提示", "已有模型正在下载中")
            return
        
        downloaded = self.whisper_manager.get_downloaded_models()
        
        if model_name in downloaded:
            self.status_var.set(f"正在加载模型 {model_name}...")
            success, msg = self.whisper_manager.load_model(model_name)
            if success:
                self.config.set("local_model", model_name)
                self.status_var.set(msg)
                self.refresh_model_status()
                messagebox.showinfo("成功", f"模型 {model_name} 加载成功！\n已保存为默认模型。")
            else:
                messagebox.showerror("错误", msg)
            return
        
        self.download_button.config(state="disabled")
        self.progress_var.set(0)
        
        def progress_callback(progress: int, message: str):
            self.window.after(0, lambda: self.update_download_progress(progress, message))
        
        success, msg = self.whisper_manager.download_model(model_name, progress_callback)
        
        if success:
            self.status_var.set(f"正在下载模型 {model_name}...")
        else:
            self.download_button.config(state="normal")
            messagebox.showerror("错误", msg)
    
    def update_download_progress(self, progress: int, message: str):
        self.progress_var.set(progress)
        self.progress_label.config(text=message)
        
        if progress >= 100:
            self.download_button.config(state="normal")
            self.status_var.set("模型下载完成")
            model_name = self.model_var.get()
            self.config.set("local_model", model_name)
            self.refresh_model_status()
            messagebox.showinfo("成功", f"模型 {model_name} 下载完成！\n已保存为默认模型。")
        elif progress < 0:
            self.download_button.config(state="normal")
            self.status_var.set("下载失败")
    
    def toggle_key_visibility(self):
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")
    
    def test_api_connection(self):
        api_key = self.api_key_entry.get().strip()
        
        if not api_key:
            messagebox.showwarning("警告", "请输入 API Key")
            return
        
        self.test_button.config(state="disabled")
        self.status_var.set("正在测试连接...")
        
        def do_test():
            api_client = SiliconFlowAPI(
                api_base_url="https://api.siliconflow.cn/v1",
                api_key=api_key
            )
            success, message = api_client.test_connection()
            self.window.after(0, lambda: self.on_test_complete(success, message))
        
        threading.Thread(target=do_test, daemon=True).start()
    
    def on_test_complete(self, success: bool, message: str):
        self.test_button.config(state="normal")
        self.status_var.set(message)
        
        if success:
            messagebox.showinfo("成功", message)
        else:
            messagebox.showerror("失败", message)
    
    def start_hotkey_capture(self):
        self.capturing_hotkey = True
        self.pressed_keys = set()
        self.set_hotkey_button.config(state="disabled")
        self.hotkey_hint_label.config(text="按下新的热键组合...", foreground="blue")
        self.status_var.set("等待按下新热键...")
        
        self.window.focus_set()
        
        self.hotkey_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.hotkey_listener.start()
    
    def on_key_press(self, key):
        if not self.capturing_hotkey:
            return
        self.pressed_keys.add(key)
    
    def on_key_release(self, key):
        if not self.capturing_hotkey:
            return
        
        if len(self.pressed_keys) >= 2:
            self.capturing_hotkey = False
            
            modifiers = []
            main_key = None
            
            for k in self.pressed_keys:
                if k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                    modifiers.append("ctrl")
                elif k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r):
                    modifiers.append("alt")
                elif k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
                    modifiers.append("shift")
                elif k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
                    modifiers.append("win")
                else:
                    if hasattr(k, 'char') and k.char:
                        main_key = k.char.lower()
                    elif hasattr(k, 'name'):
                        main_key = k.name.lower()
            
            if modifiers and main_key:
                modifiers = sorted(set(modifiers))
                hotkey_str = "+".join(modifiers + [main_key])
                
                self.config.set("hotkey", hotkey_str)
                self.hotkey_label.config(text=hotkey_str)
                self.hotkey_hint_label.config(text="热键已更新", foreground="green")
                self.status_var.set(f"热键已设置为: {hotkey_str}")
                
                if hasattr(self.app, 'hotkey_manager') and self.app.hotkey_manager:
                    self.app.hotkey_manager.update_hotkey(hotkey_str)
            else:
                self.hotkey_hint_label.config(text="无效的热键组合", foreground="red")
                self.status_var.set("热键设置失败")
            
            self.set_hotkey_button.config(state="normal")
            self.pressed_keys.clear()
            
            if self.hotkey_listener:
                self.hotkey_listener.stop()
                self.hotkey_listener = None
    
    def load_config(self):
        self.api_key_entry.delete(0, tk.END)
        self.api_key_entry.insert(0, self.config.get("api_key", ""))
        
        self.hotkey_label.config(text=self.config.get("hotkey", "ctrl+alt+v"))
        
        self.input_mode_var.set(self.config.get("input_mode", "paste"))
        
        self.chinese_mode_var.set(self.config.get("chinese_mode", "simplified"))
        
        use_local = self.config.get("use_local_whisper", False)
        self.recognition_mode_var.set("local" if use_local else "cloud")
        self.on_recognition_mode_change()
        
        self.enable_streaming_recognition_var.set(self.config.get("enable_streaming_recognition", False))
        self.streaming_chunk_duration_var.set(self.config.get("streaming_chunk_duration", 3.0))
        
        self.model_var.set(self.config.get("local_model", "base"))
        self.on_model_select()
        
        device = self.config.get("device", "cpu")
        for d in self.available_devices:
            if d["id"] == device:
                self.device_var.set(d["name"])
                break
        
        self.compute_type_var.set(self.config.get("compute_type", "int8"))
        self.cpu_threads_var.set(self.config.get("cpu_threads", 4))
        
        self.silence_threshold_var.set(self.config.get("silence_threshold", 500))
        self.silence_threshold_label.config(text=str(self.config.get("silence_threshold", 500)))
        
        self.silence_duration_var.set(self.config.get("silence_duration", 2.0))
        self.silence_duration_label.config(text=f"{self.config.get('silence_duration', 2.0):.1f}")
        
        self.sample_rate_var.set(self.config.get("sample_rate", 16000))
        self.max_duration_var.set(self.config.get("max_record_duration", 60))
        
        self.enable_llm_polish_var.set(self.config.get("enable_llm_polish", False))
        self.spark_api_password_entry.delete(0, tk.END)
        self.spark_api_password_entry.insert(0, self.config.get("spark_api_password", ""))
        
        self.enable_stream_output_var.set(self.config.get("enable_stream_output", True))
        self.polish_mode_var.set(self.config.get("polish_mode", "correct"))
    
    def save_config(self):
        try:
            use_local = self.recognition_mode_var.get() == "local"
            
            device_id = "cpu"
            for d in self.available_devices:
                if d["name"] == self.device_var.get():
                    device_id = d["id"]
                    break
            
            config_dict = {
                "api_key": self.api_key_entry.get().strip(),
                "hotkey": self.hotkey_label.cget("text"),
                "input_mode": self.input_mode_var.get(),
                "use_local_whisper": use_local,
                "local_model": self.model_var.get(),
                "chinese_mode": self.chinese_mode_var.get(),
                "device": device_id,
                "compute_type": self.compute_type_var.get(),
                "cpu_threads": self.cpu_threads_var.get(),
                "silence_threshold": self.silence_threshold_var.get(),
                "silence_duration": self.silence_duration_var.get(),
                "sample_rate": self.sample_rate_var.get(),
                "max_record_duration": self.max_duration_var.get(),
                "enable_llm_polish": self.enable_llm_polish_var.get(),
                "spark_api_password": self.spark_api_password_entry.get().strip(),
                "enable_stream_output": self.enable_stream_output_var.get(),
                "polish_mode": self.polish_mode_var.get(),
                "enable_streaming_recognition": self.enable_streaming_recognition_var.get(),
                "streaming_chunk_duration": self.streaming_chunk_duration_var.get(),
            }
            
            self.config.update(config_dict)
            
            if hasattr(self.app, 'text_input') and self.app.text_input:
                self.app.text_input.set_mode(self.input_mode_var.get())
            
            if hasattr(self.app, 'update_recognition_mode'):
                self.app.update_recognition_mode(use_local, self.model_var.get())
            
            if hasattr(self.app, 'whisper_manager') and self.app.whisper_manager:
                self.app.whisper_manager.set_chinese_mode(self.chinese_mode_var.get())
                self.app.whisper_manager.set_device(
                    device_id,
                    self.compute_type_var.get(),
                    self.cpu_threads_var.get()
                )
            
            if hasattr(self.app, 'audio_recorder') and self.app.audio_recorder:
                self.app.audio_recorder.silence_threshold = self.silence_threshold_var.get()
                self.app.audio_recorder.silence_duration = self.silence_duration_var.get()
                self.app.audio_recorder.sample_rate = self.sample_rate_var.get()
                self.app.audio_recorder.max_duration = self.max_duration_var.get()
            
            self.status_var.set("配置保存成功")
            messagebox.showinfo("成功", "配置已保存")
            
        except Exception as e:
            self.status_var.set(f"保存失败: {str(e)}")
            messagebox.showerror("错误", f"保存配置失败: {str(e)}")
    
    def reset_to_default(self):
        if messagebox.askyesno("确认", "确定要重置所有配置为默认值吗？"):
            self.config.reset_to_default()
            self.load_config()
            self.status_var.set("配置已重置为默认值")
            messagebox.showinfo("成功", "配置已重置为默认值")
    
    def on_close(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener = None
        
        self.window.withdraw()
        
        if hasattr(self.app, 'hide_settings_window'):
            self.app.hide_settings_window()
    
    def show(self):
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        self.refresh_model_status()
    
    def hide(self):
        self.window.withdraw()
    
    def browse_audio_file(self):
        file_path = filedialog.askopenfilename(
            title="选择音频文件",
            filetypes=AUDIO_FORMATS
        )
        
        if file_path:
            self.selected_audio_file = file_path
            self.file_path_var.set(file_path)
            
            file_size = os.path.getsize(file_path) / (1024 * 1024)
            self.file_progress_label.config(text=f"已选择 ({file_size:.1f} MB)")
    
    def convert_audio_file(self):
        if self.is_converting:
            return
        
        if not self.selected_audio_file:
            messagebox.showwarning("提示", "请先选择一个音频文件")
            return
        
        if not os.path.exists(self.selected_audio_file):
            messagebox.showerror("错误", "文件不存在")
            return
        
        use_local = self.config.get("use_local_whisper", False)
        
        if use_local:
            if not self.whisper_manager.is_model_loaded():
                messagebox.showwarning("提示", "本地模型未加载，请先加载模型")
                return
        else:
            api_key = self.config.get("api_key", "")
            if not api_key:
                messagebox.showwarning("提示", "请先配置 API Key")
                return
        
        self.is_converting = True
        self.convert_button.config(state="disabled")
        self.browse_button.config(state="disabled")
        self.file_progress_var.set(0)
        self.file_progress_label.config(text="正在转换...")
        self.result_text.delete(1.0, tk.END)
        
        def do_convert():
            try:
                self.window.after(0, lambda: self.file_progress_var.set(10))
                
                if use_local:
                    self.window.after(0, lambda: self.file_progress_label.config(text="本地识别中..."))
                    result = self.whisper_manager.transcribe(self.selected_audio_file, "auto")
                else:
                    self.window.after(0, lambda: self.file_progress_label.config(text="云端识别中..."))
                    api_client = SiliconFlowAPI(
                        api_base_url="https://api.siliconflow.cn/v1",
                        api_key=self.config.get("api_key", "")
                    )
                    result = api_client.transcribe(self.selected_audio_file, "auto")
                
                self.window.after(0, lambda: self.file_progress_var.set(60))
                
                if result.get("success", False):
                    text = result.get("text", "")
                    enable_polish = self.config.get("enable_llm_polish", False)
                    spark_api_password = self.config.get("spark_api_password", "")
                    
                    if enable_polish and spark_api_password and text:
                        self.window.after(0, lambda: self.file_progress_label.config(text="大模型润色中..."))
                        spark_api = SparkAPI(
                            api_url="https://spark-api-open.xf-yun.com/v1/chat/completions",
                            api_password=spark_api_password
                        )
                        polish_result = spark_api.polish_text(text)
                        if polish_result.get("success", False):
                            result["text"] = polish_result.get("text", text)
                
                self.window.after(0, lambda: self.file_progress_var.set(90))
                
                self.window.after(0, lambda: self.on_convert_complete(result))
                
            except Exception as e:
                self.window.after(0, lambda: self.on_convert_error(str(e)))
        
        threading.Thread(target=do_convert, daemon=True).start()
    
    def on_convert_complete(self, result: dict):
        self.is_converting = False
        self.convert_button.config(state="normal")
        self.browse_button.config(state="normal")
        self.file_progress_var.set(100)
        
        if result.get("success", False):
            text = result.get("text", "")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, text)
            self.file_progress_label.config(text="转换完成")
            self.status_var.set("音频文件转换完成")
        else:
            error = result.get("error", "未知错误")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, f"错误: {error}")
            self.file_progress_label.config(text="转换失败")
            self.status_var.set(f"转换失败: {error}")
    
    def on_convert_error(self, error: str):
        self.is_converting = False
        self.convert_button.config(state="normal")
        self.browse_button.config(state="normal")
        self.file_progress_var.set(0)
        self.file_progress_label.config(text="转换失败")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"错误: {error}")
        self.status_var.set(f"转换失败: {error}")
    
    def copy_result(self):
        text = self.result_text.get(1.0, tk.END).strip()
        if text:
            try:
                pyperclip.copy(text)
                self.status_var.set("结果已复制到剪贴板")
                messagebox.showinfo("成功", "结果已复制到剪贴板")
            except Exception as e:
                messagebox.showerror("错误", f"复制失败: {str(e)}")
        else:
            messagebox.showwarning("提示", "没有可复制的内容")
    
    def clear_result(self):
        self.result_text.delete(1.0, tk.END)
        self.file_progress_var.set(0)
        self.file_progress_label.config(text="")
        self.status_var.set("已清空")
