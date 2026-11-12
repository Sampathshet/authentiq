import { useRef, useState } from "react";
import { FileUp, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatBytes } from "@/lib/format";
import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
  accept?: string;
  hint?: string;
  disabled?: boolean;
  maxSizeMb?: number;
}

export function FileDropzone({ file, onFileChange, accept, hint, disabled, maxSizeMb = 200 }: FileDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const select = (next: File | null) => {
    setError(null);
    if (!next) {
      onFileChange(null);
      return;
    }
    if (next.size > maxSizeMb * 1024 * 1024) {
      setError(`File exceeds the ${maxSizeMb} MB limit`);
      return;
    }
    if (next.size === 0) {
      setError("Empty files cannot be registered");
      return;
    }
    onFileChange(next);
  };

  return (
    <div className="space-y-2">
      <div
        role="button"
        tabIndex={0}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(event) => {
          if ((event.key === "Enter" || event.key === " ") && !disabled) inputRef.current?.click();
        }}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!disabled) select(event.dataTransfer.files?.[0] || null);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
          dragging ? "border-foreground/25 bg-blue-500/5" : "border-border bg-background/30 hover:border-foreground/30 hover:bg-accent/30",
          disabled && "cursor-not-allowed opacity-60",
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          disabled={disabled}
          onChange={(event) => select(event.target.files?.[0] || null)}
        />
        {file ? (
          <div className="flex w-full max-w-md items-center gap-3 rounded-lg border border-border bg-card/80 p-3 text-left">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-accent/15 text-foreground">
              <FileUp className="size-5" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{file.name}</p>
              <p className="text-xs text-muted-foreground">
                {formatBytes(file.size)} · {file.type || "unknown type"}
              </p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={(event) => {
                event.stopPropagation();
                select(null);
              }}
            >
              <X />
              <span className="sr-only">Remove file</span>
            </Button>
          </div>
        ) : (
          <>
            <div className="mb-3 flex size-12 items-center justify-center rounded-xl bg-secondary text-muted-foreground">
              <FileUp className="size-6" />
            </div>
            <p className="text-sm font-medium">Drop your file here or click to browse</p>
            <p className="mt-1 max-w-md text-xs leading-relaxed text-muted-foreground">
              {hint || "The file is hashed in your browser, uploaded in verified chunks, scanned, and encrypted at rest."}
            </p>
          </>
        )}
      </div>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
