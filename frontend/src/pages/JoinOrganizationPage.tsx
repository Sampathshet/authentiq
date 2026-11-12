import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Building2, CheckCircle2, KeyRound, Loader2, LogIn, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { BrandLogo } from "@/components/BrandLogo";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/common/field";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { api, extractErrorMessage } from "@/lib/api";

export default function JoinOrganizationPage() {
  const { user, loading } = useAuth();
  const [params] = useSearchParams();
  const [code, setCode] = useState(params.get("code") || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [joined, setJoined] = useState<string | null>(null);

  useEffect(() => {
    const next = params.get("code");
    if (next) setCode(next);
  }, [params]);

  const accept = async () => {
    if (!code.trim()) {
      setError("Paste the invitation code you received.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await api.post<{ message: string; organization: { name: string } }>(
        "/settings/organization/invitations/accept",
        { token: code.trim() },
      );
      setJoined(response.organization.name);
      toast.success(response.message);
    } catch (caught) {
      setError(extractErrorMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-40" />
      <div className="pointer-events-none absolute -left-40 top-0 size-[520px] rounded-full bg-accent/25 blur-[140px]" />

      <header className="relative border-b border-border/60">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-5 py-5">
          <Link to="/" className="flex items-center gap-3">
            <BrandLogo className="size-10 rounded-xl ring-1 ring-foreground/10" />
            <div>
              <p className="text-sm font-semibold tracking-[0.24em]">AUTHENTIQ</p>
              <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Organization access</p>
            </div>
          </Link>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="hidden sm:inline-flex">
              <ShieldCheck className="size-3" /> Invitation only
            </Badge>
            <Button variant="ghost" size="sm" asChild>
              <Link to="/">Home</Link>
            </Button>
            {!user && (
              <Button variant="ghost" size="sm" asChild>
                <Link to={`/login?next=${encodeURIComponent(`/join?code=${code}`)}`}>
                  Sign in <LogIn />
                </Link>
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="relative mx-auto grid w-full max-w-5xl gap-8 px-5 py-12 lg:grid-cols-[1fr_1.1fr]">
        <section className="space-y-5">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-foreground/15 bg-accent/20 px-3 py-1 text-[11px] font-medium">
              <Building2 className="size-3" /> Join an organization
            </p>
            <h1 className="mt-4 text-3xl leading-tight xl:text-4xl">
              Accept the invite.
              <br />
              <span className="text-gradient">Start working together.</span>
            </h1>
            <p className="mt-4 max-w-md text-sm leading-relaxed text-muted-foreground">
              Organization invitations work exactly like team invitations. The admin issues a code, you accept it, and
              your account joins the shared workspace with access to its registrations and evidence.
            </p>
          </div>

          <div className="space-y-3 rounded-xl border border-border/70 bg-secondary/40 p-4 text-[11px] leading-relaxed">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">What happens next</p>
            <p>1. The code is validated against the organization that issued it.</p>
            <p>2. Your account becomes an active member with the invited role.</p>
            <p>3. The organization tab appears in your workspace with its members and registrations.</p>
          </div>
        </section>

        <section>
          <Card>
            <CardHeader className="border-b border-border/60 bg-secondary/30">
              <CardTitle className="flex items-center gap-2">
                <KeyRound className="size-4" /> Accept an organization invitation
              </CardTitle>
              <CardDescription>Paste the invitation code from your admin.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 pt-5">
              {loading ? (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" /> Restoring your session…
                </div>
              ) : joined ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 rounded-lg border border-foreground/20 bg-accent/20 p-3 text-sm font-medium">
                    <CheckCircle2 className="size-4" /> You joined {joined}
                  </div>
                  <Button asChild className="w-full">
                    <Link to="/organization">Open the organization workspace</Link>
                  </Button>
                  <Button asChild variant="outline" className="w-full">
                    <Link to="/dashboard">Go to dashboard</Link>
                  </Button>
                </div>
              ) : !user ? (
                <div className="space-y-3">
                  <Alert variant="info">
                    <AlertDescription>
                      Sign in with the invited email address first. The code stays in the link, so you land back here
                      right after signing in.
                    </AlertDescription>
                  </Alert>
                  <Field label="Invitation code" htmlFor="join-code">
                    <Input
                      id="join-code"
                      value={code}
                      onChange={(event) => setCode(event.target.value)}
                      placeholder="Paste the code"
                      className="font-mono text-xs"
                    />
                  </Field>
                  <Button asChild className="w-full">
                    <Link to={`/login?next=${encodeURIComponent(`/join?code=${code}`)}`}>
                      <LogIn /> Sign in to accept
                    </Link>
                  </Button>
                  <Button asChild variant="outline" className="w-full">
                    <Link to="/signup">Create the account first</Link>
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <Field label="Invitation code" htmlFor="join-code" required>
                    <Input
                      id="join-code"
                      value={code}
                      onChange={(event) => setCode(event.target.value)}
                      placeholder="Paste the code"
                      className="font-mono text-xs"
                    />
                  </Field>
                  {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
                  <Button className="w-full" onClick={accept} loading={busy}>
                    <ShieldCheck /> Accept invitation
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}
