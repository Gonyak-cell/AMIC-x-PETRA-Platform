# Performance Benchmark Results

> Auto FDD 성능 벤치마크 결과 디렉토리

## SLA 정의

| 벤치마크 | SLA | 설명 |
|----------|-----|------|
| GL Ingest (100K rows) | < 30초 | Excel GL 파일 읽기 |
| GL Ingest (1M rows) | < 300초 (5분) | 대용량 GL 처리 |
| QoE Calculation | < 60초 | 500계정 QoE Bridge 계산 |
| PPT Rendering | < 120초 (2분) | Report IR → PPTX 변환 |
| Word Rendering | < 60초 | Report IR → DOCX 변환 |
| API Response (p95) | < 500ms | API 엔드포인트 응답 |
| API Health (avg) | < 2초 | Health check 평균 |
| DB Query | < 1초 | 단일 쿼리 프로파일링 |
| FE Initial Bundle | < 500KB (gzip) | 프론트엔드 초기 로드 |
| FE Total Bundle | < 2000KB | 전체 번들 크기 |

## 벤치마크 실행 방법

```bash
# 전체 벤치마크 (보고서 저장)
python scripts/performance_benchmark.py --target all --output-dir docs/benchmarks

# 개별 벤치마크
python scripts/performance_benchmark.py --target gl_ingest --rows 100000
python scripts/performance_benchmark.py --target qoe
python scripts/performance_benchmark.py --target ppt
python scripts/performance_benchmark.py --target word
python scripts/performance_benchmark.py --target api_load --concurrency 10
python scripts/performance_benchmark.py --target db_profile

# FE 번들 분석
bash scripts/fe_bundle_analysis.sh --ci

# JSON 출력
python scripts/performance_benchmark.py --target all --json
```

## 결과 파일

벤치마크 실행 시 아래 형식으로 결과가 저장됩니다:

- `benchmark-YYYYMMDD_HHMMSS.md` — 마크다운 보고서
- `benchmark-YYYYMMDD_HHMMSS.json` — 기계 판독용 JSON

## CI 통합

- `main` push 시 자동 벤치마크 실행 (`.github/workflows/ci.yml` → `benchmark` job)
- 번들 사이즈 체크 (`.github/workflows/ci.yml` → `bundle-check` job)
- 결과는 GitHub Actions Artifacts로 30일 보관
