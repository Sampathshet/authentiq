import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Award, CheckCircle2, CopyCheck, Download, Fingerprint, KeyRound, Lock, PlusCircle, ShieldCheck, Users } from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/common/page-states";
import { FileDropzone } from "@/components/common/file-dropzone";
import { Field, InfoRow } from "@/components/common/field";
import { HashValue } from "@/components/common/hash-value";
import { LedgerBadge } from "@/components/common/status-badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { api, downloadResponse, extractErrorMessage, sha256Hex } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { hasDuplicates, perceptualHash, type DuplicateMatch, type DuplicateReport } from "@/lib/duplicates";
import { uploadFileChunked, type UploadProgress } from "@/lib/upload";
import { assetTypeOptions, formatBytes, formatDate, privacyOptions, titleCase } from "@/lib/format";
import type { Registration, Team } from "@/lib/types";
import { cn } from "@/lib/utils";

interface CreateResponse {
  registration: Registration;
  alerts_created: number;
  duplicates: DuplicateReport;
  ledger: { mode: string; tx_id: string; simulated: boolean };
  certificate_url: string;
  verification_key: string;
}

interface UploadMeta {
  upload_id: string;
  final_sha256: string;
  total_chunks: number;
  uploaded_chunks: number;
}

function DuplicateMatches({ matches, exact }: { matches: DuplicateMatch[]; exact: boolean }) {
  return (
    <ul className="mt-2 space-y-2">
      {matches.map((match) => (
        <li key={match.id} className="rounded-lg border border-border/70 bg-background/60 p-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-[11px] font-semibold">{match.registration_id}</span>
            <Badge variant={exact ? "green" : "outline"}>
              {exact ? "Identical file" : `${Math.round(match.similarity * 100)}% similar`}
            </Badge>
          </div>
          <p className="mt-1 text-xs font-medium">{match.title}</p>
          <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">
            {match.file_name} · registered {formatDate(match.registered_at)} ·{" "}
            {match.owned_by_you
              ? "your own record"
              : match.same_organization
                ? "same organization"
                : "another account"}
          </p>
        </li>
      ))}
    </ul>
  );
}

function OwnershipScopePicker({
  organization,
  scopeToOrganization,
  onChange,
  onCreateOrganization,
  creating,
  newName,
  onNameChange,
}: {
  organization: { id: string; name: string } | null;
  scopeToOrganization: boolean;
  onChange: (value: boolean) => void;
  onCreateOrganization?: () => void;
  creating?: boolean;
  newName?: string;
  onNameChange?: (value: string) => void;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-background/30 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Register under</p>
      <div className="mt-2 grid grid-cols-2 gap-1 rounded-lg border border-border/70 bg-background/60 p-1">
        <button
          type="button"
          onClick={() => onChange(false)}
          aria-pressed={!scopeToOrganization}
          className={cn(
            "rounded-md px-2 py-1.5 text-[11px] font-semibold transition-colors",
            !scopeToOrganization
              ? "bg-foreground text-background"
              : "text-muted-foreground hover:bg-accent hover:text-foreground",
          )}
        >
          My own
        </button>
        <button
          type="button"
          onClick={() => organization && onChange(true)}
          disabled={!organization}
          aria-pressed={scopeToOrganization}
          className={cn(
            "rounded-md px-2 py-1.5 text-[11px] font-semibold transition-colors",
            scopeToOrganization
              ? "bg-foreground text-background"
              : "text-muted-foreground hover:bg-accent hover:text-foreground",
            !organization && "cursor-not-allowed opacity-45 hover:bg-transparent",
          )}
        >
          Organization
        </button>
      </div>
      <p className="mt-1.5 text-[10px] leading-relaxed text-muted-foreground">
        {organization ? (
          scopeToOrganization ? (
            <>
              Owned by <span className="font-semibold text-foreground">{organization.name}</span>. Every member can open
              it from the organization workspace.
            </>
          ) : (
            <>
              Personal to you. Members of {organization.name} cannot see this record.
            </>
          )
        ) : (
          "You are not in an organization yet. Create one or join with an invite code to unlock the organization switch."
        )}
      </p>
      {!organization && (
        <div className="mt-2 space-y-2">
          {onCreateOrganization && (
            <div className="flex gap-2">
              <Input
                value={newName || ""}
                onChange={(event) => onNameChange?.(event.target.value)}
                placeholder="Organization name"
                className="h-8 text-[11px]"
              />
              <Button type="button" size="sm" variant="outline" loading={creating} onClick={onCreateOrganization}>
                Create
              </Button>
            </div>
          )}
          <Button asChild type="button" size="sm" variant="ghost" className="w-full">
            <Link to="/join">Join with an invite code</Link>
          </Button>
        </div>
      )}
    </div>
  );
}

