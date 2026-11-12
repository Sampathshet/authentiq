import { cn } from "@/lib/utils";

interface BrandLogoProps {
  className?: string;
  alt?: string;
}

export function BrandLogo({ className, alt = "AUTHENTIQ" }: BrandLogoProps) {
  return (
    <img
      src="/authentiq-logo.png"
      alt={alt}
      draggable={false}
      className={cn("shrink-0 select-none object-cover", className)}
    />
  );
}
