const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

// These TypeScript shapes mirror the FastAPI response models. Keeping them
// explicit makes UI changes safer when backend fields are added for the demo.
export type User = {
  id: string;
  name: string;
  role: string;
};

export type Project = {
  id: string;
  name: string;
  phase: string;
  milestone: string;
};

export type EventPayload = {
  id: string;
  source_type: "slack" | "email" | "meeting";
  source_ref: string;
  author_name?: string;
  author_email?: string;
  author_role?: string;
  title?: string;
  text: string;
  timestamp: string;
  project: string;
  metadata?: Record<string, unknown>;
  is_relevant?: boolean;
  relevance_score?: number;
  relevance_reason?: string;
  relevance_category?: string;
};

export type DigestItem = {
  entity: {
    id: string;
    entity_type: string;
    title: string;
    summary: string;
    status: string;
    severity: string;
    owner?: string;
    created_at: string;
    updated_at: string;
    resolved_at?: string;
    due_date?: string;
    supporting_events: string[];
  };
  score: number;
  why_this_matters: string[];
  latest_update: string;
};

export type Digest = {
  project: string;
  user_id: string;
  user_name: string;
  role: string;
  phase: string;
  team_summary: string;
  generated_at?: string;
  cache_hit: boolean;
  sections: Record<string, DigestItem[]>;
};

export type ReadinessItem = {
  entity_id: string;
  title: string;
  summary: string;
  status: string;
  severity: string;
  updated_at: string;
  supporting_events: string[];
};

export type BuildReadiness = {
  project: string;
  phase: string;
  status: "ready" | "at_risk" | "blocked";
  summary: string;
  blockers: ReadinessItem[];
  risks: ReadinessItem[];
  resolved: ReadinessItem[];
  missing_confirmations: ReadinessItem[];
  generated_at: string;
};

export type RiskCheck = {
  id: string;
  title: string;
  why_it_matters: string;
  suggested_question: string;
  related_entity_ids: string[];
};

export type RiskReview = {
  project: string;
  phase: string;
  openai_configured: boolean;
  ai_followup_enabled: boolean;
  disabled_reason?: string;
  checks: RiskCheck[];
};

export type RiskQuestionResponse = {
  enabled: boolean;
  answer?: string;
  disabled_reason?: string;
};

export type SystemStatus = {
  summary_mode: string;
  extraction_mode: string;
  openai_model?: string;
  openai_configured: boolean;
  last_sync_at?: string;
  events: number;
  relevant_events: number;
  ignored_events: number;
  entities: number;
  extracted: number;
  reused_extractions: number;
  skipped_irrelevant: number;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {})
    }
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
}

export const api = {
  users: () => request<User[]>("/users"),
  projects: () => request<Project[]>("/projects"),
  events: (project: string) => request<EventPayload[]>(`/events?project=${project}`),
  sync: () => request<{ events: number; relevant_events: number; ignored_events: number; entities: number }>("/sync", { method: "POST" }),
  systemStatus: () => request<SystemStatus>("/system-status"),
  readiness: (project: string, phase: string) =>
    request<BuildReadiness>(`/readiness?project=${project}&phase=${phase}`),
  riskReview: (project: string, phase: string) =>
    request<RiskReview>(`/risk-review?project=${project}&phase=${phase}`),
  riskReviewQuestion: (project: string, phase: string, question: string) =>
    request<RiskQuestionResponse>("/risk-review/question", {
      method: "POST",
      body: JSON.stringify({ project, phase, question })
    }),
  digest: (project: string, userId: string, phase: string) =>
    request<Digest>(`/digest?project=${project}&user_id=${userId}&phase=${phase}`),
  addEvent: (event: EventPayload) =>
    request<{ created: string }>("/events", { method: "POST", body: JSON.stringify(event) })
};
