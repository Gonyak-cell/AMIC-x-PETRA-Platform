import type { SelectOption } from "@/components/ui";

export const DEAL_TYPE_OPTIONS: SelectOption[] = [
  { value: "COMPLETION_ACCOUNTS", label: "Completion Accounts" },
  { value: "LOCKED_BOX", label: "Locked Box" },
];

export const CURRENCY_OPTIONS: SelectOption[] = [
  { value: "KRW", label: "KRW (원)" },
  { value: "USD", label: "USD ($)" },
  { value: "EUR", label: "EUR (€)" },
  { value: "JPY", label: "JPY (¥)" },
];
