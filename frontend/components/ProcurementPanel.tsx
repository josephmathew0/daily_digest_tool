"use client";

import { useState } from "react";
import { api, ProcurementDraftResponse, ProcurementForecast } from "@/services/api";

type Props = {
  projectId: string;
  phase: string;
  forecast: ProcurementForecast | null;
};

export function ProcurementPanel({ projectId, phase, forecast }: Props) {
  const [recipientEmail, setRecipientEmail] = useState("lojosephmathew@gmail.com");
  const [draft, setDraft] = useState<ProcurementDraftResponse | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [loadingItemId, setLoadingItemId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sendStatus, setSendStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!forecast) return null;

  async function draftEmail(itemId: string) {
    setLoadingItemId(itemId);
    setSelectedItemId(itemId);
    setDraft(null);
    setSendStatus(null);
    setError(null);
    try {
      const response = await api.procurementDraftEmail(projectId, phase, itemId, recipientEmail.trim());
      if (!response.enabled) {
        setError(response.disabled_reason || "Procurement email drafting is not enabled.");
      } else {
        setDraft(response);
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Unable to draft procurement email.");
    } finally {
      setLoadingItemId(null);
    }
  }

  async function sendEmail() {
    if (!draft?.subject || !draft.body) return;
    setSending(true);
    setError(null);
    setSendStatus(null);
    try {
      const response = await api.procurementSendEmail(draft.recipient_email, draft.subject, draft.body);
      if (!response.sent) {
        setError(response.disabled_reason || "Gmail sending is not enabled.");
      } else {
        setSendStatus(`Sent to ${response.recipient_email}${response.message_id ? ` (${response.message_id})` : ""}`);
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Unable to send procurement email.");
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="rounded border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Request Quote / Draft Procurement Email</p>
          <h2 className="mt-1 text-lg font-semibold">Predicted stock requirements</h2>
        </div>
        <span className="rounded border border-line px-2 py-1 text-xs text-slate-600">
          {forecast.gmail_send_configured ? "Gmail send ready" : "Gmail send disabled"}
        </span>
      </div>

      <p className="mt-2 text-sm leading-6 text-slate-700">
        Suggested from current blockers, supplier signals, validation needs, and readiness risks. This is a demo request
        workflow; no purchase is placed from the dashboard.
      </p>

      <div className="mt-4 grid gap-3">
        {forecast.items.length ? (
          forecast.items.map((item) => (
            <article key={item.id} className="rounded border border-line p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="text-sm font-semibold">{item.title}</h3>
                <span className="rounded border border-line px-2 py-1 text-xs text-slate-500">
                  {item.related_entity_ids.length} related item{item.related_entity_ids.length === 1 ? "" : "s"}
                </span>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-700">{item.reason}</p>
              <p className="mt-2 text-sm font-medium text-slate-700">{item.suggested_action}</p>
              <button
                type="button"
                className="mt-3 rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
                disabled={loadingItemId !== null}
                onClick={() => draftEmail(item.id)}
              >
                {loadingItemId === item.id ? "Drafting..." : "Draft Email"}
              </button>
            </article>
          ))
        ) : (
          <p className="rounded border border-dashed border-line p-3 text-sm text-slate-500">
            No procurement needs are predicted from the current project state.
          </p>
        )}
      </div>

      <div className="mt-4 rounded border border-line bg-panel p-3">
        <label className="text-xs font-semibold uppercase text-slate-500" htmlFor="procurement-recipient">
          Demo recipient
        </label>
        <input
          id="procurement-recipient"
          className="mt-2 w-full rounded border border-line bg-white p-2 text-sm text-slate-700"
          onChange={(event) => setRecipientEmail(event.target.value)}
          value={recipientEmail}
        />
        <p className="mt-2 text-xs text-slate-500">
          This step only drafts the email. Sending will be added after the preview is working.
        </p>
        {error && <p className="mt-2 text-sm text-danger">{error}</p>}
        {draft && (
          <div className="mt-3 rounded border border-line bg-white p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs font-semibold uppercase text-slate-500">Email Draft</p>
              {selectedItemId && (
                <span className="rounded border border-line px-2 py-0.5 text-xs text-slate-500">
                  {selectedItemId}
                </span>
              )}
            </div>
            <p className="mt-2 text-sm text-slate-600">To: {draft.recipient_email}</p>
            <p className="mt-2 text-sm font-semibold text-slate-800">Subject: {draft.subject}</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{draft.body}</p>
            <button
              type="button"
              className="mt-3 rounded bg-teal-700 px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={!forecast.gmail_send_configured || sending}
              onClick={sendEmail}
            >
              {sending ? "Sending..." : "Send Email"}
            </button>
            {!forecast.gmail_send_configured && (
              <p className="mt-2 text-xs text-slate-500">
                Set GMAIL_SEND_ENABLED=true and re-authorize Gmail with send scope to enable sending.
              </p>
            )}
            {sendStatus && <p className="mt-2 text-sm text-teal-700">{sendStatus}</p>}
          </div>
        )}
      </div>
    </section>
  );
}
