/** 공공데이터포털 자산운용사 등록 정보 */
export interface GPRegistryItem {
  company_name: string;
  company_name_en: string;
  finance_company_code: string;
  business_registration_no: string;
  corporation_registration_no: string;
  established_date: string;
  address: string;
  phone: string;
  employee_count: number | null;
  capital: string | null;
  total_assets: string | null;
  aum: string | null;
  fund_count: number | null;
  operating_revenue: string | null;
  authorization_date: string;
  data_date: string;
  source: string;
}

export interface GPRegistryListResponse {
  total: number;
  page: number;
  size: number;
  items: GPRegistryItem[];
  reference_date?: string | null;
}

export interface GPRegistryParams {
  company_name?: string;
  page?: number;
  size?: number;
}
