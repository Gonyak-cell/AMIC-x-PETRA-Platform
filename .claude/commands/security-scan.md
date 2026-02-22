---
name: security-scan
description: 모노레포 전체 보안 감사를 실행합니다. 특정 모듈을 인자로 전달 가능.
---
# 보안 감사 실행

대상: $ARGUMENTS (미지정 시 전체 모노레포)

## 1단계: 시크릿 스캔
- 코드에 하드코딩된 API 키, 비밀번호, 토큰 검색 (fdd/, kiis/, im/, amic-platform/)
- `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
- git history에 시크릿이 커밋된 적 있는지 확인

## 2단계: 코드 보안 검토
- @backend-security-reviewer 에이전트 사용
- SQL Injection 취약점 스캔 (f-string SQL 금지)
- Command Injection 패턴 검색
- XSS 취약점 (dangerouslySetInnerHTML 금지)
- SSRF 위험 (외부 URL 검증)
- Path Traversal (파일명 sanitization)

## 3단계: API 보안 검토
- 인증 미적용 엔드포인트 목록 (모든 백엔드)
- CORS 설정 검토 (docker-compose*.yml)
- Rate limiting 적용 현황

## 4단계: 의존성 취약점
```bash
# Python (각 모듈별)
cd fdd/backend && pip audit
cd kiis && pip audit
cd im && pip audit

# Node.js
cd amic-platform && npm audit
```

## 5단계: 인프라 보안
- Docker compose: 시크릿 환경변수 기본값 없는지
- Docker: root 사용자 실행 여부
- Nginx: HTTPS 강제, 보안 헤더 (X-Frame-Options, CSP 등)
- `.dockerignore` 적절성

## 6단계: 보고서 생성
- 발견 사항을 심각도별 분류 (CRITICAL/HIGH/MEDIUM/LOW)
- 각 취약점에 대한 수정 방법 제시
- 총 검사 항목 수 및 통과/실패 요약
