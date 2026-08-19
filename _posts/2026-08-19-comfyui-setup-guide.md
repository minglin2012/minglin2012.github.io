---
layout: post
title: "ComfyUI 图像生成环境完整搭建指南：从 CUDA 诊断到 IP-Adapter FaceID"
subtitle: "ComfyUI 环境搭建实战：CUDA 修复、ControlNet、预处理器与 IP-Adapter FaceID 全流程"
date: 2026-08-19
author: Minglin
header-img: img/post-bg.jpg
tags: [ComfyUI, AI, 工具, 安全]
---

> 环境：Windows 10 · NVIDIA RTX 3060 12GB · Comfy-Desktop
> 作者记录于一次完整的实战配置过程，涵盖 CUDA 修复、ControlNet、各类预处理器，以及 IP-Adapter FaceID 人像工作流的全部步骤与踩坑经验。

---

## 目录

1. [硬件与驱动诊断](#1-硬件与驱动诊断)
2. [核心概念：模型目录结构](#2-核心概念模型目录结构)
3. [ControlNet 完整配置](#3-controlnet-完整配置)
4. [ControlNet 预处理器模型](#4-controlnet-预处理器模型)
5. [深度预处理器与 HF 缓存重定向](#5-深度预处理器与-hf-缓存重定向)
6. [代理配置：让国内镜像直连](#6-代理配置让国内镜像直连)
7. [IP-Adapter FaceID 完整配置](#7-ip-adapter-faceid-完整配置)
8. [常见报错速查表](#8-常见报错速查表)
9. [总结](#9-总结)

---

## 1. 硬件与驱动诊断

### 1.1 查询显卡与 CUDA 支持

```powershell
nvidia-smi
```

| 项目 | 值 |
|------|-----|
| GPU | NVIDIA GeForce RTX 3060（12GB VRAM） |
| 驱动版本 | 576.88 |
| 驱动支持 CUDA | 12.9 |
| 计算能力 | 8.6（Ampere） |

### 1.2 CUDA 版本不匹配的坑

ComfyUI 桌面版自动装的是 PyTorch `cu130`（CUDA 13.0），但驱动 576.88 最高只支持 CUDA 12.9，启动直接崩溃（`0xC0000005`）。

**修复**：重装 PyTorch 到 CUDA 12.8 版本。

```powershell
cd D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI
.venv\Scripts\python.exe -m pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu128 --force-reinstall
```

**验证**：

```powershell
.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
# 输出：True / NVIDIA GeForce RTX 3060
```

> 关键点：**驱动支持的 CUDA 版本 ≥ PyTorch 编译的 CUDA 版本**，否则崩溃。

---

## 2. 核心概念：模型目录结构

这是 Comfy-Desktop 最容易踩坑的地方。它有两套模型目录：

```
D:\Users\user\AppData\Local\Comfy-Desktop\
├── ComfyUI-Installs\ComfyUI\ComfyUI\models\   ← 安装目录
└── ComfyUI-Shared\models\                      ← 共享目录（推荐）
```

### 2.1 各类型模型的存放位置

| 模型类型 | 目录 | 加载方式 |
|----------|------|---------|
| Checkpoint（底模） | `checkpoints\` | ComfyUI 内置 Loader |
| ControlNet | `controlnet\` | ControlNetLoader |
| VAE | `vae\` | VAELoader |
| LoRA | `loras\` | Load LoRA |
| CLIP Vision | `clip_vision\` | CLIP Vision Loader |
| IP-Adapter | `ipadapter\` | 自定义节点 |
| InsightFace | `insightface\` | 自定义节点 |
| LLM GGUF | `LLM\GGUF\` | JoyCaption 等（注意！） |

### 2.2 关键教训：谁来决定“找哪里”

- **Comfy-Desktop 会自动扫描共享目录**，把新建的文件夹自动写进 `shared_model_paths.yaml`，所以大部分模型放**共享目录**即可。
- **个别自定义节点硬编码了安装目录**，不遵循共享目录（例如 JoyCaption GGUF 只找 `安装目录\models\LLM\GGUF\`）。

判断方法：遇到“模型找不到”，先查 `folder_paths` 到底在哪个路径找：

```python
.venv\Scripts\python.exe -c "import folder_paths; print(folder_paths.get_folder_paths('某类型'))"
```

---

## 3. ControlNet 完整配置

### 3.1 下载 ControlNet 模型（fp16 版）

SD1.5 的 ControlNet 模型在 `comfyanonymous/ControlNet-v1-1_fp16_safetensors` 仓库。常用几个：

| 文件 | 用途 | 大小 |
|------|------|------|
| `control_v11p_sd15_lineart_fp16.safetensors` | 线稿 | 689 MB |
| `control_v11p_sd15_softedge_fp16.safetensors` | 软边缘（HED） | 689 MB |
| `control_v11p_sd15_scribble_fp16.safetensors` | 涂鸦 | 689 MB |
| `control_v11p_sd15_mlsd_fp16.safetensors` | 直线检测 | 689 MB |

放到 `ComfyUI-Shared\models\controlnet\`。

### 3.2 下载脚本（走国内镜像，清空代理）

```python
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ['NO_PROXY'] = '*'
from huggingface_hub import hf_hub_download

target = r'D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Shared\models\controlnet'
repo = 'comfyanonymous/ControlNet-v1-1_fp16_safetensors'
for fn in ['control_v11p_sd15_lineart_fp16.safetensors',
           'control_v11p_sd15_softedge_fp16.safetensors']:
    hf_hub_download(repo_id=repo, filename=fn, local_dir=target)
```

> 关键：**访问 hf-mirror.com 时一定要清空代理**，否则会被重定向回 huggingface.co 导致失败。

### 3.3 安装 ControlNet 预处理器节点

`comfyui_controlnet_aux`（作者 Fannovel16）负责“从原图生成提示图”（线稿/姿态/深度等）：

```powershell
cd D:\...\ComfyUI\custom_nodes
git clone --depth 1 https://github.com/Fannovel16/comfyui_controlnet_aux.git
# 安装依赖（缺什么装什么，先装 cv2 是必须的）
.venv\Scripts\python.exe -m pip install opencv-python scikit-image
```

---

## 4. ControlNet 预处理器模型

预处理器（preprocessor）的模型分两类，下载机制不同：

### 4.1 走 `hf_hub_download` 的（下到 `custom_nodes\...\ckpts\`）

| 预处理器 | 模型文件 | 大小 |
|---------|---------|------|
| HED / SoftEdge | `ControlNetHED.pth` | 29 MB |
| Realistic Lineart | `sk_model.pth` + `sk_model2.pth` | 各 17 MB |
| Anime Lineart | `netG.pth` | 218 MB |
| MLSD | `mlsd_large_512_fp32.pth` | 6 MB |
| DWPose | `yolox_l.onnx` + `dw-ll_ucoco_384_bs5.torchscript.pt` | 217 + 135 MB |

仓库：`lllyasviel/Annotators` 和 `yzd-v/DWPose` 等。下到：

```
custom_nodes\comfyui_controlnet_aux\ckpts\{仓库名}\{文件名}
```

### 4.2 走 transformers 的（下到 HF 缓存）

ZoeDepth、MiDaS 等深度预处理器用 `transformers.pipeline()` 加载完整模型，自动下到 HF 缓存（见下一节）。

### 4.3 常见预处理器依赖

| 预处理器 | 依赖 | 是否需要模型 |
|---------|------|-------------|
| Canny / Scribble / Standard Lineart | 纯 OpenCV | ❌ 无需模型 |
| HED / Lineart / MLSD | cv2 + einops | ✅ 需下载 |
| DWPose | onnxruntime + matplotlib | ✅ 需下载 |
| ZoeDepth / MiDaS | transformers | ✅ 需下载（走 HF 缓存） |

---

## 5. 深度预处理器与 HF 缓存重定向

### 5.1 问题

ZoeDepth 等深度节点用 `transformers.pipeline()` 加载模型（如 `Intel/zoedepth-nyu-kitti`，约 1.3GB），默认下载到 **C 盘**的 HF 缓存 `C:\Users\user\.cache\huggingface\hub`。而 C 盘常年快满。

### 5.2 解决方案：把 HF 缓存重定向到 D 盘

**关键发现**：ComfyUI **不读 `.env` 文件**（`main.py` 里没有 `load_dotenv()`）。之前 `.env` 里的 `HF_ENDPOINT` 之所以“看似生效”，是因为它在 **Windows 系统环境变量（Machine 级）** 里也设了。

所以正确做法是把 `HF_HOME` 也设成 **Windows 用户级环境变量**：

```powershell
[Environment]::SetEnvironmentVariable('HF_HOME', 'D:\Users\user\.cache\huggingface', 'User')
```

**设置后必须完全重启 Comfy-Desktop**（环境变量只在进程启动时读取）。

### 5.3 下载 ZoeDepth 模型

```python
import os
os.environ['HF_HOME'] = 'D:/Users/user/.cache/huggingface'
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ.pop('HTTP_PROXY', None); os.environ.pop('HTTPS_PROXY', None)
os.environ['NO_PROXY'] = '*'
from huggingface_hub import snapshot_download
snapshot_download('Intel/zoedepth-nyu-kitti')
```

---

## 6. 代理配置：让国内镜像直连

### 6.1 问题

访问 hf-mirror.com 时，如果走全局代理（Clash），会被重定向到 huggingface.co，导致下载失败或 308 报错。

### 6.2 解决方案：Clash 加规则让 hf-mirror 直连

找到 Clash for Windows 的激活配置文件（`data\profiles\xxx.yml`），在 `rules:` 最前面加一条：

```yaml
rules:
 - DOMAIN-SUFFIX,hf-mirror.com,DIRECT
 - DOMAIN,app.biliapi.net,...
```

然后**重启 Clash**（或重新点选配置）。

> 注意：订阅每 6 小时自动更新会覆盖这条规则，永久方案是用 CFW 的「Parsers（预处理）」功能自动追加。

### 6.3 各类站点代理规则速查

| 目标站点 | 是否走代理 |
|----------|-----------|
| hf-mirror.com | ❌ 直连 |
| huggingface.co | ✅ 走代理 |
| github.com | ✅ 走代理 |
| pypi.org | ✅ 走代理 |

---

## 7. IP-Adapter FaceID 完整配置

FaceID 是“人脸保持”工作流，需要**四类模型**配合，是最容易漏的一环。

### 7.1 依赖全景

| 组件 | 文件夹 | 文件示例 |
|------|--------|---------|
| CLIP Vision | `clip_vision\` | `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors`（2.5GB） |
| InsightFace | `insightface\` | `buffalo_l` 的 5 个 onnx |
| IP-Adapter 主模型 | `ipadapter\` | `ip-adapter-faceid-plusv2_sdxl.bin`（1.5GB） |
| IP-Adapter LoRA | `loras\` | `ip-adapter-faceid-plusv2_sdxl_lora.safetensors`（372MB） |

> ⚠️ **重点坑**：FaceID 模型分两半 —— 主模型 `.bin` 放 `ipadapter\`，LoRA `_lora.safetensors` 放 **`loras\`**（不是 ipadapter！）。节点加载 LoRA 时从 `loras` 文件夹找。

### 7.2 CLIP Vision 三个模型

| 文件 | 用途 | 大小 |
|------|------|------|
| `CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors` | SD1.5 IP-Adapter | 2.53 GB |
| `CLIP-ViT-bigG-14-laion2B-39B-b160k.safetensors` | SDXL | 3.69 GB |
| `clip_vision_l.safetensors` | FLUX / 图像理解 | 1.71 GB |

放到 `ComfyUI-Shared\models\clip_vision\`。

### 7.3 InsightFace 人脸分析

1. **安装 `insightface` 包**（注意 Python 3.13 兼容性 —— 用 1.0.1 版本）：

```powershell
.venv\Scripts\python.exe -m pip install insightface
```

2. **下载 buffalo_l 模型**（约 280MB，从 GitHub releases，走代理）：

```powershell
curl -L --proxy http://127.0.0.1:10809 -o D:/temp/buffalo_l.zip \
  "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip"
```

解压到 `ComfyUI-Installs\...\ComfyUI\models\insightface\models\buffalo_l\`（5 个 onnx）。

3. **provider 选 CPU**：因为 onnxruntime 装的是 CPU 版（没有 CUDA 加速），选 CUDA 会报错。

### 7.4 FaceID 模型（SD1.5 + SDXL 两套）

仓库 `h94/IP-Adapter-FaceID`，每个预设需要“主模型 + LoRA”两个文件：

| 预设 | 主模型（→ ipadapter\） | LoRA（→ loras\） |
|------|----------------------|-----------------|
| FACEID (SDXL) | `ip-adapter-faceid_sdxl.bin` | `ip-adapter-faceid_sdxl_lora.safetensors` |
| FACEID PLUS V2 (SDXL) | `ip-adapter-faceid-plusv2_sdxl.bin` | `ip-adapter-faceid-plusv2_sdxl_lora.safetensors` |

### 7.5 版本匹配提醒

- 用 **SDXL 底模** → 节点找 `faceid.sdxl.*` / `plusv2.sdxl.*` 文件。
- 用 **SD1.5 底模**（dreamshaper 等）→ 找 `faceid.sd15.*` 文件。
- LoRA 版本必须和主模型版本一致。

---

## 8. 常见报错速查表

| 报错 | 根因 | 解决 |
|------|------|------|
| `0xC0000005` 崩溃 | PyTorch CUDA 版本高于驱动 | 重装 PyTorch cu128 |
| `No module named 'insightface'` | 依赖没装 | `pip install insightface` |
| `No module named 'matplotlib'` | DWPose 依赖缺失 | `pip install matplotlib onnxruntime` |
| `IPAdapter model not found` | 主模型放错目录 | 放 `ipadapter\`（注意 SD 版本匹配） |
| `LoRA model not found` | LoRA 放错目录 | 放 `loras\`（不是 ipadapter\） |
| `LocalEntryNotFoundError` | 走代理导致镜像重定向 | 清空代理访问 hf-mirror |
| `Cannot send request, client closed` | 代理连接被重置 | 同上，或手动下载模型 |
| `No space left on device` | C 盘满 | 清 pip 缓存 + 重定向 HF 到 D 盘 |
| `buffer length not multiple` | 模型文件下载不完整 | 删掉重下 |

---

## 9. 总结

这次完整配置踩过的关键坑，浓缩成几条经验：

1. **CUDA 版本要匹配**：驱动支持的版本 ≥ PyTorch 编译的版本。
2. **模型目录分两种**：大部分放共享目录，个别硬编码节点（JoyCaption）放安装目录；判断靠 `folder_paths.get_folder_paths()`。
3. **下载国内镜像要清代理**：hf-mirror.com 走代理会被重定向，直连才正常。
4. **`.env` 文件 ComfyUI 不读**：环境变量要设成 Windows 系统级（HF_ENDPOINT 在 Machine 级，HF_HOME 在 User 级）。
5. **FaceID 模型分两半**：主模型 `.bin` 在 `ipadapter\`，LoRA 在 `loras\`，别放错。
6. **SD1.5 / SDXL 别混用**：底模、LoRA、FaceID 模型版本必须一致。
7. **C 盘空间要盯紧**：HF 缓存、pip 缓存默认都在 C 盘，满了就重定向到 D 盘。

---

> 本文记录的所有路径基于 Comfy-Desktop 的默认安装位置，如果你的安装位置不同，请自行替换对应路径。
