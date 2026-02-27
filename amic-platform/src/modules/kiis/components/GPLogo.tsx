import { useState } from "react";
import { Building2 } from "lucide-react";
import { cn } from "@/lib/cn";

interface GPLogoProps {
  logoUrl?: string;
  name: string;
  size?: "sm" | "md" | "lg";
}

const SIZE_CLASS: Record<string, string> = {
  sm: "h-8 w-8",
  md: "h-10 w-10",
  lg: "h-14 w-14",
};

const ICON_SIZE: Record<string, string> = {
  sm: "h-4 w-4",
  md: "h-5 w-5",
  lg: "h-7 w-7",
};

export function GPLogo({ logoUrl, name, size = "sm" }: GPLogoProps) {
  const [imgError, setImgError] = useState(false);

  const showImg = logoUrl && !imgError;

  return (
    <div
      className={cn(
        SIZE_CLASS[size],
        "rounded-full bg-amic-50 flex items-center justify-center shrink-0 overflow-hidden",
      )}
    >
      {showImg ? (
        <img
          src={logoUrl}
          alt={`${name} 로고`}
          className="h-full w-full object-contain"
          onError={() => setImgError(true)}
        />
      ) : (
        <Building2 className={cn(ICON_SIZE[size], "text-amic")} />
      )}
    </div>
  );
}
