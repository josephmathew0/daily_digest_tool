# EverCurrent Daily Digest

EverCurrent is an AI-ready execution intelligence system for hardware engineering teams. It continuously constructs project memory from fragmented Slack, email, and meeting-summary communication, then generates role-aware operational digests.

This is not a Slack summarizer. Slack, emails, and meetings are treated as evidence. The durable product object is the evolving project entity: issue, risk, decision, dependency, action item, or milestone.

## Architecture

```text
Slack / Emails / Meeting Summaries
  -> Source Connectors
  -> Normalized CommunicationEvent
  -> Entity Extraction
  -> Project Memory / State Tracking
  -> Dependency + Relevance Scoring
  -> Role/Phase-aware Digest
  -> Frontend Dashboard
```

## Stack

- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Backend: Python, FastAPI, Pydantic
- Storage: mock JSON files for the prototype
- Infrastructure: Docker Compose

## Entity-Centric Design

All sources normalize into `CommunicationEvent`. Downstream services never depend on Slack APIs, email formats, or meeting-summary formats.

The extractor converts communication into `ProjectEntity` records:

- issues
- risks
- decisions
- dependencies
- action items
- milestones

The merger compresses repeated discussion into one evolving entity with supporting event IDs.

## Project Memory

The prototype models three memory layers:

- Active context: unresolved blockers, active risks, pending decisions, and dependencies
- Recent changes: resolved issues and milestone changes
- Long-term memory: major decisions and high-impact recurring issues

## Relevance Scoring

Digest ranking combines:

- role relevance
- project phase relevance
- severity
- urgency and unresolved status
- dependency impact
- recency
- source signal strength

Each digest item includes `why_this_matters` explanations.

## Run With Docker

```bash
docker compose up
```

Then open:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## Run Locally

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Demo Walkthrough

1. Select `Warehouse Robot V2`.
2. Switch between Maya, Alex, Priya, Sam, and Jordan.
3. Change the project phase from `prototype` to `EVT` or `PVT`.
4. Observe that the same communication data produces different digest rankings.
5. Add a new communication event from the form.
6. Sync sources and inspect the updated digest and source evidence.

## API

- `GET /users`
- `GET /projects`
- `GET /events`
- `POST /events`
- `POST /sync`
- `GET /digest?user_id=maya&phase=prototype`

## Production Roadmap

- Real Slack Events API connector
- Gmail or Microsoft email connector
- Meeting transcription ingestion
- PostgreSQL and pgvector
- Redis-backed background sync jobs
- Scheduled digest delivery
- Semantic retrieval over long-term memory
- Feedback-based personalization
