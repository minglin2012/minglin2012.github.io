---
layout: post
title: "ComfyUI 环境搭建与 JoyCaption 安装技术文档"
subtitle: "从驱动诊断、模型下载到 JoyCaption 安装的完整实践记录"
date: 2026-08-19
author: Minglin
header-img: img/post-bg.jpg
tags: [AI, 工具, ComfyUI]
---

# ComfyUI 环境搭建与 JoyCaption 安装技术文档

> 环境：Windows 10，NVIDIA RTX 3060 12GB，Comfy-Desktop
> 日期：2026-08-12

---

## 1. 硬件与驱动诊断

### 1.1 查询命令

```powershell
nvidia-smi
```

### 1.2 环境信息

| 项目 | 值 |
|------|-----|
| GPU | NVIDIA GeForce RTX 3060 (12GB VRAM) |
| 驱动版本 | 576.88 |
| 驱动支持 CUDA | 12.9 |
| Compute Capability | 8.6 (Ampere) |

---

## 2. CUDA 版本不匹配修复

### 2.1 问题

ComfyUI 桌面版自动安装了 PyTorch 2.12.1+cu130（CUDA 13.0），但驱动 576.88 最高只支持 CUDA 12.9。

**报错**：`cudaGetDeviceCount() returned cudaErrorNotSupported`

### 2.2 修复

在 ComfyUI venv 中重装 PyTorch CUDA 12.8 版本：

```powershell
# 进入 ComfyUI 虚拟环境
cd D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI

# 重装 PyTorch (CUDA 12.8)
.venv\Scripts\python.exe -m pip install torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu128 --force-reinstall
```

### 2.3 验证

```powershell
.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

输出：`True / NVIDIA GeForce RTX 3060`

---

## 3. ComfyUI 模型目录结构

### 3.1 共享模型目录（推荐存放位置）

```text
D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Shared\models\
```

### 3.2 各类型模型存放位置

| 模型类型 | 目录 | 说明 |
|----------|------|------|
| Checkpoint (完整底模) | `checkpoints\` | SD 1.5, SDXL, SD3 等 |
| UNET/DiT | `unet\` | FLUX 系列扩散模型主体 |
| Diffusion Models | `diffusion_models\` | 旧版扩散模型 (同 UNET) |
| CLIP (文本编码器) | `clip\` | CLIP-L, T5 等 |
| Text Encoders | `text_encoders\` | 同上，部分节点路径不同 |
| VAE | `vae\` | 图像编解码器 |
| LoRA | `loras\` | 微调权重 |
| ControlNet | `controlnet\` | 图像控制模型 |
| Upscale Models | `upscale_models\` | 放大模型 (ESRGAN 等) |
| Embeddings | `embeddings\` | 文本嵌入/反嵌 |
| LLM (大语言模型) | `LLM\` | HuggingFace 格式的 VLM |
| LLM GGUF | `LLM\GGUF\` | GGUF 量化格式的 VLM |

### 3.3 FLUX.1 模型需要的 4 个文件

```text
unet\  → flux1-krea-dev_fp8_scaled.safetensors  (去噪网络)
clip\  → clip_l.safetensors                      (CLIP-L)
clip\  → t5xxl_fp16.safetensors                  (T5-XXL)
vae\   → ae.safetensors                          (VAE)
```

### 3.4 注意

- ComfyUI **安装目录** `models\` 和**共享目录** `ComfyUI-Shared\models\` 是两个位置
- 大部分节点能搜到共享目录，但部分自定义节点（如 JoyCaption GGUF）只搜安装目录

---

## 4. HuggingFace 国内镜像配置

### 4.1 创建环境变量文件

在 ComfyUI 根目录创建 `.env` 文件：

```text
D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.env
```

内容：

```text
HF_ENDPOINT=https://hf-mirror.com
```

### 4.2 注意事项

- 该镜像只影响 HuggingFace 模型下载，不覆盖 Git/PyPI
- 部分冷门模型可能未被镜像缓存，需直连下载
- **代理设置注意**：访问 hf-mirror.com 时不要走全局代理，否则会被重定向回 huggingface.co

### 4.3 下载工具

```powershell
# Python 脚本方式
.venv\Scripts\python.exe -c "from huggingface_hub import hf_hub_download; hf_hub_download(...)"

