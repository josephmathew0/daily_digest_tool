# EverCurrent Daily Digest

EverCurrent Daily Digest is an execution-intelligence prototype for hardware engineering teams. It ingests fragmented Slack messages, Gmail emails, meeting notes, and manual communication events, normalizes them into a shared event model, extracts durable project entities, and generates role-aware digests.

The core idea is entity-centric memory. Slack and email are evidence sources; the product output is an evolving view of project risks, blockers, decisions, dependencies, action items, and milestones.

## Current Capabilities

- Full-stack app with FastAPI backend and Next.js frontend
- Docker Compose setup for local demo
- Mock Slack, email, and meeting data
- Real Slack channel ingestion through a bot token
- Real Gmail inbox/sent ingestion through OAuth
- Gmail keyword, sender, and optional label filtering
- Normalized `CommunicationEvent` model across all sources
- SQLite persistence for events, extractions, merged entities, and digest cache
- Hash-based extraction cache to avoid reprocessing unchanged events
- Relevance filtering for low-value messages and account/marketing emails
- UI visibility for ignored source events and relevance reasons
- UI system status for modes, persisted counts, last sync time, and digest generation time
- Rule-based extraction by default
- Rule-based entity lifecycle tracking for resolved, still-blocked, and updated items
- Lifecycle-aware digest ordering: blocked, pending, and active items before resolved items
- Build Readiness panel for milestone-level blockers, risks, confirmations, and improving items
- AI Risk Review with hardware-specific suggested checks
- Optional AI Risk Review follow-up questions through `AI_RISK_REVIEW_ENABLED=true`
- Procurement forecast for likely quote/stock needs based on current project state
- OpenAI-generated request-for-quote email drafts from forecasted procurement items
- Optional Gmail send flow for reviewed procurement drafts through `GMAIL_SEND_ENABLED=true`
- Optional OpenAI summaries through `SUMMARY_MODE=openai`
- Optional hybrid OpenAI extraction for relevant, uncertain events
- OpenAI fallback behavior so API failures do not break the app
- GitHub Actions CI for backend tests, frontend build, and Compose validation

## Architecture

```text
Slack / Gmail / Mock JSON / Manual Event
  -> Source Connectors
  -> Normalized CommunicationEvent
  -> Relevance Filter
  -> SQLite Event Store
  -> Extraction Cache
  -> Rule / Hybrid / OpenAI Extraction
  -> Entity Merge + Project State
  -> Digest Cache / Readiness / Risk Review / Procurement Forecast
  -> Role-aware Digest + Action APIs
  -> Next.js Dashboard
```

The application stores two related layers of state:

- Raw normalized events: Slack, Gmail, meeting, mock, and manual messages preserved as source evidence.
- Extracted project entities: durable risks, blockers, decisions, dependencies, action items, and milestones derived from those events.

This separation lets the app keep an audit trail while generating a clean digest from project state instead of re-reading every raw message on every page load.

## Tech Stack

- Backend: Python, FastAPI, Pydantic
- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Storage: SQLite for prototype persistence
- Integrations: Slack Web API, Gmail API, OpenAI API
- Infrastructure: Docker Compose
- CI: GitHub Actions

## Setup

Copy the backend env template:

```bash
cp backend/.env.example backend/.env
```

Run the app:

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

To stop:

```bash
docker compose down
```

## Environment Variables

Important backend settings live in `backend/.env`.

```env
SLACK_SOURCE=mock
EMAIL_SOURCE=mock
EXTRACTION_MODE=rules
SUMMARY_MODE=rules
OPENAI_MODEL=gpt-5-mini
OPENAI_API_KEY=
AI_RISK_REVIEW_ENABLED=false
GMAIL_SEND_ENABLED=false
```

Source mode options:

- `mock`: use local mock data only
- `real`: use the real connector only
- `both`: combine mock and real data

Extraction modes:

- `rules`: local rule-based extraction, no OpenAI extraction cost
- `hybrid`: rules first, OpenAI for uncertain relevant events
- `openai`: OpenAI-first extraction with rule fallback

Summary modes:

- `rules`: local deterministic summary, no OpenAI summary cost
- `openai`: OpenAI-generated team-wide summary with rule fallback

For cost control during normal development, use:

```env
EXTRACTION_MODE=rules
SUMMARY_MODE=rules
```

For OpenAI summary demos, use:

```env
EXTRACTION_MODE=rules
SUMMARY_MODE=openai
OPENAI_MODEL=gpt-5-mini
OPENAI_API_KEY=your_api_key_here
```

Do not commit `backend/.env`, Gmail credentials, Gmail token files, or database files.

## Slack Setup

1. Create or open a Slack workspace.
2. Create a project channel, for example `#warehouse-robot-v2`.
3. Create a Slack app at https://api.slack.com/apps.
4. Add bot scopes needed for reading channel history, such as `channels:history` and `channels:read`.
5. Install the app to the workspace.
6. Invite the bot to the project channel.
7. Add these values to `backend/.env`:

```env
SLACK_SOURCE=both
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=...
SLACK_CHANNEL_NAME=warehouse-robot-v2
```

## Gmail Setup

1. Create a Google Cloud project.
2. Enable the Gmail API.
3. Configure the OAuth consent screen for a desktop/local development app.
4. Create OAuth client credentials and download them as `gmail_credentials.json`.
5. Place `gmail_credentials.json` in `backend/`.
6. Run the authorization helper:

