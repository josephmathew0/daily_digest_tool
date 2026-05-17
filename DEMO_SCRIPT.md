# Demo Script

This script is for an assessment walkthrough of EverCurrent Daily Digest.

## Before the Demo

Use low-cost defaults unless you intentionally want OpenAI summaries:

```env
EXTRACTION_MODE=rules
SUMMARY_MODE=rules
SLACK_SOURCE=both
EMAIL_SOURCE=both
```

Start the app:

```bash
docker compose up --build
```

Open http://localhost:3000.

## Baseline Walkthrough

1. Select `Warehouse Robot V2`.
2. Select Maya or Alex.
3. Click **Sync Sources**.
4. Point out:
   - Team-wide summary
   - Role-specific digest sections
   - Severity/status/score badges
   - Source Evidence
   - Ignored source events and reasons

## Slack Test Message

Send this message in the Slack project channel:

```text
The PCB thermal rise is still 12C above EVT target. Firmware tuning reduced peak current slightly, but reliability validation remains blocked until Alex confirms the connector envelope and thermal margin.
```

Expected behavior after **Sync Sources**:

- Appears as relevant Slack source evidence
- Shows up as a risk/blocker for electrical engineering and engineering management
- Should mention PCB thermal, EVT reliability, connector envelope, or thermal margin

## Low-Signal Slack Message

Send:

```text
Acknowledged.
```

Expected behavior after **Sync Sources**:

- Appears under ignored source events
- Reason should be `short acknowledgement`
- Should not appear as an active blocker or risk

## Gmail Test Email

Send an email to the configured Gmail account.

Subject:

```text
Warehouse robot bracket lead time risk
```

Body:

```text
The aluminum bracket supplier moved the confirmed lead time from 1 week to 3 weeks. This may affect the customer demo milestone unless the PO is approved today.
```

Expected behavior after **Sync Sources**:

- Appears as relevant email source evidence
- Shows as a supply-chain risk or dependency
- Should be more relevant for supply chain, engineering manager, and product manager roles

## Manual Event Test

Use the Add Communication Event form:

```text
Decision: proceed with revised motor mount CAD and spacer adjustment. Maya owns the CAD update, and Alex must validate connector clearance by Friday.
```

Expected behavior:

- Appears as a decision/action item
- Owner and deadline language should influence digest relevance
- Mechanical and electrical roles should both have some relevance

## OpenAI Summary Demo

Only use this when you want to spend API credits.

Set:

```env
SUMMARY_MODE=openai
OPENAI_MODEL=gpt-5-mini
```

Restart:

```bash
docker compose down
docker compose up --build
```

Expected behavior:

- Team-wide summary should read like a natural project status paragraph
- It should not start with the rule-template sentence:

```text
11 active execution items are tracked...
```

Switch back after the demo:

```env
SUMMARY_MODE=rules
```

## Reviewer Talking Points

- The app normalizes Slack, Gmail, mock data, and manual entries into the same event shape.
- Relevance filtering happens before extraction to reduce noise and future LLM cost.
- Extraction and digest results are cached using hashes and fingerprints.
- OpenAI is optional and has rule-based fallback behavior.
- The UI exposes ignored events so filtering is explainable.
- The project demonstrates an architecture path toward production, even though it intentionally remains a local prototype.
