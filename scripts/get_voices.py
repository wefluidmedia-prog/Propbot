import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ELEVENLABS_API_KEY")

if not api_key:
    print("API Key not found.")
    exit()

headers = {"xi-api-key": api_key}
response = requests.get("https://api.elevenlabs.io/v1/voices", headers=headers)

if response.status_code == 200:
    voices = response.json().get("voices", [])
    print("\n--- Your ElevenLabs Voice IDs ---")
    for v in voices:
        if v.get('category') != 'premade':
            print(f"Name: {v['name']}")
            print(f"ID:   {v['voice_id']}")
            print("-" * 30)
else:
    print("Failed to fetch voices:", response.text)
