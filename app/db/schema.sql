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
    subscription_status TEXT DEFAULT 'trial' CHECK (subscription_status IN ('trial', 'active', 'paused', 'cancelled', 'expired')),
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
-- API KEYS (per-client auth)
-- =========================
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    key_hash TEXT NOT NULL,
    label TEXT DEFAULT 'default',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_client_id ON api_keys(client_id);

-- =========================
-- MIGRATION: Add self-serve signup columns
-- =========================
-- Run these if your clients table already exists:
--
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS voice_id text DEFAULT '';
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS voice_name text DEFAULT 'Priya';
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS voice_gender text DEFAULT 'female';
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS language_preference text DEFAULT 'hi,en';
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS city text DEFAULT '';
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS onboarding_step int DEFAULT 0;
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS trial_ends_at timestamptz DEFAULT (now() + interval '14 days');
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS calls_this_month int DEFAULT 0;
-- ALTER TABLE clients ADD COLUMN IF NOT EXISTS messages_this_month int DEFAULT 0;

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

-- =========================
-- MIGRATION: Phone number pool + billing + calendar
-- =========================

CREATE TABLE phone_number_pool (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number TEXT NOT NULL UNIQUE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_phone_pool_available ON phone_number_pool(client_id) WHERE client_id IS NULL;
CREATE INDEX idx_phone_pool_client ON phone_number_pool(client_id) WHERE client_id IS NOT NULL;

-- New columns on clients
ALTER TABLE clients ADD COLUMN IF NOT EXISTS razorpay_subscription_id TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS razorpay_customer_id TEXT;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS google_calendar_token JSONB;
ALTER TABLE clients ADD COLUMN IF NOT EXISTS setup_status TEXT DEFAULT 'provisioning';

-- =========================
-- MIGRATION: Pricing tiers
-- =========================
-- plan_type: 'starter' (₹2,499/mo, 50 calls/mo) | 'pro' (₹4,999/mo, unlimited)
-- Default 'pro' — everyone starts on Pro trial, can choose Starter at subscribe time.
ALTER TABLE clients ADD COLUMN IF NOT EXISTS plan_type TEXT DEFAULT 'pro'
    CHECK (plan_type IN ('starter', 'pro'));
