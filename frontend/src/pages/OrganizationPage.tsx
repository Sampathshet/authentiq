import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Copy, Fingerprint, Link2, Mail, PlusCircle, Trash2, Users } from "lucide-react";
import { toast } from "sonner";
import { PageHeader, ErrorState, LoadingBlock, EmptyState } from "@/components/common/page-states";
import { HashValue } from "@/components/common/hash-value";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/common/field";
import { api, extractErrorMessage } from "@/lib/api";
import { formatBytes, formatDate, relativeTime, titleCase } from "@/lib/format";

interface OrganizationInfo {
  id: string;
  name: string;
  slug: string;
  plan: string;
  owner_id: string;
}

interface OrganizationMember {
  user_id: string;
  display_name: string;
  email: string;
  role: string;
  status: string;
  is_owner: boolean;
  is_you: boolean;
}

interface OrganizationInvitation {
  id: string;
  email: string;
  display_name?: string | null;
  role: string;
  status: string;
  invite_token: string;
  invite_url: string;
  created_at: string | null;
  expires_at: string | null;
  accepted_at: string | null;
}

interface OrganizationResponse {
  organization: OrganizationInfo | null;
  members: OrganizationMember[];
  invitations?: OrganizationInvitation[];
  registration_count?: number;
  can_manage: boolean;
}

interface OrganizationRegistration {
  id: string;
  registration_id: string;
  title: string;
  asset_type: string;
  file_size: number;
  sha256: string;
  status: string;
  privacy: string;
  owner_id: string;
  owner_name?: string | null;
  registered_at: string | null;
}

