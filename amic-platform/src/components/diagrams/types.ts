/**
 * Excalidraw 다이어그램 관련 타입 정의
 */

import type { EntityType } from "./amic-palette";

/** 백엔드 Diagram 모델 응답 타입 (상세 — excalidraw_data 포함) */
export interface Diagram {
  id: string;
  document_id: string;
  diagram_type: DiagramType;
  title: string;
  excalidraw_data: ExcalidrawData | null;
  png_path: string | null;
  created_at: string;
  updated_at: string;
}

/** 백엔드 다이어그램 목록 응답 타입 (excalidraw_data 생략) */
export type DiagramListItem = Omit<Diagram, "excalidraw_data">;

export type DiagramType =
  | "shareholding"
  | "org_chart"
  | "deal_structure"
  | "value_chain"
  | "custom";

/** Excalidraw JSON 최상위 구조 */
export interface ExcalidrawData {
  type: "excalidraw";
  version: number;
  source: string;
  elements: ExcalidrawElement[];
  appState: Record<string, unknown>;
  files: Record<string, unknown>;
}

/** Excalidraw 요소 (간소화 — 실제 타입은 @excalidraw/excalidraw에서 제공) */
export type ExcalidrawElement = Record<string, unknown>;

/** 주주관계도 입력 데이터 */
export interface ShareholdingEntity {
  id: string;
  label: string;
  type: EntityType;
  level: number;
}

export interface ShareholdingStake {
  from: string;
  to: string;
  pct: number;
  label?: string;
}

export interface ShareholdingData {
  entities: ShareholdingEntity[];
  stakes: ShareholdingStake[];
}

/** 조직도 입력 데이터 */
export interface OrgChartNode {
  id: string;
  label: string;
  level: number;
  title?: string;
}

export interface OrgChartEdge {
  from: string;
  to: string;
}

export interface OrgChartData {
  nodes: OrgChartNode[];
  edges: OrgChartEdge[];
}

/** 거래구조도 입력 데이터 */
export interface DealEntity {
  id: string;
  label: string;
  type: EntityType;
  sublabel?: string;
}

export interface DealFlow {
  from: string;
  to: string;
  label: string;
  type?: "cash" | "shares" | "asset" | "info";
}

export interface DealStructureData {
  entities: DealEntity[];
  flows: DealFlow[];
  title?: string;
}

/** 가치사슬도 입력 데이터 */
export interface ValueChainStage {
  id: string;
  label: string;
  activities: string[];
}

export interface ValueChainData {
  stages: ValueChainStage[];
  title?: string;
}
