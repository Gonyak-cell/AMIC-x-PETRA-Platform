---
name: post-deploy-check
description: 프로덕션 배포 후 검증 절차. 수정 문서화 + 커밋 + SSH 서버 검증 + 크로스 모듈 인증 테스트.
user-invokable: true
---

# 배포 후 검증 절차

> 프로덕션 코드 수정 후 배포 검증 자동화 규칙.

## 절대 금지

- `docker compose down -v` (볼륨 삭제 → 데이터 유실)
- `.env`의 `*_DB_PASSWORD` 변경 후 DB 내부 비밀번호 미동기화

## 적용 시점

`docker-compose.prod.yml`, `nginx/prod.conf`, 환경변수 설정, 인증/CORS 관련 코드 수정 후.

## Step 1: 수정 내역 문서 저장

`docs/deployment/YYYYMMDD_HHMM_{요약}.md` — 문제 요약, 근본 원인, 수정 내역, 검증 결과.

## Step 2: 커밋 & 푸시

```bash
git add <수정된 파일들>
git commit -m "<conventional commit message>"
git push origin <current-branch>
```

## Step 3: 프로덕션 서버 검증

### 3-1. 배포 반영 확인
```bash
ssh -i "ssh/amic-platform-prod_key.pem" -o StrictHostKeyChecking=no azureuser@52.231.69.38 "cd /opt/amic-platform && git log --oneline -1"
```

### 3-2. 환경변수 검증
```bash
ssh -i "ssh/amic-platform-prod_key.pem" -o StrictHostKeyChecking=no azureuser@52.231.69.38 "cd /opt/amic-platform && grep -E 'CORS_ORIGINS|ALLOWED_ORIGINS|JWT_SECRET' .env"
```

**CORS 값 형식**: FDD=`str`(쉼표), KIIS/IM/MA=`list[str]`(JSON 배열)

### 3-3. 헬스체크
```bash
curl -s https://ap-platform.kr/api/fdd/health
curl -s https://ap-platform.kr/api/kiis/health
curl -s https://ap-platform.kr/api/im/health
curl -s https://ap-platform.kr/api/ma/health
```

기대 결과: `"status":"ok"`, `"migration_ok":true`

### 3-4. 크로스 모듈 인증
```bash
curl -s -c /tmp/cookies.txt -X POST https://ap-platform.kr/api/fdd/auth/login \
  -H 'Content-Type: application/json' -d '{"email":"jwsuh@amic.kr","password":"1111"}'
curl -s -b /tmp/cookies.txt https://ap-platform.kr/api/fdd/auth/me
curl -s -b /tmp/cookies.txt https://ap-platform.kr/api/ma/transactions
```

기대 결과: 200 응답

## Step 4: 검증 실패 시

1. `docker compose logs <service> --tail=50`
2. `docker exec <container> env | grep -E 'JWT|CORS|DATABASE'`
3. DB 비밀번호 불일치: `ALTER USER` (볼륨 재사용 시)
4. `.env` 수정 후: `docker compose up -d --no-deps <service>`

## 참조

- 축약판: `.claude/rules/top5-error-prevention.md` P3 (환경변수 불일치) — 항상 로딩
- `/prod-diagnostic` 스킬 — 프로덕션 에러 통합 진단
- `.claude/rules/infra-freeze.md` — 인프라 파일 보호
