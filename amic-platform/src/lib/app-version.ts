/**
 * 앱 버전 — Single Source of Truth.
 *
 * 빌드 시 vite.config.ts의 `define`이 package.json version을 __APP_VERSION__으로 주입.
 * 모든 UI에서 이 상수를 import하여 사용 — 하드코딩 금지.
 */
export const APP_VERSION: string =
  typeof __APP_VERSION__ !== "undefined" ? __APP_VERSION__ : "0.0.0-dev";