export default function OrganizationPage() {
  const queryClient = useQueryClient();
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState("org_member");
  const [inviteBusy, setInviteBusy] = useState(false);
  const [lastInvite, setLastInvite] = useState<string | null>(null);

  const organization = useQuery({
    queryKey: ["organization-settings"],
    queryFn: () => api.get<OrganizationResponse>("/settings/organization"),
  });
  const registrations = useQuery({
    queryKey: ["organization-registrations"],
    queryFn: () => api.get<{ items: OrganizationRegistration[]; total: number }>("/settings/organization/registrations?page_size=50"),
    enabled: !!organization.data?.organization,
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["organization-settings"] });
    queryClient.invalidateQueries({ queryKey: ["organization-registrations"] });
  };

  const createInvitation = async () => {
    if (!inviteEmail.trim()) {
      toast.error("Enter the email address to invite");
      return;
    }
    setInviteBusy(true);
    try {
      const response = await api.post<{ invitation: OrganizationInvitation }>("/settings/organization/invitations", {
        email: inviteEmail.trim(),
        display_name: inviteName.trim() || undefined,
        role: inviteRole,
      });
      setLastInvite(`${window.location.origin}${response.invitation.invite_url}`);
      setInviteEmail("");
      setInviteName("");
      toast.success("Invitation created. Share the invite link.");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setInviteBusy(false);
    }
  };

  const revokeInvitation = async (invitation: OrganizationInvitation) => {
    try {
      await api.delete(`/settings/organization/invitations/${invitation.id}`);
      toast.success("Invitation revoked");
      refresh();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    }
  };

  if (organization.isLoading) return <LoadingBlock rows={6} />;
  if (organization.isError || !organization.data) {
    return <ErrorState error={organization.error} onRetry={() => organization.refetch()} />;
  }

  const data = organization.data;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Organization"
        title={data.organization?.name || "Organization"}
        description="Shared workspace for the organization: members, invitations, and every creation registered under it."
        actions={
          <Button asChild variant="gradient" size="sm">
            <Link to="/register">
              <PlusCircle /> Register creation
            </Link>
          </Button>
        }
      />

      {!data.organization ? (
        <EmptyState
          title="You are not part of an organization"
          description="Join with an invitation code from an organization admin, or create an organization account to start one."
          icon={<Building2 className="size-5" />}
          action={
            <Button asChild size="sm">
              <Link to="/join">Join with an invite code</Link>
            </Button>
          }
        />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Members</CardTitle>
                <CardDescription>Accounts with shared access.</CardDescription>
              </CardHeader>
              <CardContent className="text-2xl font-semibold">{data.members.length}</CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Registrations</CardTitle>
                <CardDescription>Creations owned by the organization.</CardDescription>
              </CardHeader>
              <CardContent className="text-2xl font-semibold">{data.registration_count ?? registrations.data?.total ?? 0}</CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Open invitations</CardTitle>
                <CardDescription>Awaiting acceptance.</CardDescription>
              </CardHeader>
              <CardContent className="text-2xl font-semibold">
                {(data.invitations || []).filter((item) => item.status === "invited").length}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Plan</CardTitle>
                <CardDescription>{data.organization.slug}</CardDescription>
              </CardHeader>
              <CardContent className="text-2xl font-semibold">{titleCase(data.organization.plan)}</CardContent>
            </Card>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Users className="size-4" /> Members</CardTitle>
                <CardDescription>Everyone who can work inside this organization.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {data.members.map((member) => (
                  <div key={member.user_id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border/60 p-3">
                    <div className="min-w-0">
                      <p className="flex items-center gap-2 text-xs font-medium">
                        {member.display_name}
                        {member.is_owner && <Badge variant="violet">Owner</Badge>}
                        {member.is_you && <Badge variant="outline">You</Badge>}
                      </p>
                      <p className="truncate text-[11px] text-muted-foreground">{member.email}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={member.role === "org_admin" ? "blue" : "slate"}>{titleCase(member.role)}</Badge>
                      <StatusBadge status={member.status} />
                    </div>
                  </div>
                ))}
                {!data.members.length && <p className="text-xs text-muted-foreground">No members yet. Invite the first one below.</p>}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Mail className="size-4" /> Invitations</CardTitle>
                <CardDescription>Same flow as team invites: issue a code, the invitee accepts it, access is granted.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.can_manage ? (
                  <div className="space-y-2 rounded-lg border border-border/60 p-3">
                    <div className="grid gap-2 sm:grid-cols-2">
                      <Field label="Invite email" htmlFor="org-invite-email" required>
                        <Input id="org-invite-email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="teammate@company.com" />
                      </Field>
                      <Field label="Name" htmlFor="org-invite-name">
                        <Input id="org-invite-name" value={inviteName} onChange={(event) => setInviteName(event.target.value)} placeholder="Optional" />
                      </Field>
                    </div>
                    <Field label="Role" htmlFor="org-invite-role">
                      <select
                        id="org-invite-role"
                        value={inviteRole}
                        onChange={(event) => setInviteRole(event.target.value)}
                        className="h-9 w-full rounded-lg border border-border bg-background px-2 text-xs"
                      >
                        <option value="org_member">Member</option>
                        <option value="org_admin">Administrator</option>
                      </select>
                    </Field>
                    <Button onClick={createInvitation} loading={inviteBusy} className="w-full">
                      <PlusCircle /> Create invitation
                    </Button>
                    {lastInvite && (
                      <div className="space-y-1.5 rounded-lg border border-foreground/20 bg-accent/10 p-2.5">
                        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Invite link</p>
                        <p className="break-all font-mono text-[10px]">{lastInvite}</p>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            navigator.clipboard.writeText(lastInvite);
                            toast.success("Invite link copied");
                          }}
                        >
                          <Copy /> Copy link
                        </Button>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-[11px] text-muted-foreground">Only an organization admin can issue invitations.</p>
                )}

                <div className="space-y-2">
                  {(data.invitations || []).map((invitation) => (
                    <div key={invitation.id} className="rounded-lg border border-border/60 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-xs font-medium">{invitation.email}</p>
                        <div className="flex items-center gap-2">
                          <StatusBadge status={invitation.status} />
                          {data.can_manage && invitation.status === "invited" && (
                            <Button size="sm" variant="ghost" onClick={() => revokeInvitation(invitation)}>
                              <Trash2 /> Revoke
                            </Button>
                          )}
                        </div>
                      </div>
                      <p className="text-[10px] text-muted-foreground">
                        {titleCase(invitation.role)} · created {relativeTime(invitation.created_at)}
                        {invitation.expires_at ? ` · expires ${formatDate(invitation.expires_at)}` : ""}
                      </p>
                      {invitation.status === "invited" && (
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <Link to={`/join?code=${invitation.invite_token}`} className="inline-flex items-center gap-1 text-[11px] font-medium text-foreground hover:text-foreground">
                            <Link2 className="size-3" /> Open invite link
                          </Link>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              navigator.clipboard.writeText(`${window.location.origin}/join?code=${invitation.invite_token}`);
                              toast.success("Invite link copied");
                            }}
                          >
                            <Copy /> Copy
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                  {!(data.invitations || []).length && <p className="text-xs text-muted-foreground">No invitations issued yet.</p>}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Fingerprint className="size-4" /> Organization registrations</CardTitle>
              <CardDescription>Every creation registered under this organization, with its owner and fingerprint.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {registrations.isLoading && <LoadingBlock rows={4} />}
              {registrations.data?.items.map((registration) => (
                <Link
                  key={registration.id}
                  to={`/registrations/${registration.id}`}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 bg-background/30 p-3 transition-colors hover:bg-accent/30"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{registration.title}</p>
                    <p className="truncate text-[11px] text-muted-foreground">
                      {registration.registration_id} · {registration.owner_name || "Unknown"} · {formatBytes(registration.file_size)} · {titleCase(registration.asset_type)} · {relativeTime(registration.registered_at)}
                    </p>
                    <div className="mt-1"><HashValue value={registration.sha256} label="SHA-256" head={14} tail={10} /></div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={registration.status} />
                    <Badge variant="outline">{titleCase(registration.privacy)}</Badge>
                  </div>
                </Link>
              ))}
              {!registrations.isLoading && !registrations.data?.items.length && (
                <p className="text-xs text-muted-foreground">
                  No organization registrations yet. Turn on “Register to organization” on the register page.
                </p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
