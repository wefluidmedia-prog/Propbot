"""
VoiceEngine factory.

Returns the right VoiceEngine implementation based on VOICE_PROVIDER env var.
This is the single switching point — change the env var and the entire
app uses a different voice provider.
"""

from app.voice.base import VoiceEngine


def get_voice_engine() -> VoiceEngine:
    """
    Instantiate the configured VoiceEngine.

    Set VOICE_PROVIDER in .env:
      - "bolna"   → BolnaEngine  (default, cheapest for India)
      - "vapi"    → VapiEngine   (fallback, more mature)
      - "pipecat" → PipecatEngine (future, self-hosted)
    """
    from app.config import settings

    provider = settings.VOICE_PROVIDER.lower()

    if provider == "bolna":
        from app.voice.bolna_engine import BolnaEngine
        return BolnaEngine(
            api_key=settings.BOLNA_API_KEY,
            api_url=settings.BOLNA_API_URL,
        )
    elif provider == "vapi":
        from app.voice.vapi_engine import VapiEngine
        return VapiEngine(api_key=settings.VAPI_API_KEY)
    elif provider == "pipecat":
        from app.voice.pipecat_engine import PipecatEngine
        return PipecatEngine()
    else:
        raise ValueError(
            f"Unknown VOICE_PROVIDER: '{provider}'. "
            f"Use 'bolna', 'vapi', or 'pipecat'."
        )
