import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { BrandLogo } from "@/components/BrandLogo";
import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/context/AuthContext";
import LoginPage from "@/pages/LoginPage";
import SignupPage from "@/pages/SignupPage";
import ResetPasswordPage from "@/pages/ResetPasswordPage";
import DashboardPage from "@/pages/DashboardPage";
import RegisterCreationPage from "@/pages/RegisterCreationPage";
import TimelinePage from "@/pages/TimelinePage";
import RegistrationDetailPage from "@/pages/RegistrationDetailPage";
import IdeasPage from "@/pages/IdeasPage";
import IdeaDetailPage from "@/pages/IdeaDetailPage";
import ProvenancePage from "@/pages/ProvenancePage";
import TeamsPage from "@/pages/TeamsPage";
import TeamDetailPage from "@/pages/TeamDetailPage";
import TransfersPage from "@/pages/TransfersPage";
import DisputesPage from "@/pages/DisputesPage";
import DisputeDetailPage from "@/pages/DisputeDetailPage";
import AnonymousVerificationPage from "@/pages/AnonymousVerificationPage";
import PublicAnonymousVerifyPage from "@/pages/PublicAnonymousVerifyPage";
import AdminPage from "@/pages/AdminPage";
import OrganizationPage from "@/pages/OrganizationPage";
import JoinOrganizationPage from "@/pages/JoinOrganizationPage";
import AlertsPage from "@/pages/AlertsPage";
import NotificationsPage from "@/pages/NotificationsPage";
import AuditLogsPage from "@/pages/AuditLogsPage";
import IntegrityCenterPage from "@/pages/IntegrityCenterPage";
import SettingsPage from "@/pages/SettingsPage";
import PublicVerifyPage from "@/pages/PublicVerifyPage";
import PublicRecordsPage from "@/pages/PublicRecordsPage";
import NotFoundPage from "@/pages/NotFoundPage";
import LandingPage from "@/pages/LandingPage";

function FullPageLoader() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background">
      <BrandLogo className="size-12 rounded-2xl shadow-lg ring-1 ring-white/10" />
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="size-3 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />
        Restoring your workspace session
      </div>
    </div>
  );
}

function ProtectedShell() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullPageLoader />;
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname, reason: "Sign in to open that workspace page." }} />;
  }
  return <AppShell />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/verify/:verificationId" element={<PublicVerifyPage />} />
      <Route path="/verify" element={<PublicAnonymousVerifyPage />} />
      <Route path="/join" element={<JoinOrganizationPage />} />
      <Route path="/records" element={<PublicRecordsPage />} />

      <Route element={<ProtectedShell />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/register" element={<RegisterCreationPage />} />
        <Route path="/timeline" element={<TimelinePage />} />
        <Route path="/registrations/:id" element={<RegistrationDetailPage />} />
        <Route path="/ideas" element={<IdeasPage />} />
        <Route path="/ideas/:ideaRef" element={<IdeaDetailPage />} />
        <Route path="/provenance" element={<ProvenancePage />} />
        <Route path="/teams" element={<TeamsPage />} />
        <Route path="/teams/:id" element={<TeamDetailPage />} />
        <Route path="/transfers" element={<TransfersPage />} />
        <Route path="/disputes" element={<DisputesPage />} />
        <Route path="/disputes/:id" element={<DisputeDetailPage />} />
        <Route path="/anonymous-verification" element={<AnonymousVerificationPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/audit-logs" element={<AuditLogsPage />} />
        <Route path="/integrity" element={<IntegrityCenterPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/organization" element={<OrganizationPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
