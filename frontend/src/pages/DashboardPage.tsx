import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity,
  ArrowLeftRight,
  ArrowUpRight,
  Boxes,
  CheckCircle2,
  FileCheck2,
  Fingerprint,
  Gavel,
  Lightbulb,
  PlusCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { PageHeader, ErrorState, LoadingBlock, EmptyState } from "@/components/common/page-states";
import { StatCard } from "@/components/common/stat-card";
import { StatusBadge, LedgerBadge } from "@/components/common/status-badge";
import { HashValue } from "@/components/common/hash-value";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { api } from "@/lib/api";
import type { AuditEntry, DashboardActivity, DashboardSummary, LedgerStatus } from "@/lib/types";
import { formatBytes, formatDate, humanizeAction, relativeTime, titleCase } from "@/lib/format";

const chartColors = ["#171717", "#B7FF00", "#454545", "#888888", "#D0D0D0", "#EAEAEA"];

interface AuditChain {
  valid: boolean;
  entries?: number;
  events?: number;
  records?: number;
  errors?: string[];
  message?: string;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const summary = useQuery({ queryKey: ["dashboard-summary"], queryFn: () => api.get<DashboardSummary>("/dashboard/summary") });
  const activity = useQuery({ queryKey: ["dashboard-activity"], queryFn: () => api.get<DashboardActivity>("/dashboard/activity") });
  const ledger = useQuery({ queryKey: ["ledger-status"], queryFn: () => api.get<LedgerStatus>("/ledger/status") });
  const audit = useQuery({ queryKey: ["audit-chain"], queryFn: () => api.get<AuditChain>("/audit-logs/verify") });

