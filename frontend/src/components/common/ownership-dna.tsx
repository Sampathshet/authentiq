import { useMemo } from "react";
import { Download } from "lucide-react";
import { fingerprintCells, downloadSvg } from "@/lib/fingerprint-art";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface OwnershipDnaProps {
  value: string;
  label?: string;
  /** Pixel size of the rendered grid. */
  size?: number;
  showCaption?: boolean;
  downloadName?: string;
  className?: string;
}

export function OwnershipDna({
  value,
  label = "Ownership DNA",
  size = 156,
  showCaption = true,
  downloadName,
  className,
}: OwnershipDnaProps) {
  const cells = useMemo(() => fingerprintCells(value), [value]);
  const cell = size / 9;

  return (
    <div className={cn("flex flex-col items-center gap-2", className)}>
      <div
        className="relative rounded-xl border border-border/70 bg-[#EAEAEA] p-2 shadow-sm"
        style={{ width: size + 16, height: size + 16 }}
      >
        <svg
          width={size}
          height={size}
          viewBox="0 0 9 9"
          role="img"
          aria-label={`${label} derived from ${value.slice(0, 16)}`}
          className="block"
        >
          {cells.map((cellData) => {
            if (!cellData.filled) return null;
            const fill =
              cellData.weight > 190 ? "#171717" : cellData.weight > 110 ? "#454545" : "#B7FF00";
            return (
              <rect
                key={`${cellData.x}-${cellData.y}`}
                x={cellData.x + 0.06}
                y={cellData.y + 0.06}
                width={0.88}
                height={0.88}
                rx={0.14}
                fill={fill}
              />
            );
          })}
        </svg>
        <span
          className="pointer-events-none absolute inset-0 rounded-xl ring-1 ring-inset ring-white/40"
          aria-hidden
        />
      </div>
      {showCaption && (
        <div className="text-center">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            {label}
          </p>
          <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
            {value.slice(0, 10)}…{value.slice(-6)}
          </p>
        </div>
      )}
      {downloadName && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 gap-1.5 px-2 text-[11px]"
          onClick={() => downloadSvg(value, downloadName)}
        >
          <Download className="size-3" /> SVG
        </Button>
      )}
      <span className="sr-only">{cell ? `Grid of ${cells.length} cells` : ""}</span>
    </div>
  );
}
