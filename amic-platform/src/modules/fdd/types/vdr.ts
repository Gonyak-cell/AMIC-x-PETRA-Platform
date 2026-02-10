export type VdrFolderType = "FINANCIAL_STATEMENTS" | "ACCOUNTS_RECEIVABLE" | "ACCOUNTS_PAYABLE" | "BANK_DEBT" | "LEASE" | "OTHERS" | "CUSTOM";

export interface VdrFolder {
  id: string;
  deal_id: string;
  parent_id: string | null;
  name: string;
  folder_type: VdrFolderType;
  order_index: number;
  is_required: boolean;
  created_at: string;
  updated_at: string;
  children: VdrFolder[];
  file_count: number;
}
