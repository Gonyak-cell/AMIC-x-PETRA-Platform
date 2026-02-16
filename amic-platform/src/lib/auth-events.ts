/**
 * 인증 이벤트 — React Router 외부(interceptor)에서 로그아웃 트리거용 (M9)
 */
export const AUTH_LOGOUT_EVENT = "auth:force-logout";

export function emitForceLogout(): void {
  window.dispatchEvent(new CustomEvent(AUTH_LOGOUT_EVENT));
}
