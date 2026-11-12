import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  Database,
  FileWarning,
  Fingerprint,
  Gavel,
  LayoutList,
  ScrollText,
  ShieldCheck,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader, ErrorState, LoadingBlock, EmptyState } from "@/components/common/page-states";
import { StatCard } from "@/components/common/stat-card";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, extractErrorMessage } from "@/lib/api";
import { formatBytes, formatDate, relativeTime, titleCase } from "@/lib/format";

interface AdminOverview {
  stats: Record<string, number>;
  ledger: { mode: string; label?: string; network?: string };
  recent_users: AdminUser[];
  recent_disputes: AdminDispute[];
  recent_audit: AuditRow[];
}

interface AdminUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  account_type: string;
  organization_id: string | null;
  is_active: boolean;
  is_demo: boolean;
  created_at: string | null;
  last_login_at: string | null;
  registrations?: number;
}

interface AdminDispute {
  id: string;
  dispute_ref: string;
  registration_id: string;
  registration_label?: string | null;
  registration_title?: string | null;
  claimant_name?: string | null;
  respondent_name?: string | null;
  reason: string;
  status: string;
  resolution?: string | null;
  created_at: string;
}

interface AuditRow {
  id: string;
  action: string;
  entity_type?: string | null;
  entity_id?: string | null;
  actor_ref?: string | null;
  created_at: string;
}

interface AdminOrganization {
  id: string;
  name: string;
  slug: string;
  plan: string;
  owner_name?: string | null;
  members: number;
  active_members: number;
  registrations: number;
  pending_invitations: number;
}

interface AdminRegistration {
  id: string;
  registration_id: string;
  title: string;
  owner_name?: string | null;
  organization_id: string | null;
  asset_type: string;
  privacy: string;
  status: string;
  file_size: number;
  registered_at: string | null;
}

interface AdminTeam {
  id: string;
  name: string;
  owner_name?: string | null;
  organization_id: string | null;
  status: string;
  created_at: string | null;
}

const ROLES = ["creator", "verifier", "org_member", "org_admin", "site_admin"];

