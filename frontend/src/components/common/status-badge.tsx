import { Badge } from "@/components/ui/badge";
import { statusTone, titleCase } from "@/lib/format";

export function StatusBadge({ status, className }: { status?: string | null; className?: string }) {
  const tone = (status && statusTone[status]) || "slate";
  return (
    <Badge variant={tone as "green" | "blue" | "amber" | "red" | "violet" | "slate"} className={className}>
      <span className="size-1.5 rounded-full bg-current opacity-80" />
      {titleCase(status || "unknown")}
    </Badge>
  );
}

export function LedgerBadge({ mode, network }: { mode?: string | null; network?: string | null }) {
  const simulated = !mode || mode === "simulation";
  return (
    <Badge variant={simulated ? "amber" : "violet"} title={network || undefined}>
      {simulated ? "Simulated ledger" : "Polygon ledger"}
    </Badge>
  );
}
