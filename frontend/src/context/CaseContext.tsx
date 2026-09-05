/**
 * CaseDataContext — the single source of truth for a case workspace.
 *
 * Loads the aggregate GET /cases/:id/context bundle once and exposes every
 * module's collection (documents, timeline, issues, risks, gaps, scenarios,
 * evidence, actions, deadlines, negotiation prep) plus mutation helpers so no
 * component keeps its own copy of case state.
 *
 * Every AI output in future phases attaches to this same case id; refresh()
 * re-pulls the whole bundle so counts stay consistent everywhere.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api } from "../services/api";
import type {
  ActionItem,
  CaseContextData,
  CaseSummary,
  Deadline,
  DocumentInfo,
  EvidenceItem,
  InfoGap,
  LegalIssue,
  NegotiationPrep,
  RiskAssessment,
  RiskFactor,
  Scenario,
  TimelineEvent,
} from "../types";

export type CaseCollection =
  | "documents"
  | "timeline"
  | "issues"
  | "risks"
  | "gaps"
  | "scenarios"
  | "evidence"
  | "actions"
  | "deadlines";

interface CaseContextValue {
  caseId: string;
  /** True only while the first load is in flight. */
  loading: boolean;
  /** True while any refresh (initial or re-pull) is in flight. */
  refreshing: boolean;
  error: string | null;
  /** Full bundle (null until first load succeeds). */
  bundle: CaseContextData | null;
  caseData: CaseSummary | null;
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
  /** Phase-7 explainable risk analysis (or null before the first run). */
  riskAssessment: RiskAssessment | null;
  /** Replace the risk assessment from a POST /risk-analysis response. */
  setRiskAssessment: (assessment: RiskAssessment) => void;
  /** Re-fetch the whole bundle from the server. */
  refresh: () => Promise<void>;
  /** Replace the case object (used when a PATCH/PUT returns the full case). */
  setCaseData: (updated: CaseSummary) => void;
  /** Upsert an item into a collection from a server response. */
  upsert: <T extends { id: number }>(collection: CaseCollection, item: T) => void;
  /** Remove an item from a collection after a successful delete. */
  removeItem: (collection: CaseCollection, id: number) => void;
  /** Replace the negotiation prep object. */
  setPrep: (prep: NegotiationPrep) => void;
}

const CaseContext = createContext<CaseContextValue | null>(null);

export function CaseProvider({ caseId, children }: {
  caseId: string;
  children: React.ReactNode;
}) {
  const [bundle, setBundle] = useState<CaseContextData | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError(null);
    try {
      const data = await api.get<CaseContextData>(`/cases/${caseId}/context`);
      setBundle(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load the case workspace");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [caseId]);

  useEffect(() => {
    let cancelled = false;
    setBundle(null);
    setLoading(true);
    setError(null);
    api.get<CaseContextData>(`/cases/${caseId}/context`)
      .then((data) => { if (!cancelled) setBundle(data); })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load the case workspace"); })
      .finally(() => { if (!cancelled) { setLoading(false); setRefreshing(false); } });
    return () => { cancelled = true; };
  }, [caseId]);

  const value = useMemo<CaseContextValue>(() => {
    const collections = {
      documents: bundle?.documents ?? [],
      timeline: bundle?.timeline ?? [],
      issues: bundle?.issues ?? [],
      risks: bundle?.risks ?? [],
      gaps: bundle?.gaps ?? [],
      scenarios: bundle?.scenarios ?? [],
      evidence: bundle?.evidence ?? [],
      actions: bundle?.actions ?? [],
      deadlines: bundle?.deadlines ?? [],
    };
    return {
      caseId,
      loading,
      refreshing,
      error,
      bundle,
      caseData: bundle?.case ?? null,
      ...collections,
      prep: bundle?.prep ?? null,
      riskAssessment: bundle?.risk_assessment ?? null,
      setRiskAssessment: (assessment: RiskAssessment) =>
        setBundle((prev) => (prev ? { ...prev, risk_assessment: assessment } : prev)),
      refresh,
      setCaseData: (updated: CaseSummary) =>
        setBundle((prev) => (prev ? { ...prev, case: updated } : prev)),
      upsert: <T extends { id: number }>(collection: CaseCollection, item: T) =>
        setBundle((prev) => {
          if (!prev) return prev;
          const list = prev[collection] as unknown as { id: number }[];
          const next = [item, ...list.filter((x) => x.id !== item.id)] as never[];
          return { ...prev, [collection]: next } as CaseContextData;
        }),
      removeItem: (collection: CaseCollection, id: number) =>
        setBundle((prev) => {
          if (!prev) return prev;
          const list = prev[collection] as unknown as { id: number }[];
          const next = list.filter((x) => x.id !== id) as never[];
          return { ...prev, [collection]: next } as CaseContextData;
        }),
      setPrep: (prep: NegotiationPrep) =>
        setBundle((prev) => (prev ? { ...prev, prep } : prev)),
    };
  }, [bundle, caseId, loading, refreshing, error, refresh]);

  return <CaseContext.Provider value={value}>{children}</CaseContext.Provider>;
}

export function useCase(): CaseContextValue {
  const ctx = useContext(CaseContext);
  if (!ctx) throw new Error("useCase must be used inside a CaseProvider");
  return ctx;
}
