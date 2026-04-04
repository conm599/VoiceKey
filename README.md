# VoiceKey - 语音转文字

一个简洁高效的 Windows 语音转文字工具，支持云端 API 和本地 Whisper 模型两种识别方式，可通过热键快速录音并自动输入识别结果。

## 功能特性

- **双模式识别**：支持云端 API 和本地 Whisper 模型
- **热键录音**：默认 `Ctrl+Alt+V` 快速启动/停止录音
- **自动静音检测**：智能检测静音自动停止录音
- **悬浮窗显示**：实时显示录音状态
- **系统托盘**：最小化到托盘，后台运行
- **中文输出**：支持简体/繁体中文转换
- **音频文件转换**：支持上传音频文件批量转文字
- **隐私保护**：本地模式无需网络，数据不上传
- **星火大模型对话**：集成星火大模型 API，润色输出

## 截图

### 应用图标

!\[FunAudioLLM]\(<https://tup-34x.pages.dev/FunAudioLLM.png> null)

### 设置界面

!\[设置界面]\(<https://tup-34x.pages.dev/htyu.png> null)

## 安装

### 环境要求

- Windows 10/11
- Python 3.8+
- 麦克风设备

### 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖列表

| 依赖               | 用途        |
| ---------------- | --------- |
| `tkinter`        | GUI 界面    |
| `pynput`         | 热键监听与键盘输入 |
| `sounddevice`    | 音频录制      |
| `scipy`          | WAV 文件处理  |
| `requests`       | API 请求    |
| `pyperclip`      | 剪贴板操作     |
| `pyautogui`      | 自动化输入     |
| `faster-whisper` | 本地语音识别    |
| `zhconv`         | 简繁转换      |

## 使用方法

### 启动程序

```bash
python main.py
```

### 基本操作

1. **启动程序**：程序启动后会在系统托盘显示图标
2. **开始录音**：按下 `Ctrl+Alt+V` 开始录音
3. **停止录音**：
   - 再次按下 `Ctrl+Alt+V` 手动停止
   - 或等待自动静音检测停止
4. **查看结果**：识别结果会自动输入到当前光标位置

### 设置界面

右键点击托盘图标选择"设置"，可配置：

- **识别模式**：云端识别 / 本地识别
- **本地模型**：Tiny / Base / Small
- **中文输出**：简体中文 / 繁体中文
- **热键配置**：自定义快捷键
- **录音设置**：静音阈值、采样率等
- **星火大模型**：API 配置和对话管理

## 识别模式

### 云端识别（默认）

使用 SiliconFlow API 的 SenseVoiceSmall 模型：

1. 注册 [SiliconFlow](https://siliconflow.cn/) 账号
2. 获取 API Key
3. 在设置中填入 API Key

**优点**：

- 无需本地计算资源
- 识别速度快
- 模型效果好

### 本地识别

使用 faster-whisper 本地模型：

1. 在设置中选择"本地识别"
2. 选择模型大小（Tiny/Base/Small）
3. 点击"下载模型"

**优点**：

- 无需网络连接
- 隐私安全
- 无 API 费用

**模型对比**：

| 模型    | 大小      | 内存    | 速度 | 准确度 |
| ----- | ------- | ----- | -- | --- |
| Tiny  | \~75MB  | \~1GB | 最快 | 一般  |
| Base  | \~150MB | \~1GB | 快  | 推荐  |
| Small | \~500MB | \~2GB | 中等 | 较高  |

## 星火大模型对话

### 功能特性

- **多轮对话**：支持连续对话，上下文理解
- **会话管理**：创建、切换、删除对话会话
- **流式输出**：实时显示模型回复
- **Token 管理**：自动管理对话长度，防止超出限制

### 配置方法

1. 获取星火大模型 API 密钥
2. 在设置中填入 API URL 和 API Password
3. 点击"测试连接"确认配置正确

### 使用方法

1. GUI选择"星火对话"
2. 在对话窗口中输入问题
3. 点击"发送"或按 `Ctrl+Enter` 发送消息
4. 模型会实时回复，支持连续对话

### 应用场景

- **文本润色**：优化语音识别结果，使文本更流畅自然
- **内容扩展**：基于识别结果进行内容扩展和丰富
- **语法修正**：自动修正识别结果中的语法问题
- **多轮交互**：通过对话形式调整和完善文本内容

## 项目结构

```
/
├── main.py                    # 程序入口
├── requirements.txt           # 依赖列表
├── FunAudioLLM.png            # 应用图标
├── local_whisper_server.py    # 测试文件
├── voice_to_text/
│   ├── __init__.py
│   ├── app.py                 # 主程序
│   ├── config.json            # 配置文件
│   ├── chat_history/          # 对话历史存储
│   └── modules/
│       ├── __init__.py
│       ├── api_client.py      # 云端 API 客户端
│       ├── audio_recorder.py  # 音频录制模块
│       ├── chat.py            # 星火大模型对话
│       ├── chat_window.py     # 对话窗口
│       ├── config.py          # 配置管理
│       ├── floating_window.py # 悬浮窗模块
│       ├── gui.py             # 设置界面
│       ├── hotkey_manager.py  # 热键管理
│       ├── local_whisper.py   # 本地 Whisper 模块
│       ├── text_input.py      # 文字输入模块
│       └── tray_icon.py       # 系统托盘模块
```

## 配置说明

配置文件 `config.json` 位于程序目录：

| 配置项                   | 类型     | 默认值          | 说明                  |
| --------------------- | ------ | ------------ | ------------------- |
| `api_key`             | string | ""           | SiliconFlow API Key |
| `hotkey`              | string | "ctrl+alt+v" | 录音热键                |
| `use_local_whisper`   | bool   | false        | 是否使用本地模型            |
| `local_model`         | string | "base"       | 本地模型名称              |
| `chinese_mode`        | string | "simplified" | 中文输出模式              |
| `silence_threshold`   | int    | 500          | 静音检测阈值              |
| `silence_duration`    | float  | 2.0          | 静音停止时间(秒)           |
| `sample_rate`         | int    | 16000        | 采样率                 |
| `max_record_duration` | int    | 60           | 最大录音时长(秒)           |
| `input_mode`          | string | "paste"      | 输入模式                |
| `spark_api_url`       | string | ""           | 星火大模型 API URL       |
| `spark_api_password`  | string | ""           | 星火大模型 API Password  |

## 测试文件

`local_whisper_server.py` 是一个独立的本地 Whisper API 服务测试文件，可提供本地 HTTP API 接口。此文件仅用于测试目的，主程序不依赖此文件。

## 常见问题

### 录音没有声音

- 检查麦克风是否正确连接
- 检查系统麦克风权限设置
- 尝试调低静音检测阈值

### 识别结果为空

- 检查 API Key 是否有效（云端模式）
- 检查模型是否已加载（本地模式）
- 尝试增加录音时长

### 热键不生效

- 检查热键是否被其他程序占用
- 尝试更换热键组合
- 以管理员权限运行程序

### 本地模型下载失败

- 检查网络连接
- 程序会自动使用 HuggingFace 镜像源
- 可手动下载模型到 `models/` 目录

### 星火大模型连接失败

- 检查 API URL 和 Password 是否正确
- 检查网络连接
- 确认 API 服务是否可用

## 开发

```bash
git clone https://github.com/conm599/VoiceKey.git
cd VoiceKey
pip install -r requirements.txt
python main.py
```

## 许可证

本项目采用 GNU General Public License v2.0 (GPLv2) 许可证。

详见 [LICENSE](LICENSE) 文件。

### 第三方库许可证

本项目使用了以下开源库：

| 库名             | 许可证                  | 来源                                                   |
| -------------- | -------------------- | ---------------------------------------------------- |
| sounddevice    | MIT                  | <https://github.com/spatialaudio/python-sounddevice> |
| numpy          | BSD-3-Clause         | <https://github.com/numpy/numpy>                     |
| scipy          | BSD-3-Clause         | <https://github.com/scipy/scipy>                     |
| pynput         | LGPL-3.0             | <https://github.com/moses-palmer/pynput>             |
| pyperclip      | BSD-3-Clause         | <https://github.com/asweigart/pyperclip>             |
| pyautogui      | BSD-3-Clause         | <https://github.com/asweigart/pyautogui>             |
| requests       | Apache-2.0           | <https://github.com/psf/requests>                    |
| Pillow         | PIL Software License | <https://github.com/python-pillow/Pillow>            |
| pystray        | LGPL-3.0             | <https://github.com/moses-palmer/pystray>            |
| faster-whisper | MIT                  | <https://github.com/guillaumekln/faster-whisper>     |
| zhconv         | MIT（代码）+ GPLv2+（转换表） | <https://github.com/gumblex/zhconv>                  |

以上库的许可证文件可在各自的 GitHub 仓库中找到。本项目在使用这些库时遵循其各自的许可证条款。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 致谢

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - 高效的 Whisper 推理
- [OpenAI Whisper](https://github.com/openai/whisper) - 原始 Whisper 模型
- [SiliconFlow](https://siliconflow.cn/) - 云端 API 服务
- [SenseVoice](https://github.com/FunAudioLLM/SenseVoice) - 语音识别模型
- [星火大模型](https://xinghuo.xfyun.cn/) - 智能对话能力

