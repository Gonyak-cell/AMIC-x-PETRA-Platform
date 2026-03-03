/**
 * 산업 가치사슬도 Excalidraw 템플릿
 *
 * ValueChainData → Excalidraw elements 변환.
 * 수평 단계별 흐름 + 각 단계의 핵심 활동 표시.
 */

import {
  AMIC_EXCALIDRAW_PALETTE,
  AMIC_TEXT_COLORS,
  AMIC_LINE_COLORS,
  EXCALIDRAW_BG,
} from "../amic-palette";
import type {
  ValueChainData,
  ExcalidrawData,
  ExcalidrawElement,
} from "../types";
import { makeRect, makeText, makeArrow } from "./helpers";

const STAGE_W = 160;
const STAGE_H = 50;
const ACTIVITY_H = 24;
const STAGE_GAP = 40;
const ACTIVITY_GAP = 6;
const ACTIVITY_OFFSET_Y = 16;

const STAGE_COLORS = [
  AMIC_EXCALIDRAW_PALETTE.primary,
  AMIC_EXCALIDRAW_PALETTE.secondary,
  AMIC_EXCALIDRAW_PALETTE.accent,
  AMIC_EXCALIDRAW_PALETTE.info,
  AMIC_EXCALIDRAW_PALETTE.fresh,
  AMIC_EXCALIDRAW_PALETTE.caution,
];

export function buildValueChainDiagram(data: ValueChainData): ExcalidrawData {
  const elements: ExcalidrawElement[] = [];

  // 타이틀
  if (data.title) {
    const totalWidth =
      data.stages.length * STAGE_W + (data.stages.length - 1) * STAGE_GAP;
    elements.push(
      makeText({ x: totalWidth / 2 - 80, y: 10 }, data.title, {
        fontSize: 22,
        color: AMIC_TEXT_COLORS.title,
        textAlign: "center",
      }) as ExcalidrawElement,
    );
  }

  const startY = data.title ? 60 : 20;
  const startX = 40;

  for (let i = 0; i < data.stages.length; i++) {
    const stage = data.stages[i];
    const x = startX + i * (STAGE_W + STAGE_GAP);
    const y = startY;
    const colors = STAGE_COLORS[i % STAGE_COLORS.length];

    // 단계 헤더 박스
    elements.push(
      makeRect(
        { x, y },
        { width: STAGE_W, height: STAGE_H },
        colors,
      ) as ExcalidrawElement,
    );

    const headerColor =
      i === 0 ? AMIC_TEXT_COLORS.onDark : AMIC_TEXT_COLORS.onLight;
    elements.push(
      makeText(
        { x: x + STAGE_W / 2 - stage.label.length * 4, y: y + 14 },
        stage.label,
        { fontSize: 14, color: headerColor, textAlign: "center" },
      ) as ExcalidrawElement,
    );

    // 활동 목록 (아래에 배치)
    for (let j = 0; j < stage.activities.length; j++) {
      const activity = stage.activities[j];
      const actY =
        y + STAGE_H + ACTIVITY_OFFSET_Y + j * (ACTIVITY_H + ACTIVITY_GAP);

      elements.push(
        makeRect(
          { x: x + 4, y: actY },
          { width: STAGE_W - 8, height: ACTIVITY_H },
          {
            fill: AMIC_EXCALIDRAW_PALETTE.neutral.fill,
            stroke: AMIC_EXCALIDRAW_PALETTE.neutral.stroke,
          },
        ) as ExcalidrawElement,
      );

      elements.push(
        makeText({ x: x + 12, y: actY + 4 }, activity, {
          fontSize: 11,
          color: AMIC_TEXT_COLORS.body,
          textAlign: "left",
        }) as ExcalidrawElement,
      );
    }

    // 단계 간 화살표 (마지막 제외)
    if (i < data.stages.length - 1) {
      const arrowElements = makeArrow(
        { x: x + STAGE_W, y: y + STAGE_H / 2 },
        { x: x + STAGE_W + STAGE_GAP, y: y + STAGE_H / 2 },
        { color: AMIC_LINE_COLORS.primary, strokeWidth: 2 },
      );
      elements.push(...(arrowElements as ExcalidrawElement[]));
    }
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
