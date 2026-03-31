from pydantic import BaseModel, Field
from typing import Optional


class LeadData(BaseModel):
    """Lead data captured during a call or chat."""
    name: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=20)
    budget_min: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    budget_max: Optional[int] = Field(default=None, ge=0, le=1_000_000_000)
    preferred_area: Optional[str] = Field(default=None, max_length=200)
    property_type: Optional[str] = Field(default=None, max_length=100)
    urgency: Optional[str] = Field(default=None, max_length=100)
    viewing_time: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=2_000)
    source: str = Field(default="voice", max_length=20)


class CallbackRequest(BaseModel):
    """Request from chat widget 'Request Callback' button."""
    name: Optional[str] = Field(default=None, max_length=200)
    phone: str = Field(..., min_length=7, max_length=20)
    preferred_time: Optional[str] = Field(default=None, max_length=200)
    context: Optional[str] = Field(default=None, max_length=1_000)
