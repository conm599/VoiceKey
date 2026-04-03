import os
import sys
import threading
import logging
import time
import re
from typing import Optional, Callable, Dict, Tuple, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_TRADITIONAL_TO_SIMPLIFIED = {
    '愛': '爱', '貝': '贝', '筆': '笔', '邊': '边', '賓': '宾',
    '並': '并', '佈': '布', '參': '参', '倉': '仓',
    '車': '车', '長': '长', '廠': '厂', '場': '场', '陳': '陈',
    '稱': '称', '處': '处', '傳': '传', '辭': '辞', '從': '从',
    '達': '达', '帶': '带', '單': '单', '當': '当', '黨': '党',
    '導': '导', '燈': '灯', '點': '点', '電': '电', '東': '东',
    '動': '动', '鬥': '斗', '斷': '断', '對': '对', '隊': '队',
    '兒': '儿', '發': '发', '範': '范', '飛': '飞', '豐': '丰',
    '風': '风', '婦': '妇', '個': '个', '給': '给', '關': '关',
    '觀': '观', '國': '国', '過': '过', '漢': '汉', '號': '号',
    '後': '后', '劃': '划', '畫': '画', '話': '话', '壞': '坏',
    '歡': '欢', '會': '会', '機': '机', '幾': '几', '際': '际',
    '紀': '纪', '價': '价', '檢': '检', '見': '见',
    '講': '讲', '將': '将', '結': '结', '屆': '届', '僅': '仅',
    '進': '进', '經': '经', '開': '开', '來': '来', '樂': '乐',
    '離': '离', '歷': '历', '兩': '两', '靈': '灵', '劉': '刘',
    '龍': '龙', '陸': '陆', '錄': '录', '論': '论', '媽': '妈',
    '馬': '马', '買': '买', '賣': '卖', '門': '门', '們': '们',
    '難': '难', '內': '内',
    '鳥': '鸟', '寧': '宁', '農': '农', '區': '区', '強': '强',
    '親': '亲', '權': '权', '卻': '却', '確': '确', '讓': '让',
    '認': '认', '榮': '荣', '軟': '软',
    '設': '设', '審': '审', '師': '师', '時': '时', '實': '实',
    '書': '书', '術': '术', '樹': '树', '雙': '双', '說': '说',
    '稅': '税', '體': '体', '聽': '听', '統': '统',
    '頭': '头', '圖': '图', '萬': '万', '網': '网', '為': '为',
    '衛': '卫', '問': '问', '無': '无', '務': '务',
    '係': '系', '細': '细', '峽': '峡', '現': '现',
    '線': '线', '憲': '宪', '鄉': '乡', '響': '响', '寫': '写',
    '謝': '谢', '興': '兴', '學': '学', '壓': '压', '嚴': '严',
    '驗': '验', '陽': '阳', '樣': '样', '頁': '页', '醫': '医',
    '藝': '艺', '義': '义', '議': '议', '營': '营', '優': '优',
    '語': '语', '員': '员', '緣': '缘', '遠': '远', '運': '运',
    '雜': '杂', '則': '则', '張': '张', '這': '这', '證': '证',
    '隻': '只', '質': '质', '種': '种', '眾': '众',
    '週': '周', '轉': '转', '裝': '装', '狀': '状', '準': '准',
    '資': '资', '總': '总', '組': '组',
    '業': '业', '舊': '旧', '戰': '战',
    '條': '条', '濟': '济', '環': '环', '聯': '联',
    '層': '层', '構': '构', '適': '适', '讀': '读',
    '變': '变', '識': '识', '須': '须', '題': '题', '類': '类',
    '據': '据', '聲': '声',
    '報': '报', '氣': '气', '縣': '县',
    '選': '选', '養': '养', '顯': '显', '齊': '齐',
    '錢': '钱', '鐘': '钟', '鐵': '铁', '鏡': '镜',
    '閉': '闭', '間': '间',
    '闆': '板', '闘': '斗', '闡': '阐',
    '額': '额', '願': '愿',
    '飯': '饭', '飲': '饮', '飼': '饲',
    '館': '馆', '驅': '驱',
    '騎': '骑', '驚': '惊',
    '髮': '发', '鬧': '闹',
    '魚': '鱼', '鮮': '鲜', '鳳': '凤',
    '鳴': '鸣', '鴨': '鸭', '鴻': '鸿', '鵝': '鹅', '鶴': '鹤',
    '鷹': '鹰', '鹵': '卤', '鹹': '咸', '麗': '丽', '麥': '麦',
    '黃': '黄', '黌': '黉',
    '齋': '斋', '齒': '齿', '齡': '龄',
    '龐': '庞', '龔': '龚', '龜': '龟',
    '測': '测', '試': '试', '簡': '简',
    '於': '于', '裡': '里',
    '計': '计', '產': '产',
    '擇': '择', '擬': '拟', '擴': '扩',
    '擺': '摆', '擾': '扰', '攝': '摄', '攜': '携',
    '敵': '敌', '數': '数',
    '與': '与',
    '麼': '么',
    '腦': '脑',
    '覺': '觉'
}

