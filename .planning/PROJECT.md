# ASR-Skill: FunASR智能语音解析工具

## What This Is

基于阿里开源FunASR框架的高性能本地化语音解析工具，支持超长音频/视频转写、多说话人分离与角色标记。可部署为Claude Code Skill、CLI工具和Python包三种形式，满足不同使用场景。

目标用户包括内容创作者、研究人员及企业用户，用于处理会议记录、访谈转录、讲座存档及视频字幕生成。

## Core Value

**在保障数据隐私（本地化处理）的前提下，实现对超长音频/视频的高精度转写，并通过说话人分离技术输出结构化的智能纪要。**

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 超长音频/视频智能转写（支持1小时以上大文件）
- [ ] 多说话人分离与角色标记
- [ ] 自动硬件检测与配置（GPU/CPU自适应）
- [ ] 多格式输出（TXT/SRT/ASS/JSON/Markdown）
- [ ] 热词注入支持（配置文件+CLI参数）
- [ ] 视频自动音轨提取
- [ ] 自动采样率标准化至16kHz

### Out of Scope

- 云端处理 — 本地化处理是核心价值主张
- 实时流式转写 — v1仅支持离线文件处理
- 多语言支持 — v1专注中文语音识别

## Context

**技术栈选型：**
- ASR模型：Paraformer-Large（非自回归架构，推理速度快3-5倍）
- VAD模型：FSMN-VAD（语音活动检测）
- 说话人识别：CAM++（声纹聚类）
- 标点恢复：CT-Transformer

**部署形式：**
- Claude Code Skill（/asr命令调用）
- 独立CLI工具
- 可导入的Python包

**硬件支持：**
- Apple Silicon (MPS)
- NVIDIA GPU (CUDA)
- CPU回退模式

## Constraints

- **Python版本**: ≥3.8 — FunASR框架要求
- **内存**: 建议8GB以上 — 处理长音频需要
- **磁盘**: 模型文件约2-3GB — 需要本地缓存空间
- **本地处理**: 不支持云端 — 隐私保护核心约束

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FunASR框架 | 阿里开源，中文识别精度高，模型丰富 | — Pending |
| Paraformer-Large | 非自回归架构，速度与精度平衡最佳 | — Pending |
| VAD智能分段 | 比固定时长分段更符合语义边界 | — Pending |
| 输出到源文件目录 | 用户习惯，减少路径配置 | — Pending |

---
*Last updated: 2026-03-13 after initialization*
