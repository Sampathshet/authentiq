import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CheckCircle2,
  Fingerprint,
  KeyRound,
  Lock,
  ShieldCheck,
  ShieldQuestion,
  ShieldX,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { BrandLogo } from "@/components/BrandLogo";
import { HashValue } from "@/components/common/hash-value";
import { OwnershipDna } from "@/components/common/ownership-dna";
import { LedgerBadge, StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, extractErrorMessage } from "@/lib/api";
import { formatDate, titleCase } from "@/lib/format";

interface PublicRecord {
  registration_reference?: string | null;
  title?: string | null;
  fingerprint?: string | null;
  registered_at?: string | null;
  commitment?: string | null;
  ledger_mode?: string | null;
  ledger_tx_id?: string | null;
  organization?: string | null;
}

interface PublicVerification {
  kind: "verification_request" | "registration" | "idea";
  verification_id: string;
  status: string;
  result?: string | null;
  message?: string | null;
  available?: boolean;
  expires_at?: string;
  verified_at?: string | null;
  uses?: number;
  max_uses?: number;
  requires_proof?: boolean;
  disclosure?: Record<string, boolean>;
  public_record: PublicRecord;
  proof_system?: string;
  privacy_note?: string;
}

interface VerifyResponse {
  valid: boolean;
  result?: string;
  message: string;
  verification_id: string;
  verified_at?: string | null;
  registration_reference?: string | null;
  fingerprint?: string | null;
  registered_at?: string | null;
  ledger_mode?: string | null;
  ledger_tx_id?: string | null;
  uses?: number;
  max_uses?: number;
  statement: string;
}

