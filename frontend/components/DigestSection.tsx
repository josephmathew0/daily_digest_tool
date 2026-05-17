import type { DigestItem } from "@/services/api";

const severityClass: Record<string, string> = {
  critical: "border-danger text-danger",
  high: "border-warn text-warn",
  medium: "border-signal text-signal",
  low: "border-slate-400 text-slate-600"
};

function formatTimestamp(value?: string) {
  if (!value) return null;
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

function lifecycleTimestamps(item: DigestItem) {
  const timestamps = [
    `Updated: ${formatTimestamp(item.entity.updated_at)}`,
    `Created: ${formatTimestamp(item.entity.created_at)}`
  ];
  if (item.entity.resolved_at) {
    timestamps.unshift(`Resolved: ${formatTimestamp(item.entity.resolved_at)}`);
  }
  if (item.entity.due_date) {
    timestamps.unshift(`Due: ${formatTimestamp(item.entity.due_date)}`);
  }
  return timestamps.filter((value) => !value.endsWith("null"));
}

export function DigestSection({ title, items }: { title: string; items: DigestItem[] }) {
  if (!items.length) return null;

  return (
    <section>
      <h2 className="mb-2 text-base font-semibold">{title}</h2>
      <div className="grid gap-3">
        {items.map((item) => (
          <article key={item.entity.id} className="rounded border border-line bg-white p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="max-w-2xl text-sm font-semibold">{item.entity.title}</h3>
              <div className="flex gap-2 text-xs font-semibold">
                <span className={`rounded border px-2 py-1 ${severityClass[item.entity.severity] || severityClass.low}`}>{item.entity.severity}</span>
                <span className="rounded border border-line px-2 py-1 text-slate-600">{item.entity.status}</span>
                <span className="rounded border border-line px-2 py-1 text-slate-600">score {item.score}</span>
              </div>
            </div>
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
              {lifecycleTimestamps(item).map((timestamp) => (
                <span key={timestamp}>{timestamp}</span>
              ))}
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{item.latest_update}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {item.why_this_matters.map((reason) => (
                <span key={reason} className="rounded bg-panel px-2 py-1 text-xs text-slate-700">{reason}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
