# Hallo3 RunPod Serverless Deployment

This directory contains the files needed to deploy Hallo3 as a RunPod serverless endpoint.

## Prerequisites

1. **RunPod Account** with credits (~$10-20 to start)
2. **GitHub Account** (for the recommended deployment method)
3. **RunPod API Key** (get from RunPod dashboard)

---

## Deployment Option A: GitHub Build (Recommended - No Docker Required!)

This is the easiest method. RunPod builds the Docker image for you on their servers.

### Step 1: Create a GitHub Repository

1. Go to [GitHub](https://github.com) and create a new repository (e.g., `hallo3-runpod`)
2. Clone it locally or use GitHub's web interface

### Step 2: Upload These Files to Your Repo

Copy these files from this `runpod/` folder to your GitHub repo:
- `handler.py` - The serverless handler
- `Dockerfile` - Build instructions
- `runpod.toml` - RunPod configuration (optional but helpful)

Your repo structure should look like:
```
your-repo/
├── handler.py
├── Dockerfile
└── runpod.toml
```

### Step 3: Create Serverless Endpoint on RunPod

1. Go to [RunPod Serverless Console](https://www.runpod.io/console/serverless)
2. Click **"+ New Endpoint"**
3. Select **"Build from GitHub"** (or "Custom Source")
4. Connect your GitHub account if not already connected
5. Select your repository
6. Configure the endpoint:

| Setting | Value |
|---------|-------|
| **Name** | `hallo3-video-generator` |
| **GPU Type** | NVIDIA RTX 4090 (or A100) |
| **Container Disk** | 100 GB |
| **Volume Disk** | 20 GB |
| **Max Workers** | 1 |
| **Idle Timeout** | 300 seconds |
| **Execution Timeout** | 600 seconds |
| **Flash Boot** | Enabled (recommended) |

7. Click **"Deploy"**

### Step 4: Wait for Build

The build will take **30-60 minutes** because it downloads ~70GB of model weights. You can monitor progress in the RunPod console.

### Step 5: Get Your Endpoint ID

Once deployed, copy the **Endpoint ID** from the dashboard. It looks like: `abc123xyz789`

### Step 6: Update Your Local Config

Edit `app/config.yaml`:

```yaml
runpod:
  api_key: "rpa_your_api_key_here"
  endpoint_id: "abc123xyz789"  # <-- Your new endpoint ID
  timeout: 300
```

### Step 7: Test It!

```bash
cd app
.\venv\Scripts\python.exe app.py test-runpod
```

---

## Deployment Option B: Docker Hub (If You Have Docker)

If you have Docker installed and prefer to build locally:

### Step 1: Build the Docker Image

```bash
cd runpod
docker build -t your-dockerhub-username/hallo3-runpod:latest .
docker push your-dockerhub-username/hallo3-runpod:latest
```

**Note:** The build downloads ~70GB of model weights. This takes a long time and requires significant disk space.

### Step 2: Create Serverless Endpoint

1. Go to [RunPod Console](https://www.runpod.io/console/serverless)
2. Click "New Endpoint"
3. Select "Docker Image"
4. Enter: `your-dockerhub-username/hallo3-runpod:latest`
5. Configure same settings as Option A above
6. Deploy

---

## Deployment Option C: Pre-built Template

Check if someone has already published a Hallo3 template on RunPod:

1. Go to RunPod Serverless Console
2. Browse "Community Templates" or "Explore"
3. Search for "Hallo3" or "talking head"

If found, you can deploy with one click!

## API Usage

### Input Format

```json
{
  "input": {
    "image": "base64_encoded_png_image",
    "audio": "base64_encoded_wav_audio",
    "prompt": "Optional text description of the video"
  }
}
```

### Output Format

```json
{
  "output": {
    "video": "base64_encoded_mp4_video"
  }
}
```

### Example Request (Python)

```python
import runpod
import base64

runpod.api_key = "your_api_key"

# Encode inputs
with open("face.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode()

with open("speech.wav", "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode()

# Submit job
endpoint = runpod.Endpoint("your_endpoint_id")
result = endpoint.run_sync({
    "image": image_b64,
    "audio": audio_b64,
    "prompt": "A person talking naturally"
})

# Decode output
video_b64 = result["video"]
with open("output.mp4", "wb") as f:
    f.write(base64.b64decode(video_b64))
```

## Estimated Costs

| Component | Cost |
|-----------|------|
| RTX 4090 GPU | ~$0.44/hour |
| Typical video (30s) | ~$0.30-0.50 per video |
| Cold start | +30-60 seconds |

## Troubleshooting

### Cold Start Timeout
If jobs timeout on cold start, increase the execution timeout to 600 seconds.

### Out of Memory
Ensure you're using an RTX 4090 or A100 with 24GB+ VRAM.

### Model Loading Failed
Check that the pretrained_models directory has all required files:
- hallo3 checkpoint
- CogVideoX-5B
- Wav2Vec2
- InsightFace models

### Video Generation Failed
- Ensure audio is WAV format at 16kHz
- Ensure image is PNG/JPG with a clear face
- Check that face is visible and well-lit

## Input Requirements

### Image
- Format: PNG or JPG
- Aspect ratio: 1:1 (square) or 3:2
- Content: Clear face, good lighting
- Size: Any (will be resized to 480x720)

### Audio
- Format: WAV
- Sample rate: 16kHz (will be converted if different)
- Language: English (model trained on English)
- Duration: Any length (longer = more processing time)

## Notes

- First request after cold start takes longer (model loading)
- Hallo3 generates motion automatically from audio (no driving video needed)
- Output is 480x720 resolution at 25fps
- Processing time scales with audio length
