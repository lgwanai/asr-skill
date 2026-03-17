# ASR Skill - AI 辅助本地语音转写技能

专为 AI Agent（Trae, Cursor, Claude）设计的本地语音识别与转写工具，基于阿里 FunASR 工业级模型，提供高精度的中文语音转写、说话人分离（Diarization）及智能标点能力。

---

## ✨ 项目亮点 (Highlights)

- **💰 纯免费 (Free)**: 无需任何 API Key，没有 Token 消耗，完全免费使用。
- **🔒 隐私安全 (Privacy)**: 所有数据处理均在本地完成，音频文件无需上传云端。
- **🚀 工业级精度**: 基于 Paraformer-Large 模型，中文识别准确率业界领先。
- **⚡️ 硬件加速**: 自动检测并调用 GPU (NVIDIA CUDA) 或 Apple Silicon (MPS) 进行加速，CPU 亦可流畅运行。
- **🗣 说话人区分**: 自动识别多人对话中的不同说话人（Speaker A, Speaker B...）。
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
1.  下载并解压 release 包到项目的 `skills/asr` 目录。
2.  Trae 会自动识别 `SKILL.md` 并加载技能。

#### Cursor
1.  将项目文件放入工作区。
2.  将 `skills/asr/SKILL.md` 的内容复制到你的 `.cursorrules` 文件中，即可让 Cursor 学会使用此技能。

#### Claude Projects
1.  上传 `skills/asr/scripts/transcribe.py` 和 `SKILL.md` 到 Project Files。
2.  将 `SKILL.md` 内容添加到 Project Instructions。

---

## 🛠 使用指南 (Usage)

### 命令行工具 (CLI)

```bash
# 基础用法
asr-skill input.mp3              # 转写音频
asr-skill video.mp4              # 转写视频（自动提取音频）

# 进阶选项
asr-skill input.mp3 -f json      # 输出 JSON 格式
asr-skill input.mp3 -f srt       # 输出字幕格式
asr-skill input.mp3 -o ./out     # 指定输出目录
```

### 脚本调用 (Agent 推荐)

AI Agent 通常使用脚本方式调用，支持更灵活的异步控制：

```bash
# 同步执行（适合短音频）
python3 skills/asr/scripts/transcribe.py input.mp3

# 异步执行（强烈推荐用于长视频/音频）
python3 skills/asr/scripts/transcribe.py input.mp4 --async
# 返回 Task ID，例如: {"task_id": "a1b2c3d4", ...}

# 查询任务进度
python3 skills/asr/scripts/transcribe.py --status a1b2c3d4
```

### Python API

```python
from asr_skill import transcribe

# 简单调用
result = transcribe("meeting.mp4", format="md")
print(result["text"])

# 获取说话人信息
for segment in result["segments"]:
    print(f"{segment['speaker']}: {segment['text']}")
```

---

## 💾 模型存储 (Model Storage)

首次运行时会自动下载 FunASR 模型（约 2-3GB），存储位置根据操作系统自动选择：

- **macOS**: `~/Library/Application Support/asr-skill/models`
- **Windows**: `%APPDATA%\asr-skill\models`
- **Linux**: `~/.local/share/asr-skill/models`

*如果上述目录不可写，会自动回退到当前目录下的 `./models`。*

---

## 🙋 常见问题 (FAQ)

**Q: 第一次运行为什么很慢？**
A: 首次运行需要从 ModelScope 下载约 2GB 的模型文件。下载速度取决于您的网络环境。下载完成后，后续运行将非常快。

**Q: 支持哪些文件格式？**
A: 音频支持 `mp3`, `wav`, `m4a`, `flac` 等；视频支持 `mp4`, `avi`, `mkv`, `mov` 等（会自动提取音频）。

**Q: 我的电脑没有 GPU 可以用吗？**
A: 可以。程序会自动检测硬件。如果没有 GPU，会自动使用 CPU 运行。虽然速度会慢一些，但依然可以完成任务。Mac 用户会自动调用 M 系列芯片的 MPS 加速。

**Q: 为什么识别结果中没有区分说话人？**
A: 请确保音频中确实有明显的对话交互。如果是单人演讲，可能只会被识别为 Speaker A。

**Q: 遇到 "Permission denied" 错误怎么办？**
A: 请检查是否有对应目录的读写权限，或者尝试使用 `sudo` (不推荐) 或将模型目录设置到用户目录下。

---

*Made with ❤️ by Trae AI & ASR Skill Team*
