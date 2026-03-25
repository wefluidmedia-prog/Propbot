from pydantic import BaseModel
from typing import Optional


class ClientConfig(BaseModel):
    """Client (tenant) configuration from Supabase."""
    id: str
    business_name: str
    agent_name: str
    agent_email: str
    agent_phone: str
    exotel_number: Optional[str] = None
    bolna_agent_id: Optional[str] = None
    vapi_assistant_id: Optional[str] = None
    knowledge_base: Optional[str] = None
    assistant_persona_name: str = "Priya"
    first_message: str = "Namaste! Aapka swagat hai. Main Priya hoon, aapki kya madad kar sakti hoon?"
    subscription_status: str = "trial"
    razorpay_payment_link: Optional[str] = None
    monthly_fee_inr: int = 5000
