# 모노레포 전용 개발 규칙

## 백엔드 코드 수정 위치

**반드시 모노레포 내 디렉터리만 수정한다.**

| 모듈 | 수정 경로 (모노레포) | 금지 경로 (단독 리포) |
|------|---------------------|---------------------|
| FDD | `fdd/backend/` | `Auto FDD/backend/` |
| KIIS | `kiis/` | `KIIS/` |
| IM | `im/` | `IM Module/auto-im-generator/` |
| MA | `deal-mgmt/` | — |

## 이유

Docker compose는 모노레포 디렉터리를 볼륨 마운트한다:
```yaml
fdd-api:  volumes: ./fdd/backend:/app
kiis-api: volumes: ./kiis:/app
im-api:   volumes: ./im:/app
```

단독 리포에서 코드를 수정해도 Docker 컨테이너에 반영되지 않는다.

## 규칙

1. 백엔드 코드 수정 시 모노레포 `fdd/`, `kiis/`, `im/`, `deal-mgmt/`만 편집
2. 단독 리포 디렉터리는 읽기 전용 참조용 (수정 금지)
3. `docker compose up --build`로 변경사항 검증
4. 단독 리포에서 발견한 코드가 모노레포에 없으면, 모노레포로 복사 후 수정