_SIMPLIFIED_TO_TRADITIONAL = {v: k for k, v in _TRADITIONAL_TO_SIMPLIFIED.items()}

_TRADITIONAL_PATTERN = re.compile(
    '[' + ''.join(re.escape(char) for char in _TRADITIONAL_TO_SIMPLIFIED.keys()) + ']'
)

_SIMPLIFIED_PATTERN = re.compile(
    '[' + ''.join(re.escape(char) for char in _SIMPLIFIED_TO_TRADITIONAL.keys()) + ']'
)


def _has_traditional_chars(text: str) -> bool:
    return bool(_TRADITIONAL_PATTERN.search(text))


def _has_simplified_chars(text: str) -> bool:
    return bool(_SIMPLIFIED_PATTERN.search(text))


def detect_traditional_chinese(text: str) -> Dict:
    """
    检测文本中是否包含繁体字符
    
    Args:
        text: 要检测的文本
        
    Returns:
        Dict: 包含以下键的字典:
            - has_traditional: bool, 是否包含繁体字符
            - traditional_chars: list, 检测到的繁体字符列表
            - count: int, 繁体字符的数量
            - positions: list, 繁体字符在文本中的位置列表
    """
    if not text:
        return {
            "has_traditional": False,
            "traditional_chars": [],
            "count": 0,
            "positions": []
        }
    
    traditional_chars = []
    positions = []
    
    for idx, char in enumerate(text):
        if char in _TRADITIONAL_TO_SIMPLIFIED:
            traditional_chars.append(char)
            positions.append(idx)
    
    result = {
        "has_traditional": len(traditional_chars) > 0,
        "traditional_chars": list(set(traditional_chars)),
        "count": len(traditional_chars),
        "positions": positions
    }
    
    logger.debug(f"繁体字符检测结果: 包含繁体={result['has_traditional']}, "
                 f"字符数={result['count']}, "
                 f"繁体字符={result['traditional_chars']}")
    
    return result


def _builtin_convert_to_simplified(text: str) -> str:
    result = []
    for char in text:
        result.append(_TRADITIONAL_TO_SIMPLIFIED.get(char, char))
    return ''.join(result)


def _builtin_convert_to_traditional(text: str) -> str:
    result = []
    for char in text:
        result.append(_SIMPLIFIED_TO_TRADITIONAL.get(char, char))
    return ''.join(result)


