import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Copy,
  Fingerprint,
  KeyRound,
  Link2,
  Lock,
  RefreshCw,
  ShieldCheck,
  ShieldX,
  Sparkles,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader, ErrorState, LoadingBlock, EmptyState } from "@/components/common/page-states";
import { FileDropzone } from "@/components/common/file-dropzone";
import { HashValue } from "@/components/common/hash-value";
import { StatusBadge, LedgerBadge } from "@/components/common/status-badge";
import { Field } from "@/components/common/field";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Select } from "@/components/ui/select";
import { api, extractErrorMessage, sha256Hex } from "@/lib/api";
import type { Paginated, Registration, ShareItem } from "@/lib/types";
import { formatDate, proofStatement, relativeTime, titleCase } from "@/lib/format";
import { cn } from "@/lib/utils";

interface Challenge {
  challenge_id: string;
  nonce: string;
  expires_at: string;
  registration_id: string;
  fingerprint: string;
  commitment: string;
  proof_system: string;
  statement: string;
}

interface GeneratedProof {
  proof_id: string;
  proof: Record<string, unknown>;
  public_signals: Record<string, unknown>;
  scheme: string;
  statement: string;
  expires_at: string;
}

interface VerifyResult {
  valid: boolean;
  message: string;
  proof_system?: string;
  registration_id: string;
  verified_at?: string | null;
  statement: string;
}

const steps = [
  { key: "challenge", label: "Request a one-time challenge", detail: "The server issues a nonce bound to the registration." },
  { key: "fingerprint", label: "Match the original file", detail: "SHA-256 is computed in your browser and compared to the record." },
  { key: "proof", label: "Generate the sigma proof", detail: "A real BN254 Schnorr proof is created for the commitment opening." },
  { key: "verify", label: "Verify on the server", detail: "The verifier checks the proof, nonce, and public signals." },
];

