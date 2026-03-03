/**
 * 주주관계도 / 지배구조도 Excalidraw 템플릿
 *
 * ShareholdingData → Excalidraw elements 변환.
 * 엔티티 타입별 shape: company=사각형, person=타원, fund=다이아몬드
 * 지분율에 따른 화살표 굵기 차등.
 */

import {
  ENTITY_COLORS,
  AMIC_EXCALIDRAW_PALETTE,
  AMIC_TEXT_COLORS,
  AMIC_LINE_COLORS,
  EXCALIDRAW_BG,
} from "../amic-palette";
import type {
  ShareholdingData,
  ExcalidrawData,
  ExcalidrawElement,
} from "../types";
import {
  makeRect,
  makeEllipse,
  makeDiamond,
  makeText,
  makeArrow,
} from "./helpers";

const NODE_W = 160;
const NODE_H = 60;
const H_GAP = 60;
const V_GAP = 120;

export function buildShareholdingDiagram(
  data: ShareholdingData,
): ExcalidrawData {
  const elements: ExcalidrawElement[] = [];

  // 레벨별 엔티티 그룹핑
  const levels = new Map<number, typeof data.entities>();
  for (const entity of data.entities) {
    const group = levels.get(entity.level) ?? [];
    group.push(entity);
    levels.set(entity.level, group);
  }

  const sortedLevels = [...levels.keys()].sort((a, b) => a - b);

  // 노드 위치 계산 (레벨별 가로 배치)
  const positions = new Map<string, { x: number; y: number }>();

  for (const level of sortedLevels) {
    const entities = levels.get(level) ?? [];
    const totalWidth = entities.length * NODE_W + (entities.length - 1) * H_GAP;
    const startX = (800 - totalWidth) / 2;
    const y = level * (NODE_H + V_GAP) + 60;

    for (let i = 0; i < entities.length; i++) {
      const entity = entities[i];
      const x = startX + i * (NODE_W + H_GAP);
      positions.set(entity.id, { x, y });

      const colors =
        ENTITY_COLORS[entity.type] ?? AMIC_EXCALIDRAW_PALETTE.neutral;

      // 엔티티 타입에 따라 shape 결정
      if (entity.type === "person") {
        elements.push(
          makeEllipse(
            { x, y },
            { width: NODE_W, height: NODE_H },
            colors,
          ) as ExcalidrawElement,
        );
      } else if (entity.type === "fund") {
        elements.push(
          makeDiamond(
            { x: x - 10, y: y - 10 },
            { width: NODE_W + 20, height: NODE_H + 20 },
            colors,
          ) as ExcalidrawElement,
        );
      } else {
        elements.push(
          makeRect(
            { x, y },
            { width: NODE_W, height: NODE_H },
            colors,
          ) as ExcalidrawElement,
        );
      }

      // 라벨 텍스트
      elements.push(
        makeText(
          {
            x: x + NODE_W / 2 - entity.label.length * 5,
            y: y + NODE_H / 2 - 10,
          },
          entity.label,
          {
            fontSize: 14,
            color:
              entity.level === 0
                ? AMIC_TEXT_COLORS.onDark
                : AMIC_TEXT_COLORS.onLight,
            textAlign: "center",
          },
        ) as ExcalidrawElement,
      );
    }
  }

  // 지분 화살표 생성
  for (const stake of data.stakes) {
    const fromPos = positions.get(stake.from);
    const toPos = positions.get(stake.to);
    if (!fromPos || !toPos) continue;

    const isMajor = stake.pct >= 50;
    const label = stake.label ?? `${stake.pct.toFixed(0)}%`;

    const arrowElements = makeArrow(
      { x: fromPos.x + NODE_W / 2, y: fromPos.y + NODE_H },
      { x: toPos.x + NODE_W / 2, y: toPos.y },
      {
        label,
        color: isMajor
          ? AMIC_LINE_COLORS.majorStake
          : AMIC_LINE_COLORS.minorStake,
        strokeWidth: isMajor ? 3 : 1.5,
      },
    );
    elements.push(...(arrowElements as ExcalidrawElement[]));
  }

  return {
    type: "excalidraw",
    version: 2,
    source: "amic-platform",
    elements,
    appState: {
      viewBackgroundColor: EXCALIDRAW_BG,
      gridSize: null,
    },
    files: {},
  };
}
