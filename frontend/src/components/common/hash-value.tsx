import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { truncateMiddle } from "@/lib/format";

interface CopyButtonProps {
  value?: string | null;
  label?: string;
  className?: string;
}

export function CopyButton({ value, label = "Value", className }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      toast.success(`${label} copied`);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      toast.error("Clipboard access was blocked by the browser");
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      disabled={!value}
      aria-label={`Copy ${label.toLowerCase()}`}
      className={cn(
        "inline-flex size-7 shrink-0 items-center justify-center rounded-md border border-border/70 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-40",
        className,
      )}
    >
      {copied ? <Check className="size-3.5 text-foreground" /> : <Copy className="size-3.5" />}
    </button>
  );
}

interface HashValueProps {
  value?: string | null;
  label?: string;
  head?: number;
  tail?: number;
  className?: string;
}

export function HashValue({ value, label = "Hash", head = 12, tail = 10, className }: HashValueProps) {
  if (!value) return <span className="text-xs text-muted-foreground">Unavailable</span>;
  return (
    <span className={cn("inline-flex min-w-0 items-center gap-2", className)}>
      <code className="truncate font-mono text-[11px] text-muted-foreground" title={value}>
        {truncateMiddle(value, head, tail)}
      </code>
      <CopyButton value={value} label={label} />
    </span>
  );
}
