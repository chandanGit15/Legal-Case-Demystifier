import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { AppLayout } from "./layouts/AppLayout";
import { CaseLayout } from "./layouts/CaseLayout";
import { Loading } from "./components/ui";
import { LandingPage } from "./pages/LandingPage";
import { PrivacyPage } from "./pages/PrivacyPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { DashboardPage } from "./pages/DashboardPage";
import { CasesPage } from "./pages/CasesPage";
import { CasePickerPage } from "./pages/CasePickerPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ActionPlanPage } from "./pages/case/ActionPlanPage";
import { AssistantPage } from "./pages/case/AssistantPage";
import { DocumentsPage } from "./pages/case/DocumentsPage";
import { EvidencePage } from "./pages/case/EvidencePage";
import { IssuesPage } from "./pages/case/IssuesPage";
import { NegotiationPage } from "./pages/case/NegotiationPage";
import { OverviewPage } from "./pages/case/OverviewPage";
import { RisksPage } from "./pages/case/RisksPage";
import { ScenariosPage } from "./pages/case/ScenariosPage";
import { TimelinePage } from "./pages/case/TimelinePage";

function Protected({ children }: { children: React.ReactNode }) {
  const { user, initializing } = useAuth();
  if (initializing) return <div className="page-wide"><Loading label="Loading workspace…" /></div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/privacy" element={<PrivacyPage />} />
      <Route path="/" element={<Protected><AppLayout /></Protected>}>
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="cases" element={<CasesPage />} />
        <Route path="documents" element={<CasePickerPage section="documents" />} />
        <Route path="assistant" element={<CasePickerPage section="assistant" />} />
        <Route path="risk-center" element={<CasePickerPage section="risks" />} />
        <Route path="scenarios" element={<CasePickerPage section="scenarios" />} />
        <Route path="negotiation" element={<CasePickerPage section="negotiation" />} />
        <Route path="action-plan" element={<CasePickerPage section="action-plan" />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="cases/:caseId" element={<CaseLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="timeline" element={<TimelinePage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="issues" element={<IssuesPage />} />
          <Route path="risks" element={<RisksPage />} />
          <Route path="scenarios" element={<ScenariosPage />} />
          <Route path="negotiation" element={<NegotiationPage />} />
          <Route path="evidence" element={<EvidencePage />} />
          <Route path="assistant" element={<AssistantPage />} />
          <Route path="action-plan" element={<ActionPlanPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}