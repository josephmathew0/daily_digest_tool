import type { EventPayload } from "@/services/api";

export function TimelineView({ events }: { events: EventPayload[] }) {
  return (
    <section>
      <h2 className="mb-2 text-base font-semibold">Source Evidence</h2>
      <div className="grid max-h-[520px] gap-2 overflow-auto rounded border border-line bg-white p-3">
        {events.slice().reverse().map((event) => (
          <article key={event.id} className="border-b border-line pb-3 last:border-b-0">
            <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500">
              <span>{event.source_type} / {event.source_ref}</span>
              <span>{new Date(event.timestamp).toLocaleString()}</span>
            </div>
            <p className="mt-1 text-sm font-medium">{event.title || event.author_name}</p>
            <p className="mt-1 text-sm leading-5 text-slate-700">{event.text}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
