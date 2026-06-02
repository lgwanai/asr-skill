# ASR Skill - AI 辅助本地语音转写技能

专为 AI Agent（Trae, Cursor, Claude）设计的本地语音识别与转写工具，基于阿里 FunASR 工业级模型，提供高精度的中文语音转写、说话人分离（Diarization）及智能标点能力。

---

## ✨ 项目亮点 (Highlights)

- **💰 纯免费 (Free)**: 无需任何 API Key，没有 Token 消耗，完全免费使用。
- **🔒 隐私安全 (Privacy)**: 所有数据处理均在本地完成，音频文件无需上传云端。
- **🚀 工业级精度**: 基于 Paraformer-Large 模型，中文识别准确率业界领先。
- **🧠 双引擎支持**: 同时支持 Paraformer（高精度）和 SenseVoice（轻量快速），自动根据硬件选择最佳模型。
- **⚡️ 硬件加速**: 自动检测并调用 GPU (NVIDIA CUDA) 或 Apple Silicon (MPS) 进行加速。CPU 环境自动使用 SenseVoice 模型。
- **🗣 说话人区分**: 自动识别多人对话中的不同说话人（Speaker A, Speaker B...）（Paraformer 引擎）。
- **🔄 异步处理**: 支持后台异步任务，防止长视频转写导致 Agent 超时。

## ❓ 为什么要这个 Skill (Why)

现在的 AI 编程助手（如 Trae, Cursor）非常强大，但它们通常只能处理文本。当你有一段会议录音、一个产品演示视频或一段播客需要 AI 分析时，你需要先找工具转写，再把文本复制给 AI。

**ASR Skill 打通了这一屏障**。它让你的 AI Agent 具备了"听觉"，可以直接处理音频和视频文件，实现从"听到"到"理解"的全链路自动化。

## 🎯 使用场景 (Use Cases)

1.  **会议纪要生成**: 直接丢给 AI 一段会议录音，让它生成结构化的会议纪要和待办事项。
2.  **视频内容分析**: 分析产品演示视频、竞品分析视频，提取关键信息。
3.  **字幕制作**: 为视频自动生成 SRT/ASS 字幕文件。
4.  **播客/课程总结**: 快速总结长达数小时的音频内容，提炼核心观点。
5.  **语音笔记整理**: 将碎片化的语音备忘录整理成条理清晰的文档。

## ⚙️ 核心工作流 (Workflow)

1.  **用户指令**: 用户在 IDE 中告诉 AI "帮我总结一下 `meeting.mp4` 的内容"。
2.  **技能触发**: AI Agent 识别意图，调用 `ASR Skill`。
3.  **异步转写**: 对于大文件，Skill 启动后台进程进行转写，立即返回任务 ID，避免阻塞。
4.  **状态轮询**: AI Agent 自动检查转写进度。
5.  **结果处理**: 转写完成后，AI 读取生成的 Markdown/文本文件，进行总结或回答用户问题。

---

## 📦 安装方式 (Installation)

### 前置要求

