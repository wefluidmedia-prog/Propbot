# Unit Economics — Per Client Monthly Cost vs ₹5,000 Revenue

## Assumptions
- 70 inbound voice calls per month per client
- Average call duration: 3 minutes
- 200 chat widget messages per month
- Average chat response: ~300 tokens

## Monthly Cost Breakdown (Per Client)

| Item | Calculation | Cost (INR) |
|------|------------|------------|
| **Bolna.ai platform** | 70 calls × 3 min × $0.02/min × ₹84/$ | ₹353 |
| **Deepgram STT** | 210 min × $0.0059/min × ₹84 | ₹104 |
| **ElevenLabs TTS** | 210 min × $0.018/min × ₹84 | ₹318 |
| **Claude API (voice via Bolna)** | 210 min × ~$0.005/min × ₹84 | ₹88 |
| **Claude API (chat widget)** | 200 msgs × ~500 tokens × $3/M input + $15/M output | ₹180 |
| **Exotel virtual number** | 1 DID/month | ₹200 |
| **Exotel call minutes** | 210 min × ₹1.5/min | ₹315 |
| **Exotel SMS alerts** | ~30 SMS × ₹0.30/SMS | ₹9 |
| **Gmail SMTP** | Free | ₹0 |
| **Supabase** | Free tier | ₹0 |
| **Render.com** | Free tier (shared across clients) | ₹0 |
| | | |
| **TOTAL COST** | | **~₹1,567** |

## Revenue & Margin

| Metric | Amount |
|--------|--------|
| Monthly revenue per client | ₹5,000 |
| Razorpay fee (2.36%) | -₹118 |
| Net revenue | ₹4,882 |
| Monthly cost | -₹1,567 |
| **Gross profit per client** | **₹3,315** |
| **Gross margin** | **~66%** |

## At 3 Clients (MVP Target)

| Metric | Amount |
|--------|--------|
| Monthly revenue | ₹15,000 |
| Razorpay fees | -₹354 |
| Total costs | -₹4,701 |
| Render upgrade (if needed) | -₹588 ($7) |
| **Monthly profit** | **~₹9,357** |
| **Annual profit** | **~₹1,12,284** |

## Break-even Analysis
- Fixed costs (your time): estimate ₹0 (solo founder, no salary)
- Variable cost per client: ~₹1,567
- Break-even: 1 client covers costs on Day 1
- Profitable from client #1

## Scaling Considerations
- At 10 clients: ₹50K revenue, ~₹15.7K costs, ₹34.3K profit/month
- At 10 clients: register GST, switch to Razorpay business
- At 20+ clients: consider self-hosting Bolna (eliminates $0.02/min platform fee)
- At 50+ clients: hire part-time support, consider Pipecat migration

## Cost Risks
- Heavy caller clients (200+ calls/month) could eat margins
- Monitor per-client usage, add overage billing if needed
- Deepgram + ElevenLabs pricing may change — lock in contracts at scale
