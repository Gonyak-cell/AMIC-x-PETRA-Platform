/**
 * Excalidraw element 생성 헬퍼 함수
 *
 * Excalidraw JSON 스펙에 맞는 element 객체를 생성.
 */

import { AMIC_TEXT_COLORS, AMIC_LINE_COLORS } from "../amic-palette";

let seedCounter = 100000;
const nextSeed = () => ++seedCounter;
const nextId = () =>
  `el_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

export interface Pos {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

/** 사각형 요소 생성 */
export function makeRect(
  pos: Pos,
  size: Size,
  opts: {
    fill: string;
    stroke: string;
    groupIds?: string[];
    roundness?: boolean;
  },
): Record<string, unknown> {
  return {
    type: "rectangle",
    id: nextId(),
    x: pos.x,
    y: pos.y,
    width: size.width,
    height: size.height,
    strokeColor: opts.stroke,
    backgroundColor: opts.fill,
    fillStyle: "solid",
    strokeWidth: 2,
    strokeStyle: "solid",
    roughness: 0,
    opacity: 100,
    angle: 0,
    seed: nextSeed(),
    version: 1,
    versionNonce: nextSeed(),
    isDeleted: false,
    groupIds: opts.groupIds ?? [],
    boundElements: null,
    link: null,
    locked: false,
    roundness: opts.roundness !== false ? { type: 3 } : null,
  };
}

/** 타원 요소 생성 */
export function makeEllipse(
  pos: Pos,
  size: Size,
  opts: {
    fill: string;
    stroke: string;
    groupIds?: string[];
  },
): Record<string, unknown> {
  return {
    type: "ellipse",
    id: nextId(),
    x: pos.x,
    y: pos.y,
    width: size.width,
    height: size.height,
    strokeColor: opts.stroke,
    backgroundColor: opts.fill,
    fillStyle: "solid",
    strokeWidth: 2,
    strokeStyle: "solid",
    roughness: 0,
    opacity: 100,
    angle: 0,
    seed: nextSeed(),
    version: 1,
    versionNonce: nextSeed(),
    isDeleted: false,
    groupIds: opts.groupIds ?? [],
    boundElements: null,
    link: null,
    locked: false,
  };
}

/** 다이아몬드 요소 생성 */
export function makeDiamond(
  pos: Pos,
  size: Size,
  opts: {
    fill: string;
    stroke: string;
    groupIds?: string[];
  },
): Record<string, unknown> {
  return {
    type: "diamond",
    id: nextId(),
    x: pos.x,
    y: pos.y,
    width: size.width,
    height: size.height,
    strokeColor: opts.stroke,
    backgroundColor: opts.fill,
    fillStyle: "solid",
    strokeWidth: 2,
    strokeStyle: "solid",
    roughness: 0,
    opacity: 100,
    angle: 0,
    seed: nextSeed(),
    version: 1,
    versionNonce: nextSeed(),
    isDeleted: false,
    groupIds: opts.groupIds ?? [],
    boundElements: null,
    link: null,
    locked: false,
  };
}

/** 텍스트 요소 생성 */
export function makeText(
  pos: Pos,
  text: string,
  opts?: {
    fontSize?: number;
    color?: string;
    textAlign?: "left" | "center" | "right";
    containerId?: string;
    groupIds?: string[];
    bold?: boolean;
  },
): Record<string, unknown> {
  const fontSize = opts?.fontSize ?? 16;
  const lineHeight = 1.25;
  const lines = text.split("\n");
  const height = lines.length * fontSize * lineHeight;
  const width = Math.max(...lines.map((l) => l.length * fontSize * 0.6));

  return {
    type: "text",
    id: nextId(),
    x: pos.x,
    y: pos.y,
    width,
    height,
    text,
    originalText: text,
    fontSize,
    fontFamily: 2,
    textAlign: opts?.textAlign ?? "center",
    verticalAlign: opts?.containerId ? "middle" : "top",
    strokeColor: opts?.color ?? AMIC_TEXT_COLORS.body,
    backgroundColor: "transparent",
    fillStyle: "solid",
    strokeWidth: 1,
    strokeStyle: "solid",
    roughness: 0,
    opacity: 100,
    angle: 0,
    seed: nextSeed(),
    version: 1,
    versionNonce: nextSeed(),
    isDeleted: false,
    groupIds: opts?.groupIds ?? [],
    boundElements: null,
    link: null,
    locked: false,
    containerId: opts?.containerId ?? null,
    lineHeight,
  };
}

/** 화살표 요소 생성 */
export function makeArrow(
  start: Pos,
  end: Pos,
  opts?: {
    label?: string;
    color?: string;
    strokeWidth?: number;
    strokeStyle?: "solid" | "dashed" | "dotted";
    groupIds?: string[];
  },
): Record<string, unknown>[] {
  const color = opts?.color ?? AMIC_LINE_COLORS.primary;
  const elements: Record<string, unknown>[] = [];

  elements.push({
    type: "arrow",
    id: nextId(),
    x: start.x,
    y: start.y,
    width: end.x - start.x,
    height: end.y - start.y,
    strokeColor: color,
    backgroundColor: "transparent",
    fillStyle: "solid",
    strokeWidth: opts?.strokeWidth ?? 2,
    strokeStyle: opts?.strokeStyle ?? "solid",
    roughness: 0,
    opacity: 100,
    angle: 0,
    seed: nextSeed(),
    version: 1,
    versionNonce: nextSeed(),
    isDeleted: false,
    groupIds: opts?.groupIds ?? [],
    boundElements: null,
    link: null,
    locked: false,
    points: [
      [0, 0],
      [end.x - start.x, end.y - start.y],
    ],
    lastCommittedPoint: null,
    startBinding: null,
    endBinding: null,
    startArrowhead: null,
    endArrowhead: "arrow",
  });

  if (opts?.label) {
    const midX = (start.x + end.x) / 2;
    const midY = (start.y + end.y) / 2;
    elements.push(
      makeText({ x: midX - 20, y: midY - 12 }, opts.label, {
        fontSize: 12,
        color: AMIC_TEXT_COLORS.secondary,
        groupIds: opts?.groupIds,
      }),
    );
  }

  return elements;
}

/** 직선 요소 생성 */
export function makeLine(
  start: Pos,
  end: Pos,
  opts?: {
    color?: string;
    strokeWidth?: number;
    strokeStyle?: "solid" | "dashed" | "dotted";
  },
): Record<string, unknown> {
  return {
    type: "line",
    id: nextId(),
    x: start.x,
    y: start.y,
    width: end.x - start.x,
    height: end.y - start.y,
    strokeColor: opts?.color ?? AMIC_LINE_COLORS.secondary,
    backgroundColor: "transparent",
    fillStyle: "solid",
    strokeWidth: opts?.strokeWidth ?? 1,
    strokeStyle: opts?.strokeStyle ?? "solid",
    roughness: 0,
    opacity: 100,
    angle: 0,
    seed: nextSeed(),
    version: 1,
    versionNonce: nextSeed(),
    isDeleted: false,
    groupIds: [],
    boundElements: null,
    link: null,
    locked: false,
    points: [
      [0, 0],
      [end.x - start.x, end.y - start.y],
    ],
    lastCommittedPoint: null,
    startBinding: null,
    endBinding: null,
    startArrowhead: null,
    endArrowhead: null,
  };
}
