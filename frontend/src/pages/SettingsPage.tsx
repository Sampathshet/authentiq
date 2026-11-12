import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Building2,
  Check,
  CircleUserRound,
  Copy,
  KeyRound,
  Laptop,
  Lock,
  LogOut,
  Palette,
  ShieldCheck,
  Trash2,
  UserPlus,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader, ErrorState, LoadingBlock } from "@/components/common/page-states";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Field, InfoRow } from "@/components/common/field";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { api, extractErrorMessage } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import type { User } from "@/lib/types";
import { formatDate, initials, relativeTime, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

interface SessionItem {
  id: string;
  user_agent?: string | null;
  ip_address?: string | null;
  created_at: string;
  expires_at: string;
  last_used_at?: string | null;
}

interface OrganizationResponse {
  organization: { id: string; name: string; slug: string; plan: string; owner_id: string } | null;
  members: {
    user_id: string;
    display_name: string;
    email: string;
    role: string;
    status: string;
    is_owner?: boolean;
    is_you?: boolean;
  }[];
  can_manage?: boolean;
}

interface IssuedCredentials {
  display_name: string;
  email: string;
  password: string;
  note: string;
}

interface SecurityOverview {
  password_hashing: string;
  access_token_minutes: number;
  refresh_token_days: number;
  session_count: number;
  passkeys: { available: boolean; reason: string };
  mfa: { available: boolean; reason: string };
  data_encryption_at_rest: boolean;
  private_files_encrypted: boolean;
  audit_chain_enabled: boolean;
}

const avatarColors = ["#171717", "#B7FF00", "#454545", "#888888", "#D0D0D0", "#EAEAEA"];

export default function SettingsPage() {
  const { user, updateUser, logout } = useAuth();
  const queryClient = useQueryClient();
  const [displayName, setDisplayName] = useState(user?.display_name || "");
  const [avatarColor, setAvatarColor] = useState(user?.avatar_color || "#171717");
  const [profileBusy, setProfileBusy] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordBusy, setPasswordBusy] = useState(false);

  const [organizationName, setOrganizationName] = useState("");
  const [organizationBusy, setOrganizationBusy] = useState(false);
  const [revoking, setRevoking] = useState<string | null>(null);

  const [inviteName, setInviteName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("org_member");
  const [inviteBusy, setInviteBusy] = useState(false);
  const [rotatingMember, setRotatingMember] = useState<string | null>(null);
  const [issued, setIssued] = useState<IssuedCredentials | null>(null);

  const sessionsQuery = useQuery({ queryKey: ["auth-sessions"], queryFn: () => api.get<SessionItem[]>("/auth/sessions") });
  const organizationQuery = useQuery({ queryKey: ["organization-settings"], queryFn: () => api.get<OrganizationResponse>("/settings/organization") });
  const securityQuery = useQuery({ queryKey: ["security-settings"], queryFn: () => api.get<SecurityOverview>("/settings/security") });

  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name);
      setAvatarColor(user.avatar_color);
    }
  }, [user]);

  useEffect(() => {
    if (organizationQuery.data?.organization) setOrganizationName(organizationQuery.data.organization.name);
  }, [organizationQuery.data]);

  const saveProfile = async () => {
    setProfileBusy(true);
    try {
      const updated = await api.patch<User>("/auth/me", { display_name: displayName.trim(), avatar_color: avatarColor });
      updateUser(updated);
      toast.success("Profile updated");
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setProfileBusy(false);
    }
  };

  const changePassword = async () => {
    setPasswordBusy(true);
    try {
      const response = await api.post<{ message: string }>("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      toast.success(response.message);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      queryClient.clear();
      await logout();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setPasswordBusy(false);
    }
  };

  const saveOrganization = async () => {
    setOrganizationBusy(true);
    try {
      await api.patch("/settings/organization", { name: organizationName.trim() });
      toast.success("Organization updated");
      organizationQuery.refetch();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setOrganizationBusy(false);
    }
  };

  const addOrganizationMember = async () => {
    setInviteBusy(true);
    try {
      const response = await api.post<{
        message: string;
        member: { display_name: string; email: string };
        credentials: { email: string; password: string; note: string };
      }>("/settings/organization/members", {
        display_name: inviteName.trim(),
        email: inviteEmail.trim(),
        role: inviteRole,
      });
      toast.success(response.message);
      setIssued({
        display_name: response.member.display_name,
        email: response.credentials.email,
        password: response.credentials.password,
        note: response.credentials.note,
      });
      setInviteName("");
      setInviteEmail("");
      setInviteRole("org_member");
      organizationQuery.refetch();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setInviteBusy(false);
    }
  };

  const rotateMemberPassword = async (member: OrganizationResponse["members"][number]) => {
    setRotatingMember(member.user_id);
    try {
      const response = await api.post<{
        message: string;
        credentials: { email: string; password: string; note: string };
      }>(`/settings/organization/members/${member.user_id}/password`);
      toast.success(response.message);
      setIssued({
        display_name: member.display_name,
        email: response.credentials.email,
        password: response.credentials.password,
        note: response.credentials.note,
      });
      organizationQuery.refetch();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setRotatingMember(null);
    }
  };

  const copyCredentials = async () => {
    if (!issued) return;
    try {
      await navigator.clipboard.writeText(`Email: ${issued.email}\nPassword: ${issued.password}`);
      toast.success("Sign-in details copied");
    } catch {
      toast.error("Clipboard access was blocked. Select the password and copy it manually.");
    }
  };

  const revokeSession = async (session: SessionItem) => {    setRevoking(session.id);
    try {
      await api.delete(`/auth/sessions/${session.id}`);
      toast.success("Session revoked");
      sessionsQuery.refetch();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setRevoking(null);
    }
  };

  if (!user) return null;

  const passwordValid =
    newPassword.length >= 10 &&
    newPassword === confirmPassword &&
    newPassword !== currentPassword &&
    [/[a-z]/.test(newPassword), /[A-Z]/.test(newPassword), /\d/.test(newPassword), /[^A-Za-z0-9]/.test(newPassword)].filter(Boolean).length >= 3;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Account"
        title="Settings and security"
        description="Manage your profile, password, active sessions, organization, and appearance. Security controls report their real availability."
      />

      <Tabs defaultValue="profile">
        <TabsList className="flex h-auto w-full flex-wrap justify-start">
          <TabsTrigger value="profile"><CircleUserRound /> Profile</TabsTrigger>
          <TabsTrigger value="security"><ShieldCheck /> Security</TabsTrigger>
          <TabsTrigger value="organization"><Building2 /> Organization</TabsTrigger>
          <TabsTrigger value="appearance"><Palette /> Appearance</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Profile</CardTitle>
                <CardDescription>Your display name and avatar color appear throughout the workspace.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4">
                  <span className="flex size-14 items-center justify-center rounded-full text-lg font-bold text-white" style={{ backgroundColor: avatarColor }}>
                    {initials(displayName)}
                  </span>
                  <div>
                    <p className="text-sm font-medium">{user.email}</p>
                    <div className="mt-1 flex flex-wrap gap-1">
                      <Badge variant={user.role === "verifier" ? "violet" : user.role === "org_admin" ? "blue" : "slate"}>{titleCase(user.role)}</Badge>
                      <Badge variant="outline">{titleCase(user.account_type)}</Badge>
                      {user.organization_name && <Badge variant="outline">{user.organization_name}</Badge>}
                    </div>
                  </div>
                </div>
                <Field label="Display name" htmlFor="settings-display-name">
                  <Input id="settings-display-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={120} />
                </Field>
                <Field label="Avatar color" htmlFor="settings-avatar-color">
                  <div className="flex flex-wrap gap-2">
                    {avatarColors.map((color) => (
                      <button
                        key={color}
                        type="button"
                        aria-label={`Use ${color}`}
                        onClick={() => setAvatarColor(color)}
                        className={cn("flex size-8 items-center justify-center rounded-full border-2 transition-all", avatarColor === color ? "scale-110 border-foreground" : "border-transparent opacity-80 hover:opacity-100")}
                        style={{ backgroundColor: color }}
                      >
                        {avatarColor === color && <Check className="size-4 text-white mix-blend-difference" />}
                      </button>
                    ))}
                  </div>
                </Field>
                <Button onClick={saveProfile} loading={profileBusy} disabled={displayName.trim().length < 2}>
                  Save profile
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Account facts</CardTitle>
                <CardDescription>Read-only identity information.</CardDescription>
              </CardHeader>
              <CardContent>
                <InfoRow label="Email">{user.email}</InfoRow>
                <InfoRow label="Role">{titleCase(user.role)}</InfoRow>
                <InfoRow label="Account type">{titleCase(user.account_type)}</InfoRow>
                <InfoRow label="Organization">{user.organization_name || "Independent account"}</InfoRow>
                <InfoRow label="Member since">{formatDate(user.created_at)}</InfoRow>
                <InfoRow label="Last sign-in">{user.last_login_at ? relativeTime(user.last_login_at) : "Not recorded"}</InfoRow>
                <InfoRow label="Workspace">{user.is_demo ? "Demo workspace, no records yet" : "Live workspace"}</InfoRow>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="security">
          <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Change password</CardTitle>
                  <CardDescription>Changing your password revokes every active session, including this one. You will be signed out.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Field label="Current password" htmlFor="current-password">
                    <Input id="current-password" type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoComplete="current-password" />
                  </Field>
                  <Field label="New password" htmlFor="new-password" hint="At least 10 characters">
                    <Input id="new-password" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} autoComplete="new-password" />
                  </Field>
                  <Field label="Confirm new password" htmlFor="confirm-password">
                    <Input id="confirm-password" type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} autoComplete="new-password" />
                  </Field>
                  <p className="text-[11px] leading-relaxed text-muted-foreground">
                    Use at least three of: lowercase, uppercase, number, symbol. Passwords are hashed with Argon2id.
                  </p>
                  <Button onClick={changePassword} loading={passwordBusy} disabled={!currentPassword || !passwordValid}>
                    <KeyRound /> Change password
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Active sessions</CardTitle>
                  <CardDescription>Revoke a session if a device should lose access.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {sessionsQuery.isLoading && <LoadingBlock rows={2} />}
                  {sessionsQuery.isError && <ErrorState error={sessionsQuery.error} onRetry={() => sessionsQuery.refetch()} />}
                  {sessionsQuery.data?.length ? sessionsQuery.data.map((session) => (
                    <div key={session.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border/60 p-3">
                      <div className="flex min-w-0 items-start gap-2">
                        <Laptop className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                        <div className="min-w-0">
                          <p className="truncate text-xs font-medium">{session.user_agent || "Unknown client"}</p>
                          <p className="text-[10px] text-muted-foreground">
                            {session.ip_address || "IP unavailable"} · started {formatDate(session.created_at)}
                            {session.last_used_at ? ` · used ${relativeTime(session.last_used_at)}` : ""}
                          </p>
                          <p className="text-[10px] text-muted-foreground">Expires {formatDate(session.expires_at)}</p>
                        </div>
                      </div>
                      <ConfirmDialog
                        trigger={<Button size="sm" variant="ghost" className="text-destructive"><Trash2 /> Revoke</Button>}
                        title="Revoke this session?"
                        description="The refresh token for this session is invalidated. The device will need to sign in again."
                        confirmLabel="Revoke session"
                        destructive
                        onConfirm={() => revokeSession(session)}
                      />
                    </div>
                  )) : (
                    !sessionsQuery.isLoading && <p className="py-4 text-center text-xs text-muted-foreground">No active sessions were returned.</p>
                  )}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Security posture</CardTitle>
                <CardDescription>Reported by the backend, including controls that are unavailable.</CardDescription>
              </CardHeader>
              <CardContent>
                {securityQuery.isLoading && <LoadingBlock rows={5} />}
                {securityQuery.isError && <ErrorState error={securityQuery.error} onRetry={() => securityQuery.refetch()} />}
                {securityQuery.data && (
                  <>
                    <InfoRow label="Password hashing">{securityQuery.data.password_hashing}</InfoRow>
                    <InfoRow label="Access token lifetime">{securityQuery.data.access_token_minutes} minutes</InfoRow>
                    <InfoRow label="Refresh token lifetime">{securityQuery.data.refresh_token_days} days</InfoRow>
                    <InfoRow label="Encryption at rest">{securityQuery.data.data_encryption_at_rest ? "Enabled" : "Disabled"}</InfoRow>
                    <InfoRow label="Private file encryption">{securityQuery.data.private_files_encrypted ? "Enabled" : "Disabled"}</InfoRow>
                    <InfoRow label="Audit hash chain">{securityQuery.data.audit_chain_enabled ? "Enabled" : "Disabled"}</InfoRow>
                    <div className="mt-3 space-y-2">
                      <div className="rounded-lg border border-border/60 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs font-medium">Passkeys</p>
                          <Badge variant={securityQuery.data.passkeys.available ? "green" : "slate"}>{securityQuery.data.passkeys.available ? "Available" : "Unavailable"}</Badge>
                        </div>
                        <p className="mt-1 text-[11px] text-muted-foreground">{securityQuery.data.passkeys.reason}</p>
                      </div>
                      <div className="rounded-lg border border-border/60 p-3">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs font-medium">Multi-factor authentication</p>
                          <Badge variant={securityQuery.data.mfa.available ? "green" : "slate"}>{securityQuery.data.mfa.available ? "Available" : "Unavailable"}</Badge>
                        </div>
                        <p className="mt-1 text-[11px] text-muted-foreground">{securityQuery.data.mfa.reason}</p>
                      </div>
                    </div>
                    <Alert variant="info" className="mt-3">
                      <AlertDescription>Unavailable controls are shown honestly instead of being simulated.</AlertDescription>
                    </Alert>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="organization">
          <div className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
              <Card>
                <CardHeader>
                  <CardTitle>Organization</CardTitle>
                  <CardDescription>Only an organization admin or owner can rename the organization.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {organizationQuery.isLoading && <LoadingBlock rows={3} />}
                  {organizationQuery.isError && <ErrorState error={organizationQuery.error} onRetry={() => organizationQuery.refetch()} />}
                  {organizationQuery.data?.organization ? (
                    <>
                      <Field label="Organization name" htmlFor="organization-name">
                        <Input
                          id="organization-name"
                          value={organizationName}
                          onChange={(event) => setOrganizationName(event.target.value)}
                          disabled={!organizationQuery.data.can_manage}
                          maxLength={160}
                        />
                      </Field>
                      <InfoRow label="Slug" mono>{organizationQuery.data.organization.slug}</InfoRow>
                      <InfoRow label="Plan">{titleCase(organizationQuery.data.organization.plan)}</InfoRow>
                      <InfoRow label="Members">{organizationQuery.data.members.length}</InfoRow>
                      {organizationQuery.data.can_manage && (
                        <Button onClick={saveOrganization} loading={organizationBusy} disabled={organizationName.trim().length < 2}>
                          Save organization
                        </Button>
                      )}
                    </>
                  ) : (
                    <Alert variant="info">
                      <AlertDescription>This account is not attached to an organization. Register an organization account or ask an organization admin to add you.</AlertDescription>
                    </Alert>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Members</CardTitle>
                  <CardDescription>People with access to the organization workspace.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  {organizationQuery.data?.members?.length ? organizationQuery.data.members.map((member) => (
                    <div key={member.user_id} className="flex flex-wrap items-center gap-3 rounded-lg border border-border/60 p-3">
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent/20 text-[10px] font-bold text-muted-foreground">
                        {initials(member.display_name)}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-medium">{member.display_name}</p>
                        <p className="truncate text-[10px] text-muted-foreground">{member.email}</p>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <div className="flex items-center gap-1">
                          {member.is_owner && <Badge variant="outline">Owner</Badge>}
                          {member.is_you && <Badge variant="outline">You</Badge>}
                          <Badge variant="outline">{titleCase(member.role)}</Badge>
                        </div>
                        <StatusBadge status={member.status} />
                      </div>
                      {organizationQuery.data?.can_manage && !member.is_owner && !member.is_you && (
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={rotatingMember === member.user_id}
                          onClick={() => rotateMemberPassword(member)}
                          title="Generate a new password and revoke this member's sessions"
                        >
                          <KeyRound /> New password
                        </Button>
                      )}
                    </div>
                  )) : (
                    <p className="py-4 text-center text-xs text-muted-foreground">No organization members to display.</p>
                  )}
                </CardContent>
              </Card>
            </div>

            {issued && (
              <Card className="border-primary/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><KeyRound className="size-4" /> One-time sign-in details</CardTitle>
                  <CardDescription>{issued.note}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div className="rounded-lg border border-border/70 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Email</p>
                      <p className="mt-1 select-all break-all font-mono text-xs">{issued.email}</p>
                    </div>
                    <div className="rounded-lg border border-border/70 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">Generated password</p>
                      <p className="mt-1 select-all break-all font-mono text-xs">{issued.password}</p>
                    </div>
                  </div>
                  <p className="text-[11px] leading-relaxed text-muted-foreground">
                    {issued.display_name} signs in at <span className="font-mono">/login</span> with these credentials. The password is not stored in readable form and cannot be shown again; generate a new one if it is lost.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" onClick={copyCredentials}><Copy /> Copy sign-in details</Button>
                    <Button size="sm" variant="outline" onClick={() => setIssued(null)}>Dismiss</Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {organizationQuery.data?.can_manage && organizationQuery.data.organization && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><UserPlus className="size-4" /> Add a member</CardTitle>
                  <CardDescription>
                    Create a real account in this organization. The backend generates a strong password and shows it once; share it with the new member over a secure channel. Email delivery is not configured, so nothing is sent automatically.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    <Field label="Display name" htmlFor="member-name">
                      <Input id="member-name" value={inviteName} onChange={(event) => setInviteName(event.target.value)} maxLength={120} placeholder="Ava Patel" />
                    </Field>
                    <Field label="Email address" htmlFor="member-email">
                      <Input id="member-email" type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} maxLength={320} placeholder="name@studio.com" autoComplete="off" />
                    </Field>
                    <Field label="Organization role" htmlFor="member-role">
                      <Select id="member-role" value={inviteRole} onChange={(event) => setInviteRole(event.target.value)}>
                        <option value="org_member">Member</option>
                        <option value="org_admin">Administrator</option>
                      </Select>
                    </Field>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      onClick={addOrganizationMember}
                      loading={inviteBusy}
                      disabled={inviteName.trim().length < 2 || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(inviteEmail.trim())}
                    >
                      <UserPlus /> Create member account
                    </Button>
                    <span className="text-[11px] text-muted-foreground">The new account can sign in immediately with the generated password.</span>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        <TabsContent value="appearance">
          <div className="grid max-w-3xl gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Typefaces</CardTitle>
                <CardDescription>Turret Road carries the display voice, Funnel Display the interface voice.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-lg border border-border/70 p-4">
                  <p className="font-display text-3xl leading-none">TURRET ROAD</p>
                  <p className="mt-2 text-[11px] text-muted-foreground">Primary typeface, headings and wordmarks.</p>
                </div>
                <div className="rounded-lg border border-border/70 p-4">
                  <p className="text-2xl leading-none">Funnel Display</p>
                  <p className="mt-2 text-[11px] text-muted-foreground">Secondary typeface, interface and body copy.</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Palette</CardTitle>
                <CardDescription>Ink, paper and one neon lime accent. No other colours are used.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { name: "Off-white", value: "#EAEAEA" },
                    { name: "Black", value: "#171717" },
                    { name: "Neon lime", value: "#B7FF00" },
                    { name: "White", value: "#FFFFFF" },
                    { name: "Dark grey", value: "#454545" },
                    { name: "Mid grey", value: "#888888" },
                    { name: "Light grey", value: "#D0D0D0" },
                  ].map((swatch) => (
                    <div key={swatch.value} className="flex items-center gap-2 rounded-lg border border-border/70 p-2">
                      <span
                        className="size-7 shrink-0 rounded-md border border-border/70"
                        style={{ backgroundColor: swatch.value }}
                      />
                      <div className="min-w-0">
                        <p className="truncate text-[11px] font-medium">{swatch.name}</p>
                        <p className="font-mono text-[10px] text-muted-foreground">{swatch.value}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      <Card>
        <CardHeader>
          <CardTitle>Sign out</CardTitle>
          <CardDescription>End this session on this device.</CardDescription>
        </CardHeader>
        <CardContent>
          <ConfirmDialog
            trigger={<Button variant="outline" className="text-destructive"><LogOut /> Sign out</Button>}
            title="Sign out of AUTHENTIQ?"
            description="This device's refresh token is revoked. You will need your email and password to sign in again."
            confirmLabel="Sign out"
            destructive
            onConfirm={() => logout()}
          />
        </CardContent>
      </Card>

      <p className="flex items-center gap-1.5 text-[10px] text-muted-foreground"><Lock className="size-3" /> Security endpoints report actual deployment capabilities.</p>
    </div>
  );
}
