import { useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export type VdrCompanyInfoDocHint = "REGISTRY_DOCS" | "BIZ_REG_DOCS";

export interface VdrUploadEntryState {
  returnTo: string;
  returnLabel?: string;
}

interface VdrUploadLocationState {
  vdrUploadEntry?: VdrUploadEntryState;
}

function toObjectState(value: unknown): Record<string, unknown> {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}

export function getVdrUploadEntryState(state: unknown): VdrUploadEntryState | null {
  const candidate = toObjectState(state).vdrUploadEntry;
  if (!candidate || typeof candidate !== "object") {
    return null;
  }

  const { returnTo, returnLabel } = candidate as VdrUploadEntryState;
  if (typeof returnTo !== "string" || returnTo.length === 0) {
    return null;
  }

  return {
    returnTo,
    returnLabel:
      typeof returnLabel === "string" && returnLabel.length > 0
        ? returnLabel
        : undefined,
  };
}

export function useOpenVdrUpload(txnId: string) {
  const navigate = useNavigate();
  const location = useLocation();

  return useCallback(
    (options?: {
      returnLabel?: string;
      docHint?: VdrCompanyInfoDocHint;
    }) => {
      const currentParams = new URLSearchParams(location.search);
      const nextParams = new URLSearchParams();
      const viewedPhase = currentParams.get("viewPhase");

      if (viewedPhase) {
        nextParams.set("viewPhase", viewedPhase);
      }
      nextParams.set("upload", "1");
      if (options?.docHint) {
        nextParams.set("docHint", options.docHint);
      }

      const nextUrl = `/ma/transactions/${txnId}/vdr?${nextParams.toString()}`;
      const returnTo = `${location.pathname}${location.search}${location.hash}`;

      navigate(nextUrl, {
        state: {
          ...toObjectState(location.state),
          vdrUploadEntry: {
            returnTo,
            returnLabel: options?.returnLabel,
          },
        } satisfies VdrUploadLocationState,
      });
    },
    [location.hash, location.pathname, location.search, location.state, navigate, txnId],
  );
}
