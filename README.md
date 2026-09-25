# Docs2Chat — open-source AI support chat widget

**An AI chat for your website that answers customers from your FAQ, website pages and PDFs —
in Georgian, English and Russian — and hands tricky conversations to a human on Telegram.**

🇬🇪 ქართულად: [README.ka.md](README.ka.md) · 💰 How the hosted version makes money: [docs/MONETIZATION.ka.md](docs/MONETIZATION.ka.md)

```html
<script src="https://your-server/widget.js" data-key="pk_..." async></script>
```

## Features

| | |
|---|---|
| 📚 **Knowledge base** | FAQ pairs, PDF upload, website import (single page or crawl), plain text. |
| 🤖 **Grounded answers** | Claude (Anthropic), OpenAI (or any OpenAI-compatible API) or local Ollama. The bot answers **only** from your content and says so when it doesn't know. Works without any AI key too (keyword search + extractive answers). |
| 🇬🇪 **Georgian / English / Russian** | Widget UI in 3 languages, automatic language detection, replies in the visitor's language. |
| ✈️ **Telegram handoff** | “Talk to a human” sends the chat to your Telegram. Reply to the message → the visitor sees it in the widget. `/done` hands the chat back to the AI. You can also reply from the web inbox. |
| 📇 **Lead capture** | Name / phone / email form, lead statuses and order value, CSV export, Telegram notification. |
| 📊 **Analytics** | Conversations per day, answer rate, most asked questions and **unanswered questions with one-click “Add answer”**. |
| 🧩 **One-line install** | Shadow-DOM widget (no CSS conflicts), mobile full-screen, brand color, `Docs2Chat.open()` JS API. |
| 🏢 **Multi-tenant SaaS ready** | Accounts, many chatbots per account, plans & monthly quotas, Paddle subscriptions, free trials, bilingual bank-transfer invoices (mark paid → plan extends automatically), platform admin page with MRR, cash collected and renewal reminders. |
| 🔒 **Secure defaults** | scrypt passwords, signed http-only cookies, CSRF header check, SSRF-safe URL import, per-site origin allow-list, rate limits, CSV-injection-safe export. |

## Quick start (self-hosted, free forever)

```bash
git clone https://github.com/tengotengo23/AI-Support-Chatbot-Knowledge-Base-Widget.git docs2chat
cd docs2chat
cp .env.example .env          # optional: add ANTHROPIC_API_KEY / OPENAI_API_KEY, TELEGRAM_BOT_TOKEN
docker compose up -d
```

Open <http://localhost:8000/admin>, create your account, add some FAQ entries, and click **Install → Open preview**.

Without Docker:

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Turn on AI answers

```env
LLM_PROVIDER=anthropic            # or: openai | ollama | none
ANTHROPIC_API_KEY=sk-ant-...
```

Local and free: `docker compose --profile ollama up -d`, then `docker compose exec ollama ollama pull llama3.1`
and set `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://ollama:11434`.

### Telegram handoff

1. Create a bot with [@BotFather](https://t.me/BotFather) and put the token in `TELEGRAM_BOT_TOKEN`.
2. Restart. In **Settings → Telegram**, click **Connect Telegram** and press *Start* in the bot.
3. When a visitor clicks “Talk to a human”, the chat appears in Telegram. **Reply** to it to answer.

Long polling is used by default, so it works behind NAT without a public URL.
With an HTTPS `PUBLIC_URL` you can use `TELEGRAM_MODE=webhook` + `TELEGRAM_WEBHOOK_SECRET`.

## Hosted (paid) mode

Set `BILLING_ENABLED=true` to run it as a SaaS: sign-ups get the Free plan, limits are enforced
and the landing page with pricing is served at `/`.

| Plan | Price | AI answers / month | Knowledge sources | Branding |
|---|---|---|---|---|
| Free | $0 | 100 | 5 | “Powered by” badge |
| Starter | $19 | 1,000 | 25 | badge |
| Pro | $49 | 5,000 | 100 | removed |
| Business | $99 | 20,000 | 500 | removed |

Plans live in [`app/plans.py`](app/plans.py). Payments:

* **Paddle Billing** (card payments worldwide, Paddle is the merchant of record and handles VAT/sales tax).
  Set `PADDLE_*` variables and add a webhook destination `https://YOUR-DOMAIN/api/billing/paddle/webhook`
  for `subscription.*` events. Upgrades/downgrades are applied automatically.
* **Bank transfer / invoice**: the platform owner sets a plan and an expiry date on the **Platform** page.

Production deploy with HTTPS (Caddy): see [`deploy/docker-compose.prod.yml`](deploy/docker-compose.prod.yml).

### Transparency — no hidden fees

* The self-hosted version has **no limits, no fees and no phone-home**. Nothing in the code sends money or data to the author.
* The optional success fee (`PLATFORM_FEE_PERCENT`, default `0`) is **shown to customers** on the pricing page and in their billing page, computed only from leads the customer marks as “Won”.
* The “Powered by” link can be disabled on self-hosted installs with `SHOW_BADGE=false`.

## Architecture

```
app/
  main.py              FastAPI app, static files, CORS for the widget API
  config.py            all settings (env variables)
  models.py            SQLAlchemy models (SQLite by default, PostgreSQL via DATABASE_URL)
  plans.py             plans, quotas, usage
  services/
    ingest.py          PDF / HTML / FAQ → chunks
    netguard.py        SSRF-safe fetching for website import
    search.py          BM25 keyword search (+ optional embeddings)
    llm.py             Anthropic / OpenAI-compatible / Ollama clients
    chat.py            answer pipeline, handoff-aware message handling
    telegram.py        connect, notify, reply-to-answer, polling / webhook
    billing.py         Paddle webhook verification & plan mapping
    analytics.py
  routers/             auth, admin API, public widget API, webhooks, platform admin
  static/widget.js     embeddable widget (vanilla JS, Shadow DOM)
  static/admin/        dashboard (vanilla JS, no build step)
  static/landing/      marketing page for the hosted version
tests/                 pytest suite (no network needed)
```

Run the tests: `pip install -r requirements-dev.txt && pytest`.

Run one worker process (the default in Docker): rate limits, the search cache and Telegram polling are in-process.

## API

Interactive docs at `/api/docs`. The public widget API:

| Method | Path | |
|---|---|---|
| GET | `/api/widget/{key}/config` | widget texts, colors, flags |
| POST | `/api/widget/{key}/messages` | `{visitor_id, conversation_id?, text, lang?}` → bot reply |
| GET | `/api/widget/{key}/conversations/{id}?visitor_id=&after=` | poll for operator replies |
| POST | `/api/widget/{key}/handoff` | ask for a human |
| POST | `/api/widget/{key}/leads` | leave contact details |

## Roadmap

- [ ] WhatsApp / Instagram / Facebook Messenger channels
- [ ] Booking & order forms with payment links (BOG / TBC / Paddle)
- [ ] pgvector for large knowledge bases, scheduled website re-sync
- [ ] Streaming answers, file attachments
- [ ] Team members & roles, Alembic migrations

## License

[AGPL-3.0](LICENSE). You can use, modify and self-host it for free, including commercially.
If you offer a modified version as a network service, you must publish your changes under the same license.
