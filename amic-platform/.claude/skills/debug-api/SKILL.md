---
name: debug-api
description: API 연동 디버깅. 프록시, 인증, 응답 형식 이슈 진단.
---
# API 디버깅 가이드

대상 엔드포인트: $ARGUMENTS

## 증상별 진단

### 404 Not Found
1. `vite.config.ts` 프록시 설정 확인
2. API 경로에 `/api/{mod}` 접두사 확인
3. 백엔드 라우터 등록 여부

### 401 Unauthorized
1. localStorage에 토큰이 저장되어 있는지
2. `src/api/client.ts` 인터셉터가 Authorization 헤더 추가하는지
3. 토큰 만료 시 자동 갱신 흐름

### 422 Validation Error
1. 프론트엔드 요청 body와 백엔드 Pydantic 모델 비교
2. 필수 필드 누락 여부
3. 타입 불일치 (string vs number)

### CORS Error
1. Vite 프록시를 통하는지 (dev에서는 CORS 이슈 없어야 함)
2. 프록시 우회 직접 호출이 있는지

### Type Mismatch (런타임)
1. 백엔드 응답 JSON 구조 확인
2. TypeScript 타입 정의와 비교
3. snake_case ↔ camelCase 변환 필요 여부

## 참조 파일
- `src/api/client.ts` — 인터셉터 로직
- `vite.config.ts` — 프록시 설정
- `src/api/{mod}Client.ts` — 모듈별 클라이언트
