import { Link } from "react-router-dom";
import { ArrowLeft, Compass, Globe2, ShieldQuestion } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

export default function NotFoundPage() {
  const { user } = useAuth();
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4">
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-50" />
      <div className="relative z-10 max-w-lg text-center">
        <div className="mx-auto flex size-16 items-center justify-center rounded-2xl border border-border/70 bg-card/70 text-foreground">
          <ShieldQuestion className="size-8" />
        </div>
        <p className="mt-6 text-[11px] font-semibold uppercase tracking-[0.24em] text-foreground">404 · Route not found</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">This page is not part of the workspace</h1>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          The address may be mistyped, or the record may have moved. Use the workspace navigation or return to a known page.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Button asChild variant="gradient">
            <Link to={user ? "/dashboard" : "/login"}><Compass /> {user ? "Go to dashboard" : "Sign in"}</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/verify"><Globe2 /> Public verification</Link>
          </Button>
          <Button asChild variant="ghost">
            <Link to={user ? "/timeline" : "/login"}><ArrowLeft /> {user ? "Creative timeline" : "Back to login"}</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
