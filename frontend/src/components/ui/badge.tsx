import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary/10 text-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "border-border text-muted-foreground",
        green: "border-foreground/20 bg-accent/25 text-foreground",
        blue: "border-foreground/20 bg-accent/15 text-foreground",
        amber: "border-foreground/20 bg-secondary text-foreground",
        red: "border-foreground/30 bg-foreground/5 text-foreground",
        violet: "border-foreground/20 bg-accent/15 text-foreground",
        slate: "border-border bg-secondary text-muted-foreground",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
