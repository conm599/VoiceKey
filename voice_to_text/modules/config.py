import json
import os
import sys
from dataclasses import dataclass, asdict, field
from typing import Any, Optional


@dataclass
class ConfigData:
    api_base_url: str = "https://api.siliconflow.cn/v1"
    api_key: str = ""
    hotkey: str = "ctrl+alt+v"
    max_record_duration: int = 60
    silence_threshold: int = 500
    silence_duration: float = 2.0
    sample_rate: int = 16000
    floating_window_x: Optional[int] = None
    floating_window_y: Optional[int] = None
    language: str = "auto"
    input_mode: str = "paste"
    use_local_whisper: bool = False
    local_whisper_url: str = "http://127.0.0.1:7860"
    local_model: str = "base"
    chinese_mode: str = "simplified"
    device: str = "cpu"
    compute_type: str = "int8"
    cpu_threads: int = 4


class Config:
    _instance: Optional['Config'] = None
    
    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        # 确定基础目录
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            base_dir = os.path.dirname(sys.executable)
        else:
            # 开发环境
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._config_file = os.path.join(base_dir, "config.json")
        self._initialized = True
        self._data = ConfigData()
        self.load()
    
    def load(self) -> None:
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                    for key, value in config_dict.items():
                        if hasattr(self._data, key):
                            setattr(self._data, key, value)
            except (json.JSONDecodeError, IOError):
                pass
    
    def save(self) -> None:
        config_dict = asdict(self._data)
        os.makedirs(os.path.dirname(self._config_file), exist_ok=True)
        with open(self._config_file, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=4, ensure_ascii=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self._data, key):
            return getattr(self._data, key)
        return default
    
    def set(self, key: str, value: Any) -> None:
        if hasattr(self._data, key):
            setattr(self._data, key, value)
            self.save()
    
    def update(self, config_dict: dict) -> None:
        for key, value in config_dict.items():
            if hasattr(self._data, key):
                setattr(self._data, key, value)
        self.save()
    
    def reset_to_default(self) -> None:
        self._data = ConfigData()
        self.save()
    
    @classmethod
    def get_instance(cls) -> 'Config':
        return cls()
