import os, requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ELEVENLABS_API_KEY")
res = requests.get('https://api.elevenlabs.io/v1/voices', headers={'xi-api-key': api_key}).json()
count = 0
for v in res.get('voices', []):
    if v.get('category') == 'premade':
        print(f"- **{v['name']}**: `{v['voice_id']}`")
        count += 1
        if count >= 10:
            break