# PowerShell 直链下载（绕过代理）
$env:HTTP_PROXY = ""; $env:HTTPS_PROXY = ""
Invoke-WebRequest -Uri "https://hf-mirror.com/..." -OutFile "..." -NoProxy
```

---

## 5. SDXL Turbo 模型下载

### 5.1 问题

ComfyUI Model Manager 下载中断，文件仅 593MB（应有 6.94GB），导致：

```text
ValueError: buffer length must be a multiple of element size (2)
```

### 5.2 下载

```powershell
.venv\Scripts\python.exe -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='stabilityai/sdxl-turbo',
    filename='sd_xl_turbo_1.0_fp16.safetensors',
    local_dir=r'D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Shared\models\checkpoints'
)
"
```

### 5.3 SDXL Turbo 使用注意

- Checkpoint 自带 VAE，不需要单独加载 VAE 节点
- 如果用独立的 VAE Loader，必须使用 SDXL 兼容的 VAE（潜空间 128 通道 vs SD 1.5 的 4 通道）
- 报错 `expected input[2, 128, 96, 94] to have 4 channels` 说明 VAE 不匹配

---

## 6. JoyCaption 图像描述模型安装

### 6.1 JoyCaption 版本对比

| 版本 | 底座 | 大小 (FP16) | 大小 (Q4) | 质量 |
|------|------|-------------|-----------|------|
| Alpha One | 较小模型 | ~2GB | - | 一般 |
| Alpha Two | Llama 3.1 8B | ~16GB | ~5GB | 较好 |
| Beta One | Llama 3.1 8B | ~16GB | ~5GB | 最佳 |

Alpha Two 和 Beta One 大小相同，Beta One 训练更好。

### 6.2 安装 1038lab/ComfyUI-JoyCaption 节点

通过 ComfyUI Manager → Install Custom Nodes → 搜索 `JoyCaption`。

### 6.3 安装 llama-cpp-python (CUDA 版)

**前提**：该节点 GGUF 模式依赖 `llama-cpp-python`，但官方仅提供 cp312 以下的 CUDA 预编译包。

**CPython 3.13 的解决方案**：使用 JamePeng 的预编译 wheel

1. 下载地址（浏览器打开）：
   ```text
   https://github.com/JamePeng/llama-cpp-python/releases
   ```

2. 下载文件：
   ```text
   llama_cpp_python-0.3.46+cu128-cp313-cp313-win_amd64.whl
   ```

3. 安装：
   ```powershell
   pip install --force-reinstall 下载目录\llama_cpp_python-0.3.46+cu128-cp313-cp313-win_amd64.whl
   ```

**注意**：`--force-reinstall` 不能省略，否则 pip 会判定"不兼容平台"。

### 6.4 下载 JoyCaption GGUF 模型文件

**从 hf-mirror.com 下载（不要走代理！）**：

目标目录：

```text
D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Shared\models\LLM\GGUF\
```

需要两个文件：

| 文件 | 大小 | 用途 |
|------|------|------|
| `Llama-Joycaption-Beta-One-Hf-Llava-Q4_K.gguf` | 4.7 GB | 语言模型主体 (Q4 量化) |
| `llama-joycaption-beta-one-llava-mmproj-model-f16.gguf` | 837 MB | 视觉投影层 |

下载方法（PowerShell，不走代理）：

```powershell
Invoke-WebRequest -Uri "https://hf-mirror.com/concedo/llama-joycaption-beta-one-hf-llava-mmproj-gguf/resolve/main/Llama-Joycaption-Beta-One-Hf-Llava-Q4_K.gguf" `
    -OutFile "目标目录\Llama-Joycaption-Beta-One-Hf-Llava-Q4_K.gguf" -NoProxy
```

**重要**：镜像上的文件名是**大写驼峰** `Llama-Joycaption-Beta-One-Hf-Llava-Q4_K.gguf`，不能用小写。

### 6.5 关键 — 文件放置位置

JoyCaption GGUF 节点硬编码了搜索路径：

```text
{models_dir}/LLM/GGUF/
```

Comfy-Desktop 中 `models_dir` 指向**安装目录**而非共享目录：

```text
D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\models\LLM\GGUF\
```

文件必须放在这里（或同时放在共享目录保留备份）。

### 6.6 两个节点不要混淆

| 节点名 | 模型下拉框内容 | 模型目录 |
|--------|---------------|----------|
| **JoyCaption** (HF 标准版) | joycaption-beta-one-fp8, joycaption-beta-one, joycaption-alpha-two | `models/LLM/` |
| **JoyCaption GGUF** | joycaption-beta-one-gguf-q4_k, JoyCaption Beta One (Q4_K_M) 等 | `models/LLM/GGUF/` |

