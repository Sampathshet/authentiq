import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Award, Download, Eye, FileJson, History, Lightbulb, Lock, PlusCircle, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, ErrorState, LoadingBlock } from "@/components/common/page-states";
import { StatusBadge, LedgerBadge } from "@/components/common/status-badge";
import { HashValue } from "@/components/common/hash-value";
import { Field, InfoRow } from "@/components/common/field";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { api, downloadResponse, extractErrorMessage } from "@/lib/api";
import type { Idea } from "@/lib/types";
import { formatDate, relativeTime, titleCase } from "@/lib/format";

interface IdeaDetail extends Idea {
  revisions: { id: string; revision_no: number; notes: string; commitment: string; ledger_tx_id?: string | null; created_at: string }[];
}

interface RevisionResponse {
  id: string;
  revision_no: number;
  commitment: string;
  ledger_tx_id: string;
  created_at: string;
  original_commitment_preserved: string;
}

export default function IdeaDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [revisionOpen, setRevisionOpen] = useState(false);
  const [revisionNotes, setRevisionNotes] = useState("");
  const [notesOpen, setNotesOpen] = useState(false);
  const [privateNotes, setPrivateNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [revealBusy, setRevealBusy] = useState(false);

  const ideaQuery = useQuery({
    queryKey: ["idea", id],
    queryFn: () => api.get<IdeaDetail>(`/ideas/${encodeURIComponent(id)}`),
  });

  if (ideaQuery.isLoading) return <LoadingBlock rows={7} />;
  if (ideaQuery.isError || !ideaQuery.data) return <ErrorState error={ideaQuery.error} onRetry={() => ideaQuery.refetch()} />;

  const idea = ideaQuery.data;

  const addRevision = async () => {
    setBusy(true);
    try {
      const response = await api.post<RevisionResponse>(`/ideas/${encodeURIComponent(id)}/revisions`, { notes: revisionNotes.trim() });
      toast.success(`Revision ${response.revision_no} recorded. Original commitment preserved.`);
      setRevisionOpen(false);
      setRevisionNotes("");
      ideaQuery.refetch();
      queryClient.invalidateQueries({ queryKey: ["ledger-status"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const updateNotes = async () => {
    setBusy(true);
    try {
      const response = await api.patch<{ message: string; revision_no: number }>(`/ideas/${encodeURIComponent(id)}/notes`, { notes: privateNotes.trim() });
      toast.success(response.message);
      setNotesOpen(false);
      setPrivateNotes("");
      ideaQuery.refetch();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const reveal = async () => {
    setRevealBusy(true);
    try {
      const response = await api.post<{ warning: string }>(`/ideas/${encodeURIComponent(id)}/reveal`);
      toast.success(response.warning);
      ideaQuery.refetch();
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setRevealBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <button type="button" onClick={() => navigate("/ideas")} className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-3.5" /> Back to idea vault
      </button>

      <PageHeader
        eyebrow={idea.idea_ref}
        title={idea.title}
        description="A committed idea record. The original text is encrypted and never rewritten."
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => setRevisionOpen(true)}>
              <PlusCircle /> Add revision
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                downloadResponse(`/ideas/${encodeURIComponent(id)}/certificate`, `AUTHENTIQ-${idea.idea_ref}.pdf`)
                  .then(() => toast.success("Idea certificate downloaded"))
                  .catch((caught) => toast.error(extractErrorMessage(caught)))
              }
            >
              <Award /> Certificate
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                downloadResponse(`/ideas/${encodeURIComponent(id)}/evidence`, `AUTHENTIQ-${idea.idea_ref}-evidence.json`)
                  .then(() => toast.success("Evidence package downloaded"))
                  .catch((caught) => toast.error(extractErrorMessage(caught)))
              }
            >
              <FileJson /> Evidence
            </Button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={idea.status} />
        <LedgerBadge mode={idea.ledger_mode} />
        <Badge variant="outline">{titleCase(idea.privacy)}</Badge>
        <span className="text-[11px] text-muted-foreground">
          Protected {relativeTime(idea.created_at)} · {formatDate(idea.created_at)}
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-2">
            <div>
              <CardTitle>Private idea content</CardTitle>
              <CardDescription>Decrypted for your authorized session only.</CardDescription>
            </div>
            <Lock className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {idea.description ? (
              <div className="whitespace-pre-wrap rounded-lg border border-border/60 bg-background/30 p-4 text-sm leading-relaxed">{idea.description}</div>
            ) : (
              <div className="rounded-lg border border-foreground/20 bg-secondary p-4 text-sm text-foreground">
                The description is not available in this response. It remains encrypted until an authorized reveal.
              </div>
            )}
            {idea.status !== "revealed" ? (
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <ConfirmDialog
                  trigger={<Button variant="outline" size="sm"><Eye /> Reveal idea</Button>}
                  title="Reveal this idea description?"
                  description="Revealing changes the idea status to revealed and makes the description available under the existing privacy rules. The original commitment and ledger record are not altered."
                  confirmLabel="Reveal idea"
                  onConfirm={reveal}
                />
                <Button variant="ghost" size="sm" onClick={() => setNotesOpen(true)}>
                  <History /> Update private notes
                </Button>
                {revealBusy && <span className="text-[11px] text-muted-foreground">Revealing...</span>}
              </div>
            ) : (
              <Alert variant="info" className="mt-4">
                <AlertDescription>
                  Revealed {formatDate(idea.revealed_at)}. The commitment remains the original cryptographic anchor.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Commitment record</CardTitle>
            <CardDescription>Poseidon commitment over the encrypted idea content hash.</CardDescription>
          </CardHeader>
          <CardContent>
            <InfoRow label="Idea reference" mono>{idea.idea_ref}</InfoRow>
            <InfoRow label="Commitment" mono><HashValue value={idea.commitment} label="Commitment" head={18} tail={12} /></InfoRow>
            <InfoRow label="Ledger transaction" mono><HashValue value={idea.ledger_tx_id} label="Ledger transaction" head={16} tail={10} /></InfoRow>
            <InfoRow label="Privacy">{titleCase(idea.privacy)}</InfoRow>
            <InfoRow label="Status">{titleCase(idea.status)}</InfoRow>
            <InfoRow label="Created">{formatDate(idea.created_at)}</InfoRow>
            <InfoRow label="Revealed">{idea.revealed_at ? formatDate(idea.revealed_at) : "Not revealed"}</InfoRow>
            <Button asChild variant="outline" size="sm" className="mt-4 w-full">
              <Link to={`/verify/${idea.idea_ref}`}>
                <ShieldCheck /> Public verification view
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-start justify-between gap-2">
          <div>
            <CardTitle>Revision history</CardTitle>
            <CardDescription>Every revision has its own commitment and ledger event. Earlier commitments are preserved.</CardDescription>
          </div>
          <Button size="sm" variant="outline" onClick={() => setRevisionOpen(true)}>
            <PlusCircle /> Add revision
          </Button>
        </CardHeader>
        <CardContent>
          {idea.revisions.length ? (
            <div className="space-y-3">
              {idea.revisions.map((revision) => (
                <div key={revision.id} className="relative border-l border-border pl-5">
                  <span className="absolute -left-[5px] top-2 size-2.5 rounded-full border-2 border-background bg-violet-400" />
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="violet">Revision {revision.revision_no}</Badge>
                    <span className="text-[11px] text-muted-foreground">{formatDate(revision.created_at)}</span>
                  </div>
                  <p className="mt-1.5 whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">{revision.notes}</p>
                  <div className="mt-1.5"><HashValue value={revision.commitment} label="Revision commitment" head={14} tail={10} /></div>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-4 text-center text-xs text-muted-foreground">No revisions yet. The original idea commitment is the only record.</p>
          )}
        </CardContent>
      </Card>

      <Dialog open={revisionOpen} onOpenChange={(value) => !busy && setRevisionOpen(value)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add a private revision</DialogTitle>
            <DialogDescription>The revision is encrypted, committed separately, and appended to the ledger. The original idea commitment never changes.</DialogDescription>
          </DialogHeader>
          <Field label="Revision notes" htmlFor="revision-notes" required>
            <Textarea id="revision-notes" value={revisionNotes} onChange={(event) => setRevisionNotes(event.target.value)} className="min-h-[140px]" maxLength={10000} placeholder="What did you add or refine?" />
          </Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRevisionOpen(false)} disabled={busy}>Cancel</Button>
            <Button onClick={addRevision} loading={busy} disabled={!revisionNotes.trim()}>Record revision</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={notesOpen} onOpenChange={(value) => !busy && setNotesOpen(value)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update private notes</DialogTitle>
            <DialogDescription>Private notes create a new encrypted revision. They do not alter the original commitment or description.</DialogDescription>
          </DialogHeader>
          <Field label="Private notes" htmlFor="idea-notes" required>
            <Textarea id="idea-notes" value={privateNotes} onChange={(event) => setPrivateNotes(event.target.value)} className="min-h-[140px]" maxLength={10000} />
          </Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setNotesOpen(false)} disabled={busy}>Cancel</Button>
            <Button onClick={updateNotes} loading={busy} disabled={!privateNotes.trim()}>Save notes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="flex items-center gap-2 rounded-lg border border-violet-500/20 bg-violet-500/5 px-4 py-3 text-[11px] text-foreground">
        <Lightbulb className="size-3.5" />
        Idea protection records knowledge at a point in time. It does not publish the idea or establish patentability.
      </div>
    </div>
  );
}
