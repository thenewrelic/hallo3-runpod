"""
RunPod Serverless Handler for Hallo3
Generates talking-head videos from image + audio inputs

Models are downloaded at runtime on first request to avoid build timeout.
"""

import os
import sys
import base64
import uuid
import tempfile
from pathlib import Path

import runpod

# Add hallo3 to path
HALLO3_PATH = Path("/workspace/hallo3")
sys.path.insert(0, str(HALLO3_PATH))

# Global generator instance (loaded once, reused)
generator = None
models_downloaded = False


def download_models():
    """Download Hallo3 models from HuggingFace (run once on first request)"""
    global models_downloaded
    if models_downloaded:
        return

    print("=" * 60)
    print("DOWNLOADING HALLO3 MODELS (first request only)")
    print("This will take several minutes...")
    print("=" * 60)

    from huggingface_hub import snapshot_download

    # Create pretrained_models directory
    models_dir = HALLO3_PATH / "pretrained_models"
    models_dir.mkdir(parents=True, exist_ok=True)

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
    print("\n[4/4] Downloading InsightFace models...")
    insightface_dir = models_dir / "insightface" / "models" / "buffalo_l"
    insightface_dir.mkdir(parents=True, exist_ok=True)

    from huggingface_hub import hf_hub_download

    # Download buffalo_l model files
    for filename in ["1k3d68.onnx", "2d106det.onnx", "det_10g.onnx", "genderage.onnx", "w600k_r50.onnx"]:
        try:
            hf_hub_download(
                repo_id="deepinsight/insightface",
                filename=f"models/buffalo_l/{filename}",
                local_dir=str(models_dir / "insightface"),
                local_dir_use_symlinks=False
            )
        except Exception as e:
            print(f"Warning: Could not download {filename}: {e}")

    models_downloaded = True
    print("\n" + "=" * 60)
    print("MODEL DOWNLOAD COMPLETE")
    print("=" * 60 + "\n")


def load_generator():
    """Load the Hallo3 video generator (singleton)"""
    global generator
    if generator is not None:
        return generator

    # Download models first (if not already done)
    download_models()

    print("Loading Hallo3 VideoGenerator...")

    # Change to hallo3 directory for proper config loading
    os.chdir(HALLO3_PATH)

    from hallo3.app import VideoGenerator
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
