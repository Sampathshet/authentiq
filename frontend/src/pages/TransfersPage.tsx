import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, ArrowRight, CheckCircle2, Clock, PlusCircle, ShieldCheck, XCircle } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, EmptyState, ErrorState, LoadingBlock } from "@/components/common/page-states";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { HashValue } from "@/components/common/hash-value";
import { Field } from "@/components/common/field";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { api, extractErrorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import type { Paginated, Registration, TransferItem } from "@/lib/types";
import { formatDate, relativeTime, titleCase } from "@/lib/format";

const statusOptions = ["pending_recipient", "recipient_accepted", "completed", "rejected", "cancelled"];

export default function TransfersPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [direction, setDirection] = useState("all");
  const [status, setStatus] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [registrationId, setRegistrationId] = useState("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [reason, setReason] = useState("");
  const [rejectTarget, setRejectTarget] = useState<TransferItem | null>(null);
  const [rejectReason, setRejectReason] = useState("");
  const [busy, setBusy] = useState(false);

  const transfersQuery = useQuery({
    queryKey: ["transfers", direction, status],
    queryFn: () =>
      api.get<{ items: TransferItem[] }>(`/transfers?page_size=100&direction=${direction}${status ? `&status=${status}` : ""}`),
  });
  const registrationsQuery = useQuery({
    queryKey: ["registrations", "transfer-options"],
    queryFn: () => api.get<Paginated<Registration>>("/registrations?page_size=100&sort=recent"),
  });

  const owned = useMemo(
    () => (registrationsQuery.data?.items || []).filter((registration) => registration.owner_id === user?.id),
    [registrationsQuery.data, user],
  );
  const transfers = transfersQuery.data?.items || [];

  const refresh = () => {
    transfersQuery.refetch();
    queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  };

  const act = async (transfer: TransferItem, action: "accept" | "cancel" | "confirm") => {
    try {
      await api.post(`/transfers/${transfer.id}/${action}`);
      toast.success(
        action === "accept" ? "Transfer accepted. The owner must now confirm." : action === "cancel" ? "Transfer cancelled" : "Ownership transfer completed",
      );
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    }
  };

  const createTransfer = async () => {
    setBusy(true);
    try {
      await api.post<TransferItem>("/transfers", {
        registration_id: registrationId,
        recipient_email: recipientEmail.trim(),
        reason: reason.trim() || null,
      });
      toast.success("Transfer proposed to the recipient");
      setCreateOpen(false);
      setRegistrationId("");
      setRecipientEmail("");
      setReason("");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const rejectTransfer = async () => {
    if (!rejectTarget) return;
    setBusy(true);
    try {
      await api.post(`/transfers/${rejectTarget.id}/reject`, { reason: rejectReason.trim() || null });
      toast.success("Transfer rejected");
      setRejectTarget(null);
      setRejectReason("");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const renderTransfer = (transfer: TransferItem) => {
    const incoming = transfer.to_user_id === user?.id;
    const outgoing = transfer.from_user_id === user?.id;
    return (
      <div key={transfer.id} className="rounded-lg border border-border/60 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={incoming ? "violet" : "blue"}>{incoming ? "Incoming" : outgoing ? "Outgoing" : "Related"}</Badge>
            <StatusBadge status={transfer.status} />
            <span className="text-[11px] text-muted-foreground">{relativeTime(transfer.created_at)}</span>
          </div>
          {transfer.registration_id && (
            <Link to={`/registrations/${transfer.registration_id}`} className="text-[11px] text-foreground hover:text-foreground">
              Open record
            </Link>
          )}
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <span className="font-medium">{transfer.registration_title || "Registration"}</span>
          <span className="font-mono text-[11px] text-muted-foreground">{transfer.registration_label}</span>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1">{transfer.from_name || transfer.from_user_id}<ArrowRight className="size-3" />{transfer.to_name || transfer.to_email}</span>
          {transfer.reason && <span>· “{transfer.reason}”</span>}
        </div>

        <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-muted-foreground">
          <span>Proposed {formatDate(transfer.created_at)}</span>
          {transfer.recipient_responded_at && <span>Recipient responded {formatDate(transfer.recipient_responded_at)}</span>}
          {transfer.owner_confirmed_at && <span>Owner confirmed {formatDate(transfer.owner_confirmed_at)}</span>}
          {transfer.completed_at && <span>Completed {formatDate(transfer.completed_at)}</span>}
        </div>

        {transfer.rejection_reason && (
          <p className="mt-2 rounded-md border border-red-500/20 bg-red-500/5 px-2 py-1.5 text-[11px] text-destructive">Rejection reason: {transfer.rejection_reason}</p>
        )}

        {transfer.ledger_tx_id && <div className="mt-2"><HashValue value={transfer.ledger_tx_id} label="Transfer ledger transaction" head={14} tail={10} /></div>}

        {incoming && transfer.status === "pending_recipient" && (
          <p className="mt-2 rounded-md border border-border/60 bg-secondary/40 px-2 py-1.5 text-[11px] text-muted-foreground">
            Accept to receive this creation. The record, its encrypted original, and every proof become visible in your
            workspace immediately; ownership itself moves when the current owner confirms.
          </p>
        )}
        {incoming && transfer.status === "recipient_accepted" && (
          <p className="mt-2 rounded-md border border-amber-500/30 bg-amber-500/5 px-2 py-1.5 text-[11px] text-muted-foreground">
            You accepted. The creation is already visible in your workspace as incoming ownership. The current owner still
            has to confirm, and your private verification key is rotated when they do.
          </p>
        )}
        {incoming && transfer.status === "completed" && (
          <p className="mt-2 rounded-md border border-emerald-500/30 bg-emerald-500/5 px-2 py-1.5 text-[11px] text-foreground">
            Ownership moved to you. The creation, its file data, its proofs, and a rotated private verification key are
            now in your workspace.
          </p>
        )}

        <div className="mt-3 flex flex-wrap gap-2">
          {incoming && transfer.status === "pending_recipient" && (
            <>
              <ConfirmDialog
                trigger={<Button size="sm" variant="success"><CheckCircle2 /> Accept transfer</Button>}
                title="Accept this ownership transfer?"
                description="Accepting signals your willingness to receive the record. The current owner still has to confirm before ownership changes."
                confirmLabel="Accept transfer"
                onConfirm={() => act(transfer, "accept")}
              />
              <Button size="sm" variant="outline" onClick={() => { setRejectTarget(transfer); setRejectReason(""); }}><XCircle /> Reject</Button>
            </>
          )}
          {outgoing && ["pending_recipient", "recipient_accepted"].includes(transfer.status) && (
            <ConfirmDialog
              trigger={<Button size="sm" variant="ghost" className="text-destructive"><XCircle /> Cancel request</Button>}
              title="Cancel this transfer?"
              description="The recipient will be notified that the pending transfer was cancelled. No ownership change is recorded."
              confirmLabel="Cancel transfer"
              destructive
              onConfirm={() => act(transfer, "cancel")}
            />
          )}
          {outgoing && transfer.status === "recipient_accepted" && (
            <ConfirmDialog
              trigger={<Button size="sm" variant="success"><ShieldCheck /> Confirm ownership transfer</Button>}
              title="Finalize ownership transfer?"
              description="This changes the recorded owner of the registration, rotates the private ownership credential so only the new owner can prove ownership, and writes both events to the append-only ledger. This cannot be undone from the UI."
              confirmLabel="Finalize transfer"
              onConfirm={() => act(transfer, "confirm")}
            />
          )}
        </div>
      </div>
    );
  };

  const renderList = (items: TransferItem[]) => {
    if (transfersQuery.isLoading) return <LoadingBlock rows={4} />;
    if (transfersQuery.isError) return <ErrorState error={transfersQuery.error} onRetry={() => transfersQuery.refetch()} />;
    if (!items.length) {
      return (
        <EmptyState
          icon={<ArrowLeftRight className="size-5" />}
          title="No transfers in this view"
          description="Ownership transfers require both the recipient's acceptance and the current owner's final confirmation. Every completed transfer is recorded in the ledger."
        />
      );
    }
    return <div className="space-y-2">{items.map(renderTransfer)}</div>;
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Ownership transfer"
        title="Hand over a registered creation"
        description="A transfer needs recipient acceptance and owner confirmation. Each step is written to the audit trail; the completed handover enters the append-only ledger."
        actions={
          <Button variant="gradient" size="sm" onClick={() => { setRegistrationId(owned[0]?.id || ""); setCreateOpen(true); }} disabled={!owned.length}>
            <PlusCircle /> New transfer
          </Button>
        }
      />

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <div className="flex items-center gap-2 text-xs text-muted-foreground"><Clock className="size-4" /> Filter transfer history</div>
          <Select value={status} onChange={(event) => setStatus(event.target.value)} className="ml-auto w-[210px]" aria-label="Filter by status">
            <option value="">All statuses</option>
            {statusOptions.map((option) => <option key={option} value={option}>{titleCase(option)}</option>)}
          </Select>
        </CardContent>
      </Card>

      <Tabs value={direction} onValueChange={setDirection}>
        <TabsList>
          <TabsTrigger value="all">All transfers</TabsTrigger>
          <TabsTrigger value="incoming">Incoming</TabsTrigger>
          <TabsTrigger value="outgoing">Outgoing</TabsTrigger>
        </TabsList>
        <TabsContent value={direction}>{renderList(transfers)}</TabsContent>
      </Tabs>

      <Alert variant="info">
        <AlertDescription>
          A recipient must already have an AUTHENTIQ account. The chain of ownership is append-only: prior transfers remain visible in the record and ledger history.
        </AlertDescription>
      </Alert>

      <Dialog open={createOpen} onOpenChange={(value) => !busy && setCreateOpen(value)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Propose an ownership transfer</DialogTitle>
            <DialogDescription>The recipient accepts first, then you confirm. Only then does the recorded owner change.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Field label="Registration" htmlFor="transfer-registration" required>
              <Select id="transfer-registration" value={registrationId} onChange={(event) => setRegistrationId(event.target.value)}>
                <option value="">Select a registration you own</option>
                {owned.map((registration) => (
                  <option key={registration.id} value={registration.id}>{registration.title} · {registration.registration_id}</option>
                ))}
              </Select>
            </Field>
            <Field label="Recipient email" htmlFor="transfer-email" required hint="Must have an account">
              <Input id="transfer-email" type="email" value={recipientEmail} onChange={(event) => setRecipientEmail(event.target.value)} placeholder="recipient@example.com" />
            </Field>
            <Field label="Reason" htmlFor="transfer-reason" hint="Optional">
              <Textarea id="transfer-reason" value={reason} onChange={(event) => setReason(event.target.value)} className="min-h-[90px]" maxLength={2000} placeholder="Why is ownership being transferred?" />
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)} disabled={busy}>Cancel</Button>
            <Button onClick={createTransfer} loading={busy} disabled={!registrationId || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(recipientEmail.trim())}>
              <ArrowLeftRight /> Propose transfer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!rejectTarget} onOpenChange={(value) => !busy && !value && setRejectTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject ownership transfer</DialogTitle>
            <DialogDescription>The owner will see your reason. The registration stays with its current owner.</DialogDescription>
          </DialogHeader>
          <Field label="Reason" htmlFor="reject-reason" hint="Optional">
            <Textarea id="reject-reason" value={rejectReason} onChange={(event) => setRejectReason(event.target.value)} className="min-h-[100px]" maxLength={2000} placeholder="Explain why you are declining the transfer." />
          </Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectTarget(null)} disabled={busy}>Keep pending</Button>
            <Button variant="destructive" onClick={rejectTransfer} loading={busy}><XCircle /> Reject transfer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
