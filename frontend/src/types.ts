export interface User {
  id: number;
  email: string;
  name: string;
  default_country: string;
  default_state: string;
  language: string;
}

export interface CaseSummary {
  id: number;
  title: string;
  description: string;
  parties: string;
  case_type: string;
  country: string;
  state: string;
  jurisdiction: string;
  stage: string;
  status: string;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  counts?: {
    documents: number;
    documents_analyzed: number;
    timeline_events: number;
    issues: number;
    risks: number;
    scenarios: number;
    evidence_items: number;
    open_actions: number;
    upcoming_deadlines: number;
  };
  highest_risk?: string | null;
}

export interface DashboardData {
  kpis: {
    active_cases: number;
    documents_analyzed: number;
    pending_actions: number;
    upcoming_deadlines: number;
  };
  recent_cases: CaseSummary[];
  upcoming_deadlines: {
    id: number;
    title: string;
    due_date: string;
    days_left: number;
    status: string;
    case: { id: number; title: string };
  }[];
  action_required: {
    kind: string;
    title: string;
    detail: string;
    severity: string;
    case: { id: number; title: string };
  }[];
  analytics: {
    issues: { total: number; open: number; by_case: { case_id: number; title: string; open: number; total: number }[] };
    high_risk_factors: { title: string; level: string; case_id: number; case_title: string }[];
    risk_areas: {
      case_id: number; title: string; overall_score: number; overall_level: string;
      worst_dimension: string | null; worst_level: string | null;
      dimensions: { label: string; level: string; score: number }[];
    }[];
    evidence: {
      items: number; verified: number; unverified: number; disputed: number; verified_pct: number;
      by_case: { case_id: number; title: string; items: number; verified: number; verified_pct: number }[];
      issues_with_evidence: number; open_issues: number;
    };
    gaps: { open: number; high: number; medium: number; low: number };
    scenarios: { total: number; analyzed: number; comparable_cases: number };
    negotiation: {
      cases: number; prepped: number; plan_ready: number; active_cases: number;
      by_case: { case_id: number; title: string; has_prep: boolean; plan_ready: boolean }[];
    };
  };
  recent_ai_insights: {
    kind: string; title: string; confidence?: string; level?: string; priority?: string;
    detail?: string; created_at: string; case_id: number; case_title: string;
  }[];
}

export interface DemoCaseMeta {
  kind: string;
  title: string;
  case_type: string;
  jurisdiction: string;
  tagline: string;
  icon: string;
  stacks: {
    documents: number; timeline: number; issues: number; evidence: number;
    risks: number; scenarios: number; actions: number;
  };
}

export interface TimelineEvent {
  id: number;
  case_id: number;
  date: string;
  title: string;
  description: string;
  category: string;
  event_type?: string;
  importance?: string;
  date_status?: string;
  source: string;
  created_at?: string;
}

export interface LegalIssue {
  id: number;
  case_id: number;
  title: string;
  description: string;
  category: string;
  jurisdiction: string;
  confidence: string;
  provenance: string;
  status: string;
  supporting_facts?: string[];
  related_documents?: string[];
  missing_information?: string[];
  impact?: string;
  created_at: string;
}

export interface RiskFactor {
  id: number;
  case_id: number;
  title: string;
  description: string;
  likelihood: string;
  impact: string;
  overall_risk: string;
  mitigation: string;
  provenance: string;
  created_at: string;
}

export interface RiskDimension {
  key: string;
  label: string;
  score: number;
  level: string; // low | medium | high | critical
  reason: string;
  supporting_factors?: string[];
  mitigating_factors?: string[];
  recommended_action?: string;
}

export interface RiskAssessment {
  id: number;
  case_id: number;
  overall_score: number;
  overall_level: string;
  summary: string;
  dimensions: RiskDimension[];
  previous: {
    overall_score?: number;
    overall_level?: string;
    summary?: string;
    dimensions?: RiskDimension[];
  };
  note: string;
  created_at: string;
  updated_at: string;
}

