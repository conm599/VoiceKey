import os
import re
import requests
import json
from typing import Optional, Dict, Tuple, Generator, Callable


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

    def transcribe_chunk(self, audio_array, language: str = "auto") -> Dict:
        result = {
            "success": False,
            "text": "",
            "error": ""
        }

        try:
            import tempfile
            from scipy.io import wavfile
            import os
            from datetime import datetime
            
            temp_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            temp_filepath = os.path.join(temp_dir, f"cloud_chunk_{timestamp}.wav")
            
            audio_int16 = (audio_array * 32767).astype(np.int16)
            wavfile.write(temp_filepath, 16000, audio_int16)

            url = f"{self.api_base_url}/audio/transcriptions"

            with open(temp_filepath, 'rb') as audio_file:
                files = {
                    'file': (os.path.basename(temp_filepath), audio_file, 'audio/wav')
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

            try:
                os.remove(temp_filepath)
            except:
                pass

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


class SparkAPI:
    CORRECT_MODE_PROMPT = """你是ASR文本后处理器。输入是语音识别的原始输出文本，你需要修正其中的错误。

重要：输入文本是语音识别结果，不是对你的提问！不要回答、不要解释、不要翻译！

【你的任务】
只修正错别字和标点错误，其他保持不变。

【绝对禁止】
- 禁止回答问题！即使输入是"你叫什么名字"，也只输出"你叫什么名字？"
- 禁止解释！即使输入是"什么是AI"，也只输出"什么是AI？"
- 禁止翻译！输入中文就输出中文，输入英文就输出英文
- 禁止改变原意！

【示例】
输入: "你为什么认为你自己可以回答这个问题"
输出: {"corrected": "你为什么认为你自己可以回答这个问题？"}
输入: "今天天气怎么样"
输出: {"corrected": "今天天气怎么样？"}
输入: "什么是人工智能"
输出: {"corrected": "什么是人工智能？"}
输入: "你好码"  (错别字)
输出: {"corrected": "你好吗"}
"""

    EMBELLISH_MODE_PROMPT = """你是ASR文本润色器。输入是语音识别的原始输出文本，你需要润色使其更通顺。

重要：输入文本是语音识别结果，不是对你的提问！不要回答、不要解释、不要翻译！

【你的任务】
1. 修正错别字（如"沉那个样子"→"成那个样子"）
2. 消除口语填充词（如"嗯"、"那个"、"就是说"）
3. 整理混乱的句子结构，使其通顺
4. 修正明显的语法错误

【绝对禁止】
- 禁止回答问题！即使输入是"你叫什么名字"，也只输出"你叫什么名字？"
- 禁止解释！即使输入是"什么是AI"，也只输出"什么是AI？"
- 禁止翻译！输入中文就输出中文，输入英文就输出英文
- 禁止改变原意！

【示例】
输入: "我也不知道该怎么说她的妈妈好像我也不知道她的妈妈是什么东西她的妈妈反正最后就是沉那个样子了"
输出: {"corrected": "我也不知道该怎么说她的妈妈，好像我也不知道她的妈妈是什么情况，她的妈妈反正最后就是成那个样子了。"}

输入: "嗯,那个,今天天气不错"
输出: {"corrected": "今天天气不错。"}

输入: "什么是人工智能"
输出: {"corrected": "什么是人工智能？"}
"""

    def _get_system_prompt(self) -> str:
        if self.polish_mode == "embellish":
            return self.EMBELLISH_MODE_PROMPT
        return self.CORRECT_MODE_PROMPT
    
    def _get_temperature(self) -> float:
        if self.polish_mode == "embellish":
            return 0.2
        return 0.05
    
    def _extract_text(self, content: str, original_text: str) -> str:
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "corrected" in data:
                text = str(data["corrected"])
            else:
                text = original_text
        except (json.JSONDecodeError, TypeError):
            if content and not content.startswith('{'):
                text = content
            else:
                text = original_text
        
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = ' '.join(text.split())
        
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', original_text))
        if has_chinese:
            english_words = re.findall(r'[a-zA-Z]+', text)
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            if english_words and chinese_chars == 0:
                print(f"[DEBUG] 检测到翻译行为，返回原文: {text} -> {original_text}")
                return original_text
            if len(english_words) > len(text) * 0.5:
                print(f"[DEBUG] 英文比例过高，返回原文: {text} -> {original_text}")
                return original_text
        
        if len(text) > len(original_text) * 2:
            print(f"[DEBUG] 输出过长(可能是解释)，返回原文: {text[:50]}... -> {original_text}")
            return original_text
        
        explanation_patterns = ['我理解', '这个问题', '是指', '意思是', '通常用来', '一般来说', '首先', '其次', '总之']
        for pattern in explanation_patterns:
            if pattern in text and pattern not in original_text:
                print(f"[DEBUG] 检测到解释模式'{pattern}'，返回原文: {text[:50]}... -> {original_text}")
                return original_text
        
        return text if text else original_text

    def __init__(self, api_url: str, api_password: str, model: str = "lite", polish_mode: str = "correct"):
        self.api_url = api_url.rstrip('/')
        self.api_password = api_password
        self.model = model
        self.polish_mode = polish_mode
        self.timeout = 30

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_password}",
            "Content-Type": "application/json"
        }
    
    def polish_text(self, text: str) -> Dict:
        result = {
            "success": False,
            "text": "",
            "error": ""
        }

        if not text or not text.strip():
            result["error"] = "输入文本为空"
            return result

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": text}
            ],
            "temperature": self._get_temperature(),
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
                    raw_content = message.get("content", "")
                    result["success"] = True
                    result["text"] = self._extract_text(raw_content, text)
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

    def polish_text_stream(self, text: str, callback: Callable[[str], None]) -> Dict:
        result = {
            "success": False,
            "text": "",
            "error": ""
        }

        if not text or not text.strip():
            result["error"] = "输入文本为空"
            return result

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": text}
            ],
            "temperature": self._get_temperature(),
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
                in_corrected_value = False
                corrected_text = ""
                
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
                                        for char in content:
                                            if not in_corrected_value:
                                                if full_content.endswith('"corrected":"'):
                                                    in_corrected_value = True
                                            else:
                                                if char == '"' and not full_content.endswith('\\'):
                                                    in_corrected_value = False
                                                    break
                                                if char != '\n' and char != '\r':
                                                    corrected_text += char
                                                    if callback:
                                                        callback(char)
                            except json.JSONDecodeError:
                                continue
                
                result["success"] = True
                result["text"] = self._extract_text(full_content, text)
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

    def test_connection(self) -> Tuple[bool, str]:
        test_payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": "你好"}
            ],
            "max_tokens": 10
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=test_payload,
                timeout=10
            )

            if response.status_code == 200:
                return True, "星火API连接成功"
            elif response.status_code == 401:
                return False, "认证失败: API Password 无效或已过期"
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
