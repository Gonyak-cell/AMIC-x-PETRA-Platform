# Naver Clova Speech STT API 키 설정

> 작성: 2026-02-26 13:30

## 목적

deal-mgmt 녹음 변환(Transcription) 기능에서 사용하는 **Naver Clova Speech STT API** 키를 로컬 + 프로덕션 환경에 설정.

## 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `deal-mgmt/app/core/config.py` | `CLOVA_CLIENT_ID`, `CLOVA_CLIENT_SECRET` 필드 추가 (pydantic-settings) |
| `deal-mgmt/.env` | 실제 API 키 값 추가 (로컬) |
| `docker-compose.prod.yml` | `deal-mgmt-api` 서비스에 환경변수 매핑 추가 |
| 프로덕션 루트 `.env` | SSH로 키 값 직접 추가 (`/opt/amic-platform/.env`) |
| 프로덕션 `deal-mgmt/.env` | SSH로 키 값 직접 추가 (`/opt/amic-platform/deal-mgmt/.env`) |

## 커밋

| 커밋 | 메시지 |
|------|--------|
| `6236ff5` | `feat(ma/transcription): add Clova Speech STT config fields` |
| `66cfca4` | `feat(docker): pass Clova STT keys to deal-mgmt container` |

## 환경변수 상세

| 환경변수 | 용도 | 출처 |
|---------|------|------|
| `CLOVA_CLIENT_ID` | NCP API Gateway Key ID (`X-NCP-APIGW-API-KEY-ID`) | 네이버 클라우드 콘솔 |
| `CLOVA_CLIENT_SECRET` | NCP API Gateway Key (`X-NCP-APIGW-API-KEY`) | 네이버 클라우드 콘솔 |

## 데이터 흐름

```
deal-mgmt/.env (로컬)
  → pydantic-settings (config.py Settings 클래스)
    → transcription_service.py에서 settings.CLOVA_CLIENT_ID / CLOVA_CLIENT_SECRET 참조
      → Clova Speech API 호출 시 HTTP 헤더로 전달:
          X-NCP-APIGW-API-KEY-ID: {CLOVA_CLIENT_ID}
          X-NCP-APIGW-API-KEY: {CLOVA_CLIENT_SECRET}

프로덕션:
  루트 .env → docker-compose.prod.yml 환경변수 매핑 → 컨테이너 내부 환경변수
```

## API 엔드포인트

- **URL**: `https://clovaspeech-gw.ncloud.com/recog/v1/stt`
- **하드코딩 위치**: `deal-mgmt/app/services/transcription_service.py:19`
- **서비스 환경 URL**: `http://ap-platform.kr` (NCP 콘솔에 등록)

## 프로덕션 검증 결과

```
헬스체크: {"status":"ok","version":"0.1.0","migration_ok":true}
환경변수: CLOVA_CLIENT_ID=f0rxh4rfw1 ✅
          CLOVA_CLIENT_SECRET=NiPlQ... ✅
```

## 이전 상태 (문제)

- `config.py`에 `CLOVA_CLIENT_ID`/`CLOVA_CLIENT_SECRET` 필드 미정의
  - `getattr(settings, "CLOVA_CLIENT_ID", "")` 폴백으로만 접근 → 값이 항상 빈 문자열
- `docker-compose.prod.yml`에서 `deal-mgmt-api`의 `environment`가 명시적으로 나열되어 있어, 컨테이너 내부 `.env`가 무시됨
  - 루트 `.env`에서 compose 변수 치환 → 컨테이너 환경변수로 전달하는 방식 필요

## 주의사항

- `.env` 파일은 git에 커밋하지 않음 (시크릿 포함)
- NCP 콘솔에서 키 재발급 시 로컬 + 프로덕션 `.env` 모두 업데이트 필요
