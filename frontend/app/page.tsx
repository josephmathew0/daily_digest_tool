"use client";

import { useEffect, useMemo, useState } from "react";
import { AddCommunicationEventForm } from "@/components/AddCommunicationEventForm";
import { Controls } from "@/components/Controls";
import { DigestSection } from "@/components/DigestSection";
import { Header } from "@/components/Header";
import { TimelineView } from "@/components/TimelineView";
import { api, Digest, EventPayload, Project, User } from "@/services/api";

export default function Home() {
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [events, setEvents] = useState<EventPayload[]>([]);
  const [digest, setDigest] = useState<Digest | null>(null);
  const [projectId, setProjectId] = useState("warehouse_robot_v2");
  const [userId, setUserId] = useState("maya");
  const [phase, setPhase] = useState("prototype");
  const [status, setStatus] = useState("Ready");

  const currentProject = useMemo(() => projects.find((project) => project.id === projectId), [projects, projectId]);

  async function refresh() {
    const [nextEvents, nextDigest] = await Promise.all([
      api.events(projectId),
      api.digest(projectId, userId, phase)
    ]);
    setEvents(nextEvents);
    setDigest(nextDigest);
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
    const result = await api.sync();
    setStatus(`Synced ${result.events} events into ${result.entities} project entities`);
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
            <p className="mt-3 text-sm text-slate-500">{status}</p>
          </section>

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
