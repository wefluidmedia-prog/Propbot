import os
import argparse
import logging
from huggingface_hub import snapshot_download

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_models(model_dir: str = "models"):
    """
    Download necessary CPU-optimized models for self-hosted Voice AI.
    - STT: faster-whisper-small (CTranslate2 INT8 format)
    - TTS: supertonic ONNX models (or we download through the SDK later, but good to ensure HF hub works)
    """
    os.makedirs(model_dir, exist_ok=True)
    
    logger.info("Downloading faster-whisper (small) CTranslate2 model...")
    stt_dir = os.path.join(model_dir, "faster-whisper-small")
    # Using a popular pre-converted int8 model for faster-whisper
    snapshot_download(
        repo_id="Systran/faster-whisper-small",
        local_dir=stt_dir,
        # Only download what we need to run it
        allow_patterns=["*.bin", "*.json", "*.txt"],
        local_dir_use_symlinks=False
    )
    logger.info(f"STT model downloaded to {stt_dir}")
    
    # Note: Supertonic 3 has its own auto-download mechanism via its Python SDK,
    # so we don't strictly need to download it manually here, but we will 
    # prepare the directory structure for it.
    tts_dir = os.path.join(model_dir, "supertonic")
    os.makedirs(tts_dir, exist_ok=True)
    logger.info(f"TTS model directory ready at {tts_dir}")
    
    logger.info("Model download complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download AI models for PropBot")
    parser.add_argument("--dir", default="models", help="Directory to store the models")
    args = parser.parse_args()
    
    download_models(args.dir)
