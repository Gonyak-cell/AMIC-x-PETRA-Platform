/// <reference types="vite/client" />

/** 빌드 시 vite.config.ts define으로 주입되는 앱 버전 (package.json version) */
declare const __APP_VERSION__: string;

interface ImportMetaEnv {
  readonly VITE_SENTRY_DSN: string;
  readonly VITE_SENTRY_ENVIRONMENT: string;
  readonly VITE_AUTH_REFRESH_URL: string;
  readonly VITE_MA_AUTH_REFRESH_URL?: string;
  readonly VITE_DEV_LOCAL_AUTH?: string;
  readonly VITE_ENABLE_BUYER_DEV_MOCKS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
