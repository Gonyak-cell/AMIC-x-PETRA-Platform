---
name: prod-diagnostic
description: 프로덕션 에러 발생 시 전체 플랫폼 관점 통합 진단. 10개 카테고리 자동 점검.
user-invokable: true
---

# 프로덕션 에러 통합 진단

> **핵심**: 프로덕션 에러는 단일 모듈이 아닌 **전체 플랫폼 관점**에서 진단한다.
> 한 모듈에서 발견된 이슈는 동일 카테고리의 다른 모듈에서도 반드시 점검한다.

## 적용 시점

프로덕션/서버 환경 에러 보고 시: HTTP 에러(401/403/500/502), 로그인 불가, 컨테이너 크래시, CORS 에러 등.

## 절대 금지

- 단일 모듈만 수정하고 끝내기
- 진단 스크립트 없이 개별 점검
- 한 에러만 수정 후 "끝" 선언

## 필수 절차

### Step 1: 통합 진단 스크립트 실행

```bash
ssh -i "ssh/amic-platform-prod_key.pem" -o StrictHostKeyChecking=no azureuser@52.231.69.38 "cd /opt/amic-platform && bash scripts/diagnose-production.sh"
```

10개 카테고리: 컨테이너 상태, DB 연결/비밀번호, DB 마이그레이션, JWT Secret 일관성, CORS 설정, 헬스체크, 크로스 모듈 인증, Nginx & SSL, Redis & ES, 디스크 & 리소스.

### Step 2: 진단 결과 기반 수정

모든 FAIL 항목을 한번에 수정. 동일 카테고리 에러는 **전체 모듈** 한 커밋에서 수정.

### Step 3: 수정 후 재진단

스크립트 재실행 → 10/10 PASS 확인.

## 에러 카테고리별 전수 점검 매트릭스

| 보고된 에러 | 반드시 점검할 카테고리 |
|------------|-------------------|
| 401/403 (인증) | JWT 일관성 + 크로스 모듈 인증 + CORS |
| 404 (Not Found) | nginx location 블록 + API 라우터 prefix + 프론트엔드 라우팅 |
| 422 (Validation) | 요청 Body 스키마 + Pydantic 모델 + FE→BE 타입 불일치 |
| 500 (서버 에러) | DB 연결 + 마이그레이션 + 컨테이너 상태 |
| 502 (게이트웨이) | nginx upstream + 컨테이너 상태 + 리소스 |
| 503 (Service Unavailable) | 컨테이너 헬스체크 + DB 연결 + 리소스 한계 |
| CORS 에러 | **전체 4개 모듈** CORS 환경변수명 + 형식 |
| CSP/보안 헤더 | nginx Content-Security-Policy + X-Frame-Options |
| SSL/인증서 | Let's Encrypt 갱신 + nginx SSL 설정 + 인증서 경로 |
| 로그인 불가 | JWT + 쿠키(Secure/SameSite) + CORS |
| 컨테이너 크래시 | docker logs + 메모리 제한 + DB 연결 |

## 모듈별 CORS 형식

| 모듈 | 환경변수명 | 타입 | .env 형식 |
|------|----------|------|----------|
| FDD | CORS_ORIGINS | str (쉼표) | `https://ap-platform.kr,http://52.231.69.38` |
| KIIS | ALLOWED_ORIGINS | list[str] (JSON) | `["https://ap-platform.kr"]` |
| IM | CORS_ORIGINS | list[str] (JSON) | `["https://ap-platform.kr"]` |
| MA | ALLOWED_ORIGINS | list[str] (JSON) | `["https://ap-platform.kr"]` |

## PostgreSQL 비밀번호 주의

Docker PostgreSQL은 **최초 볼륨 생성 시에만** `POSTGRES_PASSWORD` 적용.
비밀번호 불일치 시: `ALTER USER <user> WITH PASSWORD '<password>';`

## 참조

- 축약판: `.claude/rules/top5-error-prevention.md` P3 (환경변수 불일치) — 항상 로딩
- `scripts/diagnose-production.sh`
- `/post-deploy-check` 스킬 — 배포 후 검증 절차
- `.claude/rules/bugfix-root-cause-verification.md` — 수정 전 원인 확정 필수
