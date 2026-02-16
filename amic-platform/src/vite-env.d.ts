/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SENTRY_DSN: string;
  readonly VITE_SENTRY_ENVIRONMENT: string;
  readonly VITE_DISABLE_MSW: string;
  readonly VITE_AUTH_REFRESH_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
