"""LDD 10단계 파이프라인 독립 실행 스크립트.

Pjt. Green 실사자료를 사용하여 전체 LDD 보고서 생성 플로우를 테스트한다.
DB/서버 없이 로컬에서 실행 가능.

Usage:
    cd deal-mgmt

    # Step 1: 파싱+분류만 (비용 $0)
    python scripts/run_ldd_pipeline.py --parse-only

    # Step 2: 섹션당 상위 5개 파일만으로 파이프라인 실행
    python scripts/run_ldd_pipeline.py --max-files 5

    # Step 3: 전체 파이프라인
    python scripts/run_ldd_pipeline.py --max-cost 20.0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

# ── deal-mgmt를 PYTHONPATH에 추가 ──
DEAL_MGMT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DEAL_MGMT_DIR))

# ── .env 로드 ──
try:
    from dotenv import load_dotenv

    load_dotenv(DEAL_MGMT_DIR / ".env")
except ImportError:
    print("[WARN] python-dotenv 미설치 — 환경변수를 직접 설정하세요")

# ── 소스 폴더 (Pjt. Green) ──
DEFAULT_SOURCE_DIR = (
    r"C:\Users\서지원\OneDrive - 주식회사 페트라브릿지파트너스"
    r"\AMIC의 파일 - 1. AMIC\5. 기업 인수&합병\99_Archives\10_Pjt. Green\실사자료"
)

# ── 출력 디렉토리 ──
OUTPUT_DIR = DEAL_MGMT_DIR / "output"
TEMPLATE_DIR = DEAL_MGMT_DIR / "templates" / "ldd"

# ── 로깅 설정 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ldd_pipeline")

# 외부 라이브러리 로깅 레벨 조정
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


# ── 파일 유형별 우선순위 (문서 > 데이터) ──
EXT_PRIORITY = {
    ".pdf": 1,
    ".hwp": 2,
    ".hwpx": 2,
    ".docx": 3,
    ".xlsx": 4,
    ".xls": 5,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LDD 10단계 파이프라인 독립 실행")
    parser.add_argument(
        "--source-dir",
        default=DEFAULT_SOURCE_DIR,
        help="실사자료 폴더 경로 (기본: Pjt. Green)",
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="파싱+분류만 수행 (LLM 호출 없음, 비용 $0)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="섹션당 사용할 최대 파일 수 (0=전체)",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        default=15.0,
        help="LLM 비용 한도 USD (기본: 15.0)",
    )
    parser.add_argument(
        "--deal-type",
        default="STOCK_ACQUISITION",
        help="거래유형 (STOCK_ACQUISITION, REAL_ESTATE, IPO 등)",
    )
    parser.add_argument(
        "--no-narrative",
        action="store_true",
        help="Stage 6 서술 생성 비활성화 (비용 절약)",
    )
    parser.add_argument(
        "--no-docx",
        action="store_true",
        help="DOCX 보고서 렌더링 건너뛰기",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai", "google"],
        default=None,
        help="특정 프로바이더만 사용 (나머지 키 무시, 폴백 없이 단일 프로바이더)",
    )
    return parser.parse_args()


def print_header():
    print()
    print("=" * 60)
    print("  LDD 10단계 파이프라인 독립 실행 (Pjt. Green)")
    print("=" * 60)
    print()


# ── Stage 0: 소스 파일 스캔 + 파싱 ──


def stage0_scan(source_dir: str) -> list[dict]:
    """소스 디렉토리를 스캔하여 지원 파일 목록을 반환한다."""
    from app.ralph.parsers.file_classifier import scan_directory

    print("[Stage 0] 소스 파일 스캔")
    print(f"  폴더: {source_dir}")

    if not Path(source_dir).exists():
        print("  [ERROR] 폴더가 존재하지 않습니다!")
        sys.exit(1)

    t0 = time.time()
    file_list = scan_directory(source_dir)
    elapsed = time.time() - t0

    # 통계
    ext_counts = Counter(f["ext"] for f in file_list)
    total_size_mb = sum(f["size_kb"] for f in file_list) / 1024

    print(f"  지원 파일: {len(file_list)}개 (스캔 {elapsed:.1f}s)")
    for ext, count in ext_counts.most_common():
        print(f"    {ext:6s}: {count:>5}개")
    print(f"  총 크기: {total_size_mb:.1f} MB")
    print()

    return file_list


def _check_onedrive_availability(file_list: list[dict]) -> tuple[int, int]:
    """OneDrive 클라우드 전용 파일 비율을 확인한다.

    Returns:
        (readable_count, cloud_only_count)
    """
    import random

    # 최대 20개 샘플로 확인
    sample = random.sample(file_list, min(20, len(file_list)))
    readable = 0
    cloud_only = 0

    for info in sample:
        try:
            with open(info["path"], "rb") as f:
                f.read(1)  # 1바이트만 읽기 시도
            readable += 1
        except OSError:
            cloud_only += 1

    return readable, cloud_only


def stage0_parse(file_list: list[dict]) -> list:
    """파일 목록을 파싱하여 ParsedFile 리스트를 반환한다."""
    from app.ralph.parsers import parse_file
    from app.ralph.parsers.file_classifier import classify_file

    # OneDrive 클라우드 전용 파일 확인
    readable, cloud_only = _check_onedrive_availability(file_list)
    if cloud_only > readable:
        print("[WARN] OneDrive 클라우드 전용 파일이 다수 감지됨!")
        print(f"  샘플 검사: 읽기 가능 {readable}개, 클라우드 전용 {cloud_only}개")
        print()
        print("  해결 방법:")
        print("  1. 파일 탐색기에서 실사자료 폴더 우클릭")
        print("     → '이 디바이스에 항상 유지' 선택")
        print("  2. 또는 폴더를 로컬 경로로 복사:")
        print('     xcopy /E /I "원본폴더" "C:\\temp\\실사자료"')
        print()
        print("  파일 다운로드 후 스크립트를 다시 실행하세요.")
        print("  (일부 읽기 가능한 파일만으로 계속하려면 Enter)")
        if sys.stdin.isatty():
            try:
                input("  계속하려면 Enter, 중단하려면 Ctrl+C: ")
            except KeyboardInterrupt:
                print("\n  중단됨.")
                sys.exit(0)
        else:
            print("  (비대화형 모드 — 읽기 가능 파일만으로 계속)")

    print("[Stage 0] 파일 파싱 + 섹션 분류")
    total = len(file_list)
    parsed_files = []
    failed = 0
    cloud_errors = 0
    last_pct = -1

    t0 = time.time()
    for i, info in enumerate(file_list):
        pct = (i + 1) * 100 // total
        if pct != last_pct and pct % 5 == 0:
            print(f"  파싱 중... {pct}% ({i + 1}/{total})", end="\r")
            last_pct = pct

        try:
            pf = parse_file(info["path"])
            pf.ddrl_sections = classify_file(info["path"], pf)
            parsed_files.append(pf)
        except OSError:
            cloud_errors += 1
            # OneDrive 클라우드 전용 파일 — 무시
        except Exception as exc:
            failed += 1
            if failed <= 5:
                logger.warning("파싱 실패: %s — %s", Path(info["path"]).name, exc)

    elapsed = time.time() - t0
    valid = sum(1 for pf in parsed_files if pf.is_valid)
    invalid_with_error = sum(1 for pf in parsed_files if pf.parse_error)
    print(f"\n  파싱 완료: {len(parsed_files)}개 ({elapsed:.1f}s)")
    print(f"  유효: {valid}개, 파싱 에러: {invalid_with_error}개, 예외: {failed}개, 클라우드 전용: {cloud_errors}개")

    if valid == 0 and cloud_errors > 0:
        print()
        print("  [ERROR] 유효한 파일이 0개입니다!")
        print("  OneDrive 파일을 로컬로 다운로드 후 다시 실행하세요.")
        print("  또는 --source-dir로 로컬 폴더를 지정하세요.")
    print()

    return parsed_files


def build_source_map(parsed_files: list) -> dict[str, list]:
    """ParsedFile 목록에서 section_type → [ParsedFile] 매핑을 구축한다."""
    source_map: dict[str, list] = defaultdict(list)

    classified = 0
    unclassified = 0

    for pf in parsed_files:
        if not pf.is_valid:
            continue
        if pf.ddrl_sections:
            classified += 1
            for section in pf.ddrl_sections:
                source_map[section].append(pf)
        else:
            unclassified += 1

    print("[섹션 매핑 결과]")
    for section_type in sorted(source_map.keys()):
        print(f"  {section_type:20s}: {len(source_map[section_type]):>5}개 파일")
    print(f"  미분류: {unclassified}개")
    print()

    return dict(source_map)


def filter_source_map(source_map: dict[str, list], max_files: int) -> dict[str, list]:
    """섹션당 상위 N개 파일만 선택한다 (우선순위: PDF > HWP > DOCX > XLS)."""
    if max_files <= 0:
        return source_map

    print(f"[파일 필터링] 섹션당 상위 {max_files}개")

    filtered = {}
    total_before = sum(len(v) for v in source_map.values())

    for section_type, files in source_map.items():
        # 파일 유형 + 크기 기준 정렬
        sorted_files = sorted(
            files,
            key=lambda pf: (
                EXT_PRIORITY.get(Path(pf.source_path).suffix.lower(), 9),
                -len(pf.text),  # 텍스트 긴 것 우선
            ),
        )
        filtered[section_type] = sorted_files[:max_files]

    total_after = sum(len(v) for v in filtered.values())
    print(f"  {total_before}개 → {total_after}개 (섹션 {len(filtered)}개)")
    print()

    return filtered


def print_parse_summary(source_map: dict[str, list], sections_config: list[dict]):
    """파싱 결과 요약을 출력한다."""
    print("[파싱 결과 요약]")
    print(f"  체크리스트 섹션: {len(sections_config)}개")
    total_items = sum(len(s.get("items", [])) for s in sections_config)
    print(f"  체크리스트 항목: {total_items}개")
    print(f"  매핑된 섹션: {len(source_map)}개")

    mapped = set(source_map.keys())
    expected = set(s.get("section_type", "") for s in sections_config)
    missing = expected - mapped
    if missing:
        print(f"  [WARN] 자료 미매핑 섹션: {', '.join(sorted(missing))}")
    print()


# ── LLM 초기화 ──


def init_llm(provider: str | None = None):
    """RalphLLMClient + LDDModelRouter를 초기화한다.

    Args:
        provider: 특정 프로바이더만 사용할 경우 지정 (나머지 키 비활성화).
    """
    from app.ralph.llm_client import RalphLLMClient
    from app.ralph.routing.ldd_router import LDDModelRouter

    print("[LLM 초기화]")

    api_keys = {
        "Anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
        "OpenAI": os.getenv("OPENAI_API_KEY", ""),
        "Google": os.getenv("GOOGLE_API_KEY", ""),
    }

    # --provider 옵션: 지정 프로바이더 외 키를 비활성화하여 폴백 없이 단일 프로바이더 사용
    if provider:
        provider_key_map = {"anthropic": "Anthropic", "openai": "OpenAI", "google": "Google"}
        active_name = provider_key_map[provider]
        for name in api_keys:
            if name != active_name:
                api_keys[name] = ""
        print(f"  [단일 프로바이더 모드] {active_name}만 사용")

    for name, key in api_keys.items():
        status = "설정됨" if key else "미설정"
        print(f"  {name:10s}: {status}")

    llm_client = RalphLLMClient(
        anthropic_api_key=api_keys["Anthropic"],
        openai_api_key=api_keys["OpenAI"],
        google_api_key=api_keys["Google"],
        primary_model=os.getenv("RALPH_PRIMARY_MODEL", "claude-sonnet-4-20250514"),
        judge_model=os.getenv("RALPH_JUDGE_MODEL", "gpt-4o"),
    )

    if not llm_client.is_available:
        print("  [ERROR] 사용 가능한 LLM 프로바이더가 없습니다!")
        print("  .env 파일에 API 키를 설정하세요.")
        sys.exit(1)

    # 단일 프로바이더 모드면 모든 라우팅을 해당 프로바이더로 고정
    routing_map = None
    if provider:
        routing_map = {k: provider for k in LDDModelRouter(llm_client)._routing_map}

    router = LDDModelRouter(llm_client, routing_map=routing_map)
    print(f"  사용 가능 프로바이더: {router.available_providers}")
    print()

    return llm_client, router


# ── 메인 파이프라인 실행 ──


async def run_pipeline(
    llm_client,
    router,
    source_map: dict[str, list],
    sections_config: list[dict],
    args: argparse.Namespace,
):
    """10단계 파이프라인을 실행한다."""
    from app.ralph.generators.ldd.pipeline import LDDMultiLLMPipeline
    from app.ralph.generators.ldd.pipeline_config import LDDPipelineConfig

    config = LDDPipelineConfig(
        stage3_risk_dual=True,
        stage4_gap_detection=True,
        stage5_jurisdiction=False,  # 국내 거래
        stage6_narrative=not args.no_narrative,
        stage7_qa=True,
        max_cost_usd=args.max_cost,
        deal_type=args.deal_type,
        is_cross_border=False,
        deal_summary=f"Pjt. Green — {args.deal_type} 거래 LDD",
    )

    print("[파이프라인 실행]")
    print(f"  거래유형: {args.deal_type}")
    print(f"  비용 한도: ${args.max_cost:.2f}")
    print(f"  서술 생성: {'ON' if config.stage6_narrative else 'OFF'}")
    print(f"  듀얼 리스크: {'ON' if config.stage3_risk_dual else 'OFF'}")
    print(f"  누락 탐지: {'ON' if config.stage4_gap_detection else 'OFF'}")
    print(f"  최종 QA: {'ON' if config.stage7_qa else 'OFF'}")
    print()

    pipeline = LDDMultiLLMPipeline(
        llm_client=llm_client,
        router=router,
        config=config,
        source_map=source_map,
        sections_config=sections_config,
    )

    # VDR 문서명 목록 (갭 탐지용)
    vdr_names = []
    for files in source_map.values():
        for pf in files:
            vdr_names.append(Path(pf.source_path).name)

    t0 = time.time()
    result = await pipeline.run(vdr_document_names=vdr_names)
    elapsed = time.time() - t0

    # Stage 진행 상태 출력
    print()
    print("[Stage 결과]")
    for stage_info in result.stages:
        stage_num = stage_info["stage"]
        name = stage_info["name"]
        status = stage_info["status"]
        status_icon = {
            "completed": "OK",
            "skipped": "SKIP",
            "pending": "PENDING",
        }.get(status, status)
        print(f"  Stage {stage_num:>2}: {name:20s} [{status_icon}]")

    print(f"\n  실행 시간: {elapsed:.1f}s")
    print(f"  누적 비용: ${result.cost_usd:.4f}")
    print()

    return result


def print_result_summary(result):
    """파이프라인 결과 요약을 출력한다."""
    print("[결과 요약]")

    total_items = 0
    ok_count = issue_count = na_count = pending_count = 0
    red = amber = green = 0

    for _section_type, items in result.sections.items():
        for item in items:
            total_items += 1
            status = item.get("status", "PENDING")
            if status == "OK":
                ok_count += 1
            elif status == "ISSUE":
                issue_count += 1
                level = item.get("issue_level", "")
                if level in ("CRITICAL", "HIGH"):
                    red += 1
                elif level == "MEDIUM":
                    amber += 1
                elif level == "LOW":
                    green += 1
            elif status == "NA":
                na_count += 1
            else:
                pending_count += 1

    print(f"  총 항목: {total_items}개")
    print(f"  OK: {ok_count}, ISSUE: {issue_count}, NA: {na_count}, PENDING: {pending_count}")
    print(f"  이슈 분포: RED {red}, AMBER {amber}, GREEN {green}")
    print(f"  총 비용: ${result.cost_usd:.4f}")

    # 듀얼 리스크
    if result.dual_risk_summary:
        drs = result.dual_risk_summary
        print(
            f"\n  [듀얼 리스크] 분석 {drs.get('total_analyzed', 0)}건, "
            f"자동해결 {drs.get('auto_resolved', 0)}건, "
            f"검토필요 {drs.get('needs_human_review', 0)}건"
        )

    # 갭 탐지
    if result.gap_detection:
        gd = result.gap_detection
        print(
            f"  [누락 탐지] 체크리스트 {gd.get('total_checklist', 0)}건, "
            f"자유탐색 {gd.get('total_freeform', 0)}건, "
            f"유니크 {gd.get('total_unique', 0)}건"
        )

    # 서술
    if result.narrative_sections:
        ns = result.narrative_sections
        total_blocks = sum(len(item.get("blocks", [])) for items in ns.values() for item in items)
        print(f"  [서술] {len(ns)}개 섹션, {total_blocks}개 블록")

    # QA
    if result.qa_result:
        qa = result.qa_result
        if "overall_score" in qa:
            print(f"  [QA] 점수 {qa['overall_score']}/5.0")
        if "narrative_quality" in qa:
            nq = qa["narrative_quality"]
            print(
                f"  [서술 품질] {nq.get('passed_items', 0)}/{nq.get('total_items', 0)} 통과, "
                f"점수 {nq.get('overall_score', 0)}/5.0"
            )

    # Guardrails
    if result.guardrail_result:
        gr = result.guardrail_result
        print(
            f"  [Guardrails] 에러 {gr.get('error_count', 0)}, "
            f"경고 {gr.get('warning_count', 0)}, "
            f"통과 {gr.get('passed_rules', 0)}"
        )

    print()


def save_result_json(result, output_dir: Path):
    """파이프라인 결과를 JSON으로 저장한다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "pipeline_result.json"

    data = {
        "sections": result.sections,
        "executive_summary": result.executive_summary,
        "dual_risk_summary": result.dual_risk_summary,
        "gap_detection": result.gap_detection,
        "narrative_sections": result.narrative_sections,
        "appendices": result.appendices,
        "qa_result": result.qa_result,
        "guardrail_result": result.guardrail_result,
        "cost_usd": result.cost_usd,
        "stages": result.stages,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    size_kb = out_path.stat().st_size // 1024
    print(f"  JSON: {out_path} ({size_kb} KB)")


def render_docx(result, output_dir: Path, template_name: str = "ldd_full_template.docx"):
    """docxtpl로 DOCX 보고서를 렌더링한다."""
    try:
        from docxtpl import DocxTemplate
    except ImportError:
        print("  [WARN] docxtpl 미설치 — DOCX 렌더링 건너뜀")
        print("  설치: pip install docxtpl")
        return

    template_path = TEMPLATE_DIR / template_name

    # 서술형 템플릿이 존재하고 narrative 데이터가 있으면 사용
    if result.narrative_sections:
        narrative_template = TEMPLATE_DIR / "ldd_narrative_full_template.docx"
        if narrative_template.exists():
            template_path = narrative_template

    if not template_path.exists():
        print(f"  [WARN] 템플릿 미발견: {template_path}")
        return

    # 컨텍스트 빌드 (서비스 의존 없이 직접 구성)
    sections = list(result.sections.values()) if isinstance(result.sections, dict) else result.sections

    # sections를 dict 리스트로 변환
    sections_list = []
    for section_type, items in result.sections.items():
        sections_list.append(
            {
                "section_type": section_type,
                "title": section_type,
                "items": items,
            }
        )

    # 이슈 집계
    all_issues = []
    red_issues = []
    ok_count = issue_count = na_count = pending_count = 0

    for section in sections_list:
        for item in section.get("items", []):
            status = item.get("status", "PENDING")
            if status == "OK":
                ok_count += 1
            elif status == "ISSUE":
                issue_count += 1
                enriched = {**item, "section_title": section.get("title", "")}
                all_issues.append(enriched)
                level = item.get("issue_level", "")
                if level in ("CRITICAL", "HIGH"):
                    red_issues.append(enriched)
            elif status == "NA":
                na_count += 1
            else:
                pending_count += 1

    total_items = ok_count + issue_count + na_count + pending_count

    ctx = {
        "title": "법률실사 보고서 (Pjt. Green)",
        "target_company": "대상 회사",
        "dd_period": "2024.01 ~ 2024.12",
        "law_firm": "AMIC",
        "prepared_by": "AMIC AI LDD System",
        "report_date": date.today().strftime("%Y년 %m월 %d일"),
        "total_items": total_items,
        "issue_count": issue_count,
        "red_count": len(red_issues),
        "amber_count": sum(1 for i in all_issues if i.get("issue_level") == "MEDIUM"),
        "green_count": sum(1 for i in all_issues if i.get("issue_level") == "LOW"),
        "ok_count": ok_count,
        "na_count": na_count,
        "pending_count": pending_count,
        "rfi_count": sum(1 for s in sections_list for i in s.get("items", []) if i.get("rfi_required")),
        "sections": sections_list,
        "all_issues": all_issues,
        "red_issues": red_issues,
        "executive_summary": result.executive_summary or "",
        "vdr_source": "로컬 폴더",
        "draft_score": None,
        "final_score": None,
    }

    # 별첨
    if result.appendices and result.appendices.get("tables"):
        ctx["appendix_tables"] = [t for t in result.appendices["tables"] if t.get("row_count", 0) > 0]

    output_dir.mkdir(parents=True, exist_ok=True)
    tpl = DocxTemplate(str(template_path))
    tpl.render(ctx)
    out_path = output_dir / "LDD_FULL_standalone.docx"
    tpl.save(str(out_path))

    size_kb = out_path.stat().st_size // 1024
    print(f"  DOCX: {out_path} ({size_kb} KB)")


# ── 메인 ──


async def main():
    args = parse_args()
    print_header()

    # ── Stage 0: 스캔 + 파싱 ──
    file_list = stage0_scan(args.source_dir)

    if not file_list:
        print("[ERROR] 지원 파일이 없습니다.")
        sys.exit(1)

    parsed_files = stage0_parse(file_list)
    source_map = build_source_map(parsed_files)

    # 섹션 구성 (체크리스트)
    from app.ralph.generators.ldd.templates import TemplateRegistry

    sections_config = TemplateRegistry.get_sections_dict(args.deal_type)
    if sections_config is None:
        from app.ralph.generators.ldd.section_analyzer import DEFAULT_LDD_SECTIONS

        # DEFAULT_LDD_SECTIONS가 없을 수 있으므로 직접 구성
        print(f"  [WARN] 템플릿 미등록: {args.deal_type} — 기본 STOCK_ACQUISITION 사용")
        sections_config = TemplateRegistry.get_sections_dict("STOCK_ACQUISITION")

    print_parse_summary(source_map, sections_config)

    if args.parse_only:
        print("[--parse-only 모드] 파싱+분류 결과만 출력하고 종료합니다.")
        print("  전체 파이프라인: python scripts/run_ldd_pipeline.py --max-files 5")
        return

    # ── 파일 필터링 ──
    if args.max_files > 0:
        source_map = filter_source_map(source_map, args.max_files)

    # ── LLM 초기화 ──
    llm_client, router = init_llm(provider=args.provider)

    # ── 파이프라인 실행 ──
    result = await run_pipeline(llm_client, router, source_map, sections_config, args)

    # ── 결과 요약 ──
    print_result_summary(result)

    # ── 출력 ──
    print("[출력]")
    save_result_json(result, OUTPUT_DIR)

    if not args.no_docx:
        render_docx(result, OUTPUT_DIR)

    print()
    print("=" * 60)
    print("  완료!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
