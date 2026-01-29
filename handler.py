"""
RunPod Serverless Handler for Hallo3 - DEV/TEST VERSION
Generates talking-head videos from image + audio inputs

Models are downloaded at runtime on first request and cached on network volume.
"""

import os
import sys
import base64
import uuid
import tempfile
from pathlib import Path

import runpod

# Add hallo3 paths for imports
HALLO3_PATH = Path("/workspace/hallo3")
HALLO3_MODULE_PATH = HALLO3_PATH / "hallo3"  # Where diffusion_video.py lives
sys.path.insert(0, str(HALLO3_PATH))
sys.path.insert(0, str(HALLO3_MODULE_PATH))  # Add hallo3/hallo3 for local imports like diffusion_video

# Network volume for persistent model storage (survives rebuilds)
VOLUME_PATH = Path("/runpod-volume")
MODELS_CACHE = VOLUME_PATH / "hallo3-models"

# Global generator instance (loaded once, reused)
generator = None
models_downloaded = False


def download_models():
    """Download Hallo3 models from HuggingFace (cached on network volume)"""
    global models_downloaded
    if models_downloaded:
        return

    from huggingface_hub import snapshot_download

    # Use network volume if available, otherwise fall back to workspace
    if VOLUME_PATH.exists():
        models_dir = MODELS_CACHE / "pretrained_models"
        print(f"Using network volume for model storage: {models_dir}")
    else:
        models_dir = HALLO3_PATH / "pretrained_models"
        print(f"Network volume not found, using workspace: {models_dir}")

    models_dir.mkdir(parents=True, exist_ok=True)

    # Create symlink from hallo3 to the models location
    hallo3_models = HALLO3_PATH / "pretrained_models"
    if not hallo3_models.exists() and VOLUME_PATH.exists():
        hallo3_models.symlink_to(models_dir)
        print(f"Created symlink: {hallo3_models} -> {models_dir}")

    # Check if models already exist on volume
    marker_file = models_dir / ".download_complete"
    if marker_file.exists():
        print("=" * 60)
        print("MODELS FOUND ON NETWORK VOLUME - SKIPPING DOWNLOAD")
        print("=" * 60)
        models_downloaded = True
        return

    print("=" * 60)
    print("DOWNLOADING HALLO3 MODELS (first request only)")
    print("Models will be cached on network volume for future builds")
    print("=" * 60)

    # Download hallo3 model weights
    print("\n[1/4] Downloading Hallo3 checkpoint...")
    snapshot_download(
        repo_id="fudan-generative-ai/hallo3",
        local_dir=str(models_dir / "hallo3"),
        local_dir_use_symlinks=False
    )

    # Download CogVideoX-5B (required for video generation)
    print("\n[2/4] Downloading CogVideoX-5B...")
    snapshot_download(
        repo_id="THUDM/CogVideoX-5b",
        local_dir=str(models_dir / "CogVideoX-5b"),
        local_dir_use_symlinks=False
    )

    # Download Wav2Vec2 (required for audio processing)
    print("\n[3/4] Downloading Wav2Vec2...")
    snapshot_download(
        repo_id="facebook/wav2vec2-base-960h",
        local_dir=str(models_dir / "wav2vec2-base-960h"),
        local_dir_use_symlinks=False
    )

    # Download InsightFace models (required for face detection)
    # Use insightface package to download - it handles authentication automatically
    print("\n[4/4] Downloading InsightFace models...")
    try:
        import insightface
        from insightface.app import FaceAnalysis
        # This will automatically download buffalo_l models to ~/.insightface
        app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
        print("InsightFace models downloaded successfully")
    except Exception as e:
        print(f"Warning: Could not download InsightFace models: {e}")

    # Create marker file to indicate download is complete
    marker_file = models_dir / ".download_complete"
    marker_file.touch()
    print(f"Created marker file: {marker_file}")

    models_downloaded = True
    print("\n" + "=" * 60)
    print("MODEL DOWNLOAD COMPLETE - CACHED ON NETWORK VOLUME")
    print("=" * 60 + "\n")


def load_generator():
    """Load the Hallo3 video generator (singleton)"""
    global generator
    if generator is not None:
        return generator

    # Download models first (if not already done)
    download_models()

    print("Loading Hallo3 VideoGenerator...")

    # Change to hallo3 root directory (where ./configs/ lives)
    # The app.py uses relative paths like "./configs/cogvideox_5b_i2v_s2.yaml"
    os.chdir(HALLO3_PATH)
    print(f"Working directory: {os.getcwd()}")

    from app import VideoGenerator
    generator = VideoGenerator()

    print("Hallo3 VideoGenerator loaded successfully")
    return generator


def decode_base64_to_file(base64_data: str, suffix: str) -> str:
    """Decode base64 string to a temporary file"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.write(base64.b64decode(base64_data))
    temp_file.close()
    return temp_file.name


def encode_file_to_base64(file_path: str) -> str:
    """Encode a file to base64 string"""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def handler(job):
    """
    RunPod serverless handler for Hallo3 video generation

    Input:
        {
            "image": "base64_encoded_png",
            "audio": "base64_encoded_wav",
            "prompt": "optional text description",
            "driving_video": "optional base64_encoded_mp4"
        }

    Output:
        {
            "video": "base64_encoded_mp4"
        }
    """
    job_input = job["input"]

    # Validate required inputs
    if "image" not in job_input:
        return {"error": "Missing required input: image"}
    if "audio" not in job_input:
        return {"error": "Missing required input: audio"}

    temp_files = []

    try:
        # Load generator (cached after first call)
        gen = load_generator()

        # Decode image from base64
        print("Decoding input image...")
        image_path = decode_base64_to_file(job_input["image"], ".png")
        temp_files.append(image_path)

        # Decode audio from base64
        print("Decoding input audio...")
        audio_path = decode_base64_to_file(job_input["audio"], ".wav")
        temp_files.append(audio_path)

        # Get optional prompt
        prompt = job_input.get("prompt", "A person talking naturally")

        # Load image
        from PIL import Image
        image = Image.open(image_path)

        # Note: driving_video is not directly supported by Hallo3's current API
        # The model generates motion automatically from audio
        if "driving_video" in job_input:
            print("Note: driving_video provided but Hallo3 generates motion from audio")

        # Generate video
        print(f"Generating video with prompt: {prompt}")
        output_path = gen.generate_video(
            image=image,
            audio_file=audio_path,
            prompt=prompt
        )
        temp_files.append(output_path)

        print(f"Video generated: {output_path}")

        # Encode output video to base64
        video_base64 = encode_file_to_base64(output_path)

        return {"video": video_base64}

    except Exception as e:
        print(f"Error during generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass


# Start RunPod serverless worker
runpod.serverless.start({"handler": handler})
