from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Voice provider: "bolna" | "vapi" | "pipecat"
    VOICE_PROVIDER: str = "bolna"

    # Bolna.ai (primary)
    BOLNA_API_KEY: str = ""
    BOLNA_API_URL: str = "https://api.bolna.dev"

    # Vapi.ai (fallback)
    VAPI_API_KEY: str = ""

    # LLM for chat widget: "openai" or "anthropic"
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Exotel (telephony + SMS)
    EXOTEL_ACCOUNT_SID: str = ""
    EXOTEL_API_KEY: str = ""
    EXOTEL_API_TOKEN: str = ""
    EXOTEL_SUBDOMAIN: str = "api.in.exotel.com"
    EXOTEL_CALLER_ID: str = ""

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Gmail SMTP
    SMTP_EMAIL: str = ""
    SMTP_APP_PASSWORD: str = ""

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_PLAN_ID: str = ""           # Pro plan — ₹4,999/month
    RAZORPAY_STARTER_PLAN_ID: str = ""   # Starter plan — ₹2,499/month
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Google Calendar (OAuth2)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # App
    BASE_URL: str = "https://propbot.onrender.com"
    WEBHOOK_SECRET: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