```bash
backend/.venv/bin/python backend/scripts/authorize_gmail.py
```

This creates `gmail_token.json`. Both files are ignored by Git.

Typical Gmail settings:

```env
EMAIL_SOURCE=both
EMAIL_PROVIDER=gmail
EMAIL_ACCOUNT=josephtestemail0@gmail.com
EMAIL_INCLUDE_SENT=true
EMAIL_LOOKBACK_DAYS=14
EMAIL_REQUIRE_LABEL=false
EMAIL_GMAIL_LABEL=EverCurrent/Warehouse-Robot-V2
GMAIL_SEND_ENABLED=false
```

For cleaner demos, use a Gmail label and set:

```env
EMAIL_REQUIRE_LABEL=true
```

The procurement demo can draft quote-request emails with OpenAI. To send the reviewed draft through Gmail, set:

```env
GMAIL_SEND_ENABLED=true
```

Then rerun `backend/.venv/bin/python backend/scripts/authorize_gmail.py` so `gmail_token.json` includes the Gmail send scope. The dashboard send button remains disabled until Gmail sending is explicitly enabled.

If you are already inside the `backend/` directory, run:

```bash
.venv/bin/python scripts/authorize_gmail.py
```

## OpenAI Setup

OpenAI is optional. The app works without it.

Add a key only when you want OpenAI-generated summaries or hybrid extraction:

```env
SUMMARY_MODE=openai
OPENAI_MODEL=gpt-5-mini
OPENAI_API_KEY=your_api_key_here
```

The app has fallback behavior. If the API key, model, quota, or network is unavailable, the backend falls back to rule-based summaries or extraction instead of failing the request.

For hybrid extraction demos:

```env
EXTRACTION_MODE=hybrid
SUMMARY_MODE=rules
OPENAI_MODEL=gpt-5-mini
OPENAI_API_KEY=your_api_key_here
```

Hybrid extraction runs rules first and only uses OpenAI when the rule result is missing or low-confidence. Extraction results are cached by event hash, mode, version, and model.

For AI Risk Review follow-up questions and procurement email drafting, keep a valid `OPENAI_API_KEY` and use:

```env
AI_RISK_REVIEW_ENABLED=true
```

The static AI Risk Review checks and procurement forecast still work without this flag. The flag controls the interactive OpenAI follow-up behavior.

## Ordering and Caching

Digest items are sorted inside each section by lifecycle first:

1. `blocked`
2. `pending`
3. `active`
4. `resolved`

Within each lifecycle group, higher role/phase relevance scores appear first. Resolved items remain visible because they explain recent state changes and help reviewers verify that updates were merged into existing project entities.

Caching happens at two levels:

- Extraction cache: keyed by event content hash, extraction mode, extractor version, and model.
- Digest cache: keyed by project entity fingerprint, user, phase, summary mode, model, and digest cache version.

This keeps repeated syncs and page refreshes cheap while still invalidating stale results when source content or configuration changes.

## Common Commands

Backend tests:

```bash
cd backend
./.venv/bin/pytest
```

Backend compile check:

```bash
python3 -m compileall backend/app backend/tests
```

Frontend build:

```bash
cd frontend
npm run build
```

Docker Compose validation:

```bash
docker compose config
```

## Demo Flow

1. Start Docker.
2. Open http://localhost:3000.
3. Select `Warehouse Robot V2`.
4. Switch between roles such as Maya, Alex, Priya, Sam, and Jordan.
5. Click **Sync Sources**.
6. Review the team-wide summary and role-specific sections.
7. Review **Build Readiness** for milestone blockers, risks, missing confirmations, and improving items.
8. Review **AI Risk Review** for hardware-specific risk checks.
9. Review **Request Quote / Draft Procurement Email** for forecasted procurement needs.
10. Click **Draft Email** on a predicted procurement item and confirm the email preview appears.
11. Open Source Evidence and confirm ignored events are separated with reasons.
12. Add a manual communication event or send a Slack/Gmail test message.
13. Click **Sync Sources** again and verify the digest updates.
14. Optional: switch `SUMMARY_MODE=openai`, restart Docker, and compare the OpenAI summary against the rule summary.
15. Optional: enable `GMAIL_SEND_ENABLED=true`, re-authorize Gmail, restart Docker, and test sending a reviewed procurement draft.

See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for exact messages and expected behavior.

## API

- `GET /health`
- `GET /users`
- `GET /projects`
- `GET /events?project=warehouse_robot_v2`
- `POST /events`
- `POST /sync`
- `GET /digest?project=warehouse_robot_v2&user_id=maya&phase=prototype`

## Assessment Notes

The prototype is designed to demonstrate:

- Source integration across Slack and Gmail
- Normalization before processing
- Cheap filtering before expensive LLM calls
- Caching to avoid repeated extraction and summary work
- Human-readable relevance explanations
- Optional OpenAI usage with fallback
- State changes that update existing project entities instead of only appending messages
- Hybrid LLM extraction for ambiguous but relevant communication events
- Lifecycle-aware ordering so active operational work appears before resolved items
- Persisted status counts after backend restart, so the UI does not show zero events when SQLite already has data
- Role-aware digest generation
- CI-backed tests and build checks

## Remaining Work

- Add stronger production auth and tenant isolation
- Add queue-based ingestion for larger-scale traffic
- Move from SQLite to PostgreSQL for production persistence
- Add background workers for scheduled source polling and larger batch processing
- Add admin controls for source permissions, retention policies, and per-project access scope
