import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Lightbulb, Lock, PlusCircle, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, EmptyState, ErrorState, LoadingBlock } from "@/components/common/page-states";
import { StatusBadge, LedgerBadge } from "@/components/common/status-badge";
import { HashValue } from "@/components/common/hash-value";
import { Field } from "@/components/common/field";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { api, extractErrorMessage } from "@/lib/api";
import type { Idea } from "@/lib/types";
import { formatDate, relativeTime, titleCase } from "@/lib/format";

interface IdeasPageResponse {
  items: Idea[];
  total: number;
}

export default function IdeasPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [privacy, setPrivacy] = useState("private");
  const [busy, setBusy] = useState(false);

  const ideasQuery = useQuery({ queryKey: ["ideas"], queryFn: () => api.get<IdeasPageResponse>("/ideas?page_size=100") });

  const createIdea = async () => {
    setBusy(true);
    try {
      const idea = await api.post<Idea>("/ideas", { title: title.trim(), description: description.trim(), privacy });
      toast.success(`Idea protected · ${idea.idea_ref}`);
      setOpen(false);
      setTitle("");
      setDescription("");
      setPrivacy("private");
      ideasQuery.refetch();
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Idea vault"
        title="Protect what you have not published"
        description="Idea content is encrypted before storage. A Poseidon commitment and timestamp are written to the ledger without revealing the description."
        actions={
          <Button variant="gradient" size="sm" onClick={() => setOpen(true)}>
            <PlusCircle /> Protect an idea
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Protected ideas</p>
          <p className="mt-2 text-2xl font-semibold">{ideasQuery.data?.total ?? 0}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Revealed</p>
          <p className="mt-2 text-2xl font-semibold">{ideasQuery.data?.items.filter((idea) => idea.status === "revealed").length ?? 0}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Private descriptions</p>
          <p className="mt-2 text-2xl font-semibold">{ideasQuery.data?.items.filter((idea) => idea.status !== "revealed").length ?? 0}</p>
        </Card>
      </div>

      {ideasQuery.isLoading && <LoadingBlock rows={5} />}
      {ideasQuery.isError && <ErrorState error={ideasQuery.error} onRetry={() => ideasQuery.refetch()} />}
      {!ideasQuery.isLoading && !ideasQuery.isError && !ideasQuery.data?.items.length && (
        <EmptyState
          icon={<Lightbulb className="size-5" />}
          title="Your idea vault is empty"
          description="Protect a concept, invention, narrative, or business idea with a committed timestamp. The content stays encrypted and can be revealed later without altering the commitment."
          action={<Button onClick={() => setOpen(true)}>Protect your first idea</Button>}
        />
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {ideasQuery.data?.items.map((idea) => (
          <Link
            key={idea.id}
            to={`/ideas/${idea.idea_ref}`}
            className="group rounded-xl border border-border/70 bg-card/60 p-4 transition-all hover:border-violet-500/40 hover:bg-accent/30"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-accent/15 text-foreground">
                <Lock className="size-4" />
              </div>
              <StatusBadge status={idea.status} />
            </div>
            <h3 className="mt-3 truncate text-sm font-semibold">{idea.title}</h3>
            <p className="mt-1 text-[11px] text-muted-foreground">{idea.idea_ref} · {relativeTime(idea.created_at)}</p>
            <div className="mt-3 flex items-center justify-between gap-2">
              <LedgerBadge mode={idea.ledger_mode} />
              <ArrowUpRight className="size-4 text-muted-foreground transition-colors group-hover:text-foreground" />
            </div>
            <div className="mt-3 border-t border-border/50 pt-3">
              <HashValue value={idea.commitment} label="Idea commitment" head={12} tail={10} />
            </div>
            <p className="mt-2 text-[10px] text-muted-foreground">Privacy: {titleCase(idea.privacy)}</p>
          </Link>
        ))}
      </div>

      <Alert variant="info">
        <AlertDescription>
          Protecting an idea commits to the exact title and description that were entered. Add revisions for later notes; the original commitment cannot be rewritten.
        </AlertDescription>
      </Alert>

      <Dialog open={open} onOpenChange={(value) => !busy && setOpen(value)}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Protect a new idea</DialogTitle>
            <DialogDescription>
              The description is encrypted with the application key before storage. Only the commitment and timestamp enter the ledger.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Field label="Idea title" htmlFor="idea-title" required>
              <Input id="idea-title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} placeholder="A concise internal title" />
            </Field>
            <Field label="Idea description" htmlFor="idea-description" required hint="At least 10 characters">
              <Textarea
                id="idea-description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                className="min-h-[160px]"
                maxLength={20000}
                placeholder="Describe the idea in enough detail to prove what you knew and when."
              />
            </Field>
            <Field label="Privacy level" htmlFor="idea-privacy">
              <Select id="idea-privacy" value={privacy} onChange={(event) => setPrivacy(event.target.value)}>
                <option value="private">Private · owner only</option>
                <option value="timestamp_only">Timestamp only · public proof, no description</option>
                <option value="organization">Organization · members of my organization</option>
              </Select>
            </Field>
            <Alert variant="warning">
              <AlertDescription>Even with public verification, the description remains encrypted until you explicitly reveal it.</AlertDescription>
            </Alert>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={busy}>Cancel</Button>
            <Button onClick={createIdea} loading={busy} disabled={title.trim().length < 2 || description.trim().length < 10}>
              <Sparkles /> Protect idea
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