### 6.7 下拉框名称与磁盘文件映射

配置在 `jc_data.json` → `gguf_models` 段：

```json
"joycaption-beta-one-gguf-q4_k": {
    "name": "concedo/llama-joycaption-beta-one-hf-llava-mmproj-gguf/Llama-Joycaption-Beta-One-Hf-Llava-Q4_K.gguf",
    "description": "JoyCaption Beta One GGUF - Q4_K quantized model (4.92 GB)"
}
```

- 前面的 `concedo/...` 是 HF 仓库路径（下载用）
- 最后的文件名 `Llama-Joycaption-Beta-One-Hf-Llava-Q4_K.gguf` 是本地查找的文件名
- 节点取 `Path(name).name` 得到文件名，在 `models/LLM/GGUF/` 下查找

### 6.8 添加自定义 GGUF 模型

在 `custom_nodes/ComfyUI-JoyCaption/` 下创建 `custom_models.json`：

```json
{
  "gguf_models": {
    "我的自定义模型": {
      "name": "user/repo/my-model.gguf",
      "description": "My custom JoyCaption GGUF model"
    }
  }
}
```

---

## 7. 模型下载经验总结

### 7.1 下载方式优先级

1. **ComfyUI Model Manager**（UI 界面）— 最简单但可能中断
2. **huggingface_hub Python 库** — 走镜像但部分仓库不支持
3. **Invoke-WebRequest 直链** — 最可靠，需注意代理和文件名
4. **ModelScope** — 国内备选方案

### 7.2 常见下载问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 文件比预期小很多 | 下载中断 | 删除 `.dl-meta` 标记文件，重新下载 |
| `unicodeescape` 错误 | Python 字符串中 `\U` 被转义 | 使用 raw string `r"..."` 或正斜杠 |
| `Entry not found` | 镜像未缓存该文件 | 直连 HF 或尝试其他镜像 |
| `Page not found` | 代理将镜像请求重定向到 HF | 对镜像地址使用 `-NoProxy` |
| `not a supported wheel` | pip 平台检测过严 | 加 `--force-reinstall` |
| Windows 长路径错误 | llama.cpp 源码路径过长 | 使用预编译 wheel 而非源码构建 |

### 7.3 网络代理使用规则

| 目标站点 | 是否走代理 | 原因 |
|----------|-----------|------|
| hf-mirror.com | **不走** | 代理会重定向到 huggingface.co 导致失败 |
| huggingface.co | 走 | 国内直连超时 |
| github.com | 走 | 国内直连慢/被封 |
| pypi.org | 走 | 下载加速 |
| abetlen.github.io | 走 | 下载 CUDA wheel |

---

## 8. KSampler 图像放大流程

### 8.1 实拍图放大的提示词策略

- 低降噪（denoise 0.25-0.4）：提示词权重低，模型 90% 依赖潜变量中已有的图像信息
- 提示词只需简单描述即可："a chair, indoor, natural lighting"
- 不需要原图的精确提示词

### 8.2 Flax 放大工作流链

```text
Load Image → JoyCaption GGUF → CLIP Text Encode → KSampler → VAE Decode → Preview Image
```

---

## 9. 快捷命令参考

### 9.1 查看 GPU 状态

```powershell
nvidia-smi
```

### 9.2 验证 PyTorch CUDA

```powershell
.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

### 9.3 验证 llama-cpp-python

```powershell
.venv\Scripts\python.exe -c "import llama_cpp; print(llama_cpp.__version__)"
```

### 9.4 检查 ComfyUI 日志

```text
D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\user\comfyui.log
```

---

## 10. 关键文件路径速查

| 用途 | 路径 |
|------|------|
| ComfyUI 安装根目录 | `D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\` |
| 共享模型目录 | `D:\Users\user\AppData\Local\Comfy-Desktop\ComfyUI-Shared\models\` |
| JoyCaption 节点 | `...\ComfyUI\custom_nodes\ComfyUI-JoyCaption\` |
| JoyCaption 配置 | `...\ComfyUI-JoyCaption\jc_data.json` |
| GGUF 模型目录 | `...\ComfyUI\models\LLM\GGUF\` |
| HF 镜像配置 | `...\ComfyUI\.env` |
| ComfyUI 日志 | `...\ComfyUI\user\comfyui.log` |
| ComfyUI Manager 配置 | `...\ComfyUI\user\__manager\config.ini` |
