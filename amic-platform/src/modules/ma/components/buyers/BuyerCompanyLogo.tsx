import { useEffect, useState } from "react";
import { Building2 } from "lucide-react";

import { cn } from "@/lib/cn";

interface BuyerCompanyLogoProps {
  logoUrl?: string | null;
  name: string;
  size?: "sm" | "md";
}

const SIZE_CLASS: Record<NonNullable<BuyerCompanyLogoProps["size"]>, string> = {
  sm: "h-10 w-10",
  md: "h-14 w-14",
};

const ICON_CLASS: Record<NonNullable<BuyerCompanyLogoProps["size"]>, string> = {
  sm: "h-4 w-4",
  md: "h-6 w-6",
};

export default function BuyerCompanyLogo({
  logoUrl,
  name,
  size = "sm",
}: BuyerCompanyLogoProps) {
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    setImgError(false);
  }, [logoUrl]);

  const showImage = Boolean(logoUrl) && !imgError;

  return (
    <div
      className={cn(
        SIZE_CLASS[size],
        "flex shrink-0 items-center justify-center overflow-hidden rounded-xl border border-gray-border bg-bg-secondary/70",
      )}
    >
      {showImage ? (
        <img
          src={logoUrl ?? undefined}
          alt={`${name} logo`}
          className="h-full w-full object-contain p-1.5"
          onError={() => setImgError(true)}
        />
      ) : (
        <Building2 className={cn(ICON_CLASS[size], "text-text-muted")} />
      )}
    </div>
  );
}
