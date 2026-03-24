import type { BuyerCandidate } from "@/modules/ma/types/buyer";

const BUYER_LOGO_PROTOCOLS = ["http://", "https://", "data:image/"];

export function normalizeBuyerLogoUrl(
  value: string | null | undefined,
): string | null {
  const trimmed = value?.trim();
  if (!trimmed) {
    return null;
  }

  if (trimmed.startsWith("/")) {
    return trimmed;
  }

  if (
    BUYER_LOGO_PROTOCOLS.some((protocol) =>
      trimmed.toLowerCase().startsWith(protocol),
    )
  ) {
    return trimmed;
  }

  return null;
}

export function getBuyerLogoUrl(
  extraData: BuyerCandidate["extra_data"] | undefined,
): string | null {
  if (!extraData || typeof extraData !== "object") {
    return null;
  }

  return normalizeBuyerLogoUrl(
    typeof extraData.logo_url === "string" ? extraData.logo_url : null,
  );
}

export function mergeBuyerLogoExtraData(
  extraData: BuyerCandidate["extra_data"] | undefined,
  logoUrl: string | null,
): Record<string, unknown> {
  const next = { ...(extraData ?? {}) };

  if (logoUrl) {
    next.logo_url = logoUrl;
  } else {
    delete next.logo_url;
  }

  return next;
}