export default function AnonymousVerificationPage() {
  const [params] = useSearchParams();
  const [selected, setSelected] = useState(params.get("registration") || "");
  const [file, setFile] = useState<File | null>(null);
  const [localHash, setLocalHash] = useState<string | null>(null);
  const [hashing, setHashing] = useState(false);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [generated, setGenerated] = useState<GeneratedProof | null>(null);
  const [verification, setVerification] = useState<VerifyResult | null>(null);
  const [challengeBusy, setChallengeBusy] = useState(false);
  const [proofBusy, setProofBusy] = useState(false);
  const [verifyBusy, setVerifyBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const registrationsQuery = useQuery({
    queryKey: ["registrations", "verification-options"],
    queryFn: () => api.get<Paginated<Registration>>("/registrations?page_size=100&sort=recent"),
  });
  const sharesQuery = useQuery({ queryKey: ["shares"], queryFn: () => api.get<{ items: ShareItem[] }>("/sharing") });

  const registrations = registrationsQuery.data?.items || [];
  const registration = useMemo(
    () => registrations.find((item) => item.id === selected || item.registration_id === selected) || null,
    [registrations, selected],
  );

  useEffect(() => {
    if (!selected && registrations.length) setSelected(registrations[0].id);
  }, [selected, registrations]);

  useEffect(() => {
    let active = true;
    if (!file) {
      setLocalHash(null);
      return;
    }
    setHashing(true);
    setLocalHash(null);
    file
      .arrayBuffer()
      .then((buffer) => sha256Hex(buffer))
      .then((hash) => active && setLocalHash(hash))
      .catch(() => active && setLocalHash(null))
      .finally(() => active && setHashing(false));
    return () => {
      active = false;
    };
  }, [file]);

  useEffect(() => {
    setChallenge(null);
    setGenerated(null);
    setVerification(null);
    setError(null);
  }, [selected]);

  const fingerprintMatches = !!registration && !!localHash && localHash === registration.sha256;

  const requestChallenge = async () => {
    if (!registration) return;
    setChallengeBusy(true);
    setError(null);
    try {
      const response = await api.post<Challenge>("/zkp/challenge", {
        registration_id: registration.registration_id,
        purpose: "proof",
      });
      setChallenge(response);
      setGenerated(null);
      setVerification(null);
      toast.success("One-time challenge issued");
    } catch (caught) {
      setError(extractErrorMessage(caught));
    } finally {
      setChallengeBusy(false);
    }
  };

  const generate = async () => {
    if (!registration || !challenge || !localHash) return;
    if (!fingerprintMatches) {
      toast.error("The selected file does not match the registered fingerprint");
      return;
    }
    setProofBusy(true);
    setError(null);
    try {
      const response = await api.post<GeneratedProof>("/zkp/generate", {
        registration_id: registration.registration_id,
        challenge_id: challenge.challenge_id,
        file_sha256: localHash,
      });
      setGenerated(response);
      toast.success("Proof generated. The private opening never left the server.");
    } catch (caught) {
      setError(extractErrorMessage(caught));
    } finally {
      setProofBusy(false);
    }
  };

  const verify = async () => {
    if (!registration || !challenge || !generated) return;
    setVerifyBusy(true);
    setError(null);
    try {
      const response = await api.post<VerifyResult>("/zkp/verify", {
        registration_id: registration.registration_id,
        nonce: challenge.nonce,
        proof: generated.proof,
        public_signals: generated.public_signals,
      });
      setVerification(response);
      if (response.valid) toast.success("Ownership proof verified");
      else toast.error(response.message);
    } catch (caught) {
      setError(extractErrorMessage(caught));
    } finally {
      setVerifyBusy(false);
    }
  };

  const revokeShare = async (verificationId: string) => {
    try {
      await api.delete(`/sharing/${verificationId}`);
      toast.success("Verification link revoked");
      sharesQuery.refetch();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    }
  };

  const activeStep = verification ? 4 : generated ? 3 : fingerprintMatches && challenge ? 2 : challenge ? 1 : 0;

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Zero-knowledge verification"
        title="Prove ownership without publishing the work"
        description="Select the original file, generate a fresh challenge, and run a real BN254 Schnorr proof. The verifier learns that you can open the commitment, not what the file contains."
        actions={
          <Badge variant="violet" className="h-7 px-3">
            <KeyRound className="size-3" /> AUTHENTIQ-SCHNORR-BN254-G1-V1
          </Badge>
        }
      />

      {registrationsQuery.isLoading && <LoadingBlock rows={5} />}
      {registrationsQuery.isError && <ErrorState error={registrationsQuery.error} onRetry={() => registrationsQuery.refetch()} />}

      {!registrationsQuery.isLoading && !registrations.length && (
        <EmptyState
          icon={<Fingerprint className="size-5" />}
          title="Register a creation first"
          description="Ownership proofs are bound to a registered fingerprint and commitment. Register a file to begin."
          action={<Button asChild><Link to="/register">Register creation</Link></Button>}
        />
      )}

      {!!registrations.length && (
        <div className="grid gap-4 xl:grid-cols-[1.25fr_1fr]">
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Verification workspace</CardTitle>
                <CardDescription>All four steps execute against the live API. Nothing is simulated.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Field label="Registered creation" htmlFor="verification-registration">
                  <Select
                    id="verification-registration"
                    value={registration?.id || ""}
                    onChange={(event) => setSelected(event.target.value)}
                  >
                    {registrations.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.title} · {item.registration_id}
                      </option>
                    ))}
                  </Select>
                </Field>

                {registration && (
                  <div className="rounded-lg border border-border/60 bg-background/30 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={registration.status} />
                      <LedgerBadge mode={registration.ledger_mode} />
                      <Badge variant="outline">{titleCase(registration.asset_type)}</Badge>
                    </div>
                    <div className="mt-2 space-y-1.5 text-[11px]">
                      <div className="flex items-center gap-2">
                        <span className="w-20 shrink-0 text-muted-foreground">Fingerprint</span>
                        <HashValue value={registration.sha256} label="SHA-256" head={16} tail={12} />
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-20 shrink-0 text-muted-foreground">Commitment</span>
                        <HashValue value={registration.commitment} label="Commitment" head={16} tail={12} />
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-20 shrink-0 text-muted-foreground">Ledger</span>
                        <HashValue value={registration.ledger_tx_id} label="Ledger transaction" head={14} tail={10} />
                      </div>
                    </div>
                  </div>
                )}

                <Field label="Original file" htmlFor="verification-file" hint="Hashed locally; not uploaded">
                  <FileDropzone
                    file={file}
                    onFileChange={setFile}
                    disabled={proofBusy}
                    hint="Select the exact original file. A matching SHA-256 is required before the server will issue a proof."
                  />
                </Field>

                {file && (
                  <div className={cn("rounded-lg border p-3", fingerprintMatches ? "border-foreground/25 bg-accent/15" : localHash ? "border-foreground/25 bg-secondary" : "border-border/60")}>
                    <div className="flex items-center gap-2 text-xs font-medium">
                      {hashing ? (
                        <>Computing SHA-256 in your browser...</>
                      ) : fingerprintMatches ? (
                        <><CheckCircle2 className="size-4 text-foreground" /> Fingerprint matches the registered original</>
                      ) : localHash ? (
                        <><AlertTriangle className="size-4 text-foreground" /> Fingerprint does not match</>
                      ) : (
                        <><AlertTriangle className="size-4 text-foreground" /> Could not hash the file</>
                      )}
                    </div>
                    {localHash && <div className="mt-2"><HashValue value={localHash} label="Local SHA-256" head={18} tail={12} /></div>}
                    {localHash && !fingerprintMatches && (
                      <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">
                        A different file cannot prove knowledge of this record. This is a real check, not a UI formality.
                      </p>
                    )}
                  </div>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" onClick={requestChallenge} loading={challengeBusy} disabled={!registration}>
                    <RefreshCw /> {challenge ? "New challenge" : "Request challenge"}
                  </Button>
                  <Button onClick={generate} loading={proofBusy} disabled={!challenge || !fingerprintMatches}>
                    <Sparkles /> Generate proof
                  </Button>
                  <Button variant="success" onClick={verify} loading={verifyBusy} disabled={!generated}>
                    <ShieldCheck /> Verify proof
                  </Button>
                </div>

                {challenge && (
                  <div className="rounded-lg border border-foreground/20 bg-blue-500/5 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-muted-foreground">Challenge active</span>
                      <span className="text-[10px] text-muted-foreground">Expires {formatDate(challenge.expires_at, "MMM d, HH:mm:ss")}</span>
                    </div>
                    <div className="mt-2"><HashValue value={challenge.nonce} label="Challenge nonce" head={18} tail={12} /></div>
                    <p className="mt-1.5 text-[10px] leading-relaxed text-muted-foreground">
                      Challenges are single-use. Requesting a new nonce invalidates prior unused challenges for this purpose.
                    </p>
                  </div>
                )}

                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Flow status</CardTitle>
                <CardDescription>The final result comes from the server verifier, not from this page.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-0">
                {steps.map((step, index) => {
                  const complete = index < activeStep;
                  const current = index === activeStep;
                  return (
                    <div key={step.key} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div
                          className={cn(
                            "flex size-7 items-center justify-center rounded-full border text-[10px] font-bold",
                            complete ? "border-foreground/25 bg-accent/25 text-foreground" : current ? "border-foreground/30 bg-accent/15 text-foreground" : "border-border text-muted-foreground",
                          )}
                        >
                          {complete ? <CheckCircle2 className="size-3.5" /> : current ? <Circle className="size-3.5 animate-pulse" /> : index + 1}
                        </div>
                        {index < steps.length - 1 && <div className={cn("my-1 h-8 w-px", complete ? "bg-emerald-500/30" : "bg-border")} />}
                      </div>
                      <div className="pb-3">
                        <p className={cn("text-xs font-medium", complete ? "text-foreground" : current ? "text-foreground" : "text-muted-foreground")}>{step.label}</p>
                        <p className="text-[11px] text-muted-foreground">{step.detail}</p>
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Verification result</CardTitle>
                <CardDescription>Cryptographic outcome for the most recent attempt.</CardDescription>
              </CardHeader>
              <CardContent>
                {verification ? (
                  <div className={cn("rounded-lg border p-4", verification.valid ? "border-foreground/25 bg-accent/15" : "border-foreground/30 bg-red-500/5")}>
                    <div className="flex items-center gap-2">
                      {verification.valid ? <ShieldCheck className="size-5 text-foreground" /> : <ShieldX className="size-5 text-destructive" />}
                      <p className={cn("text-sm font-semibold", verification.valid ? "text-foreground" : "text-destructive")}>
                        {verification.valid ? "Proof valid" : "Proof rejected"}
                      </p>
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{verification.message}</p>
                    {verification.verified_at && <p className="mt-2 text-[11px] text-foreground">Verified {formatDate(verification.verified_at)}</p>}
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-border/70 p-6 text-center">
                    <ShieldCheck className="mx-auto mb-2 size-6 text-muted-foreground" />
                    <p className="text-xs text-muted-foreground">No verification has run in this workspace yet.</p>
                  </div>
                )}

                {generated && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between">
                      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Proof package</p>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          navigator.clipboard.writeText(JSON.stringify({ proof: generated.proof, public_signals: generated.public_signals }, null, 2));
                          toast.success("Proof JSON copied");
                        }}
                      >
                        <Copy /> Copy
                      </Button>
                    </div>
                    <pre className="mt-1 max-h-64 overflow-auto rounded-lg border border-border/60 bg-background/50 p-3 font-mono text-[10px] leading-relaxed text-muted-foreground">
{JSON.stringify({ scheme: generated.scheme, proof: generated.proof, public_signals: generated.public_signals }, null, 2)}
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>

            <Alert variant="info">
              <AlertDescription>
                <strong className="block text-xs font-semibold">What this proves</strong>
                <span className="mt-1 block text-[11px] leading-relaxed">{proofStatement()}</span>
              </AlertDescription>
            </Alert>

            <Card>
              <CardHeader>
                <CardTitle>Proof parameters</CardTitle>
                <CardDescription>What the verifier receives and what it does not.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-[11px] leading-relaxed text-muted-foreground">
                <p><span className="font-medium text-foreground">Disclosed:</span> the registration ID, the file fingerprint, the commitment, the challenge nonce, and the proof transcript.</p>
                <p><span className="font-medium text-foreground">Withheld:</span> the secret opening of the commitment. The file itself is never uploaded during verification.</p>
                <p><span className="font-medium text-foreground">External check:</span> the circuit proves knowledge of the commitment opening. Equality between the registered file hash and the hash you supply is checked by the server outside the proof.</p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Silent sharing links</CardTitle>
          <CardDescription>Links you created from any registration. Each is expiring and usage-limited.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-2 md:grid-cols-2">
          {sharesQuery.data?.items.length ? (
            sharesQuery.data.items.map((share) => (
              <div key={share.id} className="rounded-lg border border-border/60 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={share.status} />
                    <Badge variant="outline">{share.registration_label}</Badge>
                  </div>
                  <span className="text-[10px] text-muted-foreground">{share.uses}/{share.max_uses} uses</span>
                </div>
                <p className="mt-1.5 truncate text-xs font-medium">{share.registration_title}</p>
                <p className="mt-1 break-all font-mono text-[10px] text-muted-foreground">{`${window.location.origin}/verify/${share.verification_id}`}</p>
                <p className="mt-1 text-[10px] text-muted-foreground">Created {relativeTime(share.created_at)} · expires {formatDate(share.expires_at)}</p>
                <div className="mt-2 flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => { navigator.clipboard.writeText(`${window.location.origin}/verify/${share.verification_id}`); toast.success("Link copied"); }}>
                    <Link2 /> Copy
                  </Button>
                  {share.status !== "revoked" && (
                    <ConfirmDialog
                      trigger={<Button size="sm" variant="ghost" className="text-destructive"><Trash2 /> Revoke</Button>}
                      title="Revoke this verification link?"
                      description="Future verification attempts will receive a revoked response. Proofs already downloaded cannot be recalled."
                      confirmLabel="Revoke link"
                      destructive
                      onConfirm={() => revokeShare(share.verification_id)}
                    />
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full py-6 text-center text-xs text-muted-foreground">
              No sharing links yet. Open a registration record to create one with disclosure controls.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
