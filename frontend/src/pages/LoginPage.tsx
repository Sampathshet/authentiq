import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, Eye, EyeOff, KeyRound, ShieldCheck, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { BrandLogo } from "@/components/BrandLogo";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { useAuth } from "@/context/AuthContext";
import { api, extractErrorMessage } from "@/lib/api";

const demoAccounts = [
  {
    label: "Organization admin",
    email: "demo@authentiq.dev",
    password: "Authentiq!Demo2026",
    description: "Organization administrator account. The workspace starts empty.",
  },
  {
    label: "Verifier",
    email: "verifier@authentiq.dev",
    password: "Authentiq!Verify2026",
    description: "Reviewer role for disputes and ledger events.",
  },
  {
    label: "Team contributor",
    email: "maya@authentiq.dev",
    password: "Authentiq!Team2026",
    description: "Creator account for testing collaborations.",
  },
];

export default function LoginPage() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotBusy, setForgotBusy] = useState(false);
  const [forgotResult, setForgotResult] = useState<{ message: string; token?: string } | null>(null);

  const reason = (location.state as { reason?: string } | null)?.reason;
  const nextPath = new URLSearchParams(window.location.search).get("next");

  if (user) {
    navigate(nextPath || "/dashboard", { replace: true });
    return null;
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login({ email: email.trim(), password, remember_me: remember });
      toast.success("Welcome back to AUTHENTIQ");
      navigate(nextPath || "/dashboard", { replace: true });
    } catch (caught) {
      setError(extractErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  };

  const useDemo = (account: (typeof demoAccounts)[number]) => {
    setEmail(account.email);
    setPassword(account.password);
    setError(null);
    toast.info(`${account.label} credentials filled`);
  };

  const requestReset = async (event: React.FormEvent) => {
    event.preventDefault();
    setForgotBusy(true);
    setForgotResult(null);
    try {
      const response = await api.post<{ message: string; detail?: string }>("/auth/forgot-password", { email: forgotEmail.trim() });
      setForgotResult({ message: response.message, token: response.detail });
      if (!response.detail) toast.success(response.message);
    } catch (caught) {
      toast.error(extractErrorMessage(caught));
    } finally {
      setForgotBusy(false);
    }
  };

  return (
    <AuthLayout>
      <div className="animate-in-up">
        <div className="mb-8 flex items-center gap-3 lg:hidden">
          <BrandLogo className="size-10 rounded-xl ring-1 ring-white/10" />
          <div>
            <p className="text-sm font-semibold tracking-[0.22em]">AUTHENTIQ</p>
            <p className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Digital ownership infrastructure</p>
          </div>
        </div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground">Secure access</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight">Sign in to your workspace</h2>
        <p className="mt-2 text-sm text-muted-foreground">Use your account credentials. Every session is audited and revocable.</p>

        {reason && (
          <Alert variant="warning" className="mt-5">
            <AlertDescription>{reason}</AlertDescription>
          </Alert>
        )}
        {error && (
          <Alert variant="destructive" className="mt-5">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="email">Email address</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@organization.com"
            />
          </div>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Password</Label>
              <button type="button" onClick={() => setForgotOpen(true)} className="text-[11px] font-medium text-foreground hover:text-foreground">
                Forgot password?
              </button>
            </div>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1.5 text-muted-foreground hover:bg-accent"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={remember}
              onChange={(event) => setRemember(event.target.checked)}
              className="size-4 rounded border-border accent-blue-500"
            />
            Keep this session active on this device
          </label>
          <Button type="submit" variant="gradient" className="w-full" loading={loading}>
            Sign in <ArrowRight />
          </Button>
        </form>

        <div className="my-6 flex items-center gap-3">
          <div className="h-px flex-1 bg-border/70" />
          <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Demo accounts</span>
          <div className="h-px flex-1 bg-border/70" />
        </div>

        <Tabs defaultValue={demoAccounts[0].email}>
          <TabsList className="w-full">
            {demoAccounts.map((account) => (
              <TabsTrigger key={account.email} value={account.email} className="flex-1 text-xs">
                {account.label.replace("Organization ", "Org ")}
              </TabsTrigger>
            ))}
          </TabsList>
          {demoAccounts.map((account) => (
            <TabsContent key={account.email} value={account.email}>
              <div className="rounded-xl border border-border/70 bg-card/60 p-4">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-foreground">
                    <Sparkles className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium">{account.description}</p>
                    <p className="mt-1.5 truncate font-mono text-[11px] text-muted-foreground">{account.email}</p>
                    <p className="font-mono text-[11px] text-muted-foreground">{account.password}</p>
                  </div>
                  <Button type="button" size="sm" variant="outline" onClick={() => useDemo(account)}>
                    Fill
                  </Button>
                </div>
                <p className="mt-3 text-[10px] leading-relaxed text-muted-foreground">
                  Demo data is explicitly marked and stored in the same database. It is never presented as real user activity.
                </p>
              </div>
            </TabsContent>
          ))}
        </Tabs>

        <div className="mt-6 rounded-xl border border-border/70 bg-card/60 p-3.5">
          <div className="flex items-start gap-2.5">
            <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-foreground">
              <ShieldCheck className="size-3.5" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium">Only need to verify a creation?</p>
              <p className="mt-0.5 text-[10px] leading-relaxed text-muted-foreground">
                No account or login. Use the registration ID, the private verification key, and the original file.
              </p>
            </div>
          </div>
          <Button asChild variant="outline" size="sm" className="mt-2.5 w-full">
            <Link to="/verify">
              <ShieldCheck /> Open public verification <ArrowRight />
            </Link>
          </Button>
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          New to AUTHENTIQ?{" "}
          <Link to="/signup" className="font-medium text-foreground hover:text-foreground">
            Create an account
          </Link>
        </p>
        <p className="mt-2 text-center text-[11px] text-muted-foreground">
          Have an organization invitation?{" "}
          <Link to="/join" className="font-medium text-foreground hover:text-foreground">
            Join with an invite code
          </Link>
        </p>
        <div className="mt-6 flex items-center justify-center gap-2 text-[10px] text-muted-foreground/70">
          <KeyRound className="size-3" />
          Argon2id · short-lived access tokens · rotating refresh tokens
        </div>
      </div>

      <Dialog open={forgotOpen} onOpenChange={setForgotOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reset your password</DialogTitle>
            <DialogDescription>
              Enter the account email. In development the reset token is returned directly because email delivery is not configured.
            </DialogDescription>
          </DialogHeader>
          {forgotResult ? (
            <div className="space-y-4">
              <Alert variant="info">
                <AlertDescription>{forgotResult.message}</AlertDescription>
              </Alert>
              {forgotResult.token && (
                <div className="space-y-2">
                  <Label>Development reset token</Label>
                  <code className="block break-all rounded-lg border border-border bg-background/60 p-3 font-mono text-[11px]">{forgotResult.token}</code>
                  <Button asChild className="w-full">
                    <Link to={`/reset-password?token=${encodeURIComponent(forgotResult.token)}`}>Open reset form</Link>
                  </Button>
                  <p className="text-[11px] text-muted-foreground">
                    This token is shown only because the backend is in development mode. Production must configure email delivery.
                  </p>
                </div>
              )}
              <Button variant="outline" className="w-full" onClick={() => setForgotOpen(false)}>
                Close
              </Button>
            </div>
          ) : (
            <form onSubmit={requestReset} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="forgot-email">Account email</Label>
                <Input
                  id="forgot-email"
                  type="email"
                  required
                  value={forgotEmail}
                  onChange={(event) => setForgotEmail(event.target.value)}
                  placeholder="you@organization.com"
                />
              </div>
              <Button type="submit" className="w-full" loading={forgotBusy}>
                Request reset
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </AuthLayout>
  );
}
