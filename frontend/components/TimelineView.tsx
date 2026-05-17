import type { EventPayload } from "@/services/api";

function preview(text: string) {
  if (text.length <= 900) return text;
  return `${text.slice(0, 900)}...`;
}

function EvidenceItem({ event, muted = false }: { event: EventPayload; muted?: boolean }) {
  return (
    <article className="border-b border-line pb-3 last:border-b-0">
      <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500">
        <span>{event.source_type} / {event.source_ref}</span>
        <span>{new Date(event.timestamp).toLocaleString()}</span>
      </div>
      <div className="mt-1 flex flex-wrap items-start justify-between gap-2">
        <p className={`min-w-0 break-words text-sm font-medium ${muted ? "text-slate-500" : "text-slate-900"}`}>
          {event.title || event.author_name}
        </p>
        {event.relevance_reason && (
          <span className="rounded border border-line px-2 py-0.5 text-xs text-slate-500">
            {event.relevance_reason}
          </span>
        )}
      </div>
      <p className={`mt-1 min-w-0 overflow-hidden break-words text-sm leading-5 ${muted ? "text-slate-500" : "text-slate-700"}`}>
        {preview(event.text)}
      </p>
    </article>
  );
}

export function TimelineView({ events }: { events: EventPayload[] }) {
  // Evidence is newest-first so users can verify the latest Slack/Gmail update
  // immediately after clicking Sync Sources.
  const newestFirst = events.slice().reverse();
  const relevantEvents = newestFirst.filter((event) => event.is_relevant !== false);
  const ignoredEvents = newestFirst.filter((event) => event.is_relevant === false);

  return (
    <section>
      <h2 className="mb-2 text-base font-semibold">Source Evidence</h2>
      <div className="grid max-h-[520px] gap-2 overflow-auto rounded border border-line bg-white p-3">
        {relevantEvents.map((event) => (
          <EvidenceItem key={event.id} event={event} />
        ))}
        {ignoredEvents.length > 0 && (
          // Ignored events stay visible but collapsed for auditability; this is
          // useful when explaining why acknowledgements or account emails were skipped.
          <details className="pt-1">
            <summary className="cursor-pointer text-sm font-medium text-slate-600">
              Ignored source events ({ignoredEvents.length})
            </summary>
            <div className="mt-3 grid gap-3 border-t border-line pt-3">
              {ignoredEvents.map((event) => (
                <EvidenceItem key={event.id} event={event} muted />
              ))}
            </div>
          </details>
        )}
      </div>
    </section>
  );
}
