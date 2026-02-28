# Production Error Diagnostic Rule

> **핵심**: 프로덕션 에러는 단일 모듈이 아닌 **전체 플랫폼 관점**에서 진단한다.
> 한 모듈에서 발견된 이슈는 동일 카테고리의 다른 모듈에서도 반드시 점검한다.

## 적용 시점

사용자가 다음을 보고할 때 **자동 적용**:
- 프로덕션/서버 환경의 HTTP 에러 (401, 403, 404, 422, 500, 502, 503)
- 로그인 불가, 인증 실패
- 컨테이너 크래시, 서비스 중단
- CORS 에러, CSP 차단
- 느린 응답, 타임아웃
- SSL 인증서 문제
- 배포 후 장애

## 절대 금지

- 단일 모듈만 수정하고 끝내기 (동일 카테고리 타 모듈 미점검)
- 진단 스크립트 없이 개별 curl/docker exec로 점검
- 한 에러만 수정 후 "끝"이라 선언 (전체 진단 미완료 상태에서)

## 필수 절차

### Step 1: 통합 진단 스크립트 실행

에러 수정 **전에** 반드시 실행:

```bash
ssh -i "ssh/amic-platform-prod_key.pem" -o StrictHostKeyChecking=no azureuser@52.231.69.38 "cd /opt/amic-platform && bash scripts/diagnose-production.sh"
```

10개 카테고리를 자동 점검:
1. 컨테이너 상태 (16개 서비스)
2. DB 연결 & 비밀번호 (4개 DB)
3. DB 마이그레이션 (4개 모듈)
4. JWT Secret 일관성 (4개 API)
5. CORS 설정 (4개 API, 형식 포함)
6. 헬스체크 (4개 API + 프론트엔드)
7. 크로스 모듈 인증 (FDD JWT → MA/KIIS)
8. Nginx & SSL (upstream, CSP, HSTS, 인증서 만료)
9. Redis & Elasticsearch (KIIS/IM)
10. 디스크 & 리소스

### Step 2: 진단 결과 기반 수정 계획

진단 결과의 **모든 FAIL 항목**을 한번에 수정한다:
- 동일 카테고리의 에러는 반드시 **전체 모듈**을 한 커밋에서 수정
- 예: JWT 누락이 1개 모듈에서 발견되면, 4개 모듈 모두 확인 후 수정

### Step 3: 수정 후 재진단

수정 완료 후 스크립트를 **재실행**하여 10/10 PASS 확인.

## 에러 카테고리별 전수 점검 매트릭스

| 보고된 에러 | 반드시 점검할 카테고리 |
|------------|-------------------|
| 401/403 (인증) | JWT 일관성 + 크로스 모듈 인증 + CORS |
| 404 (라우팅) | nginx upstream 설정 + API 라우터 등록 |
| 422 (검증 실패) | 요청 스키마 + 프론트엔드 타입 + API 버전 호환성 |
| 500 (서버 에러) | DB 연결 + 마이그레이션 + 컨테이너 상태 + 로그 |
| 502 (게이트웨이) | nginx upstream + 컨테이너 상태 + 리소스 |
| 503 (서비스 불가) | 리소스(메모리/디스크) + 커넥션 풀 + Redis/ES |
| 로그인 불가 | JWT + 쿠키(Secure/SameSite) + CORS + ENV=production |
| 컨테이너 크래시 | docker logs + 메모리 제한 + depends_on + DB 연결 |
| CORS 에러 | **전체 4개 모듈** CORS 환경변수명 + 형식(str/json) |
| CSP/보안 헤더 | prod.conf + prod-nossl.conf **동시** 확인 |
| 느린 응답 | DB 커넥션 풀 + Redis + nginx 타임아웃 |
| SSL/인증서 | certbot 로그 + 만료일 + HSTS + Secure 쿠키 |

## 모듈별 CORS 형식 (필수 참조)

| 모듈 | 환경변수명 | 타입 | .env 형식 예시 |
|------|----------|------|--------------|
| FDD | CORS_ORIGINS | str (쉼표) | `https://ap-platform.kr,http://52.231.69.38` |
| KIIS | ALLOWED_ORIGINS | list[str] (JSON) | `["https://ap-platform.kr","http://52.231.69.38"]` |
| IM | CORS_ORIGINS | list[str] (JSON) | `["https://ap-platform.kr","http://52.231.69.38"]` |
| MA | ALLOWED_ORIGINS | list[str] (JSON) | `["https://ap-platform.kr","http://52.231.69.38"]` |

## PostgreSQL 비밀번호 주의

Docker PostgreSQL은 **최초 볼륨 생성 시에만** `POSTGRES_PASSWORD` 적용.
기존 볼륨 재사용 시 `.env` 변경해도 DB 내부 비밀번호는 바뀌지 않음.

비밀번호 불일치 시:
```bash
docker exec <db-container> psql -U <user> -d <db> -c "ALTER USER <user> WITH PASSWORD '<password>';"
```

## 참조

- `scripts/diagnose-production.sh` — 통합 진단 스크립트
- `docs/deployment/ERROR_CATALOG.md` — 에러 카탈로그
- `.claude/rules/post-deploy-verification.md` — 배포 후 검증 규칙
- `.claude/rules/bugfix-root-cause-verification.md` — 버그 수정 근본 원인 확정 규칙
