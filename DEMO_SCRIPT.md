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
   - Section ordering: blocked, pending, and active items appear before resolved items; score orders items within each lifecycle group
   - Status strip: summary mode, extraction mode, model, persisted event/entity counts, last sync time, and digest generated time
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

## Lifecycle Update Test

Send this message in the Slack project channel:

```text
Update: Priya released the aluminum bracket PO after confirming the final BOM. The supplier confirmed the inventory slot, so the bracket procurement action item is resolved.
```

Expected behavior after **Sync Sources**:

- `Waiting on finalized BOM before placing bracket order` should become `resolved`
- The card should show a `Resolved` timestamp
- `Connector clearance depends on final motor mount CAD` should remain `blocked`
- The bracket update should not overwrite the connector/CAD dependency summary

This demonstrates entity lifecycle tracking: the system updates the durable project state instead of only adding a new message.

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

## Hybrid LLM Extraction Demo

Only use this when you want to spend API credits. Keep this off for normal development.

Set:

```env
EXTRACTION_MODE=hybrid
SUMMARY_MODE=rules
OPENAI_MODEL=gpt-5-mini
```

Restart:

```bash
docker compose down
docker compose up --build
```

Send this Slack message:

```text
The latest thermal chamber run looks acceptable after firmware current limiting. Alex says EVT reliability validation can resume tomorrow.
```

Expected behavior after **Sync Sources**:

- The app should use rules first.
- Because the wording is more ambiguous than a direct `resolved` message, hybrid mode may use OpenAI extraction.
- The thermal/PCB reliability item should move toward `resolved` or appear as a resolved thermal risk update.
- The extraction cache should prevent repeated OpenAI calls for the same unchanged message.

Switch back after the demo:

```env
EXTRACTION_MODE=rules
```

## Reviewer Talking Points

- The app normalizes Slack, Gmail, mock data, and manual entries into the same event shape.
- Relevance filtering happens before extraction to reduce noise and future LLM cost.
- Extraction and digest results are cached using hashes and fingerprints.
- OpenAI is optional and has rule-based fallback behavior.
- Hybrid extraction calls OpenAI only for relevant, uncertain events and caches the result.
- Digest sections are lifecycle-aware: unresolved operational work appears before recently resolved items.
- After a Docker restart, the status strip derives event/entity counts from SQLite even before the first sync in that process.
- The UI exposes ignored events so filtering is explainable.
- The project demonstrates an architecture path toward production, even though it intentionally remains a local prototype.
