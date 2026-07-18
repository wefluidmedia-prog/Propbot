import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ELEVENLABS_API_KEY")
voice_id = os.getenv("ELEVENLABS_VOICE_ID")
model_id = "eleven_multilingual_v2"

print(f"Testing Voice ID: {voice_id}")
print(f"Using Model: {model_id}")

url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": api_key
}

data = {
    "text": "नमस्ते! मैं Propbot से बोल रही हूँ।",
    "model_id": model_id,
    "voice_settings": {
        "stability": float(os.getenv("ELEVENLABS_STABILITY", "0.5")),
        "similarity_boost": float(os.getenv("ELEVENLABS_SIMILARITY", "0.75")),
        "style": float(os.getenv("ELEVENLABS_STYLE", "0.0")),
        "use_speaker_boost": True
    }
}

response = requests.post(url, json=data, headers=headers)

if response.status_code == 200:
    print("SUCCESS! Audio generated successfully.")
    with open("test_audio.mp3", "wb") as f:
        f.write(response.content)
    print("Saved to test_audio.mp3")
else:
    print(f"FAILED! Status Code: {response.status_code}")
    print(f"Error Details: {response.text}")
