import * as React from "react";
import { cn } from "@/lib/utils";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  tone?: "blue" | "green" | "violet" | "amber";
}

const tones = {
  blue: "bg-foreground",
  green: "bg-accent",
  violet: "bg-accent/70",
  amber: "bg-foreground/60",
};

export function Progress({ value = 0, tone = "blue", className, ...props }: ProgressProps) {
  const bounded = Math.min(100, Math.max(0, value));
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={bounded}
      className={cn("h-2 w-full overflow-hidden rounded-full bg-secondary", className)}
      {...props}
    >
      <div className={cn("h-full rounded-full transition-all duration-500", tones[tone])} style={{ width: `${bounded}%` }} />
    </div>
  );
}
