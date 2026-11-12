import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const tones = {
  blue: "bg-accent/20 text-foreground",
  violet: "bg-accent/15 text-foreground",
  green: "bg-accent/30 text-foreground",
  amber: "bg-secondary text-foreground",
  slate: "bg-secondary text-muted-foreground",
};

interface StatCardProps {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ReactNode;
  tone?: keyof typeof tones;
  onClick?: () => void;
}

export function StatCard({ label, value, hint, icon, tone = "blue", onClick }: StatCardProps) {
  return (
    <Card
      onClick={onClick}
      className={cn(
        "relative overflow-hidden p-5 transition-all",
        onClick && "cursor-pointer hover:border-foreground/40 hover:shadow-soft",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
          {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
        </div>
        {icon && <div className={cn("flex size-9 shrink-0 items-center justify-center rounded-lg", tones[tone])}>{icon}</div>}
      </div>
    </Card>
  );
}
