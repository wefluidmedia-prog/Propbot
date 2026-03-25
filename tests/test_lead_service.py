"""Tests for lead service — data validation and storage logic."""

from app.models.lead import LeadData, CallbackRequest


class TestLeadModels:
    def test_lead_data_minimal(self):
        """Lead with just name and phone should be valid."""
        lead = LeadData(name="Amit", phone="+919999888877")
        assert lead.name == "Amit"
        assert lead.source == "voice"

    def test_lead_data_full(self):
        """Lead with all fields."""
        lead = LeadData(
            name="Amit Kumar",
            phone="+919999888877",
            budget_min=5000000,
            budget_max=8500000,
            preferred_area="Dwarka Sector 7",
            property_type="2BHK",
            urgency="1-3months",
            viewing_time="Saturday morning",
            notes="Park-facing preferred",
            source="voice",
        )
        assert lead.budget_min == 5000000
        assert lead.urgency == "1-3months"

    def test_callback_request(self):
        """Callback request requires phone only."""
        req = CallbackRequest(phone="+919888777666")
        assert req.phone == "+919888777666"
        assert req.name is None

    def test_callback_request_full(self):
        req = CallbackRequest(
            name="Priya",
            phone="+919888777666",
            preferred_time="Evening 5-7 PM",
            context="Was asking about 3BHK in Noida",
        )
        assert req.preferred_time == "Evening 5-7 PM"
