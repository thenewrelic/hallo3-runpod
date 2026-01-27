# Hallo3 RunPod Serverless Docker Image
# Based on NVIDIA CUDA with Python 3.10

FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    git \
    git-lfs \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Set working directory
WORKDIR /workspace

# Clone Hallo3 repository
RUN git clone https://github.com/fudan-generative-vision/hallo3.git

# Install Python dependencies
WORKDIR /workspace/hallo3
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install RunPod SDK
RUN pip install --no-cache-dir runpod

# Download pretrained models from HuggingFace
# This will take a while (~70GB of models)
RUN pip install huggingface_hub && \
    huggingface-cli download fudan-generative-ai/hallo3 --local-dir ./pretrained_models

# Copy handler script
COPY handler.py /workspace/handler.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# Run the handler
WORKDIR /workspace
CMD ["python", "handler.py"]
