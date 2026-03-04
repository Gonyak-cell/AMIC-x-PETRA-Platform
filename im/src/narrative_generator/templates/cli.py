"""템플릿 추출 CLI — 참조 보고서에서 YAML 템플릿 자동 생성.

> 마지막 수정: 2026-02-17

사용 예시::

    # 단일 섹션 추출
    python -m src.narrative_generator.templates.cli extract \\
        --file reference_im.pdf \\
        --section executive_summary \\
        --output templates/executive_summary.yaml

    # 전체 보고서 자동 분할 + 추출
    python -m src.narrative_generator.templates.cli extract-all \\
        --file reference_im.pdf \\
        --output-dir templates/

    # 텍스트 추출만 (디버깅용)
    python -m src.narrative_generator.templates.cli text \\
        --file reference_im.pdf

    # 지원 섹션 ID 목록
    python -m src.narrative_generator.templates.cli list-sections
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# 지원 섹션 ID 목록
SECTION_IDS = [
    "executive_summary",
    "company_overview",
    "business_overview",
    "deal_overview",
    "financial_analysis",
    "investment_highlights",
    "market_overview",
    "value_creation",
    "growth_strategy",
    "management_team",
    "business_model",
    "appendix",
    "contact",
]


def _create_parser() -> argparse.ArgumentParser:
    """CLI 인자 파서를 생성한다."""
    parser = argparse.ArgumentParser(
        prog="template-extractor",
        description="참조 IM 보고서에서 YAML 부동문자 템플릿을 자동 생성합니다.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="상세 로깅 출력",
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 명령")

    # ── extract: 단일 섹션 추출 ──
    extract_parser = subparsers.add_parser(
        "extract",
        help="단일 섹션의 YAML 템플릿을 추출합니다.",
    )
    extract_parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="참조 보고서 파일 경로 (PDF, PPTX, TXT)",
    )
    extract_parser.add_argument(
        "--section",
        "-s",
        default="",
        help="섹션 ID (비어 있으면 자동 감지)",
    )
    extract_parser.add_argument(
        "--output",
        "-o",
        default="",
        help="출력 YAML 파일 경로 (비어 있으면 stdout)",
    )
    extract_parser.add_argument(
        "--model",
        "-m",
        default="gpt-4o",
        help="LLM 모델명 (기본: gpt-4o)",
    )
    extract_parser.add_argument(
        "--no-llm",
        action="store_true",
        help="LLM 없이 휴리스틱 모드로 추출",
    )

    # ── extract-all: 전체 보고서 추출 ──
    extract_all_parser = subparsers.add_parser(
        "extract-all",
        help="전체 보고서를 섹션별로 분할하여 YAML 템플릿을 추출합니다.",
    )
    extract_all_parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="참조 보고서 파일 경로 (PDF, PPTX, TXT)",
    )
    extract_all_parser.add_argument(
        "--output-dir",
        "-o",
        default=".",
        help="출력 디렉터리 경로 (기본: 현재 디렉터리)",
    )
    extract_all_parser.add_argument(
        "--model",
        "-m",
        default="gpt-4o",
        help="LLM 모델명 (기본: gpt-4o)",
    )
    extract_all_parser.add_argument(
        "--no-llm",
        action="store_true",
        help="LLM 없이 휴리스틱 모드로 추출",
    )

    # ── text: 텍스트 추출만 ──
    text_parser = subparsers.add_parser(
        "text",
        help="파일에서 텍스트만 추출합니다 (디버깅용).",
    )
    text_parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="파일 경로 (PDF, PPTX, TXT)",
    )
    text_parser.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="최대 출력 문자 수 (0이면 제한 없음)",
    )

    # ── list-sections: 섹션 ID 목록 ──
    subparsers.add_parser(
        "list-sections",
        help="지원하는 섹션 ID 목록을 출력합니다.",
    )

    return parser


def _create_llm_client(model: str, no_llm: bool) -> tuple:
    """LLM 클라이언트를 생성한다.

    Returns:
        (client, model) 튜플. no_llm이면 (None, model).
    """
    if no_llm:
        return None, model

    try:
        from openai import OpenAI

        client = OpenAI()
        return client, model
    except ImportError:
        logger.warning("openai 패키지 미설치, 휴리스틱 모드로 전환")
        return None, model
    except Exception as exc:
        logger.warning("OpenAI 클라이언트 생성 실패: %s, 휴리스틱 모드로 전환", exc)
        return None, model


async def _cmd_extract(args: argparse.Namespace) -> int:
    """단일 섹션 추출 명령을 실행한다."""
    from src.narrative_generator.templates.extractor import TemplateExtractor

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {file_path}", file=sys.stderr)
        return 1

    client, model = _create_llm_client(args.model, args.no_llm)
    extractor = TemplateExtractor(llm_client=client, model=model)

    print(f"추출 중: {file_path} → 섹션: {args.section or '(자동 감지)'}")

    result = await extractor.extract_from_file(
        file_path,
        section_id=args.section,
    )

    if result.warnings:
        for warning in result.warnings:
            print(f"경고: {warning}", file=sys.stderr)

    if not result.yaml_content:
        print("오류: YAML 생성 실패", file=sys.stderr)
        return 1

    if args.output:
        output_path = result.save_yaml(args.output)
        print(f"저장 완료: {output_path}")
    else:
        print(result.yaml_content)

    return 0


async def _cmd_extract_all(args: argparse.Namespace) -> int:
    """전체 보고서 추출 명령을 실행한다."""
    from src.narrative_generator.templates.extractor import TemplateExtractor

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {file_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client, model = _create_llm_client(args.model, args.no_llm)
    extractor = TemplateExtractor(llm_client=client, model=model)

    print(f"전체 추출 중: {file_path}")
    print(f"출력 디렉터리: {output_dir}")

    results = await extractor.extract_all_sections(file_path)

    saved = 0
    for result in results:
        if not result.yaml_content:
            print(f"  건너뜀: {result.section_id} (YAML 생성 실패)", file=sys.stderr)
            continue

        output_path = output_dir / f"{result.section_id}.yaml"
        result.save_yaml(output_path)
        print(f"  저장: {output_path}")
        saved += 1

        if result.warnings:
            for warning in result.warnings:
                print(f"    경고: {warning}", file=sys.stderr)

    print(f"\n완료: {saved}/{len(results)}개 섹션 추출")
    return 0


async def _cmd_text(args: argparse.Namespace) -> int:
    """텍스트 추출 명령을 실행한다."""
    from src.narrative_generator.templates.extractor import TemplateExtractor

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"오류: 파일을 찾을 수 없습니다: {file_path}", file=sys.stderr)
        return 1

    extractor = TemplateExtractor()
    text = extractor._extract_text(file_path)

    if not text:
        print("오류: 텍스트 추출 실패", file=sys.stderr)
        return 1

    if args.max_chars and len(text) > args.max_chars:
        text = (
            text[: args.max_chars]
            + f"\n\n[... {len(text) - args.max_chars}자 생략 ...]"
        )

    print(text)
    return 0


def _cmd_list_sections() -> int:
    """섹션 ID 목록 명령을 실행한다."""
    print("지원하는 섹션 ID:")
    for section_id in SECTION_IDS:
        print(f"  - {section_id}")
    return 0


async def _async_main(args: argparse.Namespace) -> int:
    """비동기 메인 로직."""
    if args.command == "extract":
        return await _cmd_extract(args)
    if args.command == "extract-all":
        return await _cmd_extract_all(args)
    if args.command == "text":
        return await _cmd_text(args)
    if args.command == "list-sections":
        return _cmd_list_sections()

    print("명령을 지정하십시오. --help로 사용법을 확인하세요.", file=sys.stderr)
    return 1


def main() -> None:
    """CLI 엔트리포인트."""
    parser = _create_parser()
    args = parser.parse_args()

    # 로깅 설정
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)-7s %(name)s — %(message)s",
    )

    exit_code = asyncio.run(_async_main(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
