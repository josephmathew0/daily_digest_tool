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
- Rule-based extraction by default
- Optional OpenAI summaries through `SUMMARY_MODE=openai`
- OpenAI fallback behavior so API failures do not break the app
- Hybrid extraction infrastructure for future LLM-assisted extraction
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
  -> Digest Cache
  -> Role-aware Digest API
  -> Next.js Dashboard
```

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
cd backend
python scripts/authorize_gmail.py
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
```

For cleaner demos, use a Gmail label and set:

```env
EMAIL_REQUIRE_LABEL=true
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
7. Open Source Evidence and confirm ignored events are separated with reasons.
8. Add a manual communication event or send a Slack/Gmail test message.
9. Click **Sync Sources** again and verify the digest updates.
10. Optional: switch `SUMMARY_MODE=openai`, restart Docker, and compare the OpenAI summary against the rule summary.

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
- Role-aware digest generation
- CI-backed tests and build checks

## Remaining Work

- Turn on and polish hybrid LLM extraction for uncertain relevant events
- Improve entity lifecycle tracking for resolved and updated items
- Add visible system status in the UI, including mode, last sync time, and fallback state
- Add stronger production auth and tenant isolation
- Add queue-based ingestion for larger-scale traffic
- Move from SQLite to PostgreSQL for production persistence
