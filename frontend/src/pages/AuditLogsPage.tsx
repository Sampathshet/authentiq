import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, CheckCircle2, Database, FileSearch, Link2, ScrollText, ShieldAlert, ShieldCheck, XCircle } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, ErrorState, LoadingBlock, EmptyState } from "@/components/common/page-states";
import { Pagination } from "@/components/common/pagination";
import { HashValue } from "@/components/common/hash-value";
import { StatusBadge, LedgerBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, extractErrorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import type { AuditEntry, LedgerStatus, LedgerTransaction, Paginated } from "@/lib/types";
import { formatDate, humanizeAction, relativeTime, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

interface AuditReport {
  valid: boolean;
  records?: number | null;
  blocks?: number;
  events?: number;
  last_hash?: string;
  checked_at?: string;
  errors?: string[];
  mode?: string;
  network?: string;
}

interface LedgerTransactionDetail extends LedgerTransaction {
  raw_ledger_record: Record<string, unknown> | null;
  integrity: { database_digest: string; ledger_payload_digest?: string; matches: boolean };
}

export default function AuditLogsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [ledgerPage, setLedgerPage] = useState(1);
  const [auditPage, setAuditPage] = useState(1);
  const [ledgerScope, setLedgerScope] = useState("mine");
  const [auditScope, setAuditScope] = useState("mine");
  const [ledgerReport, setLedgerReport] = useState<AuditReport | null>(null);
  const [chainReport, setChainReport] = useState<AuditReport | null>(null);
  const [txDetail, setTxDetail] = useState<LedgerTransactionDetail | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const canSeeAll = user?.role === "verifier" || user?.role === "org_admin";

  const ledgerStatus = useQuery({ queryKey: ["ledger-status"], queryFn: () => api.get<LedgerStatus>("/ledger/status") });
  const ledgerQuery = useQuery({
    queryKey: ["ledger-transactions", ledgerPage, ledgerScope],
    queryFn: () => api.get<Paginated<LedgerTransaction> & { simulated: boolean }>(`/ledger/transactions?page=${ledgerPage}&page_size=20&scope=${ledgerScope}`),
  });
  const auditQuery = useQuery({
    queryKey: ["audit-logs", auditPage, auditScope],
    queryFn: () => api.get<Paginated<AuditEntry>>(`/audit-logs?page=${auditPage}&page_size=25&scope=${auditScope}`),
  });
  const chainQuery = useQuery({ queryKey: ["audit-chain"], queryFn: () => api.get<AuditReport>("/audit-logs/verify") });

  const runLedgerAudit = async () => {
    setBusy("ledger");
    try {
      const report = await api.post<AuditReport>("/ledger/audit");
      setLedgerReport(report);
      if (report.valid) toast.success("Ledger integrity verified");
      else toast.error("Ledger integrity check found problems");
      ledgerStatus.refetch();
      queryClient.invalidateQueries({ queryKey: ["audit-logs"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(null);
    }
  };

  const runChainAudit = async () => {
    setBusy("chain");
    try {
      const report = await api.get<AuditReport>("/audit-logs/verify");
      setChainReport(report);
      if (report.valid) toast.success("Audit hash chain verified");
      else toast.error("Audit hash chain verification failed");
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(null);
    }
  };

  const openTransaction = async (transaction: LedgerTransaction) => {
    try {
      const detail = await api.get<LedgerTransactionDetail>(`/ledger/transactions/${transaction.tx_id}`);
      setTxDetail(detail);
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    }
  };

  const chain = chainReport || chainQuery.data;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Trust center"
        title="Ledger and audit trail"
        description="Inspect the append-only ledger simulation and the hash-chained audit log. Every integrity check runs against stored records and reports the actual result."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={runLedgerAudit} loading={busy === "ledger"}>
              <Database /> Audit ledger
            </Button>
            <Button variant="outline" size="sm" onClick={runChainAudit} loading={busy === "chain"}>
              <Link2 /> Verify audit chain
            </Button>
          </div>
        }
      />

      <Alert variant="warning">
        <AlertDescription>
          The default ledger is a local append-only simulation stored as JSONL. No public blockchain transaction is created. Polygon Amoy is used only when explicitly configured with credentials.
        </AlertDescription>
      </Alert>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Ledger mode</p>
          <div className="mt-2 flex items-center gap-2">
            <LedgerBadge mode={ledgerStatus.data?.mode} />
          </div>
          <p className="mt-1 text-[10px] text-muted-foreground">{ledgerStatus.data?.label || "Loading"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Ledger blocks</p>
          <p className="mt-2 text-2xl font-semibold">{ledgerStatus.data?.block_number ?? 0}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Ledger integrity</p>
          <div className="mt-2 flex items-center gap-2">
            {ledgerStatus.data?.tamper_detected === false ? (
              <><CheckCircle2 className="size-4 text-foreground" /><span className="text-sm font-semibold text-foreground">Valid</span></>
            ) : ledgerStatus.data?.tamper_detected === true ? (
              <><ShieldAlert className="size-4 text-destructive" /><span className="text-sm font-semibold text-destructive">Problems found</span></>
            ) : (
              <span className="text-sm text-muted-foreground">Not checked</span>
            )}
          </div>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Audit hash chain</p>
          <div className="mt-2 flex items-center gap-2">
            {chain ? (
              chain.valid ? (
                <><ShieldCheck className="size-4 text-foreground" /><span className="text-sm font-semibold text-foreground">Verified</span></>
              ) : (
                <><XCircle className="size-4 text-destructive" /><span className="text-sm font-semibold text-destructive">Failed</span></>
              )
            ) : (
              <span className="text-sm text-muted-foreground">Checking...</span>
            )}
          </div>
          <p className="mt-1 text-[10px] text-muted-foreground">{chain?.events ?? 0} audit events</p>
        </Card>
      </div>

      {(ledgerReport || chainReport) && (
        <Card>
          <CardHeader>
            <CardTitle>Last integrity run</CardTitle>
            <CardDescription>Raw output from the backend verification endpoint.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {ledgerReport && (
              <div className={cn("rounded-lg border p-3", ledgerReport.valid ? "border-foreground/20 bg-accent/15" : "border-red-500/25 bg-red-500/5")}>
                <div className="flex items-center gap-2 text-xs font-semibold">
                  {ledgerReport.valid ? <CheckCircle2 className="size-4 text-foreground" /> : <ShieldAlert className="size-4 text-destructive" />}
                  Ledger audit: {ledgerReport.valid ? "valid" : "errors detected"}
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {ledgerReport.records ?? 0} records · {ledgerReport.blocks ?? 0} blocks · checked {formatDate(ledgerReport.checked_at)}
                </p>
                {!!ledgerReport.errors?.length && (
                  <ul className="mt-1 list-inside list-disc text-[11px] text-destructive">
                    {ledgerReport.errors.map((error) => <li key={error}>{error}</li>)}
                  </ul>
                )}
              </div>
            )}
            {chainReport && (
              <div className={cn("rounded-lg border p-3", chainReport.valid ? "border-foreground/20 bg-accent/15" : "border-red-500/25 bg-red-500/5")}>
                <div className="flex items-center gap-2 text-xs font-semibold">
                  {chainReport.valid ? <ShieldCheck className="size-4 text-foreground" /> : <ShieldAlert className="size-4 text-destructive" />}
                  Audit chain: {chainReport.valid ? "valid" : "errors detected"}
                </div>
                <p className="mt-1 text-[11px] text-muted-foreground">{chainReport.events ?? 0} events</p>
                {chainReport.last_hash && <div className="mt-1"><HashValue value={chainReport.last_hash} label="Audit head hash" head={20} tail={14} /></div>}
                {!!chainReport.errors?.length && (
                  <ul className="mt-1 list-inside list-disc text-[11px] text-destructive">
                    {chainReport.errors.map((error) => <li key={error}>{error}</li>)}
                  </ul>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="ledger">
        <TabsList>
          <TabsTrigger value="ledger"><Database /> Ledger events</TabsTrigger>
          <TabsTrigger value="audit"><ScrollText /> Audit trail</TabsTrigger>
        </TabsList>

        <TabsContent value="ledger">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>Ledger transactions</CardTitle>
                  <CardDescription>Block sequence, record hashes, and payload digests from the configured ledger adapter.</CardDescription>
                </div>
                {canSeeAll && (
                  <Button size="sm" variant="outline" onClick={() => { setLedgerScope(ledgerScope === "mine" ? "all" : "mine"); setLedgerPage(1); }}>
                    {ledgerScope === "mine" ? "Show all workspace events" : "Show only my events"}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {ledgerQuery.isLoading && <LoadingBlock rows={5} />}
              {ledgerQuery.isError && <ErrorState error={ledgerQuery.error} onRetry={() => ledgerQuery.refetch()} />}
              {!ledgerQuery.isLoading && !ledgerQuery.isError && !ledgerQuery.data?.items.length && (
                <EmptyState icon={<Database className="size-5" />} title="No ledger events" description="Register a creation or protect an idea to write the first append-only ledger event." />
              )}
              {!!ledgerQuery.data?.items.length && (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Block</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Entity</TableHead>
                        <TableHead>Record hash</TableHead>
                        <TableHead>Timestamp</TableHead>
                        <TableHead />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {ledgerQuery.data.items.map((transaction) => (
                        <TableRow key={transaction.id}>
                          <TableCell><Badge variant="slate">#{transaction.block_number}</Badge></TableCell>
                          <TableCell className="text-xs">{titleCase(transaction.tx_type)}</TableCell>
                          <TableCell>
                            <p className="text-xs">{titleCase(transaction.entity_type)}</p>
                            <p className="max-w-[180px] truncate font-mono text-[10px] text-muted-foreground">{transaction.entity_id}</p>
                          </TableCell>
                          <TableCell><HashValue value={transaction.record_hash} label="Record hash" head={10} tail={8} /></TableCell>
                          <TableCell className="whitespace-nowrap text-[11px] text-muted-foreground">{relativeTime(transaction.timestamp)}</TableCell>
                          <TableCell>
                            <Button size="sm" variant="ghost" onClick={() => openTransaction(transaction)}><FileSearch /> Inspect</Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <Pagination page={ledgerPage} pages={ledgerQuery.data.pages} total={ledgerQuery.data.total} onPageChange={setLedgerPage} disabled={ledgerQuery.isFetching} />
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>Append-only audit trail</CardTitle>
                  <CardDescription>Privileged actions with actor, entity, and chained record hash.</CardDescription>
                </div>
                {canSeeAll && (
                  <Button size="sm" variant="outline" onClick={() => { setAuditScope(auditScope === "mine" ? "all" : "mine"); setAuditPage(1); }}>
                    {auditScope === "mine" ? "Show all workspace events" : "Show only my events"}
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {auditQuery.isLoading && <LoadingBlock rows={6} />}
              {auditQuery.isError && <ErrorState error={auditQuery.error} onRetry={() => auditQuery.refetch()} />}
              {!auditQuery.isLoading && !auditQuery.isError && !auditQuery.data?.items.length && (
                <EmptyState icon={<ScrollText className="size-5" />} title="No audit events" description="Audit entries are appended automatically when privileged actions occur." />
              )}
              {!!auditQuery.data?.items.length && (
                <>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Action</TableHead>
                        <TableHead>Actor</TableHead>
                        <TableHead>Entity</TableHead>
                        <TableHead>Record hash</TableHead>
                        <TableHead>Timestamp</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {auditQuery.data.items.map((entry) => (
                        <TableRow key={entry.id}>
                          <TableCell>
                            <p className="text-xs font-medium">{humanizeAction(entry.action)}</p>
                            <p className="font-mono text-[10px] text-muted-foreground">{entry.event_id}</p>
                          </TableCell>
                          <TableCell className="max-w-[180px] truncate text-xs">{entry.actor_ref}</TableCell>
                          <TableCell>
                            <p className="text-xs">{titleCase(entry.entity_type || "system")}</p>
                            <p className="max-w-[170px] truncate font-mono text-[10px] text-muted-foreground">{entry.entity_id || "—"}</p>
                          </TableCell>
                          <TableCell><HashValue value={entry.record_hash} label="Audit record hash" head={10} tail={8} /></TableCell>
                          <TableCell className="whitespace-nowrap text-[11px] text-muted-foreground">{relativeTime(entry.created_at)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <Pagination page={auditPage} pages={auditQuery.data.pages} total={auditQuery.data.total} onPageChange={setAuditPage} disabled={auditQuery.isFetching} />
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={!!txDetail} onOpenChange={(value) => !value && setTxDetail(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Ledger transaction detail</DialogTitle>
            <DialogDescription>Database record compared against the stored ledger payload.</DialogDescription>
          </DialogHeader>
          {txDetail && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="slate">Block #{txDetail.block_number}</Badge>
                <LedgerBadge mode={txDetail.mode} network={txDetail.network} />
                <StatusBadge status={txDetail.status} />
                <Badge variant={txDetail.integrity.matches ? "green" : "red"}>
                  {txDetail.integrity.matches ? "Payload digest matches" : "Digest mismatch"}
                </Badge>
              </div>
              <div className="rounded-lg border border-border/60 p-3 space-y-1.5 text-xs">
                <p className="font-mono break-all"><span className="text-muted-foreground">tx_id:</span> {txDetail.tx_id}</p>
                <p className="font-mono break-all"><span className="text-muted-foreground">entity:</span> {txDetail.entity_type} / {txDetail.entity_id}</p>
                <p className="font-mono break-all"><span className="text-muted-foreground">payload_digest:</span> {txDetail.payload_digest}</p>
                <p className="font-mono break-all"><span className="text-muted-foreground">prev_hash:</span> {txDetail.prev_hash}</p>
                <p className="font-mono break-all"><span className="text-muted-foreground">record_hash:</span> {txDetail.record_hash}</p>
                <p className="text-muted-foreground">recorded {formatDate(txDetail.timestamp)}</p>
              </div>
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Raw ledger record</p>
                <pre className="max-h-[42vh] overflow-auto rounded-lg border border-border/60 bg-background/50 p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
{JSON.stringify(txDetail.raw_ledger_record, null, 2)}
                </pre>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setTxDetail(null)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {ledgerStatus.data?.errors?.length ? (
        <Alert variant="destructive"><AlertDescription>Ledger adapter reports: {ledgerStatus.data.errors.join("; ")}</AlertDescription></Alert>
      ) : null}
      <p className="flex items-center gap-1.5 text-[10px] text-muted-foreground"><Activity className="size-3" /> Ledger status refreshes automatically; integrity audits are explicit actions.</p>
    </div>
  );
}
