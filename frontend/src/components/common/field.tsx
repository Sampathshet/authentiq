import type { ReactNode } from "react";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface FieldProps {
  label: string;
  htmlFor?: string;
  hint?: ReactNode;
  error?: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
}

export function Field({ label, htmlFor, hint, error, required, children, className }: FieldProps) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={htmlFor}>
          {label}
          {required && <span className="ml-1 text-destructive">*</span>}
        </Label>
        {hint && <span className="text-[11px] text-muted-foreground">{hint}</span>}
      </div>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

export function InfoRow({ label, children, mono }: { label: string; children: ReactNode; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-1 border-b border-border/50 py-2.5 last:border-0 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className={cn("min-w-0 text-sm sm:text-right", mono && "font-mono text-xs")}>{children}</span>
    </div>
  );
}
