# 6-Week Build Plan — PropBot MVP

## Week 1: Foundation + Accounts
**Goal: All accounts created, schema live, core abstraction built**

- [ ] Sign up: Bolna.ai, Exotel, Supabase, Render, Razorpay, ElevenLabs, Deepgram
- [ ] Email hello@exotel.com to enable SIP trunking (lead time: 2-5 days)
- [ ] Run schema.sql in Supabase SQL editor
- [ ] Set up .env with all API keys
- [ ] Deploy bare FastAPI to Render (just /health endpoint)
- [ ] Set up cron-job.org to ping /health every 14 minutes
- [ ] Test: /health returns 200 on Render URL

## Week 2: Backend Core
**Goal: Webhook handler + alerts working end-to-end**

- [ ] Implement VoiceEngine abstraction (already coded — review + test)
- [ ] Implement webhook handler routing
- [ ] Implement lead storage in Supabase
- [ ] Set up Gmail app password + test email alerts
- [ ] Test Exotel SMS API
- [ ] Test: POST mock webhook JSON → lead appears in Supabase → email received

## Week 3: Voice Integration
**Goal: First real phone call answered by AI**

- [ ] Find suitable Hindi female voice on ElevenLabs (test 3-4 voices)
- [ ] Configure Exotel virtual number + SIP trunk to Bolna
- [ ] Run onboard_client.py for Sharma Properties demo
- [ ] Make first test call
- [ ] Iterate on system prompt based on call quality
- [ ] Test: Call Exotel number → Priya answers → lead captured → alert sent

## Week 4: Chat Widget + Demo Polish
**Goal: Callable demo + embeddable chat ready to show clients**

- [ ] Test chat widget on demo.html with real Claude API
- [ ] Polish widget styling, test on mobile
- [ ] Test "Request Callback" flow end-to-end
- [ ] Create Sharma Properties demo website (demo.html)
- [ ] Run full demo script: call + chat + callback in under 3 minutes
- [ ] Fix bugs found during demo testing
- [ ] Test: Full demo works reliably 5/5 times

## Week 5: First Client Outreach
**Goal: 3 warm leads for paid clients**

- [ ] Create Razorpay payment links
- [ ] Prepare WhatsApp outreach message (see docs/whatsapp_outreach.md)
- [ ] Identify 20 solo Delhi NCR agents (99acres, MagicBricks, JustDial)
- [ ] Send WhatsApp messages to 20 agents
- [ ] Offer free 7-day trial to interested agents
- [ ] Onboard first trial client

## Week 6: Onboard + Iterate
**Goal: 1-3 paying clients live**

- [ ] Onboard trial clients (custom KB, voice test, embed widget)
- [ ] Monitor call quality, lead capture rate
- [ ] Fix issues reported by clients
- [ ] Convert trials to paid (₹5,000/month via Razorpay)
- [ ] Plan Phase 2: self-serve portal, WhatsApp integration

## Key Milestones

| Week | Milestone | Success Criteria |
|------|-----------|-----------------|
| 1 | Infrastructure live | /health returns 200 on Render |
| 2 | Backend working | Mock webhook → lead + alert |
| 3 | First AI call | Real phone call answered by Priya |
| 4 | Demo ready | Full demo in <3 min, reliable |
| 5 | First outreach | 3+ interested agents |
| 6 | First revenue | 1+ paying client at ₹5,000/mo |
