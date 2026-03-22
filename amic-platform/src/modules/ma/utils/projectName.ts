import { getDealTypeCodePrefix } from "@/modules/ma/constants";
import type { DealType } from "@/modules/ma/types/transaction";
import { koreanToEnglish } from "./koreanToEnglish";

export const PROJECT_NAME_PREFIX = "Project ";

export function getProjectSuffix(name: string): string {
  return name.startsWith(PROJECT_NAME_PREFIX)
    ? name.slice(PROJECT_NAME_PREFIX.length)
    : name;
}

export function normalizeProjectSuffix(raw: string): string {
  const converted = koreanToEnglish(raw ?? "");
  const clean = converted.replace(/[^A-Za-z0-9\s-]/g, "");
  const collapsed = clean.replace(/\s+/g, " ").trim();
  if (!collapsed) return "";
  return collapsed.charAt(0).toUpperCase() + collapsed.slice(1);
}

export function buildProjectName(rawSuffix: string): string {
  const suffix = normalizeProjectSuffix(rawSuffix);
  return suffix ? `${PROJECT_NAME_PREFIX}${suffix}` : PROJECT_NAME_PREFIX;
}

export function previewProjectCode(
  dealType: DealType,
  rawSuffix: string,
): string {
  const suffix = normalizeProjectSuffix(rawSuffix).slice(0, 3).toUpperCase();
  if (!suffix) return "";
  const yy = new Date().getFullYear().toString().slice(2);
  return `${getDealTypeCodePrefix(dealType)}${yy}-${suffix}-??`;
}