export interface RiskChange {
  key: string;
  label: string;
  previous_level: string;
  current_level: string;
  direction: "improved" | "worsened";
}

export interface InfoGap {
  id: number;
  case_id: number;
  question: string;
  why_it_matters: string;
  priority: string;
  source: string;
  status: string;
  related_issue?: string;
  how_to_find?: string;
}

export interface ScenarioFact {
  text: string;
}

export interface ScenarioAnalysis {
  mode?: string;
  note?: string;
  outcome?: string;
  potential_issues?: string[];
  risk_changes?: string[];
  evidence_requirements?: string[];
  negotiation_leverage?: string[];
  next_steps?: string[];
  unknown_information?: string[];
  risks?: string[];
  opportunities?: string[];
  recommended_steps?: string[];
  key_unknowns?: string[];
  risk_level?: string;
}

export interface Scenario {
  id: number;
  case_id: number;
  name: string;
  description: string;
  parameters: string;
  facts?: ScenarioFact[];
  analysis: ScenarioAnalysis;
  risk_level: string;
  created_at: string;
}

export interface ScenarioComparison {
  columns: {
    id: string;
    name: string;
    summary: string;
    risk_level: string;
  }[];
  rows: Record<string, Partial<Record<ScenarioRowKey, string>>>;
  row_labels: Record<ScenarioRowKey, string>;
  trade_offs?: string;
  recommendation?: string;
  mode?: string;
  note?: string;
}

export type ScenarioRowKey =
  | "risk" | "evidence" | "issues" | "advantages" | "disadvantages"
  | "information_gaps" | "negotiation_position" | "next_steps";

export interface NegotiationPlan {
  opening_position?: string;
  key_arguments?: string[];
  supporting_evidence?: string[];
  likely_objections?: string[];
  responses?: string[];
  potential_concessions?: string[];
  walk_away?: string;
  questions_to_ask?: string[];
}

export interface NegotiationPrep {
  id: number;
  case_id: number;
  goals: string;
  batna: string;
  interests: string;
  concessions: string;
  red_lines: string;
  counterpart_analysis: string;
  strategy: string;
  // Phase-9 objective inputs.
  objective: string;
  desired_outcome: string;
  minimum_acceptable: string;
  key_evidence: string;
  counterpart_position: string;
  constraints: string;
  channel: string;
  // Phase-9 generated plan.
  plan: NegotiationPlan;
  updated_at: string;
}

export interface NegotiationMessage {
  subject?: string;
  message: string;
  talking_points?: string[];
  note?: string;
  mode?: string;
}

export interface SimulationMessage {
  role: "user" | "assistant";
  content: string;
  label?: string;
  note?: string;
}

export interface NegotiationEvaluation {
  scores: Record<string, number>;
  overall?: string;
  strengths?: string[];
  improvements?: string[];
  evidence_should_have_used?: string[];
  arguments_missed?: string[];
  potential_risks?: string[];
  alternative_responses?: string[];
  note?: string;
  mode?: string;
}

export interface NegotiationSession {
  id: number;
  case_id: number;
  user_id: number;
  opponent_position: string;
  language: string;
  status: "active" | "completed";
  messages: SimulationMessage[];
  evaluation: NegotiationEvaluation;
  created_at: string;
  updated_at: string;
}

export interface EvidenceItem {
  id: number;
  case_id: number;
  title: string;
  description: string;
  item_type: string;
  source: string;
  date: string | null;
  importance?: string;
  verification?: string;
  status: string;
  notes: string;
  provenance: string;
  related_issues?: { id: number; title: string }[];
  created_at?: string;
}

export interface ActionItem {
  id: number;
  case_id: number;
  title: string;
  description: string;
  priority: string;
  reason: string;
  related_issue: string;
  required_evidence: string;
  due_date: string | null;
  status: string; // not_started | in_progress | completed | skipped
  category: string;
}

