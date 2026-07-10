# go2go-new 环境部署说明

用于 Unitree Go2 机器狗（WebRTC 连接 + Flask 控制界面 + 音频/图像处理）的 Python 环境。
本文档说明如何在另一台电脑上从零重建这个 conda 环境。

## 环境信息

- 环境名：`go2go-new`
- Python 版本：`3.11.15`
- 关键依赖：`unitree_webrtc_connect`、`aiortc`、`torch (CPU 版)`、`Flask-SocketIO`、`librosa`、`PyQt5`、`opencv-python`

> ⚠️ 注意：本环境里的 `torch==2.2.2+cpu` 和 `torchvision==0.17.2+cpu` 是 **CPU 版本**，
> 无法从默认 PyPI 安装，必须使用 PyTorch 官方 CPU 索引。安装步骤见下方。

## 安装步骤

### 1. 创建 conda 环境

```bash
conda create -n go2go-new python=3.11.15 -y
conda activate go2go-new
```

### 2. 先单独安装 CPU 版 torch

```bash
pip install torch==2.2.2+cpu torchvision==0.17.2+cpu --index-url https://download.pytorch.org/whl/cpu
```

### 3. 安装其余依赖

`requirements.txt` 中已包含 torch/torchvision（带 `+cpu` 标记），
所以安装其余包时用 `--extra-index-url` 让 pip 能找到 CPU 版：

```bash
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

如果第 2 步已经装好 torch，pip 会跳过它们，直接装剩下的包。

### 4. 验证安装

```bash
python -c "import torch; print('torch', torch.__version__)"
python -c "import aiortc, flask, librosa, cv2, PyQt5; print('核心依赖 OK')"
python -c "import unitree_webrtc_connect; print('unitree webrtc OK')"
```

## 常见问题

- **`PyAudio` 安装失败**：Windows 下如果编译报错，可改用预编译轮子
  `pip install pipwin && pipwin install pyaudio`，或从 conda 装 `conda install pyaudio`。
- **`PyQt5` 相关报错**：确保 `PyQt5`、`PyQt5-Qt5`、`PyQt5-sip` 三个版本匹配（见 requirements.txt）。
- **torch 装成了 GPU/CUDA 版**：说明没走 CPU 索引，卸载后重新执行第 2 步。
- **`unitree_webrtc_connect` 找不到**：确认能访问 PyPI，该包为普通 PyPI 包。

## 快速一键（可选）

```bash
conda create -n go2go-new python=3.11.15 -y && conda activate go2go-new
pip install torch==2.2.2+cpu torchvision==0.17.2+cpu --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```
