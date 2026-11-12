import type { ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { extractErrorMessage } from "@/lib/api";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 pb-2 md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        {eyebrow && (
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-blue-400/90">{eyebrow}</p>
        )}
        <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">{title}</h1>
        {description && <div className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">{description}</div>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className = "" }: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center rounded-xl border border-dashed border-border/80 bg-card/40 px-6 py-14 text-center ${className}`}>
      {icon && <div className="mb-4 flex size-12 items-center justify-center rounded-xl bg-secondary text-muted-foreground">{icon}</div>}
      <h3 className="text-base font-semibold">{title}</h3>
      {description && <p className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-red-500/20 bg-red-500/5 px-6 py-12 text-center">
      <div className="mb-3 flex size-11 items-center justify-center rounded-xl bg-foreground/5 text-destructive">
        <AlertTriangle className="size-5" />
      </div>
      <h3 className="text-sm font-semibold">This section could not be loaded</h3>
      <p className="mt-2 max-w-lg text-sm text-muted-foreground">{extractErrorMessage(error)}</p>
      {onRetry && (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          <RefreshCw /> Try again
        </Button>
      )}
    </div>
  );
}

export function LoadingBlock({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3 rounded-xl border border-border/70 bg-card/50 p-5">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex items-center gap-4">
          <Skeleton className="size-9 rounded-lg" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-2/5" />
            <Skeleton className="h-3 w-3/5" />
          </div>
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      ))}
    </div>
  );
}

export function InlineSpinner({ label = "Loading" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
      <span className="size-3 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />
      {label}
    </span>
  );
}
