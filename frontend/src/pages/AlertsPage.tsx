import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Boxes, CopyCheck, ExternalLink, FileWarning, Search, ShieldX } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, EmptyState, ErrorState, LoadingBlock } from "@/components/common/page-states";
import { Pagination } from "@/components/common/pagination";
import { HashValue } from "@/components/common/hash-value";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
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
import type { AlertItem, Paginated } from "@/lib/types";
import { alertTypeLabels, formatDate, relativeTime, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

interface AlertListResponse extends Paginated<AlertItem> {
  counts: Record<string, number>;
}

interface AlertDetail extends AlertItem {
  matched_registration: {
    registration_id?: string | null;
    title?: string | null;
    fingerprint?: string | null;
    registered_at?: string | null;
    status?: string | null;
    ledger_tx_id?: string | null;
    is_owner: boolean;
  };
  metadata?: { registration_id: string; original_name: string; mime_type: string; size_bytes: number; perceptual_hash?: string | null }[];
}

const statusOptions = ["new", "under_review", "resolved", "dismissed"];
const typeOptions = ["exact_match", "perceptual_similarity", "near_duplicate"];

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [alertType, setAlertType] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  const alertsQuery = useQuery({
    queryKey: ["alerts", page, status, alertType],
    queryFn: () =>
      api.get<AlertListResponse>(
        `/alerts?page=${page}&page_size=15${status ? `&status=${status}` : ""}${alertType ? `&alert_type=${alertType}` : ""}`,
      ),
  });

  const detailQuery = useQuery({
    queryKey: ["alert", selectedId],
    queryFn: () => api.get<AlertDetail>(`/alerts/${selectedId}`),
    enabled: !!selectedId,
  });

  useEffect(() => {
    if (detailQuery.data) setNotes(detailQuery.data.investigation_notes || "");
  }, [detailQuery.data]);

  const updateStatus = async (nextStatus: string) => {
    if (!selectedId) return;
    setBusy(true);
    try {
      await api.patch(`/alerts/${selectedId}/status`, { status: nextStatus, investigation_notes: notes.trim() || null });
      toast.success(`Alert marked ${titleCase(nextStatus)}`);
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      detailQuery.refetch();
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const counts = alertsQuery.data?.counts || {};
  const openAlerts = (counts.new || 0) + (counts.under_review || 0);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Ownership protection"
        title="Alerts and similarity matches"
        description="Duplicate fingerprints and perceptual matches detected during registration. Similarity scores are investigation aids, not findings of infringement."
        actions={
          <Badge variant={openAlerts ? "amber" : "green"} className="h-7 px-3">
            <Boxes className="size-3" /> {openAlerts} open
          </Badge>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {statusOptions.map((option) => (
          <Card key={option} className={cn("p-4", status === option && "border-accent/50 bg-blue-500/5")}>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{titleCase(option)}</p>
            <p className="mt-2 text-2xl font-semibold">{counts[option] || 0}</p>
          </Card>
        ))}
      </div>

      <Card>
        <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Search className="size-4" /> Filter the alert queue
          </div>
          <div className="ml-auto flex flex-wrap gap-2">
            <Select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }} className="w-[170px]" aria-label="Filter by status">
              <option value="">All statuses</option>
              {statusOptions.map((option) => <option key={option} value={option}>{titleCase(option)}</option>)}
            </Select>
            <Select value={alertType} onChange={(event) => { setAlertType(event.target.value); setPage(1); }} className="w-[210px]" aria-label="Filter by alert type">
              <option value="">All alert types</option>
              {typeOptions.map((option) => <option key={option} value={option}>{alertTypeLabels[option] || titleCase(option)}</option>)}
            </Select>
          </div>
        </CardContent>
      </Card>

      {alertsQuery.isLoading && <LoadingBlock rows={5} />}
      {alertsQuery.isError && <ErrorState error={alertsQuery.error} onRetry={() => alertsQuery.refetch()} />}

      {!alertsQuery.isLoading && !alertsQuery.isError && !alertsQuery.data?.items.length && (
        <EmptyState
          icon={<CopyCheck className="size-5" />}
          title="No alerts in this view"
          description="AUTHENTIQ raises an alert when a new registration has an exact fingerprint match or a measured perceptual similarity above the configured threshold."
        />
      )}

      {!!alertsQuery.data?.items.length && (
        <Card>
          <CardHeader>
            <CardTitle>Alert queue</CardTitle>
            <CardDescription>Only alerts for registrations you own are shown.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {alertsQuery.data.items.map((alert) => (
              <button
                key={alert.id}
                type="button"
                onClick={() => setSelectedId(alert.id)}
                className="w-full rounded-lg border border-border/60 p-3 text-left transition-colors hover:bg-accent/40"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={alert.alert_type === "exact_match" ? "red" : "amber"}>
                      {alertTypeLabels[alert.alert_type] || titleCase(alert.alert_type)}
                    </Badge>
                    <StatusBadge status={alert.status} />
                    {typeof alert.similarity_score === "number" && (
                      <Badge variant="outline">{Math.round(alert.similarity_score * 100)}% similarity</Badge>
                    )}
                  </div>
                  <span className="text-[11px] text-muted-foreground">{relativeTime(alert.created_at)}</span>
                </div>
                <p className="mt-1.5 text-sm font-medium">{alert.registration_label || "Your registration"}</p>
                <p className="mt-0.5 text-[11px] text-muted-foreground">
                  Matched against {alert.matched_label || "another registration"} · opened {formatDate(alert.created_at)}
                </p>
                <div className="mt-2 flex items-center gap-2 text-[11px] text-foreground">
                  Review evidence <ExternalLink className="size-3" />
                </div>
              </button>
            ))}
            <Pagination page={page} pages={alertsQuery.data.pages} total={alertsQuery.data.total} onPageChange={setPage} disabled={alertsQuery.isFetching} />
          </CardContent>
        </Card>
      )}

      <Alert variant="warning">
        <AlertDescription>
          An exact SHA-256 match means the files are byte-identical. Perceptual similarity is probabilistic and can produce false positives. Alerts never automatically establish infringement or ownership.
        </AlertDescription>
      </Alert>

      <Dialog open={!!selectedId} onOpenChange={(value) => !value && setSelectedId(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileWarning className="size-4 text-foreground" /> Alert investigation
            </DialogTitle>
            <DialogDescription>
              {detailQuery.data ? `${alertTypeLabels[detailQuery.data.alert_type] || titleCase(detailQuery.data.alert_type)} · ${detailQuery.data.registration_label}` : "Loading alert detail"}
            </DialogDescription>
          </DialogHeader>

          {detailQuery.isLoading && <p className="py-8 text-center text-xs text-muted-foreground">Loading alert evidence...</p>}
          {detailQuery.isError && <ErrorState error={detailQuery.error} onRetry={() => detailQuery.refetch()} />}

          {detailQuery.data && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={detailQuery.data.status} />
                {typeof detailQuery.data.similarity_score === "number" && (
                  <Badge variant="outline">Score {detailQuery.data.similarity_score}</Badge>
                )}
                <span className="text-[11px] text-muted-foreground">Opened {formatDate(detailQuery.data.created_at)}</span>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-border/60 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Your registration</p>
                  <p className="mt-1 text-sm font-medium">{detailQuery.data.registration_label}</p>
                  <Link to={`/registrations/${detailQuery.data.registration_id}`} className="mt-1 inline-flex items-center gap-1 text-[11px] text-foreground">
                    Open record <ExternalLink className="size-3" />
                  </Link>
                </div>
                <div className="rounded-lg border border-border/60 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Matched registration</p>
                  <p className="mt-1 text-sm font-medium">{detailQuery.data.matched_registration?.title || detailQuery.data.matched_label || "Unavailable"}</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">{detailQuery.data.matched_registration?.registration_id}</p>
                  <p className="mt-1 text-[10px] text-muted-foreground">
                    Registered {formatDate(detailQuery.data.matched_registration?.registered_at)}
                  </p>
                  {detailQuery.data.matched_registration?.is_owner && (
                    <Link to={`/registrations/${detailQuery.data.matched_registration_id}`} className="mt-1 inline-flex items-center gap-1 text-[11px] text-foreground">
                      Open record <ExternalLink className="size-3" />
                    </Link>
                  )}
                </div>
              </div>

              {detailQuery.data.matched_registration?.fingerprint && (
                <div className="rounded-lg border border-border/60 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Matched fingerprint</p>
                  <div className="mt-1"><HashValue value={detailQuery.data.matched_registration.fingerprint} label="Fingerprint" head={20} tail={14} /></div>
                </div>
              )}

              {!!detailQuery.data.similarity_analyses?.length && (
                <div className="rounded-lg border border-border/60 p-3">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Measured similarity</p>
                  <div className="mt-2 space-y-1.5">
                    {detailQuery.data.similarity_analyses.map((analysis, index) => (
                      <div key={`${analysis.method}-${index}`} className="flex items-center justify-between gap-2 text-xs">
                        <span className="text-muted-foreground">{titleCase(analysis.method)}</span>
                        <span className="font-mono">{analysis.score}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Investigation notes</p>
                <Textarea value={notes} onChange={(event) => setNotes(event.target.value)} className="min-h-[90px]" maxLength={4000} placeholder="Record what you verified and any next steps." />
              </div>

              {detailQuery.data.disclaimer && <Alert variant="info"><AlertDescription>{detailQuery.data.disclaimer}</AlertDescription></Alert>}
            </div>
          )}

          <DialogFooter className="flex-wrap">
            <Button variant="outline" onClick={() => setSelectedId(null)} disabled={busy}>Close</Button>
            {detailQuery.data && detailQuery.data.status !== "under_review" && (
              <Button variant="outline" onClick={() => updateStatus("under_review")} loading={busy}><Search /> Under review</Button>
            )}
            {detailQuery.data && detailQuery.data.status !== "resolved" && (
              <Button variant="success" onClick={() => updateStatus("resolved")} loading={busy}><ShieldX /> Resolve</Button>
            )}
            {detailQuery.data && detailQuery.data.status !== "dismissed" && (
              <Button variant="ghost" onClick={() => updateStatus("dismissed")} loading={busy}><AlertTriangle /> Dismiss</Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
