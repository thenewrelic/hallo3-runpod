"""
Test script to verify Hallo3 imports work correctly.
Run this inside the Docker container to debug import issues.

Usage: docker run --rm hallo3-dev python /workspace/test_imports.py
"""

import sys
import os
from pathlib import Path

print("=" * 60)
print("HALLO3 IMPORT TEST")
print("=" * 60)

# Set up paths
HALLO3_PATH = Path("/workspace/hallo3")
HALLO3_MODULE_PATH = HALLO3_PATH / "hallo3"

print(f"\n1. Checking paths exist:")
print(f"   HALLO3_PATH: {HALLO3_PATH} -> exists: {HALLO3_PATH.exists()}")
print(f"   HALLO3_MODULE_PATH: {HALLO3_MODULE_PATH} -> exists: {HALLO3_MODULE_PATH.exists()}")

if HALLO3_MODULE_PATH.exists():
    print(f"\n2. Contents of {HALLO3_MODULE_PATH}:")
    for f in sorted(HALLO3_MODULE_PATH.iterdir()):
        print(f"   - {f.name}")

# Add paths to sys.path
sys.path.insert(0, str(HALLO3_PATH))
sys.path.insert(0, str(HALLO3_MODULE_PATH))

print(f"\n3. sys.path (first 5 entries):")
for i, p in enumerate(sys.path[:5]):
    print(f"   [{i}] {p}")

# Change to the module directory
print(f"\n4. Changing directory to: {HALLO3_MODULE_PATH}")
os.chdir(HALLO3_MODULE_PATH)
print(f"   Current working directory: {os.getcwd()}")

# Test imports one by one
print("\n5. Testing imports:")

imports_to_test = [
    ("torch", "import torch; print(f'   version: {torch.__version__}')"),
    ("gradio", "import gradio; print(f'   version: {gradio.__version__}')"),
    ("huggingface_hub", "import huggingface_hub; print(f'   version: {huggingface_hub.__version__}')"),
    ("transformers", "import transformers; print(f'   version: {transformers.__version__}')"),
    ("diffusers", "import diffusers; print(f'   version: {diffusers.__version__}')"),
    ("omegaconf", "from omegaconf import OmegaConf"),
    ("sat", "import sat"),
    ("sgm", "import sgm"),
    ("diffusion_video", "from diffusion_video import SATVideoDiffusionEngine"),
    ("app.VideoGenerator", "from app import VideoGenerator"),
]

all_passed = True
for name, import_code in imports_to_test:
    try:
        exec(import_code)
        print(f"   [OK] {name}")
    except Exception as e:
        print(f"   [FAIL] {name}: {e}")
        all_passed = False

print("\n" + "=" * 60)
if all_passed:
    print("ALL IMPORTS SUCCESSFUL!")
else:
    print("SOME IMPORTS FAILED - SEE ABOVE")
print("=" * 60)
