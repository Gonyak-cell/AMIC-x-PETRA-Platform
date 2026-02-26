# CI/CD 헬스체크 SSL 리다이렉트 수정 보고서

> 작성: 2026-02-26 12:54
> 브랜치: feat/ma-workflow
> 관련 커밋: 4f9b31b, 6d6a59c, 5fdf049, e5fd06f

## 배경

프로덕션 통합 진단 시스템(진단 스크립트, 에러 카탈로그, deploy.yml 강화) 배포 시 헬스체크 실패로 자동 롤백 발생. 3회 연속 배포 실패 후 근본 원인을 파악하여 수정.

## 증상

deploy.yml 헬스체크에서 4개 API + 프론트엔드 전부 `FAILED (status=unknown, migration=N/A)`:
```
fdd:      FAILED (status=unknown, migration=N/A)
kiis:     FAILED (status=unknown, migration=N/A)
im:       FAILED (status=unknown, migration=N/A)
ma:       FAILED (status=unknown, migration=N/A)
frontend: FAILED
```

## 근본 원인

**nginx SSL 리다이렉트로 인한 localhost 헬스체크 실패**

1. `docker-compose.ssl.yml`이 nginx 설정을 `prod.conf`로 오버라이드
2. `prod.conf`는 HTTP→HTTPS 리다이렉트 (`return 301 https://$host$request_uri`)
3. 헬스체크 `curl http://localhost/api/fdd/health` 실행 시:
   - nginx가 `301 https://localhost/api/fdd/health`로 리다이렉트
   - SSL 인증서가 `ap-platform.kr`용이므로 `localhost`에서 SSL 핸드셰이크 실패
   - curl이 빈 응답 반환 → `status=unknown`

## 해결 과정 (3회 실패 → 성공)

| 시도 | 커밋 | 결과 | 문제 |
|------|------|------|------|
| 1차 | 6d6a59c | 실패 (3m52s) | 헬스체크 1회 시도, SSL 리다이렉트 실패 |
| 2차 | 5fdf049 | 실패 (1m20s) | 재시도 3회 추가했으나 SSL 문제 미해결 |
| 3차 | e5fd06f | **성공** (1m19s) | docker exec로 컨테이너 내부에서 직접 헬스체크 |

## 최종 수정 (e5fd06f)

### 핵심 변경: nginx 우회 → 컨테이너 직접 헬스체크

**이전** (호스트에서 nginx 경유):
```bash
curl -sf http://localhost/api/$ep/health
```

**이후** (docker exec로 컨테이너 내부):
```bash
# 백엔드: 각 API 컨테이너 내부에서 python3로 직접 호출
$COMPOSE exec -T "$SVC" python3 -c "import urllib.request as u;r=u.urlopen('http://localhost:8000/health',timeout=10);print(r.read().decode())"

# 프론트엔드: nginx 컨테이너에서 frontend upstream 직접 호출
$COMPOSE exec -T nginx wget -qO/dev/null --timeout=10 http://frontend:80/
```

### 추가 개선

| 항목 | 변경 |
|------|------|
| 헬스체크 재시도 | 1회 → 3회 (15초 간격) |
| 롤백 방식 | `git checkout "$PREV_COMMIT"` (detached HEAD) → `git checkout "$BRANCH" && git reset --hard "$PREV_COMMIT"` |
| 응답 검증 | HTTP 200만 확인 → 응답 본문 `status`, `migration_ok` 필드 파싱 |

## 검증 결과 (e5fd06f 배포)

```
Services to rebuild: frontend nginx
=== [6/6] Health Check ===
  Attempt 1/3 (waiting 15s)...
    fdd: OK (status=ok, migration=True)
    kiis: OK (status=ok, migration=True)
    im: OK (status=ok, migration=N/A)
    ma: OK (status=ok, migration=True)
    frontend: OK
  All checks passed on attempt 1
=== [7/7] Post-Deploy Diagnostic ===
=== Deployment complete — all checks passed ===
```

## 교훈

1. **SSL 환경에서 localhost 헬스체크는 실패한다** — prod.conf의 HTTP→HTTPS 리다이렉트 때문
2. **docker exec가 가장 신뢰할 수 있는 헬스체크 방법** — nginx/SSL 설정에 의존하지 않음
3. **헬스체크는 반드시 재시도 로직 필요** — 컨테이너 재시작 후 일시적 불가 상태 대비
4. **롤백 시 detached HEAD 방지** — `git checkout <commit>`이 아닌 `git checkout <branch> && git reset --hard <commit>` 사용
