import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Download,
  FileUp,
  Gavel,
  Scale,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader, ErrorState, LoadingBlock, EmptyState } from "@/components/common/page-states";
import { HashValue } from "@/components/common/hash-value";
import { Field, InfoRow } from "@/components/common/field";
import { StatusBadge, LedgerBadge } from "@/components/common/status-badge";
import { FileDropzone } from "@/components/common/file-dropzone";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api, downloadResponse, extractErrorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import type { DisputeItem } from "@/lib/types";
import { formatBytes, formatDate, relativeTime, titleCase } from "@/lib/format";

export default function DisputeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidenceDescription, setEvidenceDescription] = useState("");
  const [nextStatus, setNextStatus] = useState("under_review");
  const [resolution, setResolution] = useState("");
  const [busy, setBusy] = useState(false);

  const disputeQuery = useQuery({
    queryKey: ["dispute", id],
    queryFn: () => api.get<DisputeItem>(`/disputes/${id}`),
    enabled: !!id,
  });
  const dispute = disputeQuery.data;

  const isParty = !!dispute && (dispute.claimant_id === user?.id || dispute.respondent_id === user?.id);
  const canReview = !!dispute?.can_review;
  const canUpdateStatus = canReview || isParty;

  const refresh = () => {
    disputeQuery.refetch();
    queryClient.invalidateQueries({ queryKey: ["disputes"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  };

  const uploadEvidence = async () => {
    if (!evidenceFile || !id) return;
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", evidenceFile);
      if (evidenceDescription.trim()) form.append("description", evidenceDescription.trim());
      await api.postForm(`/disputes/${id}/evidence`, form);
      toast.success("Evidence encrypted and attached");
      setEvidenceOpen(false);
      setEvidenceFile(null);
      setEvidenceDescription("");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const updateStatus = async () => {
    if (!id) return;
    setBusy(true);
    try {
      await api.post(`/disputes/${id}/status`, { status: nextStatus, resolution: resolution.trim() || null });
      toast.success("Dispute status updated");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const downloadReport = async () => {
    if (!dispute) return;
    try {
      await downloadResponse(`/disputes/${dispute.dispute_ref}/report`, `AUTHENTIQ-${dispute.dispute_ref}-evidence-report.json`);
      toast.success("Evidence report downloaded");
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    }
  };

  if (disputeQuery.isLoading) {
    return (
      <div className="space-y-5">
        <PageHeader eyebrow="Dispute" title="Loading dispute" />
        <LoadingBlock rows={6} />
      </div>
    );
  }

  if (disputeQuery.isError || !dispute) {
    return <ErrorState error={disputeQuery.error || new Error("Dispute not found")} onRetry={() => disputeQuery.refetch()} />;
  }

  const resolutionRequired = ["resolved", "rejected"].includes(nextStatus);
  const availableStatuses = canReview
    ? ["under_review", "evidence_requested", "resolved", "rejected"]
    : ["under_review", "evidence_requested"];

  return (
    <div className="space-y-5">
      <div>
        <Button asChild variant="ghost" size="sm" className="mb-2 text-muted-foreground">
          <Link to="/disputes"><ArrowLeft /> All disputes</Link>
        </Button>
        <PageHeader
          eyebrow="Dispute resolution"
          title={dispute.reason}
          description={`Dispute ${dispute.dispute_ref} · opened ${relativeTime(dispute.created_at)}`}
          actions={
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={downloadReport}><Download /> Evidence report</Button>
              {dispute.can_upload_evidence && (
                <Button variant="gradient" size="sm" onClick={() => setEvidenceOpen(true)}><Upload /> Attach evidence</Button>
              )}
            </div>
          }
        />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={dispute.status} />
        <Badge variant="outline">{dispute.dispute_ref}</Badge>
        <Badge variant="outline">{dispute.evidence?.length || 0} evidence files</Badge>
        {dispute.registration && <LedgerBadge mode={dispute.registration.ledger_mode} />}
        {canReview && <Badge variant="violet">Reviewer access</Badge>}
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="evidence">Evidence</TabsTrigger>
          <TabsTrigger value="review">Review</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Claim summary</CardTitle>
                <CardDescription>What the claimant submitted and how the record is identified.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg border border-border/60 bg-background/30 p-3 text-sm leading-relaxed">
                  {dispute.description}
                </div>
                <div className="mt-3">
                  <InfoRow label="Claimant">{dispute.claimant_name || "Unknown claimant"}</InfoRow>
                  <InfoRow label="Respondent">{dispute.respondent_name || "Record owner"}</InfoRow>
                  <InfoRow label="Opened">{formatDate(dispute.created_at)}</InfoRow>
                  <InfoRow label="Last updated">{formatDate(dispute.updated_at)}</InfoRow>
                  {dispute.resolved_at && <InfoRow label="Finalized">{formatDate(dispute.resolved_at)}</InfoRow>}
                  {dispute.earliest_registration_id && (
                    <InfoRow label="Earliest matching registration" mono>{dispute.earliest_registration_id}</InfoRow>
                  )}
                </div>
                {dispute.resolution && (
                  <Alert variant={dispute.status === "resolved" ? "success" : "warning"} className="mt-3">
                    <AlertDescription>
                      <strong className="block text-xs font-semibold">Recorded resolution</strong>
                      <span className="mt-1 block text-[11px] leading-relaxed">{dispute.resolution}</span>
                    </AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Disputed registration</CardTitle>
                  <CardDescription>Public record facts used in the evidence report.</CardDescription>
                </CardHeader>
                <CardContent>
                  {dispute.registration ? (
                    <>
                      <InfoRow label="Title">{dispute.registration.title}</InfoRow>
                      <InfoRow label="Reference" mono>{dispute.registration.registration_id}</InfoRow>
                      <InfoRow label="Registered">{formatDate(dispute.registration.registered_at)}</InfoRow>
                      <InfoRow label="Status">{titleCase(dispute.status)}</InfoRow>
                      <InfoRow label="Fingerprint">
                        <HashValue value={dispute.registration.sha256} label="SHA-256" head={16} tail={12} />
                      </InfoRow>
                      <InfoRow label="Ledger transaction">
                        <HashValue value={dispute.registration.ledger_tx_id} label="Ledger transaction" head={14} tail={10} />
                      </InfoRow>
                      <Button asChild variant="outline" size="sm" className="mt-3 w-full">
                        <Link to={`/registrations/${dispute.registration_id}`}>Open registration record</Link>
                      </Button>
                    </>
                  ) : (
                    <p className="text-xs text-muted-foreground">Registration detail is unavailable.</p>
                  )}
                </CardContent>
              </Card>

              <Alert variant="warning">
                <AlertDescription>
                  Registration priority is evidence, not an automatic legal decision. The report states this limitation explicitly.
                </AlertDescription>
              </Alert>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="evidence">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>Evidence files</CardTitle>
                  <CardDescription>Files are scanned, encrypted at rest, and identified by their SHA-256.</CardDescription>
                </div>
                {dispute.can_upload_evidence && (
                  <Button size="sm" variant="outline" onClick={() => setEvidenceOpen(true)}><FileUp /> Attach evidence</Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {dispute.evidence?.length ? dispute.evidence.map((item) => (
                <div key={item.id} className="rounded-lg border border-border/60 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{item.file_name}</p>
                      <p className="text-[11px] text-muted-foreground">{formatBytes(item.size_bytes)} · uploaded {relativeTime(item.created_at)}</p>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        try {
                          await downloadResponse(`/disputes/${dispute.dispute_ref}/evidence/${item.id}`, item.file_name);
                        } catch (caught) {
                          toast.error(extractErrorMessage(caught));
                        }
                      }}
                    >
                      <Download /> Download
                    </Button>
                  </div>
                  {item.description && <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">{item.description}</p>}
                  <div className="mt-2"><HashValue value={item.sha256} label="Evidence SHA-256" head={18} tail={12} /></div>
                </div>
              )) : (
                <EmptyState
                  icon={<Scale className="size-5" />}
                  title="No evidence attached"
                  description="Parties and reviewers can attach files. Each file is scanned before encryption and stored with its fingerprint."
                  action={dispute.can_upload_evidence ? <Button onClick={() => setEvidenceOpen(true)}>Attach evidence</Button> : undefined}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="review">
          <div className="grid gap-4 lg:grid-cols-[1.3fr_1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Status and resolution</CardTitle>
                <CardDescription>Only an authorized verifier or organization admin can finalize a dispute.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {canUpdateStatus ? (
                  <>
                    <Field label="Next status" htmlFor="dispute-next-status">
                      <Select id="dispute-next-status" value={nextStatus} onChange={(event) => setNextStatus(event.target.value)}>
                        {availableStatuses.map((option) => <option key={option} value={option}>{titleCase(option)}</option>)}
                      </Select>
                    </Field>
                    <Field
                      label="Resolution summary"
                      htmlFor="dispute-resolution"
                      hint={resolutionRequired ? "Required to finalize" : "Optional note"}
                    >
                      <Textarea
                        id="dispute-resolution"
                        value={resolution}
                        onChange={(event) => setResolution(event.target.value)}
                        className="min-h-[130px]"
                        maxLength={4000}
                        placeholder="Summarize the evidence reviewed and the reason for this outcome."
                      />
                    </Field>
                    <Button onClick={updateStatus} loading={busy} disabled={resolutionRequired && resolution.trim().length < 3}>
                      <Gavel /> Update dispute
                    </Button>
                  </>
                ) : (
                  <Alert variant="info">
                    <AlertDescription>You do not have permission to change this dispute. A verifier or organization admin can review it.</AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Reviewer guidance</CardTitle>
                <CardDescription>What the system can and cannot determine.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-[11px] leading-relaxed text-muted-foreground">
                <p><span className="font-medium text-foreground">Cryptographic evidence:</span> registration timestamps, SHA-256 fingerprints, commitments, transfer history, and proof verification are recorded and auditable.</p>
                <p><span className="font-medium text-foreground">Human judgment:</span> authorship, licensing, and infringement are not decided by the platform. The evidence report organizes facts for a reviewer.</p>
                <p><span className="font-medium text-foreground">Resolved status:</span> finalizing marks the registration verified and records the resolution in the audit chain.</p>
                <Button variant="outline" size="sm" onClick={downloadReport}><Download /> Download full report</Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      <Dialog open={evidenceOpen} onOpenChange={(value) => !busy && setEvidenceOpen(value)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Attach dispute evidence</DialogTitle>
            <DialogDescription>The file is scanned, hashed with SHA-256, encrypted, and stored privately. Both parties and authorized reviewers can access it.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <FileDropzone
              file={evidenceFile}
              onFileChange={setEvidenceFile}
              disabled={busy}
              maxSizeMb={25}
              hint="Screenshots, source files, contracts, or other evidence. Files are encrypted at rest."
            />
            <Field label="Description" htmlFor="evidence-description" hint="Optional">
              <Textarea id="evidence-description" value={evidenceDescription} onChange={(event) => setEvidenceDescription(event.target.value)} className="min-h-[90px]" maxLength={2000} placeholder="What does this evidence show?" />
            </Field>
            <Alert variant="warning"><AlertDescription>Only attach evidence you are authorized to share. The file fingerprint and uploader identity are recorded in the audit trail.</AlertDescription></Alert>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEvidenceOpen(false)} disabled={busy}>Cancel</Button>
            <Button onClick={uploadEvidence} loading={busy} disabled={!evidenceFile}><ShieldCheck /> Upload evidence</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