def convert_chinese(text: str, target: str = "simplified") -> str:
    start_time = time.time()
    original_text = text
    conversion_method = "none"
    has_traditional = _has_traditional_chars(text) if target == "simplified" else False
    has_simplified = _has_simplified_chars(text) if target == "traditional" else False
    
    logger.info(f"中文转换开始 - 原始文本: {text}")
    logger.info(f"目标转换类型: {target}")
    logger.info(f"检测到繁体字符: {has_traditional}" if target == "simplified" else f"检测到简体字符: {has_simplified}")
    
    if target not in ["simplified", "traditional"]:
        logger.warning(f"无效的目标转换类型: {target}，返回原始文本")
        return text
    
    try:
        try:
            from zhconv import convert
            
            if target == "simplified":
                result = convert(text, 'zh-cn')
                conversion_method = "zhconv"
            else:
                result = convert(text, 'zh-tw')
                conversion_method = "zhconv"
            
            logger.debug(f"zhconv 转换成功")
            
        except ImportError as e:
            logger.warning(f"zhconv 未安装: {e}，使用内置转换方案")
            
            if target == "simplified":
                result = _builtin_convert_to_simplified(text)
                conversion_method = "builtin"
            else:
                result = _builtin_convert_to_traditional(text)
                conversion_method = "builtin"
                
        except Exception as e:
            logger.error(f"zhconv 转换失败: {e}，回退到内置转换方案")
            
            if target == "simplified":
                result = _builtin_convert_to_simplified(text)
                conversion_method = "builtin_fallback"
            else:
                result = _builtin_convert_to_traditional(text)
                conversion_method = "builtin_fallback"
        
        if target == "simplified" and _has_traditional_chars(result):
            logger.warning("转换后仍检测到繁体字符，尝试使用内置方案再次转换")
            result = _builtin_convert_to_simplified(result)
            conversion_method = f"{conversion_method}+builtin_validation"
        elif target == "traditional" and _has_simplified_chars(result):
            logger.warning("转换后仍检测到简体字符，尝试使用内置方案再次转换")
            result = _builtin_convert_to_traditional(result)
            conversion_method = f"{conversion_method}+builtin_validation"
        
        elapsed_time = (time.time() - start_time) * 1000
        
        logger.info(f"转换方法: {conversion_method}")
        logger.info(f"转换后文本: {result}")
        logger.info(f"转换耗时: {elapsed_time:.2f}ms")
        
        if target == "simplified":
            final_has_traditional = _has_traditional_chars(result)
            logger.info(f"最终结果仍含繁体字符: {final_has_traditional}")
        else:
            final_has_simplified = _has_simplified_chars(result)
            logger.info(f"最终结果仍含简体字符: {final_has_simplified}")
        
        return result
        
    except Exception as e:
        elapsed_time = (time.time() - start_time) * 1000
        logger.error(f"中文转换过程发生未预期错误: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"转换耗时: {elapsed_time:.2f}ms")
        logger.error(f"返回原始文本")
        return original_text

# 使用相对路径，基于当前可执行文件的目录
if getattr(sys, 'frozen', False):
    # 打包后的环境
    base_dir = Path(os.path.dirname(sys.executable))
else:
    # 开发环境 - 向上两级到项目根目录
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

MODELS_DIR = base_dir / "models"
MODELS_INFO = {
    "tiny": {"name": "Tiny (最快)", "size": "~75MB", "vram": "~1GB"},
    "base": {"name": "Base (推荐)", "size": "~150MB", "vram": "~1GB"},
    "small": {"name": "Small (准确)", "size": "~500MB", "vram": "~2GB"},
}

HF_MIRROR_URL = "https://hf-mirror.com"


def set_hf_mirror(use_mirror: bool = True):
    if use_mirror:
        os.environ['HF_ENDPOINT'] = HF_MIRROR_URL
        logger.info(f"已设置 Hugging Face 镜像源: {HF_MIRROR_URL}")
    else:
        if 'HF_ENDPOINT' in os.environ:
            del os.environ['HF_ENDPOINT']
            logger.info("已恢复使用 Hugging Face 官方源")


def check_internet_connection() -> bool:
    try:
        import requests
        response = requests.get("https://www.baidu.com", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def get_available_devices() -> List[Dict]:
    devices = [{"id": "cpu", "name": "CPU (多线程)", "type": "cpu", "backend": "cpu"}]
    
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
                devices.append({
                    "id": f"cuda:{i}",
                    "name": f"{gpu_name} ({gpu_memory:.1f}GB) [CUDA]",
                    "type": "cuda",
                    "backend": "cuda"
                })
    except ImportError:
        pass
    
    try:
        result = os.popen('wmic path win32_VideoController get name /format:csv').read()
        lines = result.strip().split('\n')
        gpu_index = 0
        for line in lines[1:]:
            if line.strip():
                parts = line.strip().split(',')
                if len(parts) >= 2 and parts[1].strip():
                    gpu_name = parts[1].strip()
                    name_lower = gpu_name.lower()
                    
                    is_cuda = any(d["type"] == "cuda" and gpu_name.lower() in d["name"].lower() for d in devices)
                    
                    if not is_cuda:
                        if "amd" in name_lower or "radeon" in name_lower:
                            devices.append({
                                "id": f"dml:{gpu_index}",
                                "name": f"{gpu_name} [DirectML]",
                                "type": "amd",
                                "backend": "directml"
                            })
                            gpu_index += 1
                        elif "intel" in name_lower and ("arc" in name_lower or "iris" in name_lower or "uhd" in name_lower or "xe" in name_lower):
                            devices.append({
                                "id": f"dml:{gpu_index}",
                                "name": f"{gpu_name} [DirectML]",
                                "type": "intel",
                                "backend": "directml"
                            })
                            gpu_index += 1
    except Exception as e:
        logger.error(f"检测 GPU 失败: {e}")
    
    logger.info(f"检测到设备: {devices}")
    return devices


def check_directml_available() -> bool:
    try:
        import onnxruntime as ort
        available = 'DmlExecutionProvider' in ort.get_available_providers()
        return available
    except ImportError:
        return False
    except Exception:
        return False


def get_compute_type_options(backend: str) -> List[str]:
    if backend == "cuda":
        return ["int8", "float16", "float32"]
    elif backend == "directml":
        return ["float16", "float32"]
    else:
        return ["int8", "float32"]


class LocalWhisperManager:
    _instance: Optional['LocalWhisperManager'] = None
    _lock = threading.Lock()
    _model_lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._initialized = True
            self.model = None
            self.current_model_name = None
            self.is_downloading = False
            self.download_progress = 0
            self.chinese_mode = "simplified"
            self.device = "cpu"
            self.device_type = "cpu"
            self.backend = "cpu"
            self.compute_type = "int8"
            self.cpu_threads = os.cpu_count() or 4
            self._load_operation_lock = threading.Lock()
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    def set_chinese_mode(self, mode: str):
        self.chinese_mode = mode
    
    def set_device(self, device: str, compute_type: str = None, cpu_threads: int = None):
        self.device = device
        
        if device.startswith("cuda:"):
            self.device_type = "cuda"
            self.backend = "cuda"
        elif device.startswith("dml:"):
            self.device_type = "directml"
            self.backend = "directml"
        else:
            self.device_type = "cpu"
            self.backend = "cpu"
        
        if compute_type:
            self.compute_type = compute_type
        if cpu_threads:
            self.cpu_threads = cpu_threads
        
        logger.info(f"设置设备: {device}, 后端: {self.backend}, 计算类型: {self.compute_type}, CPU线程: {self.cpu_threads}")
    
    def get_device_info(self) -> Dict:
        return {
            "device": self.device,
            "device_type": self.device_type,
            "backend": self.backend,
            "compute_type": self.compute_type,
            "cpu_threads": self.cpu_threads
        }
    
    def check_faster_whisper_installed(self) -> bool:
        try:
            import faster_whisper
            return True
        except ImportError:
            return False
    
    def check_onnxruntime_installed(self) -> bool:
        try:
            import onnxruntime
            return True
        except ImportError:
            return False
    
    def _check_model_dir_valid(self, model_path: Path) -> bool:
        if not model_path.exists():
            return False
        
        blobs_dir = model_path / "blobs"
        if blobs_dir.exists():
            try:
                blobs = list(blobs_dir.iterdir())
                if len(blobs) > 0:
                    return True
            except Exception:
                pass
        
        try:
            for item in model_path.iterdir():
                if item.is_file() and item.suffix in ['.bin', '.pt', '.json', '.onnx']:
                    return True
        except Exception:
            pass
        
        return False
    
    def get_downloaded_models(self) -> list:
        downloaded = []
        
        check_paths = [
            MODELS_DIR,
            Path.home() / ".cache" / "huggingface" / "hub",
        ]
        
        for base_path in check_paths:
            try:
                if not base_path.exists():
                    continue
                    
                for model_name in MODELS_INFO.keys():
                    model_cache = base_path / f"models--Systran--faster-whisper-{model_name}"
                    if model_cache.exists():
                        if self._check_model_dir_valid(model_cache):
                            if model_name not in downloaded:
                                downloaded.append(model_name)
            except Exception as e:
                logger.error(f"检查路径 {base_path} 时出错: {e}")
        
        logger.info(f"已下载模型列表: {downloaded}")
        return downloaded
    
    def is_model_downloaded(self, model_name: str) -> bool:
        return model_name in self.get_downloaded_models()
    
    def _load_model_cuda(self, model_name: str):
        from faster_whisper import WhisperModel
        
        logger.info(f"使用 CUDA 后端加载模型: {model_name}")
        
        model = WhisperModel(
            model_name,
            device="cuda",
            compute_type=self.compute_type,
            download_root=str(MODELS_DIR),
            cpu_threads=self.cpu_threads
        )
        
        return model
    
    def _load_model_cpu(self, model_name: str):
        from faster_whisper import WhisperModel
        
        logger.info(f"使用 CPU 后端加载模型: {model_name}")
        
        model = WhisperModel(
            model_name,
            device="cpu",
            compute_type=self.compute_type,
            download_root=str(MODELS_DIR),
            cpu_threads=self.cpu_threads
        )
        
        return model
    
    def _load_model_directml(self, model_name: str):
        logger.info(f"使用 DirectML 后端加载模型: {model_name}")
        
        try:
            import onnxruntime as ort
            if 'DmlExecutionProvider' not in ort.get_available_providers():
                logger.warning("DirectML 不可用，回退到 CPU")
                return self._load_model_cpu(model_name)
        except ImportError:
            logger.warning("onnxruntime 未安装，回退到 CPU")
            return self._load_model_cpu(model_name)
        
        from faster_whisper import WhisperModel
        
        model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="float32",
            download_root=str(MODELS_DIR),
            cpu_threads=self.cpu_threads
        )
        
        return model
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> Tuple[bool, str]:
        if model_name not in MODELS_INFO:
            return False, f"未知模型: {model_name}"
        
        if self.is_downloading:
            return False, "已有模型正在下载中"
        
        if not self.check_faster_whisper_installed():
            if progress_callback:
                progress_callback(0, "正在安装 faster-whisper...")
            import subprocess
            result = subprocess.run(
                [os.sys.executable, "-m", "pip", "install", "faster-whisper"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return False, f"安装 faster-whisper 失败"
        
        if self.is_model_downloaded(model_name):
            if progress_callback:
                progress_callback(100, f"模型 {model_name} 已存在，正在加载...")
            success, msg = self.load_model(model_name)
            return success, msg
        
        self.is_downloading = True
        
        def download_thread():
            try:
                set_hf_mirror(True)
                
                if not check_internet_connection():
                    self.is_downloading = False
                    if progress_callback:
                        progress_callback(-1, "网络连接失败，请检查网络设置")
                    return
                
                from faster_whisper import WhisperModel
                
                if progress_callback:
                    progress_callback(10, f"正在下载模型 {model_name}...")
                
                try:
                    model = WhisperModel(
                        model_name,
                        device="cpu",
                        compute_type="int8",
                        download_root=str(MODELS_DIR),
                        cpu_threads=self.cpu_threads
                    )
                    
                    with self._model_lock:
                        self.model = model
                        self.current_model_name = model_name
                    self.is_downloading = False
                    
                    if progress_callback:
                        progress_callback(100, f"模型 {model_name} 下载完成")
                    
                except Exception as e:
                    logger.error(f"下载失败: {e}")
                    self.is_downloading = False
                    if progress_callback:
                        progress_callback(-1, f"下载失败: {str(e)}")
                
            except Exception as e:
                self.is_downloading = False
                if progress_callback:
                    progress_callback(-1, f"下载失败: {str(e)}")
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
        
        return True, "开始下载模型..."
    
    def load_model(self, model_name: str) -> Tuple[bool, str]:
        if model_name not in MODELS_INFO:
            return False, f"未知模型: {model_name}"
        
        with self._load_operation_lock:
            if self.current_model_name == model_name and self.model is not None:
                return True, f"模型 {model_name} 已加载"
            
            try:
                set_hf_mirror(True)
                
                logger.info(f"加载模型: {model_name}, 后端: {self.backend}")
                
                if self.backend == "cuda":
                    model = self._load_model_cuda(model_name)
                elif self.backend == "directml":
                    model = self._load_model_directml(model_name)
                else:
                    model = self._load_model_cpu(model_name)
                
                with self._model_lock:
                    self.model = model
                    self.current_model_name = model_name
                
                logger.info(f"模型加载完成: {model_name}")
                return True, f"模型 {model_name} 加载成功 ({self.backend})"
                
            except Exception as e:
                logger.error(f"加载模型失败: {e}")
                return False, f"加载失败: {str(e)}"
    
    def unload_model(self):
        with self._model_lock:
            self.model = None
            self.current_model_name = None
    
    def transcribe(self, audio_path: str, language: str = "auto") -> Dict:
        result = {
            "success": False,
            "text": "",
            "error": ""
        }
        
        with self._model_lock:
            if self.model is None:
                result["error"] = "模型未加载"
                return result
            
            model_ref = self.model
        
        try:
            lang = None if language == "auto" else language
            segments, info = model_ref.transcribe(
                audio_path, 
                language=lang,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
            text = "".join([segment.text for segment in segments])
            logger.info(f"识别原始文本: {text}")
            logger.info(f"当前中文模式: {self.chinese_mode}")
            
            converted_text = convert_chinese(text, self.chinese_mode)
            logger.info(f"转换后文本: {converted_text}")
            
            if self.chinese_mode == "simplified":
                detection_result = detect_traditional_chinese(converted_text)
                
                if detection_result["has_traditional"]:
                    logger.warning(f"首次转换后仍检测到繁体字符: {detection_result['traditional_chars']}")
                    logger.warning(f"繁体字符数量: {detection_result['count']}, 位置: {detection_result['positions']}")
                    logger.warning("尝试进行二次转换...")
                    
                    converted_text = convert_chinese(converted_text, self.chinese_mode)
                    logger.info(f"二次转换后文本: {converted_text}")
                    
                    second_detection = detect_traditional_chinese(converted_text)
                    if second_detection["has_traditional"]:
                        logger.warning(f"二次转换后仍存在繁体字符: {second_detection['traditional_chars']}")
                        logger.warning(f"剩余繁体字符数量: {second_detection['count']}")
                        logger.warning("这些字符可能不在转换字典中，建议手动检查")
                    else:
                        logger.info("二次转换成功，已消除所有繁体字符")
                else:
                    logger.info("转换验证通过，未检测到繁体字符")
            
            result["success"] = True
            result["text"] = converted_text.strip()
            
        except Exception as e:
            logger.error(f"识别过程发生错误: {str(e)}", exc_info=True)
            result["error"] = f"识别失败: {str(e)}"
        
        return result
    
    def is_model_loaded(self) -> bool:
        with self._model_lock:
            return self.model is not None
    
    def get_current_model(self) -> Optional[str]:
        with self._model_lock:
            return self.current_model_name
    
    @classmethod
    def get_instance(cls) -> 'LocalWhisperManager':
        return cls()