export default function AdminPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const overview = useQuery({ queryKey: ["admin-overview"], queryFn: () => api.get<AdminOverview>("/admin/overview") });
  const users = useQuery({
    queryKey: ["admin-users", search],
    queryFn: () => api.get<{ items: AdminUser[]; total: number }>(`/admin/users?page_size=50${search ? `&q=${encodeURIComponent(search)}` : ""}`),
  });
  const disputes = useQuery({
    queryKey: ["admin-disputes"],
    queryFn: () => api.get<{ items: AdminDispute[]; total: number }>("/admin/disputes?page_size=50"),
  });
  const organizations = useQuery({
    queryKey: ["admin-organizations"],
    queryFn: () => api.get<{ items: AdminOrganization[] }>("/admin/organizations"),
  });
  const registrations = useQuery({
    queryKey: ["admin-registrations"],
    queryFn: () => api.get<{ items: AdminRegistration[]; total: number }>("/admin/registrations?page_size=50"),
  });
  const teams = useQuery({
    queryKey: ["admin-teams"],
    queryFn: () => api.get<{ items: AdminTeam[] }>("/admin/teams"),
  });
  const audit = useQuery({
    queryKey: ["admin-audit"],
    queryFn: () => api.get<{ items: AuditRow[] }>("/admin/audit?page_size=60"),
  });

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-"] });
  };

  const updateUser = async (user: AdminUser, patch: Partial<AdminUser>) => {
    setBusyId(user.id);
    try {
      await api.patch(`/admin/users/${user.id}`, patch);
      toast.success("Account updated");
      refreshAll();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusyId(null);
    }
  };

  const updateDispute = async (dispute: AdminDispute, status: string) => {
    setBusyId(dispute.id);
    try {
      const resolution =
        status === "resolved"
          ? window.prompt("Resolution summary for this dispute", "Resolved by site administration after reviewing the evidence trail.")
          : undefined;
      if (status === "resolved" && !resolution) {
        setBusyId(null);
        return;
      }
      await api.patch(`/admin/disputes/${dispute.id}`, { status, resolution });
      toast.success("Dispute updated");
      refreshAll();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusyId(null);
    }
  };

  if (overview.isLoading) return <LoadingBlock rows={8} />;
  if (overview.isError || !overview.data) {
    return <ErrorState error={overview.error} onRetry={() => overview.refetch()} />;
  }

  const stats = overview.data.stats;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Site administration"
        title="Website control center"
        description="Accounts, disputes, organizations, teams, registrations, and the audit trail for the whole deployment."
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Accounts" value={stats.users} hint={`${stats.active_users} active · ${stats.suspended_users} suspended`} icon={<Users className="size-4" />} />
        <StatCard label="Organizations" value={stats.organizations} hint={`${stats.teams} team projects`} tone="blue" icon={<Building2 className="size-4" />} />
        <StatCard label="Registrations" value={stats.registrations} hint={`${stats.organization_registrations} organization owned`} tone="green" icon={<Fingerprint className="size-4" />} />
        <StatCard label="Open disputes" value={stats.open_disputes} hint={`${stats.disputes} total · ${stats.resolved_disputes} resolved`} tone="amber" icon={<Gavel className="size-4" />} />
        <StatCard label="Open alerts" value={stats.open_alerts} hint={`${stats.alerts} theft alerts`} tone="amber" icon={<FileWarning className="size-4" />} />
        <StatCard label="Ledger records" value={stats.ledger_transactions} hint={`${titleCase(overview.data.ledger.mode)} ledger`} tone="violet" icon={<Database className="size-4" />} />
        <StatCard label="Verified proofs" value={stats.verified_proofs} hint="Cryptographically accepted" tone="green" icon={<ShieldCheck className="size-4" />} />
        <StatCard label="Pending org invites" value={stats.pending_org_invitations} hint="Not yet accepted" tone="blue" icon={<LayoutList className="size-4" />} />
      </div>

      <Tabs defaultValue="users">
        <TabsList className="h-auto flex-wrap">
          <TabsTrigger value="users"><Users /> Accounts</TabsTrigger>
          <TabsTrigger value="disputes"><Gavel /> Disputes</TabsTrigger>
          <TabsTrigger value="organizations"><Building2 /> Organizations</TabsTrigger>
          <TabsTrigger value="registrations"><Fingerprint /> Registrations</TabsTrigger>
          <TabsTrigger value="teams"><LayoutList /> Teams</TabsTrigger>
          <TabsTrigger value="audit"><ScrollText /> Audit</TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-3">
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by email or display name"
            className="max-w-sm"
          />
          {users.isLoading && <LoadingBlock rows={5} />}
          <div className="space-y-2">
            {users.data?.items.map((user) => (
              <div key={user.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 bg-card/60 p-3">
                <div className="min-w-0">
                  <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                    {user.display_name}
                    <Badge variant={user.role === "site_admin" ? "violet" : "outline"}>{titleCase(user.role)}</Badge>
                    {!user.is_active && <Badge variant="red">Suspended</Badge>}
                    {user.is_demo && <Badge variant="slate">Demo</Badge>}
                  </p>
                  <p className="truncate text-[11px] text-muted-foreground">
                    {user.email} · {user.registrations ?? 0} registrations · last login {user.last_login_at ? relativeTime(user.last_login_at) : "never"}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={user.role}
                    disabled={busyId === user.id}
                    onChange={(event) => updateUser(user, { role: event.target.value as AdminUser["role"] })}
                    className="h-8 rounded-lg border border-border bg-background px-2 text-[11px]"
                    aria-label={`Role for ${user.email}`}
                  >
                    {ROLES.map((role) => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                  <Button size="sm" variant="outline" loading={busyId === user.id} onClick={() => updateUser(user, { is_active: !user.is_active })}>
                    {user.is_active ? "Suspend" : "Reactivate"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="disputes" className="space-y-2">
          {disputes.isLoading && <LoadingBlock rows={4} />}
          {disputes.data?.items.map((dispute) => (
            <div key={dispute.id} className="rounded-xl border border-border/70 bg-card/60 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                  {dispute.dispute_ref}
                  <StatusBadge status={dispute.status} />
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" loading={busyId === dispute.id} onClick={() => updateDispute(dispute, "under_review")}>
                    Take review
                  </Button>
                  <Button size="sm" variant="success" loading={busyId === dispute.id} onClick={() => updateDispute(dispute, "resolved")}>
                    Resolve
                  </Button>
                </div>
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">
                {dispute.reason} · {dispute.registration_label || "—"} · claimant {dispute.claimant_name || "unknown"} · respondent {dispute.respondent_name || "none"}
              </p>
              <p className="text-[10px] text-muted-foreground">Opened {formatDate(dispute.created_at)}</p>
            </div>
          ))}
        </TabsContent>

        <TabsContent value="organizations" className="space-y-2">
          {organizations.data?.items.map((organization) => (
            <div key={organization.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 bg-card/60 p-3">
              <div>
                <p className="text-sm font-medium">{organization.name}</p>
                <p className="text-[11px] text-muted-foreground">
                  {organization.active_members}/{organization.members} members · {organization.registrations} registrations · {organization.pending_invitations} pending invites · owner {organization.owner_name || "—"}
                </p>
              </div>
              <Badge variant="outline">{titleCase(organization.plan)}</Badge>
            </div>
          ))}
        </TabsContent>

        <TabsContent value="registrations" className="space-y-2">
          {registrations.data?.items.map((registration) => (
            <div key={registration.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 bg-card/60 p-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{registration.title}</p>
                <p className="truncate text-[11px] text-muted-foreground">
                  {registration.registration_id} · {registration.owner_name || "unknown"} · {formatBytes(registration.file_size)} · {titleCase(registration.asset_type)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {registration.organization_id && <Badge variant="blue">Organization</Badge>}
                <StatusBadge status={registration.status} />
              </div>
            </div>
          ))}
        </TabsContent>

        <TabsContent value="teams" className="space-y-2">
          {teams.data?.items.map((team) => (
            <div key={team.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 bg-card/60 p-3">
              <div>
                <p className="text-sm font-medium">{team.name}</p>
                <p className="text-[11px] text-muted-foreground">Owner {team.owner_name || "—"} · created {formatDate(team.created_at)}</p>
              </div>
              <StatusBadge status={team.status} />
            </div>
          ))}
        </TabsContent>

        <TabsContent value="audit" className="space-y-1">
          {audit.data?.items.map((entry) => (
            <div key={entry.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/60 px-3 py-2 text-[11px]">
              <span className="font-medium">{entry.action}</span>
              <span className="text-muted-foreground">{entry.actor_ref || "system"} · {entry.entity_type || "—"} · {formatDate(entry.created_at)}</span>
            </div>
          ))}
          {!audit.data?.items.length && <EmptyState title="No audit entries" description="The audit chain is empty." icon={<ScrollText className="size-5" />} />}
        </TabsContent>
      </Tabs>
    </div>
  );
}
