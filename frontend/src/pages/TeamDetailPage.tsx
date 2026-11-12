import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Award,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  FilePlus2,
  Fingerprint,
  Handshake,
  Loader2,
  MailPlus,
  Percent,
  PlusCircle,
  ShieldCheck,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader, ErrorState, LoadingBlock, EmptyState } from "@/components/common/page-states";
import { HashValue } from "@/components/common/hash-value";
import { Field, InfoRow } from "@/components/common/field";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
import type { Team } from "@/lib/types";
import { formatDate, initials, relativeTime, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

interface InviteResponse {
  member: { id: string; email: string; role: string };
  invite_token: string;
  invite_url: string;
  delivery: string;
}

export default function TeamDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const inviteFromUrl = searchParams.get("invite");
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("contributor");
  const [inviteDisplayName, setInviteDisplayName] = useState("");
  const [inviteResult, setInviteResult] = useState<InviteResponse | null>(null);
  const [contributionOpen, setContributionOpen] = useState(false);
  const [contributionDescription, setContributionDescription] = useState("");
  const [contributionReference, setContributionReference] = useState("");
  const [allocationOpen, setAllocationOpen] = useState(false);
  const [allocationValues, setAllocationValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState<string | null>(null);

  const teamQuery = useQuery({
    queryKey: ["team", id],
    queryFn: () => api.get<Team>(`/teams/${id}${inviteFromUrl ? `?invite=${encodeURIComponent(inviteFromUrl)}` : ""}`),
    enabled: !!id,
  });

  const team = teamQuery.data;
  const activeMembers = useMemo(() => (team?.members || []).filter((member) => member.status === "active"), [team]);
  const proposed = useMemo(() => (team?.allocations || []).filter((allocation) => allocation.status === "proposed"), [team]);
  const approved = useMemo(() => (team?.allocations || []).filter((allocation) => allocation.status === "approved"), [team]);
  const allocationTotal = useMemo(
    () => Object.values(allocationValues).reduce((total, value) => total + (Number.parseFloat(value) || 0), 0),
    [allocationValues],
  );
  const myMembership = activeMembers.find((member) => member.user_id === user?.id);
  const myProposal = proposed.find((allocation) => allocation.member_id === myMembership?.id);
  const hasApproved = myProposal ? myProposal.approvals.includes(user?.id || "") : false;

  const refresh = () => {
    teamQuery.refetch();
    queryClient.invalidateQueries({ queryKey: ["teams"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
  };

  const joinTeam = async () => {
    if (!id) return;
    setActionBusy("join");
    try {
      await api.post(`/teams/${id}/join`, inviteFromUrl ? { token: inviteFromUrl } : {});
      toast.success("Invitation accepted");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setActionBusy(null);
    }
  };

  const redeemHere = async () => {
    if (!id || !inviteFromUrl) return;
    setActionBusy("join");
    try {
      await api.post("/teams/redeem", { token: inviteFromUrl });
      toast.success("Invitation accepted");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setActionBusy(null);
    }
  };

  const invite = async () => {
    if (!id) return;
    setBusy(true);
    try {
      const response = await api.post<InviteResponse>(`/teams/${id}/invite`, {
        email: inviteEmail.trim(),
        role: inviteRole,
        display_name: inviteDisplayName.trim() || null,
      });
      setInviteResult(response);
      toast.success("Invitation created");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const submitContribution = async () => {
    if (!id) return;
    setBusy(true);
    try {
      await api.post(`/teams/${id}/contributions`, {
        description: contributionDescription.trim(),
        file_reference: contributionReference.trim() || null,
      });
      toast.success("Contribution submitted");
      setContributionOpen(false);
      setContributionDescription("");
      setContributionReference("");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const approveContribution = async (contributionId: string) => {
    if (!id) return;
    setActionBusy(contributionId);
    try {
      await api.patch(`/teams/${id}/contributions/${contributionId}/approve`);
      toast.success("Contribution approved");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setActionBusy(null);
    }
  };

  const openAllocationDialog = () => {
    if (!team) return;
    const count = activeMembers.length || 1;
    const base = Math.floor((100 / count) * 100) / 100;
    const initial: Record<string, string> = {};
    activeMembers.forEach((member) => {
      initial[member.id] = base.toFixed(2);
    });
    if (activeMembers.length) {
      const last = activeMembers[activeMembers.length - 1];
      initial[last.id] = (100 - base * (count - 1)).toFixed(2);
    }
    setAllocationValues(initial);
    setAllocationOpen(true);
  };

  const proposeAllocation = async () => {
    if (!id || !team) return;
    setBusy(true);
    try {
      await api.post(`/teams/${id}/ownership/propose`, {
        allocations: activeMembers.map((member) => ({
          member_id: member.id,
          percent: Number.parseFloat(allocationValues[member.id] || "0"),
        })),
      });
      toast.success("Allocation proposed. Every member must approve.");
      setAllocationOpen(false);
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const approveAllocation = async () => {
    if (!id) return;
    setActionBusy("allocation");
    try {
      const response = await api.post<{ approved: boolean; message: string }>(`/teams/${id}/ownership/approve`, {
        allocation_ids: proposed.filter((allocation) => allocation.member_id === myMembership?.id).map((allocation) => allocation.id),
      });
      toast.success(response.message);
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setActionBusy(null);
    }
  };

  const downloadCertificate = async () => {
    if (!team) return;
    setActionBusy("certificate");
    try {
      await downloadResponse(`/teams/${team.id}/certificate`, `AUTHENTIQ-${team.name.slice(0, 40).replace(/\s+/g, "-")}-ownership.json`);
      toast.success("Ownership certificate downloaded");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setActionBusy(null);
    }
  };

  if (teamQuery.isLoading) {
    return (
      <div className="space-y-5">
        <PageHeader eyebrow="Team project" title="Loading team" />
        <LoadingBlock rows={6} />
      </div>
    );
  }

  if (teamQuery.isError || !team) {
    return <ErrorState error={teamQuery.error || new Error("Team project not found")} onRetry={() => teamQuery.refetch()} />;
  }

  const invited = team.my_status === "invited";
  const isActiveMember = activeMembers.some((member) => member.user_id === user?.id) || team.owner_id === user?.id;
  const canAccept = invited || (!!inviteFromUrl && !isActiveMember);

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Team project"
        title={team.name}
        description={team.description || "No project description provided."}
        actions={
          <div className="flex flex-wrap gap-2">
            {canAccept && (
              <Button variant="success" size="sm" onClick={inviteFromUrl ? redeemHere : joinTeam} loading={actionBusy === "join"}>
                <CheckCircle2 /> Accept invitation
              </Button>
            )}
            {team.can_manage && !invited && (
              <Button variant="outline" size="sm" onClick={() => { setInviteResult(null); setInviteEmail(""); setInviteDisplayName(""); setInviteRole("contributor"); setInviteOpen(true); }}>
                <MailPlus /> Invite member
              </Button>
            )}
            {team.status === "ownership_approved" && (
              <Button variant="outline" size="sm" onClick={downloadCertificate} loading={actionBusy === "certificate"}>
                <Download /> Ownership certificate
              </Button>
            )}
          </div>
        }
      />

      {invited && (
        <Alert variant="info">
          <AlertDescription>You have a pending invitation to this project. Accept it to view contributions and take part in ownership approvals.</AlertDescription>
        </Alert>
      )}

      {inviteFromUrl && !isActiveMember && (
        <Alert variant="info">
          <AlertDescription>
            You opened this project with an invitation code. Accept the invitation to activate your membership with the role the owner assigned.
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={team.status} />
        <Badge variant="outline">{titleCase(team.my_role || "member")}</Badge>
        <Badge variant="outline">{activeMembers.length} active members</Badge>
        {team.ledger_tx_id && <HashValue value={team.ledger_tx_id} label="Ownership ledger transaction" head={14} tail={10} />}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Active members</p>
          <p className="mt-2 text-2xl font-semibold">{activeMembers.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Contributions</p>
          <p className="mt-2 text-2xl font-semibold">{team.contributions?.length || 0}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Proposed allocation</p>
          <p className="mt-2 text-2xl font-semibold">{proposed.length ? `${team.allocation_total ?? 0}%` : "None"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Owner</p>
          <p className="mt-2 truncate text-lg font-semibold">{team.owner_name || "Project owner"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Registered creations</p>
          <p className="mt-2 text-2xl font-semibold">{team.creations?.length || 0}</p>
        </Card>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="outline" asChild>
          <Link to={`/register?team=${team.id}`}>
            <PlusCircle /> Register a creation for this team
          </Link>
        </Button>
      </div>

      <Tabs defaultValue="overview">
        <TabsList className="flex h-auto w-full flex-wrap justify-start">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="creations">Creations ({team.creations?.length || 0})</TabsTrigger>
          <TabsTrigger value="contributions">Contributions</TabsTrigger>
          <TabsTrigger value="ownership">Ownership</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Members</CardTitle>
                <CardDescription>Roles and recorded ownership percentages.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {team.members.map((member) => (
                  <div key={member.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-border/60 p-3">
                    <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-accent/20 text-[11px] font-bold text-muted-foreground">
                      {initials(member.display_name || member.email)}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">
                        {member.display_name || member.email}
                        {member.user_id === user?.id && <span className="ml-1.5 text-[10px] text-muted-foreground">(you)</span>}
                      </p>
                      <p className="truncate text-[11px] text-muted-foreground">{member.email}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge variant="outline">{titleCase(member.role)}</Badge>
                      <StatusBadge status={member.status} />
                      <Badge variant="slate">{member.ownership_percent}%</Badge>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Project facts</CardTitle>
                <CardDescription>Record and confirmation details.</CardDescription>
              </CardHeader>
              <CardContent>
                <InfoRow label="Project ID" mono>{team.id}</InfoRow>
                <InfoRow label="Owner">{team.owner_name || "Not available"}</InfoRow>
                <InfoRow label="Your role">{titleCase(team.my_role || "member")}</InfoRow>
                <InfoRow label="Created">{formatDate(team.created_at)}</InfoRow>
                <InfoRow label="Status">{titleCase(team.status)}</InfoRow>
                <InfoRow label="Ledger transaction" mono>{team.ledger_tx_id || "Not recorded"}</InfoRow>
                <InfoRow label="Demo project">{team.is_demo ? "Yes, seeded example" : "No"}</InfoRow>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="creations">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>Registered creations</CardTitle>
                  <CardDescription>
                    Creations registered under this team. Every active member can open them.
                  </CardDescription>
                </div>
                <Button size="sm" variant="outline" asChild>
                  <Link to={`/register?team=${team.id}`}>
                    <PlusCircle /> Register creation
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {team.creations?.length ? team.creations.map((creation) => (
                <div key={creation.id} className="rounded-lg border border-border/60 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="blue">{titleCase(creation.asset_type)}</Badge>
                      <Badge variant={creation.privacy === "public" ? "green" : "outline"}>
                        {titleCase(creation.privacy)}
                      </Badge>
                      <span className="font-mono text-[11px] text-muted-foreground">
                        {creation.registration_id}
                      </span>
                    </div>
                    <span className="text-[11px] text-muted-foreground">
                      {formatDate(creation.registered_at)}
                    </span>
                  </div>
                  <p className="mt-1.5 text-sm font-medium">{creation.title}</p>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    Registered by {creation.owner_name || "a team member"}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                    <HashValue value={creation.sha256} label="SHA-256" head={12} tail={8} />
                    <div className="flex flex-wrap gap-2">
                      {creation.privacy !== "private" && (
                        <Button size="sm" variant="outline" asChild>
                          <Link to={`/verify/${creation.registration_id}`}>
                            <ShieldCheck /> Public record
                          </Link>
                        </Button>
                      )}
                      <Button size="sm" variant="outline" asChild>
                        <Link to={`/registrations/${creation.id}`}>
                          <Fingerprint /> Open record
                        </Link>
                      </Button>
                    </div>
                  </div>
                </div>
              )) : (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  No creation has been registered under this team yet.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="contributions">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <CardTitle>Contributions</CardTitle>
                  <CardDescription>Contributions are self-reported and approved by the owner or a co-owner.</CardDescription>
                </div>
                {!invited && (
                  <Button size="sm" variant="outline" onClick={() => setContributionOpen(true)}>
                    <FilePlus2 /> Submit contribution
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {team.contributions?.length ? team.contributions.map((contribution) => (
                <div key={contribution.id} className="rounded-lg border border-border/60 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="blue">{contribution.member_name}</Badge>
                      <StatusBadge status={contribution.status} />
                      <span className="text-[11px] text-muted-foreground">{relativeTime(contribution.created_at)}</span>
                    </div>
                    {team.can_manage && contribution.status === "submitted" && (
                      <Button size="sm" variant="outline" loading={actionBusy === contribution.id} onClick={() => approveContribution(contribution.id)}>
                        <CheckCircle2 /> Approve
                      </Button>
                    )}
                  </div>
                  <p className="mt-2 text-sm leading-relaxed">{contribution.description}</p>
                  {contribution.file_reference && <p className="mt-1 font-mono text-[11px] text-muted-foreground">Reference: {contribution.file_reference}</p>}
                  {contribution.approved_at && <p className="mt-1 text-[10px] text-foreground">Approved {formatDate(contribution.approved_at)}</p>}
                </div>
              )) : (
                <p className="py-8 text-center text-xs text-muted-foreground">No contributions have been submitted yet.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ownership">
          <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <CardTitle>Ownership allocation</CardTitle>
                    <CardDescription>Percentages must total exactly 100% and every active member must approve.</CardDescription>
                  </div>
                  {team.can_manage && !invited && (
                    <Button size="sm" variant="outline" onClick={openAllocationDialog}>
                      <Percent /> Propose split
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {team.allocations?.length ? team.allocations.map((allocation) => (
                  <div key={allocation.id} className="rounded-lg border border-border/60 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{allocation.member_name || allocation.member_email}</span>
                        <StatusBadge status={allocation.status} />
                      </div>
                      <span className="text-sm font-semibold">{allocation.percent}%</span>
                    </div>
                    <Progress value={allocation.percent} className="mt-2 h-1.5" />
                    <p className="mt-1.5 text-[10px] text-muted-foreground">
                      {allocation.approvals.length} approval{allocation.approvals.length === 1 ? "" : "s"} · proposed {relativeTime(allocation.created_at)}
                      {allocation.approved_at ? ` · approved ${relativeTime(allocation.approved_at)}` : ""}
                    </p>
                  </div>
                )) : (
                  <div className="py-6 text-center text-xs text-muted-foreground">
                    No allocation has been proposed. Members currently show the initial ownership each joined with.
                  </div>
                )}
                {!!proposed.length && myProposal && !hasApproved && (
                  <Button className="w-full" onClick={approveAllocation} loading={actionBusy === "allocation"}>
                    <Handshake /> Approve my {myProposal.percent}% allocation
                  </Button>
                )}
                {!!proposed.length && hasApproved && (
                  <Alert variant="info"><AlertDescription>Your approval is recorded. Finalization waits for every active member.</AlertDescription></Alert>
                )}
                {team.status === "ownership_approved" && (
                  <Alert variant="success">
                    <AlertDescription>The split is finalized and written to the ledger. Download the ownership certificate for the full approval record.</AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Finalized split</CardTitle>
                <CardDescription>Approved allocations recorded for the project.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {approved.length ? approved.map((allocation) => (
                  <div key={allocation.id} className="flex items-center justify-between rounded-lg border border-emerald-500/20 bg-accent/15 p-3">
                    <div>
                      <p className="text-sm font-medium">{allocation.member_name || allocation.member_email}</p>
                      <p className="text-[10px] text-muted-foreground">Approved {formatDate(allocation.approved_at)}</p>
                    </div>
                    <Badge variant="green">{allocation.percent}%</Badge>
                  </div>
                )) : (
                  <p className="py-6 text-center text-xs text-muted-foreground">No finalized percentage split yet.</p>
                )}
                {team.ledger_tx_id && <div className="pt-2"><HashValue value={team.ledger_tx_id} label="Ledger transaction" head={16} tail={12} /></div>}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="timeline">
          <Card>
            <CardHeader>
              <CardTitle>Project timeline</CardTitle>
              <CardDescription>Membership, contributions, and ownership events in reverse chronological order.</CardDescription>
            </CardHeader>
            <CardContent>
              {team.timeline?.length ? (
                <div className="space-y-0">
                  {team.timeline.map((event, index) => (
                    <div key={`${event.type}-${event.timestamp}-${index}`} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className={cn("mt-1 size-2 rounded-full", event.type === "ownership" ? "bg-emerald-400" : event.type === "contribution" ? "bg-violet-400" : "bg-blue-400")} />
                        {index < team.timeline!.length - 1 && <div className="my-1 h-10 w-px bg-border" />}
                      </div>
                      <div className="pb-3">
                        <p className="text-xs font-medium">{event.label}</p>
                        <p className="text-[10px] text-muted-foreground">{formatDate(event.timestamp)} · {titleCase(event.type)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="py-8 text-center text-xs text-muted-foreground">No timeline events recorded yet.</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Alert variant="warning">
        <AlertDescription>
          Ownership percentages document the team's internal agreement and approval process. They are not a legal determination of copyright ownership.
        </AlertDescription>
      </Alert>

      <Dialog open={inviteOpen} onOpenChange={(value) => !busy && setInviteOpen(value)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite a team member</DialogTitle>
            <DialogDescription>Email delivery is not configured. The invitation creates an in-app notification and a shareable token for the invitee.</DialogDescription>
          </DialogHeader>
          {inviteResult ? (
            <div className="space-y-3">
              <Alert variant="success"><AlertDescription>Invitation created for {inviteResult.member.email}.</AlertDescription></Alert>
              <Field label="Invite token" htmlFor="invite-token">
                <div className="flex gap-2">
                  <Input id="invite-token" readOnly value={inviteResult.invite_token} className="font-mono text-xs" />
                  <Button variant="outline" size="icon" onClick={() => { navigator.clipboard.writeText(inviteResult.invite_token); toast.success("Invite token copied"); }}><Copy /></Button>
                </div>
              </Field>
              <Field label="Join link" htmlFor="invite-link">
                <div className="flex gap-2">
                  <Input id="invite-link" readOnly value={`${window.location.origin}${inviteResult.invite_url}`} className="font-mono text-xs" />
                  <Button variant="outline" size="icon" onClick={() => { navigator.clipboard.writeText(`${window.location.origin}${inviteResult.invite_url}`); toast.success("Join link copied"); }}><Copy /></Button>
                </div>
              </Field>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Send the link or the code to the invitee. They sign in at /login, then open Teams and paste the code into "Join with an invitation code". The code activates their membership with the role you chose.
              </p>
              <p className="text-[11px] leading-relaxed text-muted-foreground">{inviteResult.delivery}</p>
            </div>
          ) : (
            <div className="space-y-3">
              <Field label="Email address" htmlFor="invite-email" required>
                <Input id="invite-email" type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="collaborator@example.com" />
              </Field>
              <Field label="Display name" htmlFor="invite-name" hint="Optional">
                <Input id="invite-name" value={inviteDisplayName} onChange={(event) => setInviteDisplayName(event.target.value)} />
              </Field>
              <Field label="Role" htmlFor="invite-role">
                <Select id="invite-role" value={inviteRole} onChange={(event) => setInviteRole(event.target.value)}>
                  <option value="contributor">Contributor</option>
                  <option value="reviewer">Reviewer</option>
                  <option value="co_owner">Co-owner</option>
                </Select>
              </Field>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setInviteOpen(false)} disabled={busy}>{inviteResult ? "Done" : "Cancel"}</Button>
            {!inviteResult && (
              <Button onClick={invite} loading={busy} disabled={!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(inviteEmail.trim())}>
                <MailPlus /> Send invitation
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={contributionOpen} onOpenChange={(value) => !busy && setContributionOpen(value)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit a contribution</DialogTitle>
            <DialogDescription>Describe what you contributed. The owner or a co-owner can approve it for the ownership record.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <Field label="Contribution description" htmlFor="contribution-description" required hint="At least 3 characters">
              <Textarea id="contribution-description" value={contributionDescription} onChange={(event) => setContributionDescription(event.target.value)} className="min-h-[140px]" maxLength={4000} placeholder="What did you create, design, write, or review?" />
            </Field>
            <Field label="File or registration reference" htmlFor="contribution-reference" hint="Optional">
              <Input id="contribution-reference" value={contributionReference} onChange={(event) => setContributionReference(event.target.value)} placeholder="Registration ID, file name, or design link" />
            </Field>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setContributionOpen(false)} disabled={busy}>Cancel</Button>
            <Button onClick={submitContribution} loading={busy} disabled={contributionDescription.trim().length < 3}>
              <FilePlus2 /> Submit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={allocationOpen} onOpenChange={(value) => !busy && setAllocationOpen(value)}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Propose ownership split</DialogTitle>
            <DialogDescription>Enter a percentage for every active member. The total must equal exactly 100%. Each member then approves their own line.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            {activeMembers.map((member) => (
              <div key={member.id} className="flex items-center gap-3 rounded-lg border border-border/60 p-3">
                <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent/20 text-[10px] font-bold text-muted-foreground">
                  {initials(member.display_name || member.email)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{member.display_name || member.email}</p>
                  <p className="text-[10px] text-muted-foreground">{titleCase(member.role)}</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <Input
                    type="number"
                    min={0}
                    max={100}
                    step="0.01"
                    value={allocationValues[member.id] || ""}
                    onChange={(event) => setAllocationValues((current) => ({ ...current, [member.id]: event.target.value }))}
                    className="w-24 text-right"
                  />
                  <span className="text-xs text-muted-foreground">%</span>
                </div>
              </div>
            ))}
          </div>
          <div className={cn("flex items-center justify-between rounded-lg border px-3 py-2 text-sm", Math.abs(allocationTotal - 100) < 0.001 ? "border-foreground/25 bg-accent/15 text-foreground" : "border-foreground/25 bg-secondary text-foreground")}>
            <span className="flex items-center gap-2"><Percent className="size-4" /> Total</span>
            <span className="font-semibold">{allocationTotal.toFixed(2)}%</span>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAllocationOpen(false)} disabled={busy}>Cancel</Button>
            <Button onClick={proposeAllocation} loading={busy} disabled={!activeMembers.length || Math.abs(allocationTotal - 100) >= 0.001}>
              <Award /> Propose split
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
