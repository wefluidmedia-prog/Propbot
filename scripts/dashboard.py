import os
import signal
import subprocess
import sys
import threading
import collections
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI()

process = None
# Thread-safe log buffer (last 200 lines from subprocess)
log_buffer = collections.deque(maxlen=200)
log_thread = None


class Settings(BaseModel):
    sarvam_model: str
    sarvam_voice: str
    sarvam_pace: float
    sarvam_temperature: float
    sarvam_pitch: float
    sarvam_loudness: float
    deepgram_model: str
    deepgram_smart_format: bool
    deepgram_punctuate: bool
    deepgram_keywords: str
    deepgram_endpointing: int
    llm_provider: str   # "openai" | "bedrock"
    llm_model: str
    audio_input_device: str   # "" means default
    audio_output_device: str  # "" means default


def _stream_output(proc):
    """Read subprocess stdout/stderr line-by-line and store in log_buffer."""
    try:
        with open("bot.log", "a", encoding="utf-8") as f:
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                stripped = line.rstrip("\r\n")
                log_buffer.append(stripped)
                f.write(stripped + "\n")
                f.flush()
    except Exception:
        pass


@app.get("/")
def get_dashboard():
    html_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.post("/api/start")
def start_bot(settings: Settings):
    global process, log_thread
    if process is not None and process.poll() is None:
        return JSONResponse({"status": "already_running"})

    log_buffer.clear()

    env = os.environ.copy()
    env["SARVAM_MODEL"] = settings.sarvam_model
    env["SARVAM_VOICE"] = settings.sarvam_voice
    env["SARVAM_PACE"] = str(settings.sarvam_pace)
    env["SARVAM_TEMPERATURE"] = str(settings.sarvam_temperature)
    env["SARVAM_PITCH"] = str(settings.sarvam_pitch)
    env["SARVAM_LOUDNESS"] = str(settings.sarvam_loudness)

    env["DEEPGRAM_MODEL"] = settings.deepgram_model
    env["DEEPGRAM_SMART_FORMAT"] = "true" if settings.deepgram_smart_format else "false"
    env["DEEPGRAM_PUNCTUATE"] = "true" if settings.deepgram_punctuate else "false"
    env["DEEPGRAM_KEYWORDS"] = settings.deepgram_keywords
    env["DEEPGRAM_ENDPOINTING"] = str(settings.deepgram_endpointing)

    env["LLM_PROVIDER"] = settings.llm_provider
    env["LLM_MODEL"] = settings.llm_model

    if settings.audio_input_device:
        env["AUDIO_INPUT_DEVICE"] = settings.audio_input_device
    if settings.audio_output_device:
        env["AUDIO_OUTPUT_DEVICE"] = settings.audio_output_device

    script_path = os.path.join(os.path.dirname(__file__), "local_mic_test.py")

    # Use CREATE_NEW_PROCESS_GROUP on Windows to allow sending CTRL_BREAK_EVENT
    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    process = subprocess.Popen(
        [sys.executable, "-u", script_path],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=creationflags,
    )

    log_thread = threading.Thread(target=_stream_output, args=(process,), daemon=True)
    log_thread.start()

    return JSONResponse({"status": "started"})


@app.post("/api/stop")
def stop_bot():
    global process
    if process is not None and process.poll() is None:
        try:
            if sys.platform == "win32":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.send_signal(signal.SIGINT)
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.terminate()
        process = None
        return JSONResponse({"status": "stopped"})
    return JSONResponse({"status": "not_running"})


@app.get("/api/status")
def status_bot():
    global process
    is_running = process is not None and process.poll() is None
    return JSONResponse({"status": "running" if is_running else "stopped"})


@app.get("/api/logs")
def get_logs():
    """Return recent log lines from the voice bot subprocess."""
    return JSONResponse({"logs": list(log_buffer)})


if __name__ == "__main__":
    print("Starting Dashboard on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
