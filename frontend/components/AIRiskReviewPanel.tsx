"use client";

import { useState } from "react";
import { api, RiskReview } from "@/services/api";

export function AIRiskReviewPanel({ projectId, phase, review }: { projectId: string; phase: string; review: RiskReview | null }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!review) return null;

  async function askQuestion() {
    if (!question.trim() || !review) return;
    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const response = await api.riskReviewQuestion(projectId, phase, question.trim());
      if (!response.enabled) {
        setError(response.disabled_reason || "AI follow-up is not enabled.");
      } else {
        setAnswer(response.answer || "No answer was generated.");
      }
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Unable to ask AI.");
    } finally {
      setLoading(false);
    }
  }

  const canAsk = review.ai_followup_enabled && question.trim().length > 0 && !loading;

  return (
    <section className="rounded border border-line bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">AI Risk Review</p>
          <h2 className="mt-1 text-lg font-semibold">Suggested hardware risk checks</h2>
        </div>
        <span className="rounded border border-line px-2 py-1 text-xs text-slate-600">
          {review.ai_followup_enabled ? "Ask AI enabled" : "Ask AI disabled"}
        </span>
      </div>

      <div className="mt-4 grid gap-3">
        {review.checks.map((check) => (
          <article key={check.id} className="rounded border border-line p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <h3 className="text-sm font-semibold">{check.title}</h3>
              {check.related_entity_ids.length > 0 && (
                <span className="rounded border border-line px-2 py-0.5 text-xs text-slate-500">
                  {check.related_entity_ids.length} related
                </span>
              )}
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-700">{check.why_it_matters}</p>
            <p className="mt-2 rounded bg-panel px-3 py-2 text-xs leading-5 text-slate-700">
              {check.suggested_question}
            </p>
          </article>
        ))}
      </div>

      <div className="mt-4 rounded border border-line bg-panel p-3">
        <label className="text-xs font-semibold uppercase text-slate-500" htmlFor="ai-risk-question">
          Ask a follow-up
        </label>
        <textarea
          id="ai-risk-question"
          className="mt-2 h-20 w-full resize-y rounded border border-line bg-white p-3 text-sm text-slate-700"
          disabled={!review.ai_followup_enabled}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={
            review.ai_followup_enabled
              ? "Example: What should we verify before releasing the bracket PO?"
              : review.disabled_reason || "OpenAI follow-up is not enabled."
          }
          value={question}
        />
        <button
          className="mt-2 rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-slate-400"
          disabled={!canAsk}
          onClick={askQuestion}
          type="button"
        >
          {loading ? "Asking..." : "Ask AI"}
        </button>
        {error && <p className="mt-2 text-sm text-danger">{error}</p>}
        {answer && (
          <div className="mt-3 rounded border border-line bg-white p-3">
            <p className="text-xs font-semibold uppercase text-slate-500">AI Answer</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-700">{answer}</p>
          </div>
        )}
      </div>
    </section>
  );
}
