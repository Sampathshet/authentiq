import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { BrandLogo } from "@/components/BrandLogo";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { api, extractErrorMessage } from "@/lib/api";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [token, setToken] = useState(params.get("token") || "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      const response = await api.post<{ message: string }>("/auth/reset-password", {
        token,
        new_password: password,
        confirm_password: confirm,
      });
      toast.success(response.message);
      navigate("/login", { replace: true });
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
        <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-foreground">Account recovery</p>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight">Choose a new password</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Resetting the password revokes every active session on the account.
        </p>
        {error && (
          <Alert variant="destructive" className="mt-5">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <form onSubmit={submit} className="mt-6 space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="reset-token">Reset token</Label>
            <Input id="reset-token" required value={token} onChange={(event) => setToken(event.target.value)} placeholder="Paste the reset token" className="font-mono text-xs" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="new-password">New password</Label>
            <Input id="new-password" type="password" autoComplete="new-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="confirm-new-password">Confirm new password</Label>
            <Input id="confirm-new-password" type="password" autoComplete="new-password" required value={confirm} onChange={(event) => setConfirm(event.target.value)} />
          </div>
          <p className="text-[11px] text-muted-foreground">At least 10 characters with three of: lowercase, uppercase, number, symbol.</p>
          <Button type="submit" variant="gradient" className="w-full" loading={loading}>
            Reset password <ArrowRight />
          </Button>
        </form>
        <p className="mt-6 text-center text-xs text-muted-foreground">
          <Link to="/login" className="font-medium text-foreground hover:text-foreground">
            Back to sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
