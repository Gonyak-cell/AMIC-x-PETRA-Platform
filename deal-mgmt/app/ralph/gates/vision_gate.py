"""Vision Gate — PPTX 시각 품질 평가 (GPT-4o Vision API).

파이프라인: PPTX → PDF (LibreOffice headless) → PNG (PyMuPDF) → Vision API 평가

5차원 평가:
- layout_balance: 레이아웃 균형/여백
- color_harmony: 색상 조화/브랜드 일관성
- typography: 타이포그래피 가독성
- data_viz: 데이터 시각화 품질
- professionalism: 전문성/IB 수준
"""

from __future__ import annotations

import asyncio
import base64
import logging
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from app.ralph.gates.base import DimensionScore, GateResult, QualityGate

logger = logging.getLogger(__name__)

VISION_SYSTEM_PROMPT = """당신은 M&A 투자은행(IB)의 시니어 디자이너입니다.
프레젠테이션 슬라이드의 시각적 품질을 평가합니다.

각 차원에 대해 1-5점으로 평가하세요.

점수 앵커:
- 5점: Goldman Sachs / Morgan Stanley 급 프레젠테이션
- 4점: 전문적이고 깔끔한 딜 문서
- 3점: 기업 내부 보고서 수준
- 2점: 아마추어/학생 프레젠테이션
- 1점: 사용 불가

## 출력 형식 (JSON)
```json
{
  "dimensions": [
    {"name": "layout_balance", "score": 4, "feedback": "..."},
    {"name": "color_harmony", "score": 3, "feedback": "..."},
    {"name": "typography", "score": 4, "feedback": "..."},
    {"name": "data_viz", "score": 3, "feedback": "..."},
    {"name": "professionalism", "score": 4, "feedback": "..."}
  ],
  "overall_feedback": "전체적 시각 품질 평가"
}
```
"""

VISION_WEIGHTS: dict[str, tuple[float, str]] = {
    "layout_balance": (0.25, "레이아웃 균형"),
    "color_harmony": (0.15, "색상 조화"),
    "typography": (0.20, "타이포그래피"),
    "data_viz": (0.20, "데이터 시각화"),
    "professionalism": (0.20, "전문성"),
}