- **Python**: >= 3.10
- **FFmpeg**: 用于音视频处理
  - macOS: `brew install ffmpeg`
  - Windows: [下载安装包](https://ffmpeg.org/download.html)
  - Ubuntu: `sudo apt install ffmpeg`

### 1. 极速安装 (Quick Install via Chat)

如果你正在使用 **Cursor**, **Claude Code**, or **OpenClaw**，直接在对话框中发送以下内容即可一键安装：

```
https://github.com/lgwanai/asr-skill help me install asr skill
```

### 2. 手动安装

```bash
# 克隆仓库
git clone https://github.com/lgwanai/asr-skill.git
cd asr-skill

# 安装依赖
pip install -e .
```

### 3. IDE 集成指南

#### Trae
1.  下载并解压 release 包到项目目录。
2.  Trae 会自动识别 `SKILL.md` 并加载技能。

#### Cursor
1.  将项目文件放入工作区。
2.  将 `SKILL.md` 的内容复制到你的 `.cursorrules` 文件中，即可让 Cursor 学会使用此技能。

#### Claude Projects
1.  上传 `scripts/transcribe.py` 和 `SKILL.md` 到 Project Files。
2.  将 `SKILL.md` 内容添加到 Project Instructions。

---

## ⚙️ 配置文件 (Configuration)

可选配置文件 `config.txt`，不提供则使用默认值：

```properties
# ── 运行模式（必选，二选一）──
# local: 本地 ASR 模型 / api: 远程 API 服务（互斥）
mode = local

# ── 本地模式 ──
asr_model = auto       # ASR 引擎: auto / paraformer / sensevoice
model_dir =            # 模型缓存目录，空 = 平台默认

# ── 输出配置 ──
output_format = txt    # 默认输出格式: txt / json / srt / ass / md
output_dir =           # 默认输出目录，空 = 与输入同目录

# ── 小米 MiMo API 模式（仅 mode=api 时生效）──
# api.key = your-xiaomi-mimo-api-key
# api.language = auto        # auto, zh, en
# api.model = mimo-v2.5-asr
# api.max_file_mb = 7        # Base64 前最大 MB
# api.timeout = 300
```

| 配置项 | 说明 |
|--------|------|
| `mode` | 运行模式：`local`（本地）或 `api`（远程），**二选一，互斥** |
| `asr_model` | ASR 引擎选择：`auto`（自动）/ `paraformer`（高精度）/ `sensevoice`（轻量快速） |
| `model_dir` | 模型存储目录，空则使用系统默认路径 |
| `output_format` | 默认输出格式：txt/json/srt/ass/md |
| `output_dir` | 默认输出目录，空则与输入文件同目录 |
| `api.key` | MiMo API 密钥（也可用环境变量 `MIMO_API_KEY`） |
| `api.language` | 语言选项：`auto`（自动）/ `zh`（中文）/ `en`（英文） |
| `api.model` | ASR 模型名称（当前仅 `mimo-v2.5-asr`） |
| `api.max_file_mb` | 最大原始文件大小（MB），MiMo API 限制 Base64 后 ≤ 10 MB |
| `api.timeout` | API 请求超时时间（秒） |

### ASR 引擎对比

| 引擎 | 模型大小 | 最佳硬件 | 说话人分离 | 适用场景 |
|------|---------|---------|-----------|---------|
| **Paraformer** | ~1.3 GB | GPU (CUDA/MPS) | ✅ 支持 | 会议记录、高精度需求 |
| **SenseVoice** | ~200 MB | CPU | ❌ 不支持 | 快速转写、无 GPU 环境 |
| **auto** (默认) | 自动选择 | 自动适配 | 取决于选择 | 通用场景 |

环境变量：
```bash
export ASR_FORCE_CPU=1        # 强制使用 CPU
export ASR_MODEL_DIR=/path   # 自定义模型路径
```

---

## 🛠 使用指南 (Usage)

### 命令行工具 (CLI)

```bash
# 基础用法（自动选择最佳模型）
asr-skill input.mp3              # 转写音频
asr-skill video.mp4              # 转写视频（自动提取音频）

# 模型选择
asr-skill input.mp3 -m sensevoice   # 使用 SenseVoice（CPU 更快）
asr-skill input.mp3 -m paraformer   # 使用 Paraformer（GPU 高精度）
asr-skill input.mp3 -m auto         # 自动选择（默认）

# 进阶选项
asr-skill input.mp3 -f json      # 输出 JSON 格式
asr-skill input.mp3 -f srt       # 输出字幕格式
asr-skill input.mp3 -o ./out     # 指定输出目录
```

### 脚本调用 (Agent 推荐)

AI Agent 通常使用脚本方式调用，支持更灵活的异步控制：

```bash
# 同步执行（适合短音频，自动选择模型）
python3 scripts/transcribe.py input.mp3

# 指定模型引擎
python3 scripts/transcribe.py input.mp3 -m sensevoice   # CPU 快速模式
python3 scripts/transcribe.py input.mp3 -m paraformer   # GPU 高精度模式

# 异步执行（强烈推荐用于长视频/音频）
python3 scripts/transcribe.py input.mp4 --async
# 返回 Task ID，例如: {"task_id": "a1b2c3d4", ...}

# 查询任务进度
python3 scripts/transcribe.py --status a1b2c3d4
```

### Python API

```python
from asr_skill import transcribe

# 自动选择最佳模型
result = transcribe("meeting.mp4", format="md")
print(result["text"])
print(f"使用模型: {result['model_used']}")

# 指定引擎
result = transcribe("lecture.mp3", model_type="sensevoice")  # CPU 快速模式
result = transcribe("meeting.wav", model_type="paraformer")  # GPU 高精度模式

# 获取说话人信息（仅 Paraformer）
for segment in result["segments"]:
    print(f"{segment['speaker']}: {segment['text']}")
```

---

## 💾 模型存储 (Model Storage)

首次运行时会自动下载 FunASR 模型，存储位置根据操作系统自动选择：

- **macOS**: `~/Library/Application Support/asr-skill/models`
- **Windows**: `%APPDATA%\asr-skill\models`
- **Linux**: `~/.local/share/asr-skill/models`

*如果上述目录不可写，会自动回退到当前目录下的 `./models`。*

**模型大小**:
- Paraformer-Large: ~1.3 GB（GPU 推荐）
- SenseVoiceSmall: ~200 MB（CPU 友好）

模型选择策略：有 GPU → Paraformer，纯 CPU → SenseVoice。也可以手动在 `config.txt` 中通过 `asr_model` 字段指定。

---

## 🙋 常见问题 (FAQ)

**Q: 第一次运行为什么很慢？**
A: 首次运行需要从 ModelScope 下载约 2GB 的模型文件。下载速度取决于您的网络环境。下载完成后，后续运行将非常快。

**Q: 支持哪些文件格式？**
A: 音频支持 `mp3`, `wav`, `m4a`, `flac` 等；视频支持 `mp4`, `avi`, `mkv`, `mov` 等（会自动提取音频）。

**Q: 我的电脑没有 GPU 可以用吗？**
A: 可以。程序会自动检测硬件。如果没有 GPU，会自动使用 SenseVoice 模型在 CPU 上运行，速度比 Paraformer 快约 6 倍。Mac 用户会自动调用 M 系列芯片的 MPS 加速。

**Q: SenseVoice 和 Paraformer 有什么区别？**
A: Paraformer 精度更高、支持说话人分离，但需要 GPU 才能流畅运行（~1.3 GB）。SenseVoice 更轻量（~200 MB），CPU 上速度快 6 倍，但不支持说话人分离。默认 `auto` 模式会根据硬件自动选择。

**Q: 如何强制使用某个引擎？**
A: 在 `config.txt` 中设置 `asr_model = paraformer` 或 `asr_model = sensevoice`，或使用 CLI 参数 `-m paraformer` / `-m sensevoice`。

**Q: 为什么识别结果中没有区分说话人？**
A: 请确保音频中确实有明显的对话交互。如果是单人演讲，可能只会被识别为 Speaker A。

**Q: 遇到 "Permission denied" 错误怎么办？**
A: 请检查是否有对应目录的读写权限，或者尝试使用 `sudo` (不推荐) 或将模型目录设置到用户目录下。

---

*Made with ❤️ by Trae AI & ASR Skill Team*
