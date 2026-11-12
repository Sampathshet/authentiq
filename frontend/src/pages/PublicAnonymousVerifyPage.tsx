import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  Copy,
  Eye,
  EyeOff,
  Fingerprint,
  KeyRound,
  Loader2,
  Lock,
  RefreshCw,
  ShieldCheck,
  ShieldX,
  Sparkles,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { BrandLogo } from "@/components/BrandLogo";
import { FileDropzone } from "@/components/common/file-dropzone";
import { HashValue } from "@/components/common/hash-value";
import { Field } from "@/components/common/field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, extractErrorMessage, sha256File } from "@/lib/api";
import { generateSchnorrProof, parseVerificationKey } from "@/lib/schnorr";
import { cn } from "@/lib/utils";

interface AnonymousChallenge {
  challenge_id: string;
  nonce: string;
  expires_at: string;
  registration_id: string;
  fingerprint: string;
  commitment: string;
  poseidon_commitment: string;
  proof_system: string;
  statement: string;
  challenge_minutes: number;
}

interface AnonymousResult {
  valid: boolean;
  message: string;
  registration_id: string;
  proof_system: string;
  verified_at: string | null;
  statement: string;
  checks: {
    registration_exists: boolean;
    file_fingerprint_matches: boolean;
    challenge_valid: boolean;
    proof_valid: boolean;
    private_key_disclosed: boolean;
    login_required: boolean;
  };
  public_record: {
    fingerprint: string;
    commitment: string;
    registered_at: string | null;
    ledger_tx_id: string | null;
    ledger_mode: string;
  };
}

const steps = [
  { title: "Registration ID", detail: "The public reference printed on the certificate." },
  { title: "Private key", detail: "The creator-only credential issued at registration." },
  { title: "Original file", detail: "Hashed locally in this browser; the file is never uploaded." },
  { title: "Challenge + proof", detail: "A one-time nonce, then a BN254 Schnorr proof generated here." },
];

const CHECK_LABELS: Array<[keyof AnonymousResult["checks"], string]> = [
  ["registration_exists", "Registration exists"],
  ["file_fingerprint_matches", "File fingerprint matches"],
  ["challenge_valid", "Challenge valid"],
  ["proof_valid", "Proof valid"],
  ["private_key_disclosed", "Private key disclosed"],
  ["login_required", "User login required"],
];

