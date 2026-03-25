from pydantic import BaseModel
from typing import Optional


class LeadData(BaseModel):
    """Lead data captured during a call or chat."""
    name: Optional[str] = None
    phone: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    preferred_area: Optional[str] = None
    property_type: Optional[str] = None
    urgency: Optional[str] = None
    viewing_time: Optional[str] = None
    notes: Optional[str] = None
    source: str = "voice"


class CallbackRequest(BaseModel):
    """Request from chat widget 'Request Callback' button."""
    name: Optional[str] = None
    phone: str
    preferred_time: Optional[str] = None
    context: Optional[str] = None
