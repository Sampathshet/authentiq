import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface PaginationProps {
  page: number;
  pages?: number;
  total?: number;
  onPageChange: (page: number) => void;
  disabled?: boolean;
}

export function Pagination({ page, pages = 1, total, onPageChange, disabled }: PaginationProps) {
  if (pages <= 1 && !total) return null;
  return (
    <div className="flex flex-col gap-3 border-t border-border/60 pt-4 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
      <span>
        Page {page} of {Math.max(1, pages)}
        {typeof total === "number" ? ` · ${total} records` : ""}
      </span>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={disabled || page <= 1} onClick={() => onPageChange(page - 1)}>
          <ChevronLeft /> Previous
        </Button>
        <Button variant="outline" size="sm" disabled={disabled || page >= pages} onClick={() => onPageChange(page + 1)}>
          Next <ChevronRight />
        </Button>
      </div>
    </div>
  );
}