class VisionGate(QualityGate):
    """PPTX 시각 품질 평가 게이트 — GPT-4o Vision API.

    Args:
        openai_api_key: OpenAI API 키 (Vision API용)
        max_slides: 평가할 최대 슬라이드 수 (전략적 샘플링)
    """

    def __init__(
        self,
        openai_api_key: str = "",
        max_slides: int = 5,
    ) -> None:
        self._api_key = openai_api_key
        self._max_slides = max_slides

    @property
    def name(self) -> str:
        return "vision"

    async def evaluate(
        self,
        artifact_path: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        start = time.perf_counter_ns()

        if not artifact_path.endswith(".pptx"):
            return self._timed_result(
                start,
                [],
                ["Vision Gate는 PPTX 파일만 지원합니다"],
                [],
                [],
            )

        if not self._api_key:
            return self._fallback_evaluate(start)

        try:
            # 1. PPTX → PDF (LibreOffice headless)
            pdf_path = await self._convert_to_pdf(artifact_path)
            if not pdf_path:
                return self._timed_result(
                    start,
                    [],
                    ["PDF 변환 실패 — LibreOffice가 설치되어 있는지 확인하세요"],
                    [],
                    [],
                )

            # 2. PDF → PNG (전략적 샘플링)
            images = self._extract_slide_images(pdf_path)

            if not images:
                return self._timed_result(
                    start,
                    [],
                    ["슬라이드 이미지 추출 실패"],
                    [],
                    [],
                )

            # 3. GPT-4o Vision 평가
            result = await self._evaluate_with_vision(images)
            return self._build_result(start, result)

        except Exception as exc:
            logger.warning("Vision Gate 실행 실패, fallback 사용: %s", exc)
            return self._fallback_evaluate(start)

    async def _convert_to_pdf(self, pptx_path: str) -> str | None:
        """LibreOffice headless로 PPTX → PDF 변환."""
        libreoffice = shutil.which("libreoffice") or shutil.which("soffice")
        if not libreoffice:
            logger.warning("LibreOffice가 설치되어 있지 않습니다")
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            proc = await asyncio.create_subprocess_exec(
                libreoffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                tmpdir,
                pptx_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.wait()

            # 변환된 PDF 찾기
            pdf_files = list(Path(tmpdir).glob("*.pdf"))
            if pdf_files:
                # 영구 경로로 복사
                dest = Path(pptx_path).with_suffix(".pdf")
                shutil.copy2(str(pdf_files[0]), str(dest))
                return str(dest)

        return None

    def _extract_slide_images(self, pdf_path: str) -> list[bytes]:
        """PDF에서 전략적으로 슬라이드 이미지를 추출한다.

        전략: 표지(0) + 중간 2장 + 끝 1장 = max 5장
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF가 설치되어 있지 않습니다")
            return []

        doc = fitz.open(pdf_path)
        total = doc.page_count

        if total == 0:
            return []

        # 전략적 샘플링: 표지 + 균등 분포
        if total <= self._max_slides:
            indices = list(range(total))
        else:
            indices = [0]  # 표지
            step = total // (self._max_slides - 1)
            for i in range(1, self._max_slides - 1):
                indices.append(min(i * step, total - 1))
            indices.append(total - 1)  # 마지막
            indices = sorted(set(indices))

        images: list[bytes] = []
        for idx in indices[: self._max_slides]:
            page = doc[idx]
            pix = page.get_pixmap(dpi=150)
            images.append(pix.tobytes("png"))

        doc.close()
        return images

    async def _evaluate_with_vision(self, images: list[bytes]) -> dict:
        """GPT-4o Vision API로 슬라이드 시각 품질을 평가한다."""
        import openai

        client = openai.AsyncOpenAI(api_key=self._api_key)

        # 이미지를 base64로 인코딩
        content: list[dict] = [
            {"type": "text", "text": "아래 M&A 프레젠테이션 슬라이드들의 시각적 품질을 평가해 주세요."},
        ]
        for _i, img_bytes in enumerate(images):
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"},
                }
            )

        response = await client.chat.completions.create(
            model="gpt-4o",
            temperature=0.3,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": VISION_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        )

        text = response.choices[0].message.content or ""
        return self._parse_vision_response(text)

    def _parse_vision_response(self, response: str) -> dict:
        """Vision API 응답에서 JSON을 파싱한다."""
        import json

        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.index("```") + 3
            end = response.index("```", start)
            response = response[start:end].strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"dimensions": [], "overall_feedback": response[:200]}

    def _build_result(self, start: int, data: dict) -> GateResult:
        """파싱된 데이터로 GateResult를 빌드한다."""
        dimensions: list[DimensionScore] = []
        for dim_data in data.get("dimensions", []):
            dim_name = dim_data.get("name", "")
            if dim_name in VISION_WEIGHTS:
                weight, label = VISION_WEIGHTS[dim_name]
                dimensions.append(
                    DimensionScore(
                        name=dim_name,
                        label=label,
                        score=float(dim_data.get("score", 3)),
                        weight=weight,
                        feedback=dim_data.get("feedback", ""),
                    )
                )

        issues = [d.feedback for d in dimensions if d.score < 3 and d.feedback]
        suggestions = [data.get("overall_feedback", "")]
        # Vision API 비용: ~$0.003/이미지
        cost = len(dimensions) * 0.003

        return self._timed_result(
            start,
            dimensions,
            issues,
            suggestions,
            [],
            cost_usd=cost,
        )

    def _fallback_evaluate(self, start: int) -> GateResult:
        """Vision API 없을 때 규칙 기반 평가."""
        dimensions = []
        for dim_name, (weight, label) in VISION_WEIGHTS.items():
            dimensions.append(DimensionScore(dim_name, label, 3.0, weight))

        return self._timed_result(
            start,
            dimensions,
            ["Vision API 미연결 — 규칙 기반 fallback 평가"],
            [],
            [],
        )
