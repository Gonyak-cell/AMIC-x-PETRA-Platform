# Security Checklist

> 출처: software-dev-ai-claude-toolkit (Ashfaqbs) + Trail of Bits 참조

## 커밋 전 필수 확인
- [ ] 코드에 하드코딩된 시크릿, API 키, 비밀번호, 토큰 없음.
- [ ] SQL 쿼리는 파라미터화된 구문 사용 (문자열 연결 금지).
- [ ] 사용자 입력은 검증 후 사용 (Pydantic 모델 또는 명시적 검증).
- [ ] `.env` 파일이 `.gitignore`에 포함.

## 인증 & 인가
- JWT 기반 인증. httpOnly 쿠키에 저장 (localStorage 금지 — SEC-001 완료).
- 짧은 수명 액세스 토큰 (15~60분), 긴 수명 리프레시 토큰.
- 엔드포인트별 권한 체크: `Depends(get_current_user)`.
- 커스텀 암호화 구현 금지. 검증된 라이브러리 사용.

## 시크릿 관리
- 민감 정보: 환경 변수 또는 시크릿 매니저 (Vault, AWS Secrets Manager).
- `.env` 파일 커밋 금지.
- 로그에 시크릿 출력 금지.

## API 보안
- CORS: 명시적 허용 오리진. 와일드카드(`*`) 금지.
- 보안 헤더: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`.
- Rate limiting 적용 (인증 엔드포인트 필수).
- 에러 응답에 내부 스택 트레이스 노출 금지.

## 데이터 보호
- 전송 중 데이터: TLS 필수 (DB 연결, API 통신 포함).
- 감사 로깅: 로그인, 데이터 액세스, 관리자 작업 기록.
- PII (개인정보): 최소 수집, 암호화 저장.

## 컨테이너 보안
- Docker 이미지 취약점 스캔 (Trivy, Snyk).
- non-root 사용자로 컨테이너 실행.
- 최신 의존성 유지. 보안 업데이트 모니터링.

## 정적 분석 (참고 — Trail of Bits)
- CodeQL 또는 Semgrep 규칙 적용 고려.
- OWASP Top 10 취약점 체크리스트 주기적 검토.
- 코드 리뷰 시 보안 관점 포함 (`security-reviewer` 에이전트 활용).
