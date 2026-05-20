import type { BuildReadiness, ReadinessItem } from "@/services/api";

const statusClass: Record<string, string> = {
  blocked: "border-danger text-danger",
  at_risk: "border-warn text-warn",
  ready: "border-signal text-signal"
};

const statusLabel: Record<string, string> = {
  blocked: "Blocked",
  at_risk: "At Risk",
  ready: "Ready"
};

const groups: Array<{ key: keyof BuildReadiness; label: string }> = [
  { key: "blockers", label: "Blockers" },
  { key: "risks", label: "Risks" },
  { key: "missing_confirmations", label: "Missing Confirmations" },
  { key: "resolved", label: "Resolved / Improving" }
];

function ReadinessList({ items }: { items: ReadinessItem[] }) {
  if (!items.length) {
    return <p className="text-xs text-slate-500">None identified</p>;
  }

  return (
    <ul className="grid gap-2">
      {items.slice(0, 3).map((item) => (
        <li key={item.entity_id} className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="min-w-0 text-xs font-semibold text-slate-900">{item.title}</p>
            <span className="rounded border border-line px-1.5 py-0.5 text-[11px] text-slate-500">{item.status}</span>
          </div>
          <p className="mt-1 text-xs leading-5 text-slate-600">{item.summary}</p>
        </li>
      ))}
    </ul>
  );
}

export function BuildReadinessPanel({ readiness }: { readiness: BuildReadiness | null }) {
  if (!readiness) return null;

  return (
    <section className="rounded border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Build Readiness</p>
          <h2 className="mt-1 text-lg font-semibold">{readiness.phase.replace("_", " ")} milestone</h2>
        </div>
        <span className={`rounded border px-3 py-1 text-sm font-semibold ${statusClass[readiness.status] || statusClass.at_risk}`}>
          {statusLabel[readiness.status] || readiness.status}
        </span>
      </div>

      <p className="mt-2 text-sm leading-6 text-slate-700">{readiness.summary}</p>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {groups.map(({ key, label }) => (
          <div key={key} className="rounded border border-line p-3">
            <h3 className="mb-2 text-xs font-semibold uppercase text-slate-500">{label}</h3>
            <ReadinessList items={readiness[key] as ReadinessItem[]} />
          </div>
        ))}
      </div>
    </section>
  );
}
