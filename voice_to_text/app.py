import tkinter as tk
import threading
import os
from typing import Optional

from voice_to_text.modules.config import Config
from voice_to_text.modules.api_client import SiliconFlowAPI
from voice_to_text.modules.local_whisper import LocalWhisperManager
from voice_to_text.modules.audio_recorder import AudioRecorder
from voice_to_text.modules.hotkey_manager import HotkeyManager
from voice_to_text.modules.text_input import TextInput
from voice_to_text.modules.tray_icon import TrayIcon
from voice_to_text.modules.floating_window import FloatingWindow
from voice_to_text.modules.gui import SettingsWindow


class VoiceToTextApp:
    def __init__(self):
        print("[DEBUG] 初始化配置...")
        self.config = Config.get_instance()
        
        print("[DEBUG] 创建主窗口...")
        self.root = tk.Tk()
        self.root.title("VoiceToText")
        self.root.geometry("1x1")
        self.root.overrideredirect(True)
        self.root.attributes('-alpha', 0.0)
        self.root.withdraw()
        
        self.is_recording = False
        self.is_processing = False
        self.current_state = "idle"
        
        self.api_client = None
        self.whisper_manager = None
        self.audio_recorder: Optional[AudioRecorder] = None
        self.hotkey_manager: Optional[HotkeyManager] = None
        self.text_input: Optional[TextInput] = None
        self.tray_icon: Optional[TrayIcon] = None
        self.floating_window: Optional[FloatingWindow] = None
        self.settings_window: Optional[SettingsWindow] = None
        
        print("[DEBUG] 初始化模块...")
        self._init_modules()
        self._setup_callbacks()
        
        print("[DEBUG] 设置协议...")
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        
    def _init_modules(self):
        input_mode = self.config.get("input_mode", "paste")
        self.text_input = TextInput(mode=input_mode)
        
        sample_rate = self.config.get("sample_rate", 16000)
        self.audio_recorder = AudioRecorder(sample_rate=sample_rate, channels=1)
        
        self.hotkey_manager = HotkeyManager()
        
        self._init_recognition_engine()
        
    def _init_recognition_engine(self):
        use_local = self.config.get("use_local_whisper", False)
        
        if use_local:
            print("[DEBUG] 初始化本地 Whisper...")
            self.whisper_manager = LocalWhisperManager.get_instance()
            
            chinese_mode = self.config.get("chinese_mode", "simplified")
            print(f"[DEBUG] 从配置读取 chinese_mode: {chinese_mode}")
            
            self.whisper_manager.set_chinese_mode(chinese_mode)
            
            actual_chinese_mode = self.whisper_manager.chinese_mode
            print(f"[DEBUG] 验证 chinese_mode 已设置: {actual_chinese_mode}")
            
            if actual_chinese_mode == chinese_mode:
                print(f"[DEBUG] ✓ chinese_mode 配置验证成功: {chinese_mode}")
            else:
                print(f"[DEBUG] ✗ chinese_mode 配置验证失败! 期望: {chinese_mode}, 实际: {actual_chinese_mode}")
            
            device = self.config.get("device", "cpu")
            compute_type = self.config.get("compute_type", "int8")
            cpu_threads = self.config.get("cpu_threads", 4)
            self.whisper_manager.set_device(device, compute_type, cpu_threads)
            
            model_name = self.config.get("local_model", "base")
            
            downloaded = self.whisper_manager.get_downloaded_models()
            print(f"[DEBUG] 已下载的模型: {downloaded}")
            
            if model_name in downloaded:
                print(f"[DEBUG] 自动加载模型: {model_name}")
                success, msg = self.whisper_manager.load_model(model_name)
                if success:
                    print(f"[DEBUG] {msg}")
                else:
                    print(f"[DEBUG] 模型加载失败: {msg}")
            else:
                print(f"[DEBUG] 模型 {model_name} 未在已下载列表中，尝试直接加载...")
                success, msg = self.whisper_manager.load_model(model_name)
                if success:
                    print(f"[DEBUG] 模型加载成功: {msg}")
                else:
                    print(f"[DEBUG] 模型加载失败: {msg}")
        else:
            print("[DEBUG] 初始化云端 API...")
            api_key = self.config.get("api_key", "")
            
            if api_key:
                self.api_client = SiliconFlowAPI(
                    api_base_url="https://api.siliconflow.cn/v1",
                    api_key=api_key
                )
            else:
                self.api_client = None
                print("[DEBUG] API Key 未配置")
    
    def update_recognition_mode(self, use_local: bool, model_name: str = None):
        print(f"[DEBUG] 更新识别模式: use_local={use_local}, model_name={model_name}")
        
        if use_local:
            self.api_client = None
            self.whisper_manager = LocalWhisperManager.get_instance()
            
            chinese_mode = self.config.get("chinese_mode", "simplified")
            print(f"[DEBUG] 更新模式时从配置读取 chinese_mode: {chinese_mode}")
            
            self.whisper_manager.set_chinese_mode(chinese_mode)
            
            actual_chinese_mode = self.whisper_manager.chinese_mode
            print(f"[DEBUG] 验证 chinese_mode 已更新: {actual_chinese_mode}")
            
            if actual_chinese_mode == chinese_mode:
                print(f"[DEBUG] ✓ chinese_mode 更新验证成功: {chinese_mode}")
            else:
                print(f"[DEBUG] ✗ chinese_mode 更新验证失败! 期望: {chinese_mode}, 实际: {actual_chinese_mode}")
            
            if model_name:
                downloaded = self.whisper_manager.get_downloaded_models()
                if model_name in downloaded:
                    print(f"[DEBUG] 加载模型: {model_name}")
                    self.whisper_manager.load_model(model_name)
        else:
            if self.whisper_manager:
                self.whisper_manager.unload_model()
            self.whisper_manager = None
            
            api_key = self.config.get("api_key", "")
            if api_key:
                self.api_client = SiliconFlowAPI(
                    api_base_url="https://api.siliconflow.cn/v1",
                    api_key=api_key
                )
        
        self.config.set("use_local_whisper", use_local)
        if model_name:
            self.config.set("local_model", model_name)
        
        print(f"[DEBUG] 识别模式更新完成")
            
    def _setup_callbacks(self):
        if self.audio_recorder:
            self.audio_recorder.on_volume_change = self.on_volume_change
            self.audio_recorder.on_silence_detected = self.on_silence_detected
            
    def _create_tray(self):
        print("[DEBUG] 创建托盘图标...")
        self.tray_icon = TrayIcon(self)
        self.tray_icon.show()
        
    def _register_hotkey(self):
        print("[DEBUG] 注册热键...")
        hotkey = self.config.get("hotkey", "ctrl+alt+v")
        if hotkey and self.hotkey_manager:
            self.hotkey_manager.register_hotkey(hotkey, self.toggle_recording)
            self.hotkey_manager.start()
            
    def toggle_recording(self):
        if self.is_processing:
            return
            
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
            
    def start_recording(self):
        if self.is_recording or self.is_processing:
            return
            
        self.is_recording = True
        self.current_state = "recording"
        
        self.show_floating_window()
        self.update_floating_window_status("recording")
        self.update_tray_icon("recording")
        
        silence_threshold = self.config.get("silence_threshold", 500)
        silence_duration = self.config.get("silence_duration", 2.0)
        max_duration = self.config.get("max_record_duration", 60)
        
        if self.audio_recorder:
            try:
                self.audio_recorder.start_recording(
                    silence_threshold=float(silence_threshold),
                    silence_duration=silence_duration,
                    max_duration=float(max_duration)
                )
            except Exception as e:
                self.is_recording = False
                self.current_state = "idle"
                self.show_error(f"无法启动录音: {str(e)}")
                self.hide_floating_window()
                
    def stop_recording(self):
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.is_processing = True
        self.current_state = "processing"
        
        self.update_floating_window_status("recognizing")
        self.update_tray_icon("processing")
        
        audio_file_path = ""
        if self.audio_recorder:
            try:
                audio_file_path = self.audio_recorder.stop_recording()
            except Exception as e:
                self.is_processing = False
                self.current_state = "idle"
                self.show_error(f"停止录音失败: {str(e)}")
                self.hide_floating_window()
                return
                
        if audio_file_path:
            self.process_audio(audio_file_path)
        else:
            self.is_processing = False
            self.current_state = "idle"
            self.show_error("没有录制到音频数据")
            self.hide_floating_window()
            
    def cancel_recording(self):
        if not self.is_recording:
            return
            
        self.is_recording = False
        self.current_state = "idle"
        
        if self.audio_recorder:
            try:
                self.audio_recorder.cancel_recording()
            except Exception:
                pass
                
        self.update_tray_icon("idle")
        self.hide_floating_window()
        
    def on_silence_detected(self):
        if self.is_recording:
            self.root.after(0, self.stop_recording)
            
    def on_volume_change(self, volume: float):
        if self.floating_window and self.is_recording:
            self.root.after(0, lambda: self.floating_window.update_volume(volume))
            
    def process_audio(self, audio_file_path: str):
        use_local = self.config.get("use_local_whisper", False)
        
        def do_process():
            language = self.config.get("language", "auto")
            
            if use_local:
                if self.whisper_manager and self.whisper_manager.is_model_loaded():
                    result = self.whisper_manager.transcribe(audio_file_path, language)
                else:
                    result = {"success": False, "text": "", "error": "本地模型未加载，请先下载模型"}
            else:
                if self.api_client:
                    result = self.api_client.transcribe(audio_file_path, language)
                else:
                    result = {"success": False, "text": "", "error": "API 未配置"}
            
            self.root.after(0, lambda: self._on_transcribe_complete(result, audio_file_path))
            
        threading.Thread(target=do_process, daemon=True).start()
        
    def _on_transcribe_complete(self, result: dict, audio_file_path: str):
        self.is_processing = False
        self.current_state = "idle"
        self.update_tray_icon("idle")
        
        if result.get("success", False):
            text = result.get("text", "")
            if text:
                self.input_text(text)
                if self.floating_window:
                    self.floating_window.show_result(text)
                self.update_floating_window_status("completed")
            else:
                self.show_error("未识别到文字")
        else:
            error = result.get("error", "未知错误")
            self.show_error(error)
            
        try:
            if audio_file_path and os.path.exists(audio_file_path):
                os.remove(audio_file_path)
        except Exception:
            pass
        
    def input_text(self, text: str):
        if not text:
            return
            
        if self.text_input:
            self.text_input.input_with_fallback(text)
                
    def show_floating_window(self):
        if not self.floating_window:
            self.floating_window = FloatingWindow(self)
        self.floating_window.reset()
        self.floating_window.show()
        
    def hide_floating_window(self):
        if self.floating_window:
            self.floating_window.hide()
            
    def update_floating_window_status(self, status: str):
        if self.floating_window:
            self.floating_window.update_status(status)
            
    def show_settings_window(self):
        if not self.settings_window:
            self.settings_window = SettingsWindow(self)
        self.settings_window.show()
        
    def hide_settings_window(self):
        if self.settings_window:
            self.settings_window.hide()
            
    def show_settings(self):
        self.show_settings_window()
        
    def update_tray_icon(self, status: str):
        if self.tray_icon:
            self.tray_icon.update_icon(status)
            
    def show_notification(self, title: str, message: str):
        if self.tray_icon:
            self.tray_icon.show_notification(title, message)
            
    def show_error(self, error: str):
        if self.floating_window:
            self.floating_window.show_error(error)
        
    def update_hotkey(self, new_hotkey: str):
        if self.hotkey_manager:
            success = self.hotkey_manager.update_hotkey(new_hotkey)
            if success:
                self.config.set("hotkey", new_hotkey)
            return success
        return False
        
    def update_config(self, key: str, value):
        print(f"[DEBUG] 更新配置: {key} = {value}")
        self.config.set(key, value)
        
        if key == "sample_rate":
            if self.audio_recorder:
                self.audio_recorder.sample_rate = value
                print(f"[DEBUG] ✓ sample_rate 已更新到 audio_recorder: {value}")
        
        if key == "chinese_mode":
            if self.whisper_manager:
                old_mode = self.whisper_manager.chinese_mode
                self.whisper_manager.set_chinese_mode(value)
                actual_mode = self.whisper_manager.chinese_mode
                print(f"[DEBUG] chinese_mode 更新: {old_mode} -> {actual_mode}")
                
                if actual_mode == value:
                    print(f"[DEBUG] ✓ chinese_mode 已成功应用到 whisper_manager: {value}")
                else:
                    print(f"[DEBUG] ✗ chinese_mode 应用失败! 期望: {value}, 实际: {actual_mode}")
            else:
                print(f"[DEBUG] whisper_manager 未初始化，chinese_mode 将在下次初始化时生效")
                
    def run(self):
        print("[DEBUG] 启动应用...")
        print("[DEBUG] 延迟创建托盘和热键...")
        self.root.after(100, self._create_tray)
        self.root.after(200, self._register_hotkey)
        self.root.after(300, lambda: print("[DEBUG] 应用已启动，按 Ctrl+Alt+V 开始录音"))
        print("[DEBUG] 进入主循环...")
        self.root.mainloop()
        
    def quit(self):
        if self.is_recording:
            self.cancel_recording()
            
        if self.hotkey_manager:
            self.hotkey_manager.stop()
            
        if self.tray_icon:
            self.tray_icon.hide()
            
        self.root.quit()
