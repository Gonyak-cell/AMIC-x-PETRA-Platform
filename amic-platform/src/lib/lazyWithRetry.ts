import { lazy, type ComponentType, type LazyExoticComponent } from "react";

const CHUNK_LOAD_ERROR_PATTERNS = [
  /ChunkLoadError/i,
  /Failed to fetch dynamically imported module/i,
  /Importing a module script failed/i,
  /error loading dynamically imported module/i,
];

function getAppVersion() {
  return typeof __APP_VERSION__ === "string" ? __APP_VERSION__ : "dev";
}

function getRetryStorageKey(moduleKey: string) {
  return `lazy-retry:${getAppVersion()}:${moduleKey}`;
}

export function isRecoverableChunkLoadError(error: unknown): boolean {
  const message =
    error instanceof Error
      ? `${error.name} ${error.message}`
      : typeof error === "string"
        ? error
        : "";

  return CHUNK_LOAD_ERROR_PATTERNS.some((pattern) => pattern.test(message));
}

export async function loadModuleWithRetry<
  // React.lazy 자체가 Promise<{ default: ComponentType<any> }> 시그니처를 사용한다.
  // Helper 바깥으로는 각 컴포넌트의 실제 props 타입이 그대로 보존된다.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  TModule extends { default: ComponentType<any> },
>(
  importer: () => Promise<TModule>,
  moduleKey: string,
  reload: () => void = () => {
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  },
): Promise<TModule> {
  try {
    const module = await importer();

    if (typeof window !== "undefined") {
      window.sessionStorage.removeItem(getRetryStorageKey(moduleKey));
    }

    return module;
  } catch (error) {
    if (
      typeof window !== "undefined" &&
      isRecoverableChunkLoadError(error)
    ) {
      const retryKey = getRetryStorageKey(moduleKey);
      const hasRetried =
        window.sessionStorage.getItem(retryKey) === "true";

      if (!hasRetried) {
        window.sessionStorage.setItem(retryKey, "true");
        reload();
        return new Promise(() => {});
      }

      window.sessionStorage.removeItem(retryKey);
    }

    throw error;
  }
}

export function lazyWithRetry<
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  TModule extends { default: ComponentType<any> },
>(
  importer: () => Promise<TModule>,
  moduleKey: string,
): LazyExoticComponent<TModule["default"]> {
  return lazy(() => loadModuleWithRetry(importer, moduleKey));
}