export default function PublicVerifyPage() {
  const { verificationId } = useParams<{ verificationId: string }>();
  const [packageText, setPackageText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<VerifyResponse | null>(null);

  const verificationQuery = useQuery({
    queryKey: ["public-verification", verificationId],
    queryFn: () => api.publicGet<PublicVerification>(`/public/verify/${verificationId}`),
    enabled: !!verificationId,
    retry: false,
  });

  const verification = verificationQuery.data;
  const alreadyVerified = verification?.status === "verified" || verification?.result === "valid";
  const blocked = useMemo(() => ["revoked", "expired", "private"].includes(verification?.status || ""), [verification]);

  const submitProof = async () => {
    if (!verificationId) return;
    let parsed: unknown;
    try {
      parsed = JSON.parse(packageText);
    } catch {
      toast.error("The proof package is not valid JSON");
      return;
    }
    setBusy(true);
    try {
      const response = await api.publicPost<VerifyResponse>(`/public/verify/${verificationId}`, {
        proof_package: parsed,
      });
      setResult(response);
      if (response.valid) toast.success("Ownership proof verified");
      else toast.error(response.message);
      verificationQuery.refetch();
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const readFile = async (file: File | null) => {
    if (!file) return;
    try {
      const text = await file.text();
      setPackageText(text);
      toast.success("Proof package loaded");
    } catch {
      toast.error("The file could not be read");
    }
  };

  const record = verification?.public_record;
  const showResult = result || (alreadyVerified && verification?.status === "verified");

  return (
    <div className="relative min-h-screen overflow-hidden bg-foreground text-foreground">
      <div className="pointer-events-none absolute inset-0 -z-0 grid-bg opacity-40" />
      <div className="pointer-events-none absolute -left-24 top-0 -z-0 size-[420px] rounded-full bg-blue-600/15 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 bottom-0 -z-0 size-[420px] rounded-full bg-violet-600/15 blur-3xl" />

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 py-8 md:px-8">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-2.5">
            <BrandLogo className="size-10 rounded-xl shadow-lg ring-1 ring-white/10" />
            <span>
              <span className="block text-sm font-semibold tracking-[0.2em]">AUTHENTIQ</span>
              <span className="block text-[10px] uppercase tracking-[0.16em] text-muted-foreground">Public verification</span>
            </span>
          </Link>
          <Button asChild variant="outline" size="sm" className="border-border bg-card text-foreground hover:bg-card">
            <Link to="/login">Sign in <ArrowRight /></Link>
          </Button>
        </header>

        <main className="mt-10 flex-1">
          {verificationQuery.isLoading && (
            <div className="rounded-xl border border-border bg-card p-10 text-center text-sm text-muted-foreground">
              Loading the verification record...
            </div>
          )}

          {verificationQuery.isError && (
            <Card className="border-border bg-card">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-foreground"><ShieldQuestion className="size-5 text-muted-foreground" /> Verification not found</CardTitle>
                <CardDescription className="text-muted-foreground">{extractErrorMessage(verificationQuery.error)}</CardDescription>
              </CardHeader>
              <CardContent className="text-xs leading-relaxed text-muted-foreground">
                The link may have been revoked, expired, or never existed. Ask the owner for a fresh silent-sharing link.
              </CardContent>
            </Card>
          )}

          {verification && (
            <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
              <div className="space-y-4">
                <Card className="border-border bg-card">
                  <CardHeader>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant="violet">{titleCase(verification.kind)}</Badge>
                      <StatusBadge status={verification.status} />
                      {record?.ledger_mode && <LedgerBadge mode={record.ledger_mode} />}
                    </div>
                    <CardTitle className="mt-2 text-foreground">
                      {record?.title || record?.registration_reference || verification.verification_id}
                    </CardTitle>
                    <CardDescription className="text-muted-foreground">
                      {verification.message || "This page shows only the record fields the owner chose to disclose."}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {record?.fingerprint && (
                      <div className="flex items-center justify-center rounded-lg border border-border bg-muted/40 py-3">
                        <OwnershipDna
                          value={record.fingerprint}
                          size={112}
                          label="Public ownership DNA"
                          downloadName={`AUTHENTIQ-${record.registration_reference || verification.verification_id}-dna.svg`}
                        />
                      </div>
                    )}
                    <div className="rounded-lg border border-border bg-muted/50 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Public record</p>
                      <div className="mt-2 space-y-2 text-xs">
                        {record?.registration_reference && (
                          <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-muted-foreground">Reference</span><code className="font-mono text-foreground">{record.registration_reference}</code></div>
                        )}
                        {record?.registered_at && (
                          <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-muted-foreground">Registered</span><span className="text-foreground">{formatDate(record.registered_at)}</span></div>
                        )}
                        {record?.fingerprint && (
                          <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-muted-foreground">SHA-256</span><HashValue value={record.fingerprint} label="Public fingerprint" head={16} tail={12} /></div>
                        )}
                        {record?.commitment && (
                          <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-muted-foreground">Commitment</span><HashValue value={record.commitment} label="Commitment" head={16} tail={12} /></div>
                        )}
                        {record?.ledger_tx_id && (
                          <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-muted-foreground">Ledger transaction</span><HashValue value={record.ledger_tx_id} label="Ledger transaction" head={14} tail={10} /></div>
                        )}
                        {record?.organization && (
                          <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-muted-foreground">Organization</span><span className="text-foreground">{record.organization}</span></div>
                        )}
                        {verification.expires_at && (
                          <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-muted-foreground">Link expires</span><span className="text-foreground">{formatDate(verification.expires_at)}</span></div>
                        )}
                        {typeof verification.uses === "number" && typeof verification.max_uses === "number" && (
                          <div className="flex flex-wrap items-center justify-between gap-2"><span className="text-muted-foreground">Uses</span><span className="text-foreground">{verification.uses} / {verification.max_uses}</span></div>
                        )}
                      </div>
                    </div>

                    {blocked && (
                      <Alert variant="destructive" className="border-foreground/30 bg-foreground/5 text-destructive">
                        <AlertDescription>
                          {verification.status === "expired" ? "This verification link has expired." : verification.status === "revoked" ? "The owner revoked this verification link." : "This record is private. Request a fresh link from the owner."}
                        </AlertDescription>
                      </Alert>
                    )}

                    {verification.kind === "verification_request" && verification.requires_proof && !blocked && (
                      <div className="space-y-2">
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Submit proof package</p>
                        <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-border bg-muted/40 px-4 py-4 text-xs text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground">
                          <Upload className="size-4" />
                          Load a .json proof package
                          <input type="file" accept="application/json,.json" className="hidden" onChange={(event) => readFile(event.target.files?.[0] || null)} />
                        </label>
                        <Textarea
                          value={packageText}
                          onChange={(event) => setPackageText(event.target.value)}
                          className="min-h-[150px] border-border bg-muted/50 font-mono text-[10px] text-muted-foreground"
                          placeholder="Paste the AUTHENTIQ-VERIFICATION-PACKAGE-V1 JSON here"
                        />
                        <Button onClick={submitProof} loading={busy} disabled={!packageText.trim()} className="w-full">
                          <ShieldCheck /> Verify proof
                        </Button>
                      </div>
                    )}

                    {showResult && (
                      <div className={`rounded-lg border p-4 ${result ? (result.valid ? "border-foreground/25 bg-accent/25" : "border-foreground/30 bg-foreground/5") : "border-foreground/25 bg-accent/25"}`}>
                        <div className="flex items-center gap-2">
                          {result?.valid === false ? <ShieldX className="size-5 text-destructive" /> : <CheckCircle2 className="size-5 text-foreground" />}
                          <p className={`text-sm font-semibold ${result?.valid === false ? "text-destructive" : "text-foreground"}`}>
                            {result?.valid === false ? "Proof rejected" : "Ownership proof verified"}
                          </p>
                        </div>
                        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                          {result?.message || "A valid proof was previously recorded for this verification request."}
                        </p>
                        {result?.statement && <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">{result.statement}</p>}
                        {(result?.verified_at || verification.verified_at) && (
                          <p className="mt-1 text-[10px] text-foreground">Verified {formatDate(result?.verified_at || verification.verified_at)}</p>
                        )}
                      </div>
                    )}

                    {verification.kind !== "verification_request" && (
                      <Alert variant="info" className="border-foreground/20 bg-accent/15 text-foreground">
                        <AlertDescription>
                          This is public registration metadata. A zero-knowledge ownership proof requires a silent-sharing link created by the record owner.
                        </AlertDescription>
                      </Alert>
                    )}
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-4">
                <Card className="border-border bg-card">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-sm text-foreground"><KeyRound className="size-4 text-foreground" /> What this page proves</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 text-[11px] leading-relaxed text-muted-foreground">
                    <p><span className="font-medium text-foreground">Disclosed:</span> only the fields the owner allowed. Private files, passwords, and the commitment opening are never exposed.</p>
                    <p><span className="font-medium text-foreground">Proof:</span> the sigma proof demonstrates knowledge of the Pedersen commitment opening over BN254 G1. The file fingerprint is compared separately against the registered SHA-256.</p>
                    <p><span className="font-medium text-foreground">Bound:</span> the challenge nonce, registration reference, fingerprint, and commitment are bound into the Fiat–Shamir transcript. A stale or altered package fails.</p>
                    {verification.proof_system && <p className="font-mono text-[10px] text-muted-foreground">{verification.proof_system}</p>}
                  </CardContent>
                </Card>

                <Card className="border-foreground/20 bg-secondary">
                  <CardContent className="pt-5 text-[11px] leading-relaxed text-amber-100/80">
                    <p className="flex items-center gap-2 font-semibold text-foreground"><Fingerprint className="size-4" /> Ledger transparency</p>
                    <p className="mt-1.5">
                      {record?.ledger_mode === "polygon" ? "This record is anchored on Polygon Amoy." : "This record is stored in a local append-only simulation. No public blockchain transaction is claimed."}
                    </p>
                  </CardContent>
                </Card>

                {verification.privacy_note && (
                  <p className="flex items-start gap-1.5 px-1 text-[10px] leading-relaxed text-muted-foreground"><Lock className="mt-0.5 size-3 shrink-0" /> {verification.privacy_note}</p>
                )}
              </div>
            </div>
          )}
        </main>

        <footer className="mt-10 border-t border-border pt-4 text-[10px] text-muted-foreground">
          AUTHENTIQ public verification · The platform organizes cryptographic evidence and does not provide legal advice.
        </footer>
      </div>
    </div>
  );
}
