const PREFIX = "amic_";

export function getItem<T>(key: string, defaultValue: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    if (raw === null) return defaultValue;
    return JSON.parse(raw) as T;
  } catch {
    return defaultValue;
  }
}

export function setItem<T>(key: string, value: T): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // QuotaExceededError — 조용히 무시 (데이터 미저장, 기능은 계속)
    console.warn(`[storage] Failed to save key "${key}" — quota exceeded`);
  }
}
