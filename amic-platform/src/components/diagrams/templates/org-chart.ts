/**
 * 조직도 Excalidraw 템플릿
 *
 * OrgChartData → Excalidraw elements 변환.
 * 계층적 트리 레이아웃. 레벨별 색상 차등.
 */

import {
  AMIC_EXCALIDRAW_PALETTE,
  AMIC_TEXT_COLORS,
  EXCALIDRAW_BG,
} from "../amic-palette";
import type { OrgChartData, ExcalidrawData, ExcalidrawElement } from "../types";
import { makeRect, makeText, makeLine } from "./helpers";

const NODE_W = 180;
const NODE_H = 50;
const H_GAP = 40;
const V_GAP = 80;

const LEVEL_COLORS = [
  AMIC_EXCALIDRAW_PALETTE.primary,
  AMIC_EXCALIDRAW_PALETTE.secondary,
  AMIC_EXCALIDRAW_PALETTE.accent,
  AMIC_EXCALIDRAW_PALETTE.neutral,
];

export function buildOrgChartDiagram(data: OrgChartData): ExcalidrawData {
  const elements: ExcalidrawElement[] = [];

  // 레벨별 노드 그룹핑
  const levels = new Map<number, typeof data.nodes>();
  for (const node of data.nodes) {
    const group = levels.get(node.level) ?? [];
    group.push(node);
    levels.set(node.level, group);
  }

  const sortedLevels = [...levels.keys()].sort((a, b) => a - b);

  // 위치 계산
  const positions = new Map<string, { x: number; y: number }>();

  for (const level of sortedLevels) {
    const nodes = levels.get(level) ?? [];
    const totalWidth = nodes.length * NODE_W + (nodes.length - 1) * H_GAP;
    const startX = (1000 - totalWidth) / 2;
    const y = level * (NODE_H + V_GAP) + 40;

    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const x = startX + i * (NODE_W + H_GAP);
      positions.set(node.id, { x, y });

      const colors = LEVEL_COLORS[Math.min(level, LEVEL_COLORS.length - 1)];
      const textColor =
        level === 0 ? AMIC_TEXT_COLORS.onDark : AMIC_TEXT_COLORS.onLight;

      elements.push(
        makeRect(
          { x, y },
          { width: NODE_W, height: NODE_H },
          colors,
        ) as ExcalidrawElement,
      );

      // 라벨 (이름 + 직위)
      const label = node.title ? `${node.label}\n${node.title}` : node.label;
      elements.push(
        makeText(
          {
            x: x + NODE_W / 2 - label.length * 3,
            y: y + (node.title ? 8 : 15),
          },
          label,
          {
            fontSize: node.title ? 12 : 14,
            color: textColor,
            textAlign: "center",
          },
        ) as ExcalidrawElement,
      );
    }
  }

  // 엣지 (수직선 연결)
  for (const edge of data.edges) {
    const fromPos = positions.get(edge.from);
    const toPos = positions.get(edge.to);
    if (!fromPos || !toPos) continue;

    const fromCenterX = fromPos.x + NODE_W / 2;
    const fromBottomY = fromPos.y + NODE_H;
    const toCenterX = toPos.x + NODE_W / 2;
    const toTopY = toPos.y;

    // 수직선 + 수평선 (L자형 연결)
    const midY = (fromBottomY + toTopY) / 2;

    elements.push(
      makeLine(
        { x: fromCenterX, y: fromBottomY },
        { x: fromCenterX, y: midY },
      ) as ExcalidrawElement,
    );
    elements.push(
      makeLine(
        { x: fromCenterX, y: midY },
        { x: toCenterX, y: midY },
      ) as ExcalidrawElement,
    );
    elements.push(
      makeLine(
        { x: toCenterX, y: midY },
        { x: toCenterX, y: toTopY },
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
