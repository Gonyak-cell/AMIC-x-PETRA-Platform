export type MovementType = "transfer" | "resignation" | "appointment";

export interface ManagerMovement {
  id: number;
  manager_name: string;
  from_company_id: number | null;
  from_company_name: string | null;
  from_fund_id: number | null;
  to_company_id: number | null;
  to_company_name: string | null;
  to_fund_id: number | null;
  movement_type: MovementType;
  detected_at: string;
  source: string | null;
  notes: string | null;
}

export interface ManagerMovementListResponse {
  total: number;
  page: number;
  size: number;
  items: ManagerMovement[];
}

export interface ManagerMovementParams {
  manager_name?: string;
  page?: number;
  size?: number;
}

export interface ManagerDeal {
  id: number;
  target_company: string;
  amount_display: string | null;
  round_stage: string | null;
  sector: string | null;
}

export interface ManagerProfile {
  manager_name: string;
  current_company: string | null;
  current_fund: string | null;
  specialty_sectors: string[];
  career_years: number | null;
  total_deals_involved: number;
  movements: ManagerMovement[];
  deals: ManagerDeal[];
}

export interface TrackResponse {
  scanned_count: number;
  new_movements_count: number;
  movements: ManagerMovement[];
}
