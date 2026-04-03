import os
import requests
from typing import Optional, Dict, Tuple


class SiliconFlowAPI:
    def __init__(self, api_base_url: str, api_key: str):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.model = "FunAudioLLM/SenseVoiceSmall"
        self.timeout = 60

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}"
        }

    def _get_mime_type(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.m4a': 'audio/mp4',
        }
        return mime_types.get(ext, 'application/octet-stream')

    def transcribe(self, audio_file_path: str, language: str = "auto") -> Dict:
        result = {
            "success": False,
            "text": "",
            "error": ""
        }

        if not os.path.exists(audio_file_path):
            result["error"] = f"音频文件不存在: {audio_file_path}"
            return result

        url = f"{self.api_base_url}/audio/transcriptions"

        try:
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': (os.path.basename(audio_file_path), audio_file, self._get_mime_type(audio_file_path))
                }
                data = {
                    'model': self.model,
                    'language': language
                }

                response = requests.post(
                    url,
                    headers=self._get_headers(),
                    files=files,
                    data=data,
                    timeout=self.timeout
                )

            if response.status_code == 200:
                response_data = response.json()
                result["success"] = True
                result["text"] = response_data.get("text", "")
            elif response.status_code == 401:
                result["error"] = "认证失败: API Key 无效或已过期"
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

    def test_connection(self) -> Tuple[bool, str]:
        url = f"{self.api_base_url}/models"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10
            )

            if response.status_code == 200:
                return True, "API 连接成功"
            elif response.status_code == 401:
                return False, "认证失败: API Key 无效或已过期"
            elif response.status_code == 429:
                return False, "请求过于频繁,请稍后再试"
            else:
                return False, f"连接失败: HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            return False, "连接超时,请检查网络"
        except requests.exceptions.ConnectionError:
            return False, "网络连接失败,请检查网络设置"
        except requests.exceptions.RequestException as e:
            return False, f"连接异常: {str(e)}"
        except Exception as e:
            return False, f"未知错误: {str(e)}"
