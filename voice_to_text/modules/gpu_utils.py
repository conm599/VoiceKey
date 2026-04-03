import subprocess
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def get_dx12_gpus() -> List[Dict]:
    gpus = []
    
    try:
        result = subprocess.run(
            ['wmic', 'path', 'win32_VideoController', 'get', 'name,adapterram,driverversion', '/format:csv'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:
                if line.strip():
                    parts = line.strip().split(',')
                    if len(parts) >= 4:
                        name = parts[2].strip() if parts[2] else ""
                        ram = parts[1].strip() if parts[1] else "0"
                        driver = parts[3].strip() if parts[3] else ""
                        
                        if name:
                            try:
                                ram_mb = int(ram) // (1024 * 1024) if ram.isdigit() else 0
                            except:
                                ram_mb = 0
                            
                            gpu_type = "unknown"
                            name_lower = name.lower()
                            if "nvidia" in name_lower or "geforce" in name_lower or "gtx" in name_lower or "rtx" in name_lower:
                                gpu_type = "nvidia"
                            elif "amd" in name_lower or "radeon" in name_lower or "rx " in name_lower:
                                gpu_type = "amd"
                            elif "intel" in name_lower and ("arc" in name_lower or "iris" in name_lower or "uhd" in name_lower or "xe" in name_lower):
                                gpu_type = "intel"
                            
                            gpus.append({
                                "name": name,
                                "type": gpu_type,
                                "ram_mb": ram_mb,
                                "driver": driver,
                                "id": f"gpu_{len(gpus)}"
                            })
    except Exception as e:
        logger.error(f"检测 GPU 失败: {e}")
    
    return gpus


def check_directml_available() -> bool:
    try:
        import onnxruntime as ort
        available = 'DmlExecutionProvider' in ort.get_available_providers()
        logger.info(f"DirectML 可用: {available}")
        return available
    except ImportError:
        logger.info("onnxruntime 未安装")
        return False
    except Exception as e:
        logger.error(f"检查 DirectML 失败: {e}")
        return False


def check_cuda_available() -> bool:
    try:
        import torch
        available = torch.cuda.is_available()
        logger.info(f"CUDA 可用: {available}")
        return available
    except ImportError:
        return False
    except Exception:
        return False


def get_available_compute_devices() -> List[Dict]:
    devices = []
    
    devices.append({
        "id": "cpu",
        "name": "CPU (多线程)",
        "type": "cpu",
        "backend": "cpu",
        "ram_mb": 0
    })
    
    gpus = get_dx12_gpus()
    cuda_available = check_cuda_available()
    directml_available = check_directml_available()
    
    for i, gpu in enumerate(gpus):
        device = {
            "id": f"gpu_{i}",
            "name": gpu["name"],
            "type": gpu["type"],
            "ram_mb": gpu["ram_mb"],
            "backend": "cpu"
        }
        
        if gpu["type"] == "nvidia" and cuda_available:
            device["backend"] = "cuda"
            device["id"] = f"cuda:{i}"
        elif directml_available:
            device["backend"] = "directml"
            device["id"] = f"dml:{i}"
        
        devices.append(device)
    
    logger.info(f"可用计算设备: {devices}")
    return devices


def get_compute_type_options(backend: str) -> List[str]:
    if backend == "cuda":
        return ["int8", "float16", "float32"]
    elif backend == "directml":
        return ["float16", "float32"]
    else:
        return ["int8", "float32"]


def install_onnxruntime_directml() -> bool:
    try:
        import subprocess
        import sys
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "onnxruntime-directml"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            logger.info("onnxruntime-directml 安装成功")
            return True
        else:
            logger.error(f"onnxruntime-directml 安装失败: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"安装 onnxruntime-directml 异常: {e}")
        return False
