# Post-Deploy Verification Rule

> 프로덕션 코드 수정 후 배포 검증 자동화 규칙

## 적용 시점

다음 파일을 수정한 후 **자동 적용**:
- `docker-compose.prod.yml`, `docker-compose.ssl.yml`
- `nginx/prod.conf`, `nginx/prod-nossl.conf`
- 백엔드 환경변수 관련 설정 (`config.py`, `settings.py` 등)
- 인증/CORS 관련 코드 (auth, security, middleware)

## 필수 절차 (코드 수정 완료 후)

### Step 1: 수정 내역 문서 저장

수정 내용을 `docs/deployment/` 폴더에 문서로 저장한다:
- 파일명: `YYYYMMDD_HHMM_{요약}.md` (타임스탬프 규칙 적용)
- 내용: 문제 요약, 근본 원인, 수정 내역, 검증 결과
- `docs/INDEX.md` 업데이트

### Step 2: 커밋 & 푸시

```bash
git add <수정된 파일들>
git commit -m "<conventional commit message>"
git push origin <current-branch>
```

### Step 3: 프로덕션 서버 검증 (SSH)

커밋 & 푸시 후 반드시 SSH로 서버 상태를 검증한다:

#### 3-1. 배포 반영 확인
```bash
# CI/CD 자동 배포 대기 또는 수동 pull
ssh azureuser@52.231.69.38 "cd /opt/amic-platform && git log --oneline -1"
```

#### 3-2. 환경변수 검증
```bash
# .env의 CORS 값이 올바른 형식인지 확인
ssh azureuser@52.231.69.38 "cd /opt/amic-platform && grep -E 'CORS_ORIGINS|ALLOWED_ORIGINS|JWT_SECRET' .env"
```

**CORS 값 형식 규칙:**
| 백엔드 설정 타입 | .env 형식 | 예시 |
|-----------------|----------|------|
| `str` (쉼표 구분) | `value1,value2` | `FDD_CORS_ORIGINS=https://ap-platform.kr,http://52.231.69.38` |
| `list[str]` (JSON 배열) | `["v1","v2"]` | `KIIS_CORS_ORIGINS=["https://ap-platform.kr","http://52.231.69.38"]` |

**현재 모듈별 CORS 타입:**
- FDD: `cors_origins: str` → 쉼표 구분
- KIIS: `ALLOWED_ORIGINS: list[str]` → JSON 배열
- IM: `allowed_origins: list[str]` (alias `CORS_ORIGINS`) → JSON 배열
- MA: `ALLOWED_ORIGINS: list[str]` → JSON 배열

#### 3-3. 컨테이너 헬스체크
```bash
curl -s https://ap-platform.kr/api/fdd/health
curl -s https://ap-platform.kr/api/kiis/health
curl -s https://ap-platform.kr/api/im/health
curl -s https://ap-platform.kr/api/ma/health
```

**기대 결과:** 모든 모듈 `"status":"ok"`, `"migration_ok":true`

#### 3-4. 크로스 모듈 인증 검증
```bash
# FDD 로그인
curl -s -c /tmp/cookies.txt -X POST https://ap-platform.kr/api/fdd/auth/login \
  -H 'Content-Type: application/json' -d '{"email":"jwsuh@amic.kr","password":"1111"}'

# 다른 모듈에서 FDD JWT 검증
curl -s -b /tmp/cookies.txt https://ap-platform.kr/api/fdd/auth/me
curl -s -b /tmp/cookies.txt https://ap-platform.kr/api/ma/transactions
```

**기대 결과:** 200 응답 (401/500 아님)

### Step 4: 검증 실패 시

1. 컨테이너 로그 확인: `docker compose logs <service> --tail=50`
2. 환경변수 실제 값 확인: `docker exec <container> env | grep -E 'JWT|CORS|ALLOWED|DATABASE'`
3. DB 비밀번호 불일치 시: `ALTER USER <user> WITH PASSWORD '<password>';` (볼륨 재사용 시 발생)
4. `.env` 수정 후: `docker compose restart` 아닌 `docker compose up -d --no-deps <service>` 사용

## PostgreSQL 비밀번호 관련 주의사항

> `docker compose up -d`로 DB 컨테이너를 재생성해도, 기존 볼륨의 비밀번호는 변경되지 않는다.
> `POSTGRES_PASSWORD`는 **최초 데이터 디렉토리 생성 시에만** 적용된다.

비밀번호 불일치 발생 시:
```bash
docker exec <db-container> psql -U <user> -d <db> -c "ALTER USER <user> WITH PASSWORD '<new-password>';"
```

## 절대 금지

- `docker compose down -v` (볼륨 삭제 → 데이터 유실)
- 컨테이너 재빌드 시 계정 리셋
- `.env`의 `*_DB_PASSWORD` 변경 후 DB 내부 비밀번호 미동기화
