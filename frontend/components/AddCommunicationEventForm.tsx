"use client";

import { Plus } from "lucide-react";
import { FormEvent, useState } from "react";
import type { EventPayload } from "@/services/api";

type Props = {
  projectId: string;
  onAdd: (event: EventPayload) => Promise<void>;
};

export function AddCommunicationEventForm({ projectId, onAdd }: Props) {
  const [sourceType, setSourceType] = useState<EventPayload["source_type"]>("slack");
  const [text, setText] = useState("");
  const [author, setAuthor] = useState("Sam Ortiz");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;

    await onAdd({
      id: `ui_${Date.now()}`,
      source_type: sourceType,
      source_ref: sourceType === "slack" ? "#robotics-prototype" : "Manual entry",
      author_name: author,
      author_role: "engineering_manager",
      title: sourceType === "meeting" ? "Manual Meeting Summary" : undefined,
      text,
      timestamp: new Date().toISOString(),
      project: projectId
    });
    setText("");
  }

  return (
    <form className="rounded border border-line bg-white p-4" onSubmit={submit}>
      <div className="grid gap-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="text-sm font-medium">
            Source
            <select className="mt-1 w-full rounded border border-line px-3 py-2" value={sourceType} onChange={(event) => setSourceType(event.target.value as EventPayload["source_type"])}>
              <option value="slack">Slack</option>
              <option value="email">Email</option>
              <option value="meeting">Meeting Summary</option>
            </select>
          </label>
          <label className="text-sm font-medium">
            Author
            <input className="mt-1 w-full rounded border border-line px-3 py-2" value={author} onChange={(event) => setAuthor(event.target.value)} />
          </label>
        </div>
        <textarea
          className="min-h-28 rounded border border-line px-3 py-2 text-sm"
          placeholder="Example: Action item: Alex validates connector clearance by Friday. PCB thermal risk still affects EVT readiness."
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <button className="inline-flex w-fit items-center gap-2 rounded bg-signal px-4 py-2 text-sm font-semibold text-white">
          <Plus size={16} /> Add Event
        </button>
      </div>
    </form>
  );
}
