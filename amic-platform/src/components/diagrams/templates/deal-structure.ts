/**
 * 거래구조도 Excalidraw 템플릿
 *
 * DealStructureData → Excalidraw elements 변환.
 * 매도자/매수자/대상회사/SPV 간 자금/지분 흐름 시각화.
 */

import {
  ENTITY_COLORS,
  AMIC_EXCALIDRAW_PALETTE,
  AMIC_TEXT_COLORS,
  AMIC_LINE_COLORS,
  EXCALIDRAW_BG,
} from "../amic-palette";
import type {
  DealStructureData,
  ExcalidrawData,
  ExcalidrawElement,
} from "../types";
import { makeRect, makeText, makeArrow } from "./helpers";

const NODE_W = 180;
const NODE_H = 70;

/** 흐름 유형별 화살표 스타일 */
const FLOW_STYLES: Record<
  string,
  { color: string; strokeStyle: "solid" | "dashed" | "dotted" }
> = {
  cash: { color: AMIC_LINE_COLORS.primary, strokeStyle: "solid" },
  shares: { color: AMIC_LINE_COLORS.accent, strokeStyle: "dashed" },
  asset: {
    color: AMIC_EXCALIDRAW_PALETTE.caution.stroke,
    strokeStyle: "solid",
  },
  info: { color: AMIC_LINE_COLORS.secondary, strokeStyle: "dotted" },
};

export function buildDealStructureDiagram(
  data: DealStructureData,
): ExcalidrawData {
  const elements: ExcalidrawElement[] = [];

  // 타이틀
  if (data.title) {
    elements.push(
      makeText({ x: 300, y: 20 }, data.title, {
        fontSize: 24,
        color: AMIC_TEXT_COLORS.title,
        textAlign: "center",
      }) as ExcalidrawElement,
    );
  }

  // 엔티티 배치 (2행 레이아웃: 상단 매도자/매수자, 하단 대상회사/SPV)
  const entityCount = data.entities.length;
  const cols = Math.min(entityCount, 3);
  const rows = Math.ceil(entityCount / cols);
  const totalW = cols * NODE_W + (cols - 1) * 80;
  const startX = (900 - totalW) / 2;
  const startY = data.title ? 80 : 40;

  const positions = new Map<string, { x: number; y: number }>();

  for (let i = 0; i < data.entities.length; i++) {
    const entity = data.entities[i];
    const row = Math.floor(i / cols);
    const col = i % cols;
    const x = startX + col * (NODE_W + 80);
    const y = startY + row * (NODE_H + 100);
    positions.set(entity.id, { x, y });

    const colors =
      ENTITY_COLORS[entity.type] ?? AMIC_EXCALIDRAW_PALETTE.neutral;

    elements.push(
      makeRect(
        { x, y },
        { width: NODE_W, height: NODE_H },
        colors,
      ) as ExcalidrawElement,
    );

    // 라벨
    const label = entity.sublabel
      ? `${entity.label}\n${entity.sublabel}`
      : entity.label;
    const textColor =
      entity.type === "company" || entity.type === "target"
        ? AMIC_TEXT_COLORS.onDark
        : AMIC_TEXT_COLORS.onLight;

    elements.push(
      makeText(
        {
          x: x + NODE_W / 2 - label.length * 3,
          y: y + (entity.sublabel ? 15 : 22),
        },
        label,
        {
          fontSize: entity.sublabel ? 12 : 14,
          color: textColor,
          textAlign: "center",
        },
      ) as ExcalidrawElement,
    );
  }

  // 흐름 화살표
  for (const flow of data.flows) {
    const fromPos = positions.get(flow.from);
    const toPos = positions.get(flow.to);
    if (!fromPos || !toPos) continue;

    const style = FLOW_STYLES[flow.type ?? "cash"] ?? FLOW_STYLES.cash;

    // 연결 방향 자동 결정
    const fromCenter = { x: fromPos.x + NODE_W / 2, y: fromPos.y + NODE_H / 2 };
    const toCenter = { x: toPos.x + NODE_W / 2, y: toPos.y + NODE_H / 2 };
    const dx = toCenter.x - fromCenter.x;
    const dy = toCenter.y - fromCenter.y;

    let startPoint: { x: number; y: number };
    let endPoint: { x: number; y: number };

    if (Math.abs(dy) > Math.abs(dx)) {
      // 수직 연결
      startPoint = {
        x: fromCenter.x,
        y: dy > 0 ? fromPos.y + NODE_H : fromPos.y,
      };
      endPoint = {
        x: toCenter.x,
        y: dy > 0 ? toPos.y : toPos.y + NODE_H,
      };
    } else {
      // 수평 연결
      startPoint = {
        x: dx > 0 ? fromPos.x + NODE_W : fromPos.x,
        y: fromCenter.y,
      };
      endPoint = {
        x: dx > 0 ? toPos.x : toPos.x + NODE_W,
        y: toCenter.y,
      };
    }

    const arrowElements = makeArrow(startPoint, endPoint, {
      label: flow.label,
      color: style.color,
      strokeWidth: 2,
      strokeStyle: style.strokeStyle,
    });
    elements.push(...(arrowElements as ExcalidrawElement[]));
  }

  // 범례 (Legend)
  const legendY = startY + rows * (NODE_H + 100) + 20;
  const legendItems = [
    { label: "현금 흐름", color: FLOW_STYLES.cash.color, style: "━━━" },
    { label: "지분 이전", color: FLOW_STYLES.shares.color, style: "- - -" },
    { label: "자산 이전", color: FLOW_STYLES.asset.color, style: "━━━" },
    { label: "정보 흐름", color: FLOW_STYLES.info.color, style: "· · ·" },
  ];

  for (let i = 0; i < legendItems.length; i++) {
    const item = legendItems[i];
    elements.push(
      makeText(
        { x: startX + i * 180, y: legendY },
        `${item.style} ${item.label}`,
        {
          fontSize: 11,
          color: item.color,
          textAlign: "left",
        },
      ) as ExcalidrawElement,
    );
  }

  return {
    type: "excalidraw",
    version: 2,
    source: "amic-platform",
    elements,
    appState: { viewBackgroundColor: EXCALIDRAW_BG, gridSize: null },
    files: {},
  };
}
