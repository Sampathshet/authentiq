import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Gavel, PlusCircle, Scale, ShieldQuestion } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, EmptyState, ErrorState, LoadingBlock } from "@/components/common/page-states";
import { StatusBadge } from "@/components/common/status-badge";
import { Field } from "@/components/common/field";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import type { DisputeItem, Paginated, Registration } from "@/lib/types";
import { formatDate, relativeTime, titleCase } from "@/lib/format";

const statusOptions = ["open", "under_review", "evidence_requested", "resolved", "rejected"];

export default function DisputesPage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("");
  const [open, setOpen] = useState(false);
  const [registrationId, setRegistrationId] = useState("");
  const [reason, setReason] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  const disputesQuery = useQuery({
    queryKey: ["disputes", status],
    queryFn: () => api.get<{ items: DisputeItem[] }>(`/disputes?page_size=100${status ? `&status=${status}` : ""}`),
  });
  const registrationsQuery = useQuery({
    queryKey: ["registrations", "dispute-options"],
    queryFn: () => api.get<Paginated<Registration>>("/registrations?page_size=100&sort=recent"),
  });

  const disputes = disputesQuery.data?.items || [];
  const registrations = registrationsQuery.data?.items || [];

  const raiseDispute = async () => {
    setBusy(true);
    try {
      const dispute = await api.post<DisputeItem>("/disputes", {
        registration_id: registrationId,
        reason: reason.trim(),
        description: description.trim(),
      });
      toast.success(`Dispute ${dispute.dispute_ref} opened`);
      setOpen(false);
      setRegistrationId("");
      setReason("");
      setDescription("");
      disputesQuery.refetch();
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const openCount = disputes.filter((dispute) => ["open", "under_review", "evidence_requested"].includes(dispute.status)).length;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Dispute resolution"
        title="Contested ownership records"
        description="Open a structured dispute, attach evidence, and let an authorized verifier or organization admin review the cryptographic record. The earliest registration is displayed as evidence, not as an automatic legal ruling."
        actions={
          <Button variant="gradient" size="sm" onClick={() => { setRegistrationId(registrations[0]?.id || ""); setOpen(true); }} disabled={!registrations.length}>
            <PlusCircle /> Raise a dispute
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Disputes in view</p>
          <p className="mt-2 text-2xl font-semibold">{disputes.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Active</p>
          <p className="mt-2 text-2xl font-semibold">{openCount}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Resolved</p>
          <p className="mt-2 text-2xl font-semibold">{disputes.filter((dispute) => dispute.status === "resolved").length}</p>
        </Card>
      </div>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground"><Gavel className="size-4" /> Filter by status</div>
          <Select value={status} onChange={(event) => setStatus(event.target.value)} className="ml-auto w-[210px]" aria-label="Filter disputes by status">
            <option value="">All statuses</option>
            {statusOptions.map((option) => <option key={option} value={option}>{titleCase(option)}</option>)}
          </Select>
        </CardContent>
      </Card>

      {disputesQuery.isLoading && <LoadingBlock rows={4} />}
      {disputesQuery.isError && <ErrorState error={disputesQuery.error} onRetry={() => disputesQuery.refetch()} />}

      {!disputesQuery.isLoading && !disputesQuery.isError && !disputes.length && (
        <EmptyState
          icon={<Scale className="size-5" />}
          title="No disputes in this view"
          description="Disputes collect the registration record, transfer history, version history, proof activity, and evidence into a structured report. Reviewers can update the status and record a resolution."
          action={<Button onClick={() => setOpen(true)} disabled={!registrations.length}>Raise a dispute</Button>}
        />
      )}

      <div className="grid gap-3 md:grid-cols-2">
        {disputes.map((dispute) => (
          <Link key={dispute.id} to={`/disputes/${dispute.dispute_ref}`} className="group rounded-xl border border-border/70 bg-card/60 p-4 transition-all hover:border-amber-500/40 hover:bg-accent/30">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="amber">{dispute.dispute_ref}</Badge>
                <StatusBadge status={dispute.status} />
              </div>
              <ArrowUpRight className="size-4 text-muted-foreground transition-colors group-hover:text-foreground" />
            </div>
            <p className="mt-2 truncate text-sm font-semibold">{dispute.reason}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">{dispute.registration_title || "Registration"} · {dispute.registration_label}</p>
            <p className="mt-2 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">{dispute.description}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border/50 pt-2 text-[10px] text-muted-foreground">
              <span>Claimant: {dispute.claimant_name || "Unknown"}</span>
              <span>· Opened {relativeTime(dispute.created_at)}</span>
              {dispute.earliest_registration_id && <span>· Earliest {dispute.earliest_registration_id}</span>}
            </div>
          </Link>
        ))}
      </div>

      <Alert variant="info">
        <AlertDescription>
          AUTHENTIQ organizes evidence; it does not provide legal advice. Registration order and cryptographic proofs are inputs to a human review, not an automatic determination of authorship or copyright.
        </AlertDescription>
      </Alert>

      <Dialog open={open} onOpenChange={(value) => !busy && setOpen(value)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Raise an ownership dispute</DialogTitle>
            <DialogDescription>
              The respondent and authorized reviewers can see this dispute. Attach evidence after opening it. A new dispute cannot be opened while one is already active for the same record.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Field label="Registration" htmlFor="dispute-registration" required>
              <Select id="dispute-registration" value={registrationId} onChange={(event) => setRegistrationId(event.target.value)}>
                <option value="">Select a registration</option>
                {registrations.map((registration) => (
                  <option key={registration.id} value={registration.id}>{registration.title} · {registration.registration_id}</option>
                ))}
              </Select>
            </Field>
            <Field label="Reason" htmlFor="dispute-reason" required hint="Short summary">
              <Input id="dispute-reason" value={reason} onChange={(event) => setReason(event.target.value)} maxLength={200} placeholder="e.g. Unauthorized reproduction of my artwork" />
            </Field>
            <Field label="Description" htmlFor="dispute-description" required hint="At least 20 characters">
              <Textarea id="dispute-description" value={description} onChange={(event) => setDescription(event.target.value)} className="min-h-[150px]" maxLength={8000} placeholder="Explain the competing ownership claim and what evidence you can provide." />
            </Field>
            <Alert variant="warning"><AlertDescription>The evidence report includes the full registration and transfer history for the matching fingerprint. Do not include sensitive personal information that is not needed for the claim.</AlertDescription></Alert>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
            <Button onClick={raiseDispute} loading={busy} disabled={!registrationId || reason.trim().length < 3 || description.trim().length < 20}>
              <Gavel /> Open dispute
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {registrationsQuery.isError && (
        <Alert variant="warning"><AlertDescription><ShieldQuestion className="mr-1 inline size-3.5" /> Registrations could not be loaded, so a new dispute cannot be opened from this page.</AlertDescription></Alert>
      )}
    </div>
  );
}