export default function PublicAnonymousVerifyPage() {
  const [params] = useSearchParams();
  const [reference, setReference] = useState(params.get("registration") || "");
  const [keyInput, setKeyInput] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [localHash, setLocalHash] = useState<string | null>(null);
  const [hashing, setHashing] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnonymousResult | null>(null);
  const [fingerprintCheck, setFingerprintCheck] = useState<{ registered: boolean; records: number } | null>(null);
  const [checkingFingerprint, setCheckingFingerprint] = useState(false);

  const parsedKey = useMemo(() => parseVerificationKey(keyInput), [keyInput]);
  const keyLooksValid = !keyInput.trim() || parsedKey !== null;
  const ready = !!reference.trim() && parsedKey !== null && !!file && !!localHash && !hashing && !working;

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
      .then((buffer) =>
        crypto.subtle
          .digest("SHA-256", buffer)
          .then((digest) =>
            Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join(""),
          ),
      )
      .then((hash) => {
        if (active) setLocalHash(hash);
      })
      .catch(() => {
        if (active) setLocalHash(null);
      })
      .finally(() => {
        if (active) setHashing(false);
      });
    return () => {
      active = false;
    };
  }, [file]);

  useEffect(() => {
    setResult(null);
    setError(null);
    setFingerprintCheck(null);
  }, [reference, keyInput, file]);

  const checkPublicFingerprint = async () => {
    if (!localHash) return;
    setCheckingFingerprint(true);
    try {
      const response = await api.publicPost<{ registered: boolean; records: number }>(
        "/public/fingerprints/check",
        { sha256: localHash },
      );
      setFingerprintCheck(response);
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setCheckingFingerprint(false);
    }
  };

  const runVerification = async () => {
    if (!parsedKey) {
      setError("The private verification key must look like aqv1_<64 hex characters>_<64 hex characters>.");
      return;
    }
    if (!file) {
      setError("Select the original file to hash.");
      return;
    }
    setWorking(true);
    setResult(null);
    setError(null);
    try {
      setPhase("Hashing the file locally");
      const fileSha256 = localHash || (await sha256File(file));

      setPhase("Matching the fingerprint and requesting a one-time challenge");
      const challenge = await api.publicPost<AnonymousChallenge>("/public/verify/anonymous/challenge", {
        registration_id: reference.trim(),
        file_sha256: fileSha256,
      });

      setPhase("Generating the BN254 Schnorr proof in this browser");
      const proof = await generateSchnorrProof({
        key: parsedKey,
        fingerprint: challenge.fingerprint,
        registrationId: challenge.registration_id,
        nonce: challenge.nonce,
        commitment: challenge.commitment,
      });

      setPhase("Verifying the proof on the AUTHENTIQ server");
      const response = await api.publicPost<AnonymousResult>("/public/verify/anonymous/verify", {
        challenge_id: challenge.challenge_id,
        proof,
      });
      setResult(response);
      if (response.valid) toast.success("Cryptographic ownership proof accepted");
      else toast.error(response.message);
    } catch (caught) {
      setError(extractErrorMessage(caught));
    } finally {
      setWorking(false);
      setPhase(null);
    }
  };

  const reset = () => {
    setResult(null);
    setError(null);
    setKeyInput("");
    setFile(null);
    setLocalHash(null);
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-40" />
      <div className="pointer-events-none absolute -right-40 top-0 size-[520px] rounded-full bg-accent/25 blur-[140px]" />

      <header className="relative border-b border-border/60">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-5 py-5">
          <Link to="/" className="flex items-center gap-3">
            <BrandLogo className="size-10 rounded-xl ring-1 ring-foreground/10" />
            <div>
              <p className="text-sm font-semibold tracking-[0.24em]">AUTHENTIQ</p>
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Public verification</p>
            </div>
          </Link>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="hidden sm:inline-flex">
              <Lock className="size-3" /> No account required
            </Badge>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/">Home</Link>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/login">
                Sign in <ArrowRight />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="relative mx-auto grid w-full max-w-6xl gap-8 px-5 py-10 lg:grid-cols-[0.95fr_1.05fr] lg:py-16">
        <section className="space-y-6">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-foreground/15 bg-accent/20 px-3 py-1 text-[11px] font-medium">
              <Sparkles className="size-3" /> Anonymous ownership verification
            </p>
            <h1 className="mt-4 text-4xl leading-[1.05] xl:text-5xl">
              Verify the claim.
              <br />
              <span className="text-gradient">Reveal nothing else.</span>
            </h1>
            <p className="mt-4 max-w-lg text-sm leading-relaxed text-muted-foreground">
              Prove that a registered creation belongs to the holder of its private credential — without an
              AUTHENTIQ account, without publishing the file, and without sending the key anywhere it can be
              read by the verifier.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {steps.map((step, index) => (
              <div key={step.title} className="rounded-xl border border-border/70 bg-card/70 p-3.5">
                <div className="flex items-center gap-2">
                  <span className="flex size-6 items-center justify-center rounded-full border border-foreground/20 bg-accent/20 text-[10px] font-bold">
                    {index + 1}
                  </span>
                  <p className="text-xs font-semibold">{step.title}</p>
                </div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-muted-foreground">{step.detail}</p>
              </div>
            ))}
          </div>

          <div className="space-y-3 rounded-xl border border-border/70 bg-secondary/40 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Three different things</p>
            <div className="space-y-2 text-[11px] leading-relaxed">
              <p>
                <span className="font-semibold text-foreground">Registration ID</span> identifies the record. It is
                public and printed on certificates.
              </p>
              <p>
                <span className="font-semibold text-foreground">SHA-256 fingerprint</span> identifies the exact file.
                Anyone may compare a public fingerprint; it is never a private credential.
              </p>
              <p>
                <span className="font-semibold text-foreground">Private verification key</span> proves knowledge of
                the commitment opening. It is issued once at registration and must stay with the creator.
              </p>
            </div>
          </div>

          <Alert variant="info">
            <AlertDescription>
              <strong className="block text-xs font-semibold">What the server learns</strong>
              <span className="mt-1 block text-[11px] leading-relaxed">
                The reference, the file fingerprint, and the public proof transcript. The private key is used only in
                this browser to build the proof; it is never sent to the server and never appears in the result.
              </span>
            </AlertDescription>
          </Alert>
        </section>

        <section className="space-y-4">
          <Card className="overflow-hidden">
            <CardHeader className="border-b border-border/60 bg-secondary/30">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <ShieldCheck className="size-4" /> Anonymous ownership verification
                  </CardTitle>
                  <CardDescription>Verify without revealing your identity.</CardDescription>
                </div>
                <Badge variant="violet" className="hidden shrink-0 sm:inline-flex">
                  BN254 · Schnorr
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 pt-5">
              <Field label="Registration reference ID" htmlFor="verify-reference" required hint="e.g. AQ-2026-1A2B3C4D">
                <Input
                  id="verify-reference"
                  value={reference}
                  onChange={(event) => setReference(event.target.value.toUpperCase())}
                  placeholder="AQ-2026-XXXXXXXX"
                  autoComplete="off"
                  spellCheck={false}
                  disabled={working}
                />
              </Field>

              <Field
                label="Private verification key"
                htmlFor="verify-key"
                required
                hint="Issued at registration"
                error={keyLooksValid ? undefined : "Expected aqv1_ followed by two 64-character hex values"}
              >
                <div className="relative">
                  <KeyRound className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="verify-key"
                    type={showKey ? "text" : "password"}
                    value={keyInput}
                    onChange={(event) => setKeyInput(event.target.value)}
                    placeholder="aqv1_…"
                    autoComplete="off"
                    spellCheck={false}
                    className="pl-9 pr-10 font-mono text-xs"
                    disabled={working}
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey((value) => !value)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                    aria-label={showKey ? "Hide key" : "Show key"}
                  >
                    {showKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                  </button>
                </div>
              </Field>

              <Field label="Original file" htmlFor="verify-file" required hint="Hashed locally; never uploaded">
                <FileDropzone
                  file={file}
                  onFileChange={setFile}
                  disabled={working}
                  hint="Select the exact original creation. The SHA-256 is computed in this browser and compared to the registered record."
                />
              </Field>

              {file && (
                <div
                  className={cn(
                    "rounded-lg border p-3",
                    hashing ? "border-border/60" : localHash ? "border-foreground/20 bg-accent/10" : "border-border/60",
                  )}
                >
                  <div className="flex items-center gap-2 text-xs font-medium">
                    {hashing ? (
                      <>
                        <Loader2 className="size-4 animate-spin" /> Computing SHA-256 in your browser…
                      </>
                    ) : localHash ? (
                      <>
                        <Fingerprint className="size-4" /> Local fingerprint ready
                      </>
                    ) : (
                      <>
                        <XCircle className="size-4" /> Could not hash this file
                      </>
                    )}
                  </div>
                  {localHash && (
                    <div className="mt-2 space-y-2">
                      <HashValue value={localHash} label="Local SHA-256" head={18} tail={12} />
                      <div className="flex flex-wrap items-center gap-2">
                        <Button size="sm" variant="ghost" onClick={checkPublicFingerprint} loading={checkingFingerprint}>
                          <Fingerprint /> Check public registry
                        </Button>
                        {fingerprintCheck && (
                          <span
                            className={cn(
                              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium",
                              fingerprintCheck.registered
                                ? "border-foreground/20 bg-accent/20 text-foreground"
                                : "border-border bg-secondary text-muted-foreground",
                            )}
                          >
                            {fingerprintCheck.registered ? <CheckCircle2 className="size-3.5" /> : <XCircle className="size-3.5" />}
                            {fingerprintCheck.registered
                              ? `Registered (${fingerprintCheck.records} record${fingerprintCheck.records === 1 ? "" : "s"})`
                              : "No registration for this fingerprint"}
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] leading-relaxed text-muted-foreground">
                        Existence checks are public and disclose no owner or title. The private ownership claim still
                        requires the key.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {working && phase && (
                <div className="rounded-lg border border-foreground/15 bg-secondary/60 p-3">
                  <div className="flex items-center gap-2 text-xs font-medium">
                    <Loader2 className="size-4 animate-spin" /> {phase}
                  </div>
                  <div className="mt-2 h-1 overflow-hidden rounded-full bg-border">
                    <div className="h-full w-1/2 animate-pulse rounded-full bg-foreground" />
                  </div>
                </div>
              )}

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button className="w-full" size="lg" onClick={runVerification} loading={working} disabled={!ready}>
                <ShieldCheck /> Verify ownership
              </Button>
              <p className="text-center text-[10px] leading-relaxed text-muted-foreground">
                No account login required · Private credential never exposed to the verifier
              </p>
            </CardContent>
          </Card>

          {result && (
            <Card className={cn("overflow-hidden border-2", result.valid ? "border-foreground/25" : "border-foreground/20")}>
              <CardHeader className={cn(result.valid ? "bg-accent/20" : "bg-secondary")}>
                <div className="flex items-start gap-3">
                  <div
                    className={cn(
                      "flex size-10 shrink-0 items-center justify-center rounded-xl",
                      result.valid ? "bg-accent text-accent-foreground" : "bg-foreground text-background",
                    )}
                  >
                    {result.valid ? <ShieldCheck className="size-5" /> : <ShieldX className="size-5" />}
                  </div>
                  <div className="min-w-0">
                    <CardTitle>{result.valid ? "Verification successful" : "Verification failed"}</CardTitle>
                    <CardDescription>
                      {result.valid ? "Cryptographic proof accepted" : "The server rejected the proof"}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 pt-4">
                <div className="space-y-1.5">
                  {CHECK_LABELS.map(([key, label]) => {
                    const raw = result.checks[key];
                    const positive = key === "private_key_disclosed" ? !raw : key === "login_required" ? !raw : raw;
                    const display = key === "private_key_disclosed" || key === "login_required" ? (raw ? "Yes" : "No") : raw ? "Yes" : "No";
                    return (
                      <div key={key} className="flex items-center justify-between gap-3 rounded-lg border border-border/60 px-3 py-2">
                        <span className="text-xs text-muted-foreground">{label}</span>
                        <span className={cn("inline-flex items-center gap-1.5 text-xs font-semibold", positive ? "text-foreground" : "text-destructive")}>
                          {positive ? <CheckCircle2 className="size-3.5" /> : <XCircle className="size-3.5" />}
                          {display}
                        </span>
                      </div>
                    );
                  })}
                </div>

                <div className="rounded-lg border border-border/60 bg-secondary/30 p-3 text-[11px]">
                  <p className="font-semibold">Registration {result.registration_id}</p>
                  <p className="mt-1 text-muted-foreground">{result.message}</p>
                  <div className="mt-2 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="w-20 shrink-0 text-muted-foreground">Fingerprint</span>
                      <HashValue value={result.public_record.fingerprint} label="SHA-256" head={16} tail={12} />
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="w-20 shrink-0 text-muted-foreground">Commitment</span>
                      <HashValue value={result.public_record.commitment} label="Commitment" head={16} tail={12} />
                    </div>
                    {result.public_record.ledger_tx_id && (
                      <div className="flex items-center gap-2">
                        <span className="w-20 shrink-0 text-muted-foreground">Ledger</span>
                        <HashValue value={result.public_record.ledger_tx_id} label="Ledger transaction" head={14} tail={10} />
                      </div>
                    )}
                  </div>
                  {result.verified_at && (
                    <p className="mt-2 text-muted-foreground">Verified at {new Date(result.verified_at).toLocaleString()}</p>
                  )}
                  <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">{result.statement}</p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(
                        JSON.stringify(
                          {
                            registration_id: result.registration_id,
                            valid: result.valid,
                            verified_at: result.verified_at,
                            checks: result.checks,
                            fingerprint: result.public_record.fingerprint,
                            commitment: result.public_record.commitment,
                            proof_system: result.proof_system,
                          },
                          null,
                          2,
                        ),
                      );
                      toast.success("Verification result copied");
                    }}
                  >
                    <Copy /> Copy result
                  </Button>
                  <Button variant="ghost" size="sm" onClick={reset}>
                    <RefreshCw /> Verify another
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </section>
      </main>

      <footer className="relative border-t border-border/60">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-2 px-5 py-5 text-[11px] text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>AUTHENTIQ public verification · No account, no tracking, no file upload.</span>
          <span className="inline-flex items-center gap-1.5">
            <Lock className="size-3" /> aes-256-gcm at rest · argon2id accounts · append-only audit chain
          </span>
        </div>
      </footer>
    </div>
  );
}
