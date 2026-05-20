"use client";

import { useEffect, useMemo, useState } from "react";
import { AddCommunicationEventForm } from "@/components/AddCommunicationEventForm";
import { AIRiskReviewPanel } from "@/components/AIRiskReviewPanel";
import { BuildReadinessPanel } from "@/components/BuildReadinessPanel";
import { Controls } from "@/components/Controls";
import { DigestSection } from "@/components/DigestSection";
import { Header } from "@/components/Header";
import { TimelineView } from "@/components/TimelineView";
import { api, BuildReadiness, Digest, EventPayload, Project, RiskReview, SystemStatus, User } from "@/services/api";

function formatTimestamp(value?: string) {
  if (!value) return "Not yet";
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  });
}

export default function Home() {
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [events, setEvents] = useState<EventPayload[]>([]);
  const [digest, setDigest] = useState<Digest | null>(null);
  const [readiness, setReadiness] = useState<BuildReadiness | null>(null);
  const [riskReview, setRiskReview] = useState<RiskReview | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [projectId, setProjectId] = useState("warehouse_robot_v2");
  const [userId, setUserId] = useState("maya");
  const [phase, setPhase] = useState("prototype");
  const [status, setStatus] = useState("Ready");

  const currentProject = useMemo(() => projects.find((project) => project.id === projectId), [projects, projectId]);

  async function refresh() {
    // Read-only refresh: reload source evidence, the role-specific digest, and
    // backend mode/count badges without forcing a new source sync.
    const [nextEvents, nextDigest, nextReadiness, nextRiskReview, nextSystemStatus] = await Promise.all([
      api.events(projectId),
      api.digest(projectId, userId, phase),
      api.readiness(projectId, phase),
      api.riskReview(projectId, phase),
      api.systemStatus()
    ]);
    setEvents(nextEvents);
    setDigest(nextDigest);
    setReadiness(nextReadiness);
    setRiskReview(nextRiskReview);
    setSystemStatus(nextSystemStatus);
  }

  useEffect(() => {
    async function load() {
      const [nextUsers, nextProjects] = await Promise.all([api.users(), api.projects()]);
      setUsers(nextUsers);
      setProjects(nextProjects);
    }
    load().catch((error) => setStatus(error.message));
  }, []);

  useEffect(() => {
    refresh().catch((error) => setStatus(error.message));
  }, [projectId, userId, phase]);

  async function sync() {
    // Sync Sources is the expensive refresh path. It pulls configured sources,
    // rebuilds extraction/entity state, then refreshes the UI from the backend.
    const result = await api.sync();
    setStatus(`Synced ${result.events} events (${result.ignored_events} ignored) into ${result.entities} project entities`);
    await refresh();
  }

  async function addEvent(event: EventPayload) {
    await api.addEvent(event);
    setStatus("Added event. Sync or regenerate to inspect updated state.");
    await sync();
  }

  return (
    <main>
      <Header />
      <Controls
        projects={projects}
        users={users}
        projectId={projectId}
        userId={userId}
        phase={phase}
        onProject={setProjectId}
        onUser={setUserId}
        onPhase={setPhase}
        onSync={sync}
      />

      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-5 lg:grid-cols-[1fr_380px]">
        <div className="grid gap-5">
          <section className="rounded border border-line bg-white p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">Team-wide Summary</p>
            <h2 className="mt-1 text-lg font-semibold">{currentProject?.name || "Warehouse Robot V2"}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-700">{digest?.team_summary || "Loading digest..."}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-600">
              {/* These badges make demo mode visible without opening .env. */}
              <span className="rounded border border-line px-2 py-1">Summary: {systemStatus?.summary_mode || "rules"}</span>
              <span className="rounded border border-line px-2 py-1">Extraction: {systemStatus?.extraction_mode || "rules"}</span>
              {systemStatus?.openai_model && (
                <span className="rounded border border-line px-2 py-1">Model: {systemStatus.openai_model}</span>
              )}
              <span className="rounded border border-line px-2 py-1">Events: {systemStatus?.events ?? events.length}</span>
              <span className="rounded border border-line px-2 py-1">Ignored: {systemStatus?.ignored_events ?? events.filter((event) => event.is_relevant === false).length}</span>
              <span className="rounded border border-line px-2 py-1">Entities: {systemStatus?.entities ?? 0}</span>
            </div>
            <div className="mt-3 grid gap-1 text-xs text-slate-500 sm:grid-cols-2">
              {/* Last sync is source ingestion time; digest generated is when the
                  current digest response was computed or read from cache. */}
              <p>Last sync: {formatTimestamp(systemStatus?.last_sync_at)}</p>
              <p>Digest generated: {formatTimestamp(digest?.generated_at)}{digest?.cache_hit ? " (cached)" : ""}</p>
            </div>
            <p className="mt-3 text-sm text-slate-500">{status}</p>
          </section>

          <BuildReadinessPanel readiness={readiness} />
          <AIRiskReviewPanel projectId={projectId} phase={phase} review={riskReview} />

          {digest && Object.entries(digest.sections).map(([section, items]) => (
            <DigestSection key={section} title={section} items={items} />
          ))}
        </div>

        <aside className="grid content-start gap-5">
          <section>
            <h2 className="mb-2 text-base font-semibold">Add Communication Event</h2>
            <AddCommunicationEventForm projectId={projectId} onAdd={addEvent} />
          </section>
          <TimelineView events={events} />
        </aside>
      </div>
    </main>
  );
}