export interface DeadlineCandidate {
  title: string;
  date: string;
  source: string;
  confidence: "extracted" | "potential";
  note?: string;
}

export interface Deadline {
  id: number;
  case_id: number;
  title: string;
  description: string;
  due_date: string;
  status: string;
  source: string;
}

export interface DocumentParty {
  name: string;
  role?: string;
}

export interface DocumentClause {
  quote?: string;
  meaning?: string;
  section?: string;
  reason?: string;
  severity?: string;
}

export interface DocumentDeadline {
  date?: string;
  title?: string;
  description?: string;
}

export interface DocumentObligation {
  party?: string;
  obligation?: string;
}

/** Structured findings produced by document analysis (AI, labeled). */
export interface DocumentAnalysis {
  summary?: string;
  document_type?: string;
  parties?: DocumentParty[];
  obligations?: DocumentObligation[];
  important_clauses?: DocumentClause[];
  concerning_clauses?: DocumentClause[];
  deadlines?: DocumentDeadline[];
  entities?: string[];
  warnings?: string[];
  key_facts?: { text?: string; source?: string; label?: string }[];
  dates_found?: { date?: string; description?: string }[];
  possible_issues?: { title?: string; category?: string; confidence?: string; basis?: string }[];
  information_gaps?: { question?: string; why_it_matters?: string }[];
  requires_verification?: string[];
  mode?: string;
  note?: string;
  disclaimer?: string;
  [key: string]: unknown;
}

export interface DocumentInfo {
  id: number;
  case_id: number;
  filename: string;
  file_type: string;
  mime_type: string;
  size_bytes: number;
  extraction_status: string;
  analysis_status: string;
  has_text: boolean;
  chunk_count: number;
  analysis: DocumentAnalysis;
  uploaded_at: string;
}

export interface DocumentContent {
  document_id: number;
  has_text: boolean;
  text_length: number;
  excerpt: string;
  excerpt_truncated: boolean;
  chunks: {
    id: number;
    document_id: number;
    chunk_index: number;
    content: string;
    token_count: number;
  }[];
  chunk_count: number;
}

export interface ChatSession {
  id: number;
  user_id: number;
  case_id: number;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatSource {
  type: string;
  label: string;
}

/** Structured CaseGuide payload stored on assistant messages. */
export interface ChatMeta {
  answer?: string;
  why_this_matters?: string;
  evidence_needed?: string[];
  potential_risk?: string;
  next_question?: string;
  recommended_next_step?: string;
  follow_up_suggestions?: string[];
  sources?: ChatSource[];
  labels?: string[];
  mode?: string;
  note?: string;
}

export interface ChatMessage {
  id: number;
  case_id: number;
  session_id?: number | null;
  role: string;
  content: string;
  provenance: {
    mode?: string;
    labels?: string[];
    note?: string;
    [key: string]: unknown;
  };
  meta: ChatMeta;
  language: string;
  created_at: string;
}

export interface ChatResponse {
  user_message: string;
  session: ChatSession;
  assistant: ChatMessage;
  result: {
    mode?: string;
    note?: string;
    [key: string]: unknown;
  };
}

export interface MessagesResponse {
  messages: ChatMessage[];
  session: ChatSession;
}

export interface AiResult {
  mode: string;
  note?: string;
  disclaimer?: string;
  [key: string]: unknown;
}

export type Provenance = "user" | "document" | "ai";

/** Aggregate workspace payload from GET /cases/:id/context. */
export interface CaseContextData {
  case: CaseSummary;
  documents: DocumentInfo[];
  timeline: TimelineEvent[];
  issues: LegalIssue[];
  risks: RiskFactor[];
  gaps: InfoGap[];
  scenarios: Scenario[];
  evidence: EvidenceItem[];
  actions: ActionItem[];
  deadlines: Deadline[];
  prep: NegotiationPrep | null;
  risk_assessment: RiskAssessment | null;
}