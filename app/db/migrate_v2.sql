-- PropBot Migration v2: Self-serve onboarding + assistant customization
-- Run in Supabase: Dashboard → SQL Editor → New query → paste + run

ALTER TABLE clients
  ADD COLUMN IF NOT EXISTS city TEXT,
  ADD COLUMN IF NOT EXISTS specialty TEXT,
  ADD COLUMN IF NOT EXISTS voice_id TEXT DEFAULT '',
  ADD COLUMN IF NOT EXISTS voice_gender TEXT DEFAULT 'female';
