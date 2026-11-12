import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  CheckCircle2,
  Copy,
  Database,
  FileWarning,
  Fingerprint,
  Link2,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader, ErrorState, LoadingBlock, EmptyState } from "@/components/common/page-states";
import { StatCard } from "@/components/common/stat-card";
import { HashValue } from "@/components/common/hash-value";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import type { IntegrityOverview } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { Link } from "react-router-dom";

export default function IntegrityCenterPage() {
  const [busy, setBusy] = useState(false);

  const overview = useQuery({
    queryKey: ["integrity-overview"],
    queryFn: () => api.get<IntegrityOverview>("/integrity/overview"),
    refetchInterval: 60_000,
  });

  const recheck = async () => {
    setBusy(true);
    try {
      const result = await overview.refetch();
      if (result.data?.ledger.valid && result.data?.audit_chain.valid) {
        toast.success("Ledger and audit chains verified");
      } else {
        toast.error("Integrity check found problems");
      }
    } finally {
      setBusy(false);
    }
  };

  if (overview.isLoading) return <LoadingBlock rows={8} />;
  if (overview.isError || !overview.data) return <ErrorState error={overview.error} onRetry={() => overview.refetch()} />;

  const data = overview.data;
  const ledgerOk = data.ledger.valid;
  const auditOk = data.audit_chain.valid;
  const issues =
    data.checks.missing_files.length +
    data.checks.missing_ledger_records.length +
    data.checks.duplicate_fingerprints.length +
    data.ledger.errors.length +
    data.audit_chain.errors.length;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Integrity center"
        title="Trust, verified end to end"
        description="Live verification of the append-only ledger, the audit hash chain, stored file bytes, and the evidence attached to your workspace. Every value on this page is recomputed from real data."
        actions={
          <Button variant="gradient" size="sm" onClick={recheck} loading={busy}>
            <RefreshCw /> Run integrity check
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Ledger chain"
          value={ledgerOk ? "Verified" : "Tampered"}
          hint={`${data.ledger.records} block(s) · ${data.ledger.mode}`}
          tone={ledgerOk ? "green" : "amber"}
          icon={ledgerOk ? <ShieldCheck /> : <FileWarning />}
        />
        <StatCard
          label="Audit chain"
          value={auditOk ? "Verified" : "Broken"}
          hint={`${data.audit_chain.events} event(s) hashed`}
          tone={auditOk ? "green" : "amber"}
          icon={auditOk ? <Link2 /> : <XCircle />}
        />
        <StatCard
          label="Workspace digest"
          value={<span className="font-mono text-base">{data.workspace_digest.slice(0, 12)}…</span>}
          hint="Deterministic snapshot of your records"
          tone="violet"
          icon={<Fingerprint />}
        />
        <StatCard
          label="Open issues"
          value={issues}
          hint={issues === 0 ? "No integrity gaps found" : "Review the checks below"}
          tone={issues === 0 ? "green" : "amber"}
          icon={issues === 0 ? <CheckCircle2 /> : <FileWarning />}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Chain verification</CardTitle>
            <CardDescription>Recomputed hash links for the local ledger and the audit log chain.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 p-3">
              <div>
                <p className="text-xs font-medium">Ledger integrity</p>
                <p className="text-[11px] text-muted-foreground">
                  {data.ledger.network} · record hash, previous hash, and payload digest recomputed
                </p>
              </div>
              <Badge variant={ledgerOk ? "green" : "red"}>{ledgerOk ? "Valid" : "Invalid"}</Badge>
            </div>
            {data.ledger.last_hash && (
              <HashValue value={data.ledger.last_hash} label="Last ledger hash" head={16} tail={12} />
            )}
            {data.ledger.errors.length > 0 && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-destructive">Ledger errors</p>
                <ul className="mt-1 space-y-1 text-[11px] text-muted-foreground">
                  {data.ledger.errors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 p-3">
              <div>
                <p className="text-xs font-medium">Audit hash chain</p>
                <p className="text-[11px] text-muted-foreground">
                  Every audit event links to the previous event hash
                </p>
              </div>
              <Badge variant={auditOk ? "green" : "red"}>{auditOk ? "Valid" : "Invalid"}</Badge>
            </div>
            <HashValue value={data.audit_chain.last_hash} label="Last audit hash" head={16} tail={12} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Evidence coverage</CardTitle>
            <CardDescription>What the workspace currently stores and exposes.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {[
              ["Registrations", data.counts.registrations],
              ["Zero-knowledge proofs", data.counts.proofs],
              ["Open alerts", data.exposure.open_alerts],
              ["Public fingerprints", data.exposure.public_fingerprint_records],
              ["Audit events", data.exposure.audit_events],
            ].map(([label, value]) => (
              <div key={String(label)} className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2">
                <span className="text-[11px] text-muted-foreground">{label}</span>
                <span className="text-sm font-semibold">{value}</span>
              </div>
            ))}
            <Button
              variant="outline"
              size="sm"
              className="mt-1 w-full"
              onClick={recheck}
              loading={busy}
            >
              <Activity /> Recompute
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Workspace checks</CardTitle>
          <CardDescription>Automated comparisons between the database, the ledger, and encrypted storage.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <CheckTile
            ok={data.checks.missing_files.length === 0}
            title="Stored files"
            detail={
              data.checks.missing_files.length === 0
                ? "Every registered file is present in encrypted storage."
                : `${data.checks.missing_files.length} record(s) point at missing storage.`
            }
          />
          <CheckTile
            ok={data.checks.missing_ledger_records.length === 0}
            title="Ledger linkage"
            detail={
              data.checks.missing_ledger_records.length === 0
                ? "Every ledger reference resolves to a real ledger block."
                : `${data.checks.missing_ledger_records.length} reference(s) could not be resolved.`
            }
          />
          <CheckTile
            ok={data.checks.duplicate_fingerprints.length === 0}
            title="Fingerprint uniqueness"
            detail={
              data.checks.duplicate_fingerprints.length === 0
                ? "No duplicate fingerprints inside your workspace."
                : `${data.checks.duplicate_fingerprints.length} duplicated fingerprint(s) found.`
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Record ledger map</CardTitle>
          <CardDescription>Ledger linkage and storage presence for every registration you own.</CardDescription>
        </CardHeader>
        <CardContent>
          {data.records.length === 0 ? (
            <EmptyState
              icon={<Database />}
              title="No records to verify yet"
              description="Register a creation to populate the integrity map."
              action={
                <Button asChild size="sm" variant="gradient">
                  <Link to="/register">Register a creation</Link>
                </Button>
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Registration</TableHead>
                  <TableHead>Fingerprint</TableHead>
                  <TableHead>Ledger</TableHead>
                  <TableHead>Storage</TableHead>
                  <TableHead>Registered</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.records.map((record) => (
                  <TableRow key={record.registration_id}>
                    <TableCell>
                      <Link
                        to={`/registrations/${record.registration_id}`}
                        className="font-mono text-[11px] font-semibold underline-offset-4 hover:underline"
                      >
                        {record.registration_id}
                      </Link>
                      <p className="mt-0.5 max-w-[220px] truncate text-[11px] text-muted-foreground">{record.title}</p>
                    </TableCell>
                    <TableCell>
                      <button
                        type="button"
                        className="flex items-center gap-1 font-mono text-[10px] text-muted-foreground hover:text-foreground"
                        onClick={() => {
                          navigator.clipboard.writeText(record.sha256);
                          toast.success("Fingerprint copied");
                        }}
                      >
                        {record.sha256.slice(0, 10)}…{record.sha256.slice(-6)}
                        <Copy className="size-3" />
                      </button>
                    </TableCell>
                    <TableCell>
                      <Badge variant={record.ledger_ok ? "green" : "amber"}>
                        {record.ledger_ok ? "Confirmed" : "Unresolved"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={record.file_present ? "green" : "red"}>
                        {record.file_present ? "Present" : "Missing"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-[11px] text-muted-foreground">{formatDate(record.registered_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function CheckTile({ ok, title, detail }: { ok: boolean; title: string; detail: string }) {
  return (
    <div className="rounded-lg border border-border/60 p-3">
      <div className="flex items-center gap-2">
        {ok ? <CheckCircle2 className="size-4" /> : <FileWarning className="size-4" />}
        <p className="text-xs font-semibold">{title}</p>
      </div>
      <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{detail}</p>
    </div>
  );
}
