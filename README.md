# 🎯 Qwen3 实时语音翻译系统

基于阿里云 DashScope Qwen3-LiveTranslate 模型的实时语音翻译 Web 应用，支持多语言实时翻译、语音合成和翻译记录保存。

## ✨ 功能特性

### 🔥 核心功能
- **实时语音翻译**：支持中文、英文、日文、韩文等多种语言的实时翻译
- **语音合成**：支持多种音色的语音输出（Cherry、Longwan、Qianfeng等）
- **翻译记录**：自动保存翻译内容，支持Markdown格式导出
- **Web界面**：现代化的响应式Web界面，支持桌面和移动端
- **会话管理**：自动创建会话文件夹，按时间戳组织翻译记录
- **文件下载**：支持单个文件和批量下载翻译记录

### 🛡️ 安全特性
- **API密钥保护**：所有敏感信息通过环境变量管理
- **文件安全**：严格的文件名验证和路径遍历保护
- **会话隔离**：每个翻译会话独立存储，避免数据混淆

### 🏗️ 技术架构
- **后端**：FastAPI + WebSocket 实时通信
- **前端**：原生 HTML5 + JavaScript，支持 WebRTC 音频处理
- **AI服务**：阿里云 DashScope Qwen3-LiveTranslate 模型
- **存储**：本地文件系统，Markdown格式保存翻译记录
- **日志系统**：分级日志记录，支持错误追踪和调试

## 🚀 快速开始

### 📋 系统要求
- Python 3.12 或更高版本
- 现代浏览器（支持 WebRTC 和 WebSocket）
- 稳定的网络连接（用于访问阿里云服务）

### 📦 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/yourusername/Qwen3-Livetranslate.git
cd Qwen3-Livetranslate
```

2. **创建虚拟环境**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

## 🔑 API Key 配置

### 获取 DashScope API Key

1. 访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/)
2. 注册/登录阿里云账号
3. 开通 DashScope 服务
4. 在 API-KEY 管理页面创建新的 API Key
5. 复制生成的 API Key（格式类似：`sk-xxxxxxxxxxxxxx`）

### 配置环境变量

#### Windows (PowerShell)
```powershell
# 临时设置（当前会话有效）
$env:DASHSCOPE_API_KEY="sk-your-api-key-here"

# 永久设置（推荐）
[Environment]::SetEnvironmentVariable("DASHSCOPE_API_KEY", "sk-your-api-key-here", "User")
```

#### Windows (命令提示符)
```cmd
# 临时设置
set DASHSCOPE_API_KEY=sk-your-api-key-here

# 永久设置
setx DASHSCOPE_API_KEY "sk-your-api-key-here"
```

#### macOS/Linux
```bash
# 临时设置
export DASHSCOPE_API_KEY="sk-your-api-key-here"

# 永久设置（添加到 ~/.bashrc 或 ~/.zshrc）
echo 'export DASHSCOPE_API_KEY="sk-your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

#### 使用 .env 文件（可选）
在项目根目录创建 `.env` 文件：
```env
DASHSCOPE_API_KEY=sk-your-api-key-here
```

## 🚀 启动服务

```bash
# 启动Web服务器
python start_server.py
```

默认情况下，服务器将在 http://localhost:8000 启动。在浏览器中访问此地址即可使用翻译系统。

## 📝 翻译记录功能

### 自动保存翻译
- 系统会自动为每个会话创建独立的文件夹和Markdown文件
- 翻译内容实时保存，包含时间戳和原文/译文
- 会话目录格式：`translation_outputs/session_YYYYMMDD_HHMMSS/`

### 查看和导出翻译记录
- 所有翻译记录保存在 `translation_outputs` 目录下
- 每个会话有独立的Markdown文件，可直接查看或下载
- 支持通过Web界面下载单个或批量翻译记录

## 🎵 音频功能增强

### 语音合成配置
- 支持多种语音合成音色选择
- 可调整语音速度、音量和音调
- 支持按段落或句子进行语音合成

### 音频输入优化
- 自动降噪和音频增强
- 支持麦克风静音/取消静音
- 实时音量可视化显示

## 🛠️ 高级配置

### 自定义模型与调用地址
本项目使用阿里云 DashScope 实时服务，默认模型为 `qwen3-livetranslate-flash-realtime`。

如需更换模型，请在 `web_translate_client.py` 的 `WebTranslateClient.__init__` 中，修改连接地址中 `model=` 的取值：
```python
# 在 WebTranslateClient.__init__ 中设置模型
self.api_url = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3-livetranslate-flash-realtime"

# 示例：切换为其他可用的实时模型（请根据账号权限与官方文档确认）
new_model = "qwen3-livetranslate-pro-realtime"
self.api_url = f"wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model={new_model}"
```

注意：当前客户端未使用名为 `MODEL_ID` 的变量，该示例已过时，请勿参考。

### 调整WebSocket参数
在 `web_server.py` 中可以修改以下参数：
```python
# WebSocket心跳配置
HEARTBEAT_INTERVAL = 25  # 心跳间隔（秒）
WEBSOCKET_TIMEOUT = 60   # 超时时间（秒）
```

## 📊 日志系统

系统使用分级日志记录所有操作：
- 普通日志：`logs/web_server_YYYYMMDD.log`
- 错误日志：`logs/web_server_errors_YYYYMMDD.log`
- 翻译客户端日志：`logs/web_translate_client.log`

## 🤝 贡献指南

欢迎提交问题报告、功能请求和代码贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件

## 📞 联系方式

如有任何问题或建议，请通过以下方式联系我们：

- GitHub Issues: [提交问题](https://github.com/reknottycat/Qwen3-Livetranslate/issues)
- 电子邮件: your.email@example.com

---

**注意**：本项目需要阿里云 DashScope API 密钥才能正常工作。请确保在使用前正确配置环境变量。