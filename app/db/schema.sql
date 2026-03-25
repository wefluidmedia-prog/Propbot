-- PropBot: AI Receptionist SaaS — Supabase Schema
-- Run this in your Supabase SQL Editor (Dashboard > SQL Editor > New query)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================
-- CLIENTS (tenants)
-- =========================
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_name TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    agent_email TEXT NOT NULL,
    agent_phone TEXT NOT NULL,
    exotel_number TEXT,
    bolna_agent_id TEXT,
    vapi_assistant_id TEXT,
    knowledge_base TEXT,
    assistant_persona_name TEXT DEFAULT 'Priya',
    first_message TEXT DEFAULT 'Namaste! Aapka swagat hai. Main Priya hoon, aapki kya madad kar sakti hoon?',
    subscription_status TEXT DEFAULT 'trial' CHECK (subscription_status IN ('trial', 'active', 'paused', 'cancelled')),
    razorpay_payment_link TEXT,
    monthly_fee_inr INTEGER DEFAULT 5000,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =========================
-- LEADS
-- =========================
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    source TEXT NOT NULL DEFAULT 'voice' CHECK (source IN ('voice', 'chat', 'callback')),
    call_id TEXT,
    caller_name TEXT,
    caller_phone TEXT,
    budget_min BIGINT,
    budget_max BIGINT,
    preferred_area TEXT,
    property_type TEXT,
    urgency TEXT CHECK (urgency IN ('immediate', '1-3months', '3-6months', 'exploring', NULL)),
    preferred_viewing_time TEXT,
    notes TEXT,
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'contacted', 'qualified', 'converted', 'lost')),
    alert_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_leads_client_id ON leads(client_id);
CREATE INDEX idx_leads_created_at ON leads(created_at DESC);

-- =========================
-- CONVERSATIONS
-- =========================
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    source TEXT NOT NULL DEFAULT 'voice' CHECK (source IN ('voice', 'chat')),
    call_id TEXT,
    transcript TEXT,
    messages JSONB,
    recording_url TEXT,
    duration_seconds INTEGER,
    ended_reason TEXT,
    language_detected TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_client_id ON conversations(client_id);
CREATE INDEX idx_conversations_lead_id ON conversations(lead_id);

-- =========================
-- CALLBACK REQUESTS (from chat widget)
-- =========================
CREATE TABLE callback_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    visitor_name TEXT,
    visitor_phone TEXT NOT NULL,
    preferred_time TEXT,
    context TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'called', 'no_answer')),
    alert_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_callback_requests_client_id ON callback_requests(client_id);

-- =========================
-- Auto-update updated_at
-- =========================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER leads_updated_at
    BEFORE UPDATE ON leads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