export default function RegisterCreationPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();
  const [searchParams] = useSearchParams();
  const [file, setFile] = useState<File | null>(null);
  const [localHash, setLocalHash] = useState<string | null>(null);
  const [hashingFile, setHashingFile] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assetType, setAssetType] = useState("document");
  const [privacy, setPrivacy] = useState("private");
  const [tags, setTags] = useState("");
  const [creationDate, setCreationDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CreateResponse | null>(null);
  const [uploadMeta, setUploadMeta] = useState<UploadMeta | null>(null);
  const [certificateBusy, setCertificateBusy] = useState(false);
  const [duplicates, setDuplicates] = useState<DuplicateReport | null>(null);
  const [checkingDuplicates, setCheckingDuplicates] = useState(false);
  const [teamId, setTeamId] = useState(searchParams.get("team") || "");
  const [scopeToOrganization, setScopeToOrganization] = useState(true);
  const [newOrganizationName, setNewOrganizationName] = useState("");
  const [creatingOrganization, setCreatingOrganization] = useState(false);

  const organizationQuery = useQuery({
    queryKey: ["organization-settings"],
    queryFn: () => api.get<{ organization: { id: string; name: string } | null }>("/settings/organization"),
    staleTime: 30000,
  });
  const organization = organizationQuery.data?.organization ?? null;

  const createOrganization = async () => {
    if (newOrganizationName.trim().length < 2) {
      toast.error("Enter a name for the organization");
      return;
    }
    setCreatingOrganization(true);
    try {
      await api.post("/settings/organization", { name: newOrganizationName.trim() });
      toast.success("Organization created. You are its administrator.");
      setNewOrganizationName("");
      setScopeToOrganization(true);
      queryClient.invalidateQueries({ queryKey: ["organization-settings"] });
      await refreshUser();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setCreatingOrganization(false);
    }
  };

  const teamsQuery = useQuery({
    queryKey: ["teams"],
    queryFn: () => api.get<{ items: Team[] }>("/teams"),
    staleTime: 30000,
  });

  const selectableTeams = (teamsQuery.data?.items ?? []).filter(
    (team) => team.my_status === "active" || team.my_status === "owner" || team.my_role === "owner",
  );
  const selectedTeam = selectableTeams.find((team) => team.id === teamId) ?? null;

  useEffect(() => {
    if (!teamId || !teamsQuery.data) return;
    if (!selectableTeams.some((team) => team.id === teamId)) setTeamId("");
  }, [teamId, teamsQuery.data, selectableTeams]);

  useEffect(() => {
    let active = true;
    if (!file) {
      setLocalHash(null);
      return;
    }
    setHashingFile(true);
    setLocalHash(null);
    file
      .arrayBuffer()
      .then((buffer) => sha256Hex(buffer))
      .then((hash) => {
        if (active) setLocalHash(hash);
      })
      .catch(() => {
        if (active) setLocalHash(null);
      })
      .finally(() => {
        if (active) setHashingFile(false);
      });
    return () => {
      active = false;
    };
  }, [file]);

  useEffect(() => {
    let active = true;
    if (!localHash || !file) {
      setDuplicates(null);
      return;
    }
    setCheckingDuplicates(true);
    (async () => {
      try {
        const perceptual = await perceptualHash(file);
        const report = await api.post<DuplicateReport>("/registrations/duplicate-check", {
          sha256: localHash,
          perceptual_hash: perceptual ?? undefined,
        });
        if (active) setDuplicates(report);
      } catch {
        if (active) setDuplicates(null);
      } finally {
        if (active) setCheckingDuplicates(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [localHash, file]);

  useEffect(() => {
    if (file && !title) setTitle(file.name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " ").slice(0, 160));
  }, [file, title]);

  const reset = () => {
    setFile(null);
    setLocalHash(null);
    setTitle("");
    setDescription("");
    setAssetType("document");
    setPrivacy("private");
    setTags("");
    setCreationDate("");
    setTeamId("");
    setResult(null);
    setUploadMeta(null);
    setProgress(null);
    setError(null);
    setDuplicates(null);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError("Select the file you want to register");
      return;
    }
    if (!title.trim() || title.trim().length < 2) {
      setError("Give the creation a title of at least two characters");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const uploaded = await uploadFileChunked(file, setProgress);
      setUploadMeta({
        upload_id: uploaded.upload.upload_id,
        final_sha256: uploaded.sha256,
        total_chunks: uploaded.upload.total_chunks,
        uploaded_chunks: uploaded.upload.uploaded_chunks,
      });
      setProgress({
        phase: "finalizing",
        currentChunk: uploaded.upload.total_chunks,
        totalChunks: uploaded.upload.total_chunks,
        percent: 97,
        message: "Creating the Poseidon commitment, Pedersen opening, and ledger record",
      });
      const payload = {
        upload_id: uploaded.upload.upload_id,
        title: title.trim(),
        description: description.trim() || undefined,
        asset_type: assetType,
        privacy,
        creation_timestamp: creationDate ? new Date(creationDate).toISOString() : undefined,
        team_id: teamId || undefined,
        scope_to_organization: organization ? scopeToOrganization : undefined,
        tags: tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean)
          .slice(0, 12),
      };
      const response = await api.post<CreateResponse>("/registrations", payload);
      setResult(response);
      setProgress(null);
      if (hasDuplicates(response.duplicates)) {
        toast.warning("Registered, and this file was flagged as already present in the workspace");
      } else {
        toast.success("Creation registered with a real fingerprint and commitment");
      }
      queryClient.invalidateQueries({ queryKey: ["registrations"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["ledger-status"] });
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      if (response.registration.team_id) {
        queryClient.invalidateQueries({ queryKey: ["team", response.registration.team_id] });
      }
    } catch (caught) {
      setError(extractErrorMessage(caught));
      setProgress(null);
    } finally {
      setBusy(false);
    }
  };

  const downloadCertificate = async () => {
    if (!result) return;
    setCertificateBusy(true);
    try {
      await downloadResponse(`/registrations/${result.registration.id}/certificate`, `AUTHENTIQ-${result.registration.registration_id}.pdf`);
      toast.success("Certificate downloaded");
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setCertificateBusy(false);
    }
  };

  if (result) {
    const registration = result.registration;
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex flex-col items-center pt-6 text-center">
          <div className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-accent/25 text-foreground ring-1 ring-foreground/15">
            <CheckCircle2 className="size-7" />
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground">Registration complete</p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight">{registration.title}</h1>
          <p className="mt-2 max-w-xl text-sm text-muted-foreground">
            The fingerprint was computed in your browser, verified per chunk, re-computed on the server, and committed before the record was written.
          </p>
        </div>

        <Card>
          <CardHeader className="flex-row items-center justify-between gap-3">
            <div>
              <CardTitle>Cryptographic record</CardTitle>
              <CardDescription>Reference {registration.registration_id}</CardDescription>
            </div>
            <LedgerBadge mode={registration.ledger_mode} />
          </CardHeader>
          <CardContent>
            <InfoRow label="SHA-256 fingerprint" mono>
              <HashValue value={registration.sha256} label="SHA-256" head={16} tail={12} />
            </InfoRow>
            <InfoRow label="Poseidon commitment" mono>
              <HashValue value={registration.poseidon_commitment} label="Poseidon commitment" head={16} tail={12} />
            </InfoRow>
            <InfoRow label="Pedersen commitment" mono>
              <HashValue value={registration.commitment} label="Pedersen commitment" head={16} tail={12} />
            </InfoRow>
            <InfoRow label="Ledger transaction" mono>
              <HashValue value={registration.ledger_tx_id} label="Ledger transaction" head={14} tail={10} />
            </InfoRow>
            <InfoRow label="File">
              {registration.file_name} · {formatBytes(registration.file_size)}
            </InfoRow>
            <InfoRow label="Registered at">{formatDate(registration.registered_at)}</InfoRow>
            <InfoRow label="Ownership">{registration.team_name || "Personal"}</InfoRow>
            <InfoRow label="Privacy">{titleCase(registration.privacy)}</InfoRow>
            <InfoRow label="Alerts created">{result.alerts_created}</InfoRow>
          </CardContent>
        </Card>

        {uploadMeta && (
          <Alert variant="info">
            <AlertDescription>
              Chunked upload complete: {uploadMeta.uploaded_chunks} of {uploadMeta.total_chunks} chunks verified against individual SHA-256 digests, then matched to the overall browser fingerprint.
            </AlertDescription>
          </Alert>
        )}

        {result.verification_key && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <KeyRound className="size-4" /> Private verification key
              </CardTitle>
              <CardDescription>
                Issued once for this registration. Keep it private — it is the credential for anonymous ownership proofs.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="break-all rounded-lg border border-foreground/20 bg-accent/10 p-3 font-mono text-[10px] leading-relaxed">
                {result.verification_key}
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(result.verification_key);
                    toast.success("Private verification key copied");
                  }}
                >
                  <CopyCheck /> Copy key
                </Button>
                <Button variant="outline" size="sm" asChild>
                  <Link to={`/verify?registration=${encodeURIComponent(registration.registration_id)}`}>
                    <ShieldCheck /> Open public verifier
                  </Link>
                </Button>
              </div>
              <p className="text-[11px] leading-relaxed text-muted-foreground">
                Anyone who holds this key can produce an anonymous ownership proof for this record. It cannot decrypt the
                stored file. You can reveal it again from the registration record at any time.
              </p>
            </CardContent>
          </Card>
        )}

        {hasDuplicates(result.duplicates) && (
          <Card>
            <CardHeader>
              <CardTitle>Duplicate detected</CardTitle>
              <CardDescription>This fingerprint was already registered in the workspace.</CardDescription>
            </CardHeader>
            <CardContent>
              {result.duplicates.exact_matches.length ? (
                <DuplicateMatches matches={result.duplicates.exact_matches} exact />
              ) : (
                <DuplicateMatches matches={result.duplicates.similar_matches} exact={false} />
              )}
              <p className="mt-3 text-[11px] leading-relaxed text-muted-foreground">
                {result.alerts_created} duplicate alert(s) were created and the existing owner was notified. Both records stay on the append-only ledger with their own timestamps, so the earlier registration keeps priority. This is an investigation indicator, not a finding of infringement.
              </p>
            </CardContent>
          </Card>
        )}

        {result.ledger.simulated && (
          <Alert variant="warning">
            <AlertDescription>
              This ledger transaction is a local append-only simulation record, not a public blockchain transaction. The interface and certificate label it accordingly.
            </AlertDescription>
          </Alert>
        )}

        <div className="flex flex-wrap justify-center gap-2">
          <Button variant="gradient" onClick={downloadCertificate} loading={certificateBusy}>
            <Download /> Download certificate
          </Button>
          <Button variant="outline" asChild>
            <Link to={`/registrations/${registration.id}`}>
              Open record <ArrowRight />
            </Link>
          </Button>
          {registration.team_id && (
            <Button variant="outline" asChild>
              <Link to={`/teams/${registration.team_id}`}>
                <Users /> Open team workspace
              </Link>
            </Button>
          )}
          <Button variant="ghost" onClick={reset}>
            <PlusCircle /> Register another file
          </Button>
        </div>
        <p className="text-center text-[11px] text-muted-foreground">
          A certificate declares the recorded fingerprint and timestamp. It is not a legal determination of copyright ownership.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Register"
        title="Register a new creation"
        description="The browser computes SHA-256 locally. The file is uploaded in verified chunks, scanned, encrypted at rest, committed with Poseidon, and written to the append-only ledger."
        actions={
          <Button asChild variant="ghost" size="sm">
            <Link to="/timeline">View timeline</Link>
          </Button>
        }
      />

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <form onSubmit={submit} className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>1. Select the original file</CardTitle>
              <CardDescription>Supported document, image, audio, video, code, and design formats up to 200 MB.</CardDescription>
            </CardHeader>
            <CardContent>
              <FileDropzone file={file} onFileChange={setFile} disabled={busy} />
              {file && (
                <div className="mt-4 rounded-lg border border-border/60 bg-background/30 p-3">
                  <div className="flex items-center gap-2 text-xs font-medium">
                    <Fingerprint className="size-4 text-foreground" />
                    Browser fingerprint
                  </div>
                  <div className="mt-1.5">
                    {hashingFile ? (
                      <span className="text-xs text-muted-foreground">Computing SHA-256 locally...</span>
                    ) : localHash ? (
                      <HashValue value={localHash} label="SHA-256" head={20} tail={14} />
                    ) : (
                      <span className="text-xs text-destructive">The browser could not hash this file</span>
                    )}
                  </div>
                  <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">
                    This hash is compared with the server fingerprint after chunk assembly. A mismatch rejects the registration.
                  </p>
                </div>
              )}
              {file && (
                <div className="mt-3">
                  {checkingDuplicates ? (
                    <p className="text-[11px] text-muted-foreground">
                      Checking the workspace for this fingerprint...
                    </p>
                  ) : hasDuplicates(duplicates) ? (
                    <div className="rounded-lg border border-foreground/30 bg-accent/15 p-3">
                      <div className="flex items-center gap-2 text-xs font-semibold">
                        <CopyCheck className="size-4" />
                        This file is already in the workspace
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                        {duplicates?.exact_matches.length
                          ? "An identical SHA-256 fingerprint is already registered. Registering anyway writes a second ledger record and opens a duplicate alert for the existing owner."
                          : "A visually similar file is already registered. Registering anyway writes a second ledger record and opens a similarity alert for the existing owner."}
                      </p>
                      {duplicates?.exact_matches.length ? (
                        <DuplicateMatches matches={duplicates.exact_matches} exact />
                      ) : (
                        <DuplicateMatches matches={duplicates?.similar_matches ?? []} exact={false} />
                      )}
                    </div>
                  ) : (
                    <p className="text-[11px] text-muted-foreground">
                      No matching fingerprint found in the workspace.
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>2. Describe the creation</CardTitle>
              <CardDescription>Metadata is attached to the record; the file itself remains encrypted.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Field label="Title" htmlFor="creation-title" required>
                <Input id="creation-title" value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} placeholder="Name this creation" />
              </Field>
              <Field label="Description" htmlFor="creation-description" hint="Optional">
                <Textarea
                  id="creation-description"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  maxLength={4000}
                  placeholder="What is this work, and what should the record capture?"
                />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Asset type" htmlFor="asset-type">
                  <Select id="asset-type" value={assetType} onChange={(event) => setAssetType(event.target.value)}>
                    {assetTypeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Creation date" htmlFor="creation-date" hint="Optional">
                  <Input id="creation-date" type="datetime-local" value={creationDate} onChange={(event) => setCreationDate(event.target.value)} />
                </Field>
              </div>
              <Field label="Tags" htmlFor="creation-tags" hint="Comma separated · up to 12">
                <Input id="creation-tags" value={tags} onChange={(event) => setTags(event.target.value)} placeholder="illustration, client-work, campaign" />
              </Field>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>3. Assign ownership</CardTitle>
              <CardDescription>
                Register the creation under your own account, or attribute it to a team you own or belong to.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <OwnershipScopePicker
                organization={organization}
                scopeToOrganization={scopeToOrganization}
                onChange={setScopeToOrganization}
                onCreateOrganization={createOrganization}
                creating={creatingOrganization}
                newName={newOrganizationName}
                onNameChange={setNewOrganizationName}
              />

              <Field label="Team" htmlFor="creation-team" hint="Optional">
                <Select id="creation-team" value={teamId} onChange={(event) => setTeamId(event.target.value)}>
                  <option value="">Personal — no team</option>
                  {selectableTeams.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name} · {titleCase(team.my_role || "member")} · {team.member_count}{" "}
                      {team.member_count === 1 ? "member" : "members"}
                    </option>
                  ))}
                </Select>
              </Field>

              {teamsQuery.isLoading && (
                <p className="text-[11px] text-muted-foreground">Loading your team workspaces...</p>
              )}

              {!teamsQuery.isLoading && selectableTeams.length === 0 && (
                <div className="rounded-lg border border-dashed border-border bg-background/30 p-3">
                  <p className="text-[11px] leading-relaxed text-muted-foreground">
                    You do not belong to a team yet. Create one from{" "}
                    <Link to="/teams" className="font-medium text-foreground underline underline-offset-2">
                      Teams
                    </Link>{" "}
                    to register shared work and split ownership.
                  </p>
                </div>
              )}

              {selectedTeam && (
                <div className="rounded-lg border border-foreground/20 bg-accent/15 p-3">
                  <div className="flex items-center gap-2 text-xs font-semibold">
                    <Users className="size-3.5" /> {selectedTeam.name}
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                    The record is attributed to this team. Every active member can open it from the team
                    workspace, and if the team has an approved allocation the ownership split is recorded with
                    the record.
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {selectedTeam.members
                      .filter((member) => member.status === "active")
                      .map((member) => (
                        <span
                          key={member.id}
                          className="rounded-md border border-border/70 px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                        >
                          {member.display_name || member.email} · {titleCase(member.role)}
                        </span>
                      ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>4. Choose disclosure</CardTitle>
              <CardDescription>Privacy controls what public verification can reveal. Private files are never served publicly.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {privacyOptions.map((option) => (
                <label
                  key={option.value}
                  className={cn(
                    "flex cursor-pointer items-start gap-3 rounded-lg border p-3.5 transition-colors",
                    privacy === option.value ? "border-blue-500/60 bg-blue-500/5" : "border-border/70 hover:bg-accent/40",
                  )}
                >
                  <input
                    type="radio"
                    name="privacy"
                    value={option.value}
                    checked={privacy === option.value}
                    onChange={() => setPrivacy(option.value)}
                    className="mt-1 size-4 accent-blue-500"
                  />
                  <span>
                    <span className="block text-sm font-medium">{option.label}</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">{option.hint}</span>
                  </span>
                </label>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4 xl:sticky xl:top-24 xl:self-start">
          <Card>
            <CardHeader>
              <CardTitle>Registration summary</CardTitle>
              <CardDescription>Review before writing the commitment.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <InfoRow label="File">{file ? file.name : "No file selected"}</InfoRow>
              <InfoRow label="Size">{file ? formatBytes(file.size) : "—"}</InfoRow>
              <InfoRow label="Type">{titleCase(assetType)}</InfoRow>
              <InfoRow label="Ownership">
                {selectedTeam
                  ? selectedTeam.name
                  : organization && scopeToOrganization
                    ? organization.name
                    : "My own (personal)"}
              </InfoRow>
              <OwnershipScopePicker
                organization={organization}
                scopeToOrganization={scopeToOrganization}
                onChange={setScopeToOrganization}
                onCreateOrganization={createOrganization}
                creating={creatingOrganization}
                newName={newOrganizationName}
                onNameChange={setNewOrganizationName}
              />
              <InfoRow label="Privacy">{titleCase(privacy)}</InfoRow>
              <InfoRow label="Tags">{tags.split(",").map((tag) => tag.trim()).filter(Boolean).length || "None"}</InfoRow>
              <InfoRow label="Duplicate check">
                {checkingDuplicates
                  ? "Checking"
                  : hasDuplicates(duplicates)
                    ? `${duplicates?.exact_matches.length ?? 0} identical, ${duplicates?.similar_matches.length ?? 0} similar`
                    : "No match found"}
              </InfoRow>
              <div className="rounded-lg border border-border/60 bg-background/30 p-3">
                <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  <Lock className="size-3.5" />
                  Storage guarantees
                </div>
                <ul className="mt-2 space-y-1.5 text-[11px] leading-relaxed text-muted-foreground">
                  <li className="flex gap-2"><ShieldCheck className="mt-0.5 size-3 shrink-0 text-foreground" /> Each chunk verified before assembly</li>
                  <li className="flex gap-2"><ShieldCheck className="mt-0.5 size-3 shrink-0 text-foreground" /> Malware scanner gate before storage</li>
                  <li className="flex gap-2"><ShieldCheck className="mt-0.5 size-3 shrink-0 text-foreground" /> AES-256-GCM encrypted at rest</li>
                  <li className="flex gap-2"><ShieldCheck className="mt-0.5 size-3 shrink-0 text-foreground" /> Duplicate and similarity detection</li>
                  <li className="flex gap-2"><ShieldCheck className="mt-0.5 size-3 shrink-0 text-foreground" /> Append-only ledger transaction</li>
                </ul>
              </div>

              {progress && (
                <div className="rounded-lg border border-foreground/20 bg-blue-500/5 p-3">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-medium text-muted-foreground">{titleCase(progress.phase)}</span>
                    <span className="text-muted-foreground">{progress.percent}%</span>
                  </div>
                  <Progress value={progress.percent} className="my-2" />
                  <p className="text-[11px] text-muted-foreground">{progress.message}</p>
                  {progress.chunkSha256 && (
                    <div className="mt-2">
                      <HashValue value={progress.chunkSha256} label="Chunk SHA-256" head={12} tail={8} />
                    </div>
                  )}
                </div>
              )}

              <Button type="submit" variant="gradient" className="w-full" loading={busy} disabled={!file || hashingFile}>
                <Award />{" "}
                {busy ? "Registering" : hasDuplicates(duplicates) ? "Register and flag duplicate" : "Register and commit"}
              </Button>
              <p className="text-center text-[10px] leading-relaxed text-muted-foreground">
                Registering creates an immutable local record. It does not publish your file.
              </p>
            </CardContent>
          </Card>

          <Alert variant="info">
            <AlertDescription>
              <strong className="block text-xs font-semibold">Proof scope</strong>
              <span className="mt-1 block text-[11px] leading-relaxed">
                The default proof proves knowledge of the commitment opening. File fingerprint equality is checked outside the sigma proof and is documented explicitly.
              </span>
            </AlertDescription>
          </Alert>
        </div>
      </form>
    </div>
  );
}
