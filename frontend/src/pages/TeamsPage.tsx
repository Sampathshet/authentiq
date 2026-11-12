import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Check, Crown, KeyRound, Mail, PlusCircle, ShieldCheck, Users } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, EmptyState, ErrorState, LoadingBlock } from "@/components/common/page-states";
import { HashValue } from "@/components/common/hash-value";
import { Field } from "@/components/common/field";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
import type { Team } from "@/lib/types";
import { formatDate, relativeTime, titleCase } from "@/lib/format";

export default function TeamsPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [joining, setJoining] = useState<string | null>(null);
  const [redeemCode, setRedeemCode] = useState("");
  const [redeemBusy, setRedeemBusy] = useState(false);

  const teamsQuery = useQuery({ queryKey: ["teams"], queryFn: () => api.get<{ items: Team[] }>("/teams") });
  const teams = teamsQuery.data?.items || [];
  const invitations = teams.filter((team) => team.my_status === "invited");
  const activeTeams = teams.filter((team) => team.my_status !== "invited");

  const createTeam = async () => {
    setBusy(true);
    try {
      const project = await api.post<Team>("/teams", { name: name.trim(), description: description.trim() || null });
      toast.success(`${project.name} created`);
      setCreateOpen(false);
      setName("");
      setDescription("");
      teamsQuery.refetch();
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const acceptInvitation = async (team: Team) => {
    setJoining(team.id);
    try {
      await api.post(`/teams/${team.id}/join`, {});
      toast.success(`You joined ${team.name}`);
      await queryClient.invalidateQueries({ queryKey: ["teams"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setJoining(null);
    }
  };

  const redeemInviteCode = async () => {
    const code = redeemCode.trim();
    if (!code) return;
    setRedeemBusy(true);
    try {
      const response = await api.post<{ message: string; project_id: string; project_name: string }>("/teams/redeem", { token: code });
      toast.success(`${response.message}: ${response.project_name}`);
      setRedeemCode("");
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      navigate(`/teams/${response.project_id}`);
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setRedeemBusy(false);
    }
  };

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Collaboration"
        title="Teams and shared ownership"
        description="Invite contributors, record contributions, and finalize an ownership split only when every active member approves. Final allocations enter the append-only ledger."
        actions={
          <Button variant="gradient" size="sm" onClick={() => setCreateOpen(true)}>
            <PlusCircle /> New team project
          </Button>
        }
      />

      {!!invitations.length && (
        <Card className="border-accent/40 bg-violet-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Mail className="size-4 text-foreground" /> Pending invitations</CardTitle>
            <CardDescription>Accepting an invitation activates your membership and lets you submit contributions.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {invitations.map((team) => (
              <div key={team.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-violet-500/20 bg-background/30 p-3">
                <div>
                  <p className="text-sm font-medium">{team.name}</p>
                  <p className="text-[11px] text-muted-foreground">
                    Invited by {team.owner_name || "project owner"} · role {titleCase(team.my_role)} · {team.member_count} members
                  </p>
                </div>
                <Button size="sm" onClick={() => acceptInvitation(team)} loading={joining === team.id}>
                  <Check /> Accept invitation
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><KeyRound className="size-4" /> Join with an invitation code</CardTitle>
          <CardDescription>
            Paste the code the team owner shared with you. Redeeming it activates your membership with the role the owner assigned.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <div className="flex-1">
              <Field label="Invitation code" htmlFor="redeem-code">
                <Input
                  id="redeem-code"
                  value={redeemCode}
                  onChange={(event) => setRedeemCode(event.target.value)}
                  placeholder="Paste the invitation code"
                  className="font-mono text-xs"
                  maxLength={200}
                />
              </Field>
            </div>
            <Button onClick={redeemInviteCode} loading={redeemBusy} disabled={redeemCode.trim().length < 8}>
              <KeyRound /> Join team
            </Button>
          </div>
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            You need an AUTHENTIQ account first. Sign in, then paste the code here. If the code was sent to a different email address, redeem it with the account you want to join with.
          </p>
        </CardContent>
      </Card>

      {teamsQuery.isLoading && <LoadingBlock rows={4} />}
      {teamsQuery.isError && <ErrorState error={teamsQuery.error} onRetry={() => teamsQuery.refetch()} />}

      {!teamsQuery.isLoading && !teamsQuery.isError && !activeTeams.length && (
        <EmptyState
          icon={<Users className="size-5" />}
          title="No active team projects"
          description="Create a project to coordinate contributors and agree on a percentage ownership split. The owner starts with 100%; changes become final only after every member approves."
          action={<Button onClick={() => setCreateOpen(true)}>Create a team project</Button>}
        />
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {activeTeams.map((team) => (
          <Link
            key={team.id}
            to={`/teams/${team.id}`}
            className="group flex flex-col rounded-xl border border-border/70 bg-card/60 p-4 transition-all hover:border-accent/50 hover:bg-accent/30"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex size-9 items-center justify-center rounded-lg bg-accent/15 text-foreground">
                <Users className="size-4" />
              </div>
              <Badge variant={team.status === "ownership_approved" ? "green" : "slate"}>{titleCase(team.status)}</Badge>
            </div>
            <h3 className="mt-3 truncate text-sm font-semibold">{team.name}</h3>
            <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">
              {team.description || "No project description provided."}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
              <span className="inline-flex items-center gap-1"><Users className="size-3" /> {team.member_count} members</span>
              <span>· {titleCase(team.my_role || "member")}</span>
              {team.owner_id && <span className="inline-flex items-center gap-1"><Crown className="size-3" /> {team.owner_name || "owner"}</span>}
            </div>
            <div className="mt-3 border-t border-border/50 pt-3">
              {team.ledger_tx_id ? (
                <HashValue value={team.ledger_tx_id} label="Ownership ledger transaction" head={12} tail={10} />
              ) : (
                <span className="text-[11px] text-muted-foreground">Ownership split not finalized</span>
              )}
            </div>
            <div className="mt-auto flex items-center justify-between pt-3">
              <span className="text-[10px] text-muted-foreground">Created {relativeTime(team.created_at)}</span>
              <ArrowUpRight className="size-4 text-muted-foreground transition-colors group-hover:text-foreground" />
            </div>
          </Link>
        ))}
      </div>

      <Alert variant="info">
        <AlertDescription>
          Team ownership records document an internal agreement. They are not a legal determination of copyright ownership. Email delivery is not configured; invitations create in-app notifications and a shareable invite token.
        </AlertDescription>
      </Alert>

      <Dialog open={createOpen} onOpenChange={(value) => !busy && setCreateOpen(value)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create a team project</DialogTitle>
            <DialogDescription>You become the owner with 100% initial ownership. Add members, collect contributions, then propose a split.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Field label="Project name" htmlFor="team-name" required>
              <Input id="team-name" value={name} onChange={(event) => setName(event.target.value)} maxLength={200} placeholder="e.g. Atlas brand identity" />
            </Field>
            <Field label="Description" htmlFor="team-description" hint="Optional">
              <Textarea id="team-description" value={description} onChange={(event) => setDescription(event.target.value)} className="min-h-[110px]" maxLength={4000} placeholder="What is the team producing, and what needs protection?" />
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)} disabled={busy}>Cancel</Button>
            <Button onClick={createTeam} loading={busy} disabled={name.trim().length < 2}>
              <ShieldCheck /> Create project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
