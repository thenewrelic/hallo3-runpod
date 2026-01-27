# Hallo3 RunPod Serverless Docker Image
# Optimized for fast builds - uses RunPod's pre-built PyTorch base image

FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install additional system dependencies
RUN apt-get update && apt-get install -y \
    git-lfs \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Clone Hallo3 repository
RUN git clone https://github.com/fudan-generative-vision/hallo3.git

# Install Python dependencies (PyTorch already in base image, skip heavy packages)
WORKDIR /workspace/hallo3
RUN pip install --upgrade pip && \
    # Remove torch/torchvision from requirements (already installed in base image)
    sed -i '/^torch==/d' requirements.txt && \
    sed -i '/^torchvision==/d' requirements.txt && \
    sed -i '/^nvidia-/d' requirements.txt && \
    # Fix pyav version issue
    sed -i 's/pyav==14.0.1/av>=11.0.0/' requirements.txt && \
    # Install remaining dependencies
    pip install --no-cache-dir -r requirements.txt

# Install RunPod SDK and huggingface_hub
RUN pip install --no-cache-dir runpod huggingface_hub

# Note: Models (~70GB) are downloaded on first request to avoid build timeout
# They will be cached in the container volume for subsequent requests

# Copy handler script
COPY handler.py /workspace/handler.py

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# Run the handler
WORKDIR /workspace
CMD ["python", "handler.py"]
