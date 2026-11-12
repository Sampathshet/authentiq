import * as React from "react";
import { CheckCircle2, Info, TriangleAlert, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const variants = {
  default: "border-border bg-card text-foreground",
  info: "border-foreground/20 bg-accent/15 text-foreground",
  success: "border-foreground/20 bg-accent/25 text-foreground",
  warning: "border-foreground/20 bg-secondary text-foreground",
  destructive: "border-foreground/30 bg-foreground/5 text-foreground",
};

const icons = {
  default: Info,
  info: Info,
  success: CheckCircle2,
  warning: TriangleAlert,
  destructive: XCircle,
};

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: keyof typeof variants;
  hideIcon?: boolean;
}

export function Alert({ className, variant = "default", hideIcon, children, ...props }: AlertProps) {
  const Icon = icons[variant];
  return (
    <div
      role="alert"
      className={cn("relative flex gap-3 rounded-lg border px-4 py-3 text-sm [&>svg]:mt-0.5", variants[variant], className)}
      {...props}
    >
      {!hideIcon && <Icon className="size-4 shrink-0" />}
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

export function AlertTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h5 className={cn("mb-1 font-semibold leading-none tracking-tight", className)} {...props} />;
}

export function AlertDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <div className={cn("text-sm opacity-85 [&_p]:leading-relaxed", className)} {...props} />;
}
