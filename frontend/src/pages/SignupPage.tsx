import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight, Building2, Check, User } from "lucide-react";
import { toast } from "sonner";
import { BrandLogo } from "@/components/BrandLogo";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/context/AuthContext";
import { extractErrorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";

const checks = [
  { key: "length", label: "At least 10 characters", test: (value: string) => value.length >= 10 },
  { key: "lower", label: "Lowercase letter", test: (value: string) => /[a-z]/.test(value) },
  { key: "upper", label: "Uppercase letter", test: (value: string) => /[A-Z]/.test(value) },
  { key: "number", label: "Number", test: (value: string) => /\d/.test(value) },
  { key: "symbol", label: "Symbol", test: (value: string) => /[^A-Za-z0-9]/.test(value) },
];

export default function SignupPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [accountType, setAccountType] = useState<"individual" | "organization">("individual");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const results = useMemo(() => checks.map((check) => ({ ...check, passed: check.test(password) })), [password]);
  const categoryCount = results.filter((item) => item.key !== "length" && item.passed).length;
  const strength = password.length >= 10 && categoryCount >= 3 ? (results.every((item) => item.passed) ? 100 : 75) : password.length ? 35 : 0;
  const passwordValid = password.length >= 10 && categoryCount >= 3;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (!passwordValid) {
      setError("Use at least 10 characters and three of: lowercase, uppercase, number, symbol");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (!acceptTerms) {
      setError("You must accept the terms before creating an account");
      return;
    }
    setLoading(true);
    try {
      await register({
        display_name: displayName.trim(),
        email: email.trim(),
        password,
        confirm_password: confirmPassword,
        account_type: accountType,
        organization_name: accountType === "organization" ? organizationName.trim() : undefined,
        accept_terms: acceptTerms,
      });
      toast.success("Account created. Your workspace is ready.");
      navigate("/dashboard", { replace: true });
    } catch (caught) {
      setError(extractErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout>
      <div className="animate-in-up">
        <div className="mb-7 flex items-center gap-3 lg:hidden">
          <BrandLogo className="size-10 rounded-xl ring-1 ring-white/10" />
          <p className="text-sm font-semibold tracking-[0.22em]">AUTHENTIQ</p>
        </div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground">Create workspace</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight">Start protecting your work</h2>
        <p className="mt-2 text-sm text-muted-foreground">Real fingerprints, commitments, proofs, and an auditable ownership record.</p>

        {error && (
          <Alert variant="destructive" className="mt-5">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <form onSubmit={submit} className="mt-6 space-y-4">
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => setAccountType("individual")}
              className={cn(
                "flex items-center gap-2 rounded-lg border p-3 text-left transition-colors",
                accountType === "individual" ? "border-blue-500/60 bg-accent/15" : "border-border hover:bg-accent/40",
              )}
            >
              <User className="size-4 text-foreground" />
              <span>
                <span className="block text-xs font-medium">Individual</span>
                <span className="block text-[10px] text-muted-foreground">Personal creator</span>
              </span>
            </button>
            <button
              type="button"
              onClick={() => setAccountType("organization")}
              className={cn(
                "flex items-center gap-2 rounded-lg border p-3 text-left transition-colors",
                accountType === "organization" ? "border-blue-500/60 bg-accent/15" : "border-border hover:bg-accent/40",
              )}
            >
              <Building2 className="size-4 text-foreground" />
              <span>
                <span className="block text-xs font-medium">Organization</span>
                <span className="block text-[10px] text-muted-foreground">Shared workspace</span>
              </span>
            </button>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="display-name">Display name</Label>
            <Input id="display-name" required minLength={2} value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="Ada Lovelace" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="signup-email">Email address</Label>
            <Input id="signup-email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@organization.com" />
          </div>
          {accountType === "organization" && (
            <div className="space-y-1.5">
              <Label htmlFor="organization-name">Organization name</Label>
              <Input
                id="organization-name"
                required
                value={organizationName}
                onChange={(event) => setOrganizationName(event.target.value)}
                placeholder="Studio or company name"
              />
            </div>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="signup-password">Password</Label>
            <Input
              id="signup-password"
              type="password"
              autoComplete="new-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Create a strong password"
            />
            <Progress value={strength} tone={strength === 100 ? "green" : strength >= 75 ? "blue" : "amber"} className="mt-1 h-1.5" />
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 pt-1">
              {results.map((item) => (
                <span key={item.key} className={cn("flex items-center gap-1 text-[10px]", item.passed ? "text-foreground" : "text-muted-foreground")}>
                  <Check className={cn("size-3", !item.passed && "opacity-30")} />
                  {item.label}
                </span>
              ))}
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm-password">Confirm password</Label>
            <Input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="Repeat your password"
            />
          </div>
          <label className="flex cursor-pointer items-start gap-2 text-xs leading-relaxed text-muted-foreground">
            <input
              type="checkbox"
              checked={acceptTerms}
              onChange={(event) => setAcceptTerms(event.target.checked)}
              className="mt-0.5 size-4 rounded border-border accent-blue-500"
            />
            I accept the terms of service and understand that AUTHENTIQ records cryptographic evidence, not a legal determination of ownership.
          </label>
          <Button type="submit" variant="gradient" className="w-full" loading={loading}>
            Create account <ArrowRight />
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-foreground hover:text-foreground">
            Sign in
          </Link>
        </p>
        <p className="mt-2 text-center text-[11px] text-muted-foreground">
          Verifying someone else&apos;s creation?{" "}
          <Link to="/verify" className="font-medium text-foreground hover:text-foreground">
            Open public verification
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