  if (summary.isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader eyebrow="Overview" title="Dashboard" description="Loading your workspace summary from the AUTHENTIQ backend." />
        <LoadingBlock rows={6} />
      </div>
    );
  }

  if (summary.isError || !summary.data) {
    return <ErrorState error={summary.error} onRetry={() => summary.refetch()} />;
  }

  const stats = summary.data.stats;
  const charts = summary.data.charts;
  const data = activity.data;
  const maxRegistrations = Math.max(1, ...charts.registrations_by_month.map((item) => item.registrations));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Overview"
        title="Ownership command center"
        description="Every figure below is computed from your authorized records. No fabricated statistics, no imaginary chain activity."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => { summary.refetch(); activity.refetch(); ledger.refetch(); audit.refetch(); }}>
              <RefreshCw /> Refresh
            </Button>
            <Button asChild variant="gradient" size="sm">
              <Link to="/register">
                <PlusCircle /> Register creation
              </Link>
            </Button>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total creations" value={stats.total_creations} hint="Fingerprinted records" icon={<Fingerprint className="size-4" />} onClick={() => navigate("/timeline")} />
        <StatCard label="Verified records" value={stats.verified_records} hint="Ownership proof or verifier confirmed" tone="green" icon={<CheckCircle2 className="size-4" />} onClick={() => navigate("/timeline")} />
        <StatCard label="Protected ideas" value={stats.protected_ideas} hint="Commitments without public disclosure" tone="violet" icon={<Lightbulb className="size-4" />} onClick={() => navigate("/ideas")} />
        <StatCard label="Team projects" value={stats.team_projects} hint="Shared ownership workspaces" tone="blue" icon={<Users className="size-4" />} onClick={() => navigate("/teams")} />
        <StatCard label="Pending transfers" value={stats.pending_transfers} hint="Awaiting recipient or owner action" tone="amber" icon={<FileCheck2 className="size-4" />} onClick={() => navigate("/transfers")} />
        <StatCard label="Incoming ownership" value={stats.incoming_ownership ?? 0} hint="Creations being handed to you" tone="amber" icon={<ArrowLeftRight className="size-4" />} onClick={() => navigate("/transfers")} />
        <StatCard label="Active disputes" value={stats.active_disputes} hint="Open, under review, or evidence requested" tone="amber" icon={<Gavel className="size-4" />} onClick={() => navigate("/disputes")} />
        <StatCard label="Security alerts" value={stats.security_alerts} hint="New or under investigation" tone="violet" icon={<ShieldCheck className="size-4" />} onClick={() => navigate("/alerts")} />
        <StatCard label="Verified proofs" value={stats.verified_proofs} hint={`${stats.active_shares} active silent shares`} tone="green" icon={<Sparkles className="size-4" />} onClick={() => navigate("/anonymous-verification")} />
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader className="flex-row items-start justify-between gap-3">
            <div>
              <CardTitle>Registration activity</CardTitle>
              <CardDescription>Real registrations recorded over the last six months.</CardDescription>
            </div>
            <Badge variant="outline">{stats.total_creations} total</Badge>
          </CardHeader>
          <CardContent>
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={charts.registrations_by_month} margin={{ left: -18, right: 8, top: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: "var(--chart-label)", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} domain={[0, maxRegistrations + 1]} tick={{ fill: "var(--chart-label)", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ background: "var(--chart-tooltip-bg)", border: "1px solid var(--chart-tooltip-border)", borderRadius: 10, fontSize: 12, color: "var(--chart-tooltip-text)" }}
                    labelStyle={{ color: "var(--chart-tooltip-text)" }}
                    itemStyle={{ color: "var(--chart-tooltip-text)" }}
                  />
                  <Area type="monotone" dataKey="registrations" stroke="var(--chart-line)" strokeWidth={2} fill="var(--chart-line)" fillOpacity={0.08} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Asset mix</CardTitle>
            <CardDescription>Distribution of your registered creations.</CardDescription>
          </CardHeader>
          <CardContent>
            {charts.asset_types.length ? (
              <div className="h-[260px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={charts.asset_types} dataKey="value" nameKey="name" innerRadius={54} outerRadius={86} paddingAngle={3} stroke="none">
                      {charts.asset_types.map((entry, index) => (
                        <Cell key={entry.name} fill={chartColors[index % chartColors.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ background: "var(--chart-tooltip-bg)", border: "1px solid var(--chart-tooltip-border)", borderRadius: 10, fontSize: 12, color: "var(--chart-tooltip-text)" }} itemStyle={{ color: "var(--chart-tooltip-text)" }} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="-mt-3 flex flex-wrap justify-center gap-x-3 gap-y-1">
                  {charts.asset_types.slice(0, 6).map((entry, index) => (
                    <span key={entry.name} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                      <span className="size-2 rounded-full" style={{ backgroundColor: chartColors[index % chartColors.length] }} />
                      {titleCase(entry.name)} · {entry.value}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <EmptyState title="No asset data yet" description="Register a creation to populate this chart." className="border-0 py-12" />
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-start justify-between gap-3">
          <div>
            <CardTitle>Creation cadence</CardTitle>
            <CardDescription>Each square is one day. Every registration, idea, version, and verified proof adds a mark.</CardDescription>
          </div>
          <Badge variant="outline">Last 26 weeks</Badge>
        </CardHeader>
        <CardContent>
          <ActivityHeatmap days={charts.activity_heatmap || []} />
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle>Recent creations</CardTitle>
              <CardDescription>Newest fingerprints in your workspace.</CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link to="/timeline">Open timeline <ArrowUpRight /></Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-2">
            {data?.recent_registrations?.length ? (
              data.recent_registrations.map((registration) => (
                <Link
                  key={registration.id}
                  to={`/registrations/${registration.id}`}
                  className="flex items-center gap-3 rounded-lg border border-border/60 bg-background/30 p-3 transition-colors hover:border-accent/50 hover:bg-accent/40"
                >
                  <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-foreground">
                    <Fingerprint className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-2 truncate text-sm font-medium">
                      {registration.title}
                      {registration.pending_ownership && (
                        <Badge variant="amber" className="shrink-0">
                          Incoming
                        </Badge>
                      )}
                    </p>
                    <p className="truncate text-[11px] text-muted-foreground">
                      {registration.registration_id} · {formatBytes(registration.file_size)} · {relativeTime(registration.registered_at)}
                      {registration.pending_ownership ? " · ownership pending confirmation" : ""}
                    </p>
                  </div>
                  <div className="hidden text-right sm:block">
                    <StatusBadge status={registration.pending_ownership ? "pending_recipient" : registration.status} />
                    <p className="mt-1 text-[10px] text-muted-foreground">{titleCase(registration.asset_type)}</p>
                  </div>
                </Link>
              ))
            ) : (
              <EmptyState
                title="No creations registered"
                description="Register a file to generate a real SHA-256 fingerprint, commitment, and ledger record."
                icon={<Fingerprint className="size-5" />}
                action={
                  <Button asChild size="sm">
                    <Link to="/register">Register your first creation</Link>
                  </Button>
                }
              />
            )}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Trust posture</CardTitle>
              <CardDescription>Live cryptographic state, not decoration.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between gap-3 rounded-lg border border-border/60 p-3">
                <div className="min-w-0">
                  <p className="text-xs font-medium">Ledger mode</p>
                  <p className="truncate text-[11px] text-muted-foreground">{ledger.data?.label || "Checking adapter"}</p>
                </div>
                <LedgerBadge mode={ledger.data?.mode} network={ledger.data?.network} />
              </div>
              <div className="flex items-center justify-between gap-3 rounded-lg border border-border/60 p-3">
                <div>
                  <p className="text-xs font-medium">Audit hash chain</p>
                  <p className="text-[11px] text-muted-foreground">
                    {audit.data ? `${audit.data.events ?? audit.data.records ?? audit.data.entries ?? 0} entries verified` : "Verifying"}
                  </p>
                </div>
                <Badge variant={audit.data?.valid ? "green" : audit.data ? "red" : "slate"}>
                  {audit.data?.valid ? "Intact" : audit.data ? "Check failed" : "Checking"}
                </Badge>
              </div>
              <div className="flex items-center justify-between gap-3 rounded-lg border border-border/60 p-3">
                <div>
                  <p className="text-xs font-medium">Ledger integrity</p>
                  <p className="text-[11px] text-muted-foreground">
                    {ledger.data?.database_records ?? 0} transactions · block {ledger.data?.block_number ?? 0}
                  </p>
                </div>
                <Badge variant={ledger.data?.tamper_detected === false ? "green" : ledger.data?.tamper_detected ? "red" : "slate"}>
                  {ledger.data?.tamper_detected === false ? "Intact" : ledger.data?.tamper_detected ? "Tampered" : "Unknown"}
                </Badge>
              </div>
              <p className="text-[10px] leading-relaxed text-muted-foreground">
                Simulation records are append-only locally and can be audited. They are not public blockchain transactions.
              </p>
              <Button asChild variant="outline" size="sm" className="w-full">
                <Link to="/audit-logs">Inspect audit trail</Link>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick actions</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-2">
              {(data?.quick_actions || []).map((action) => (
                <Link
                  key={action.path}
                  to={action.path}
                  className="flex flex-col gap-2 rounded-lg border border-border/60 p-3 text-xs font-medium transition-colors hover:border-accent/50 hover:bg-accent/40"
                >
                  <PlusCircle className="size-4 text-foreground" />
                  {action.label}
                </Link>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle>Ledger events</CardTitle>
              <CardDescription>Append-only records tied to your entities.</CardDescription>
            </div>
            <Activity className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-2">
            {data?.ledger_transactions?.length ? (
              data.ledger_transactions.map((transaction) => (
                <div key={transaction.id} className="rounded-lg border border-border/60 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-medium">{titleCase(transaction.tx_type)}</p>
                    <Badge variant="outline">Block {transaction.block_number}</Badge>
                  </div>
                  <p className="mt-1 truncate text-[11px] text-muted-foreground">
                    {transaction.entity_type} · {relativeTime(transaction.timestamp)}
                  </p>
                  <div className="mt-2">
                    <HashValue value={transaction.record_hash} label="Record hash" head={14} tail={10} />
                  </div>
                </div>
              ))
            ) : (
              <EmptyState title="No ledger events" description="Register or verify a creation to create an append-only event." className="border-0 py-8" />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle>Audit timeline</CardTitle>
              <CardDescription>Actions recorded against your identity and entities.</CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link to="/audit-logs">View all <ArrowUpRight /></Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-1">
            {data?.audit_timeline?.length ? (
              data.audit_timeline.slice(0, 7).map((entry: AuditEntry) => (
                <div key={entry.id} className="flex items-start gap-3 border-b border-border/50 py-2.5 last:border-0">
                  <span className="mt-1 size-1.5 shrink-0 rounded-full bg-blue-400" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium">{humanizeAction(entry.action)}</p>
                    <p className="truncate text-[11px] text-muted-foreground">
                      {entry.actor_ref} · {formatDate(entry.created_at, "MMM d, HH:mm")}
                    </p>
                  </div>
                  <HashValue value={entry.record_hash} label="Audit hash" head={6} tail={6} />
                </div>
              ))
            ) : (
              <EmptyState title="No audit entries" description="Authenticated actions appear here with a hash-chain commitment." className="border-0 py-8" />
            )}
          </CardContent>
        </Card>
      </div>

      {!!data?.alerts?.length && (
        <Alert variant="warning">
          <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span>
              {data.alerts.length} similarity alert{data.alerts.length === 1 ? "" : "s"} require review. Similarity is an investigation aid, not a finding of infringement.
            </span>
            <Button asChild size="sm" variant="outline">
              <Link to="/alerts">Review alerts</Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {!!data?.team_activity?.length && (
        <div className="flex flex-wrap gap-3">
          {data.team_activity.map((item) => (
            <Badge key={item.id} variant="outline" className="gap-2 py-1.5">
              <Users className="size-3" />
              {item.title}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function ActivityHeatmap({ days }: { days: { date: string; total: number }[] }) {
  if (!days.length) {
    return <p className="text-xs text-muted-foreground">No activity recorded yet.</p>;
  }
  const leading = new Date(`${days[0].date}T00:00:00`).getDay();
  const cells: ({ date: string; total: number } | null)[] = [
    ...Array.from({ length: leading }, () => null),
    ...days,
  ];
  const columns: ({ date: string; total: number } | null)[][] = [];
  for (let index = 0; index < cells.length; index += 7) {
    columns.push(cells.slice(index, index + 7));
  }
  const shade = (total: number) => {
    if (total === 0) return "bg-[#D0D0D0]/60";
    if (total === 1) return "bg-[#B7FF00]/45";
    if (total === 2) return "bg-[#B7FF00]/70";
    return "bg-[#B7FF00]";
  };
  return (
    <div className="space-y-3">
      <div className="flex gap-1 overflow-x-auto pb-1">
        {columns.map((column, columnIndex) => (
          <div key={columnIndex} className="flex flex-col gap-1">
            {column.map((day, dayIndex) =>
              day ? (
                <span
                  key={day.date}
                  title={`${day.date} � ${day.total} event${day.total === 1 ? "" : "s"}`}
                  className={`size-[11px] rounded-[2px] ${shade(day.total)}`}
                />
              ) : (
                <span key={`empty-${columnIndex}-${dayIndex}`} className="size-[11px]" />
              ),
            )}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
        <span>Less</span>
        <span className="size-[10px] rounded-[2px] bg-[#D0D0D0]/60" />
        <span className="size-[10px] rounded-[2px] bg-[#B7FF00]/45" />
        <span className="size-[10px] rounded-[2px] bg-[#B7FF00]/70" />
        <span className="size-[10px] rounded-[2px] bg-[#B7FF00]" />
        <span>More</span>
        <span className="ml-auto">{days.reduce((sum, day) => sum + day.total, 0)} events in the last 26 weeks</span>
      </div>
    </div>
  );
}
