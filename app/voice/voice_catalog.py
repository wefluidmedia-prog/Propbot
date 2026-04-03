"""
Curated voice catalog for PropBot.

Pre-tested ElevenLabs voices for Indian real estate use cases.
Clients pick from this list during signup — no ElevenLabs API calls needed.
"""

VOICE_CATALOG = [
    # ── Female voices ──
    {
        "id": "QTKSa2Iyv0yoxvXY2V8a",
        "name": "Priya",
        "gender": "female",
        "language": "Hindi / English",
        "accent": "Delhi Hindi",
        "description": "Warm, professional voice. Natural Hindi-English switching. Best for residential properties.",
        "recommended": True,
    },
    {
        "id": "XB0fDUnXU5powFXDhCwa",
        "name": "Ananya",
        "gender": "female",
        "language": "Hindi / English",
        "accent": "Neutral Indian",
        "description": "Friendly, youthful voice. Clear pronunciation. Great for first-time buyers.",
        "recommended": False,
    },
    {
        "id": "pFZP5JQG7iQjIQuC4Bku",
        "name": "Meera",
        "gender": "female",
        "language": "Hindi / English",
        "accent": "Soft Hindi",
        "description": "Calm, reassuring voice. Good for luxury and premium segment.",
        "recommended": False,
    },
    # ── Male voices ──
    {
        "id": "bIHbv24MWmeRgasZH58o",
        "name": "Arjun",
        "gender": "male",
        "language": "Hindi / English",
        "accent": "Professional Hindi",
        "description": "Confident, authoritative voice. Great for commercial properties.",
        "recommended": True,
    },
    {
        "id": "onwK4e9ZLuTAKqWW03F9",
        "name": "Rohan",
        "gender": "male",
        "language": "Hindi / English",
        "accent": "Neutral Indian",
        "description": "Friendly, approachable voice. Good all-around choice.",
        "recommended": False,
    },
    {
        "id": "N2lVS1w4EtoT3dr4eOWO",
        "name": "Vikram",
        "gender": "male",
        "language": "Hindi / English",
        "accent": "Formal Hindi",
        "description": "Deep, trustworthy voice. Ideal for senior clientele.",
        "recommended": False,
    },
]


def get_catalog() -> list[dict]:
    """Return the full voice catalog."""
    return VOICE_CATALOG


def get_voice_by_id(voice_id: str) -> dict | None:
    """Look up a voice by ElevenLabs ID."""
    return next((v for v in VOICE_CATALOG if v["id"] == voice_id), None)


def get_voices_by_gender(gender: str) -> list[dict]:
    """Filter catalog by gender."""
    return [v for v in VOICE_CATALOG if v["gender"] == gender]
