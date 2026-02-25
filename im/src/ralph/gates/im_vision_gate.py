"""IM Vision Gate — PPTX 시각 품질 평가 (GPT-4o Vision API).

파이프라인: PPTX → PDF (LibreOffice headless) → PNG (PyMuPDF) → Vision API 평가

5차원 평가 (IM PPTX 디자인 특화):
- layout_balance: 레이아웃 균형/여백
- color_harmony: AMIC 5단계 그린 팔레트 준수 + 색상 조화
- typography: SUITE/Pretendard 가독성
- data_viz: 데이터 시각화 품질 (IM 핵심)
- professionalism: IB 수준 전문성
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

from src.ralph.gates.base import DimensionScore, GateResult, QualityGate

logger = logging.getLogger(__name__)

IM_VISION_SYSTEM_PROMPT = """당신은 M&A Investment Banking(IB)의 시니어 디자이너입니다.
IM(Investment Memorandum) PPTX 슬라이드의 시각적 품질을 평가합니다.

AMIC의 공식 디자인 시스템:
- 5단계 그린: #0F3A32(Signature) → #1C8F57(Solid) → #26C260(Highlight) → #A3E96B(Fresh) → #E6FDD6(Light)
- 헤딩 폰트: SUITE (Bold)
- 본문 폰트: Pretendard (Regular/Medium)

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

IM_VISION_WEIGHTS: dict[str, tuple[float, str]] = {
    "layout_balance":  (0.20, "레이아웃 균형"),
    "color_harmony":   (0.20, "색상 조화"),
    "typography":      (0.15, "타이포그래피"),
    "data_viz":        (0.25, "데이터 시각화"),
    "professionalism": (0.20, "전문성"),
}


class IMVisionGate(QualityGate):
    """IM PPTX 시각 품질 평가 게이트 — GPT-4o Vision API.

    Args:
        openai_api_key: OpenAI API 키 (Vision API용).
        max_slides: 평가할 최대 슬라이드 수 (전략적 샘플링).
    """

    def __init__(
        self,
        openai_api_key: str = "",
        max_slides: int = 6,
    ) -> None:
        self._api_key = openai_api_key
        self._max_slides = max_slides

    @property
    def name(self) -> str:
        return "im_vision"

    async def evaluate(
        self,
        artifact_path: str,
        prd_section: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> GateResult:
        start = time.perf_counter_ns()

        if not self._api_key:
            return self._timed_result(
                start, [], ["Vision Gate 비활성: OpenAI API 키 미설정"], [],
                [], cost_usd=0.0,
            )

        try:
            images = await self._pptx_to_images(artifact_path)
        except Exception as exc:
            return self._timed_result(
                start, [], [f"PPTX → 이미지 변환 실패: {exc}"], [], [],
            )

        if not images:
            return self._timed_result(
                start, [], ["평가할 슬라이드 이미지 없음"], [], [],
            )

        try:
            result_json = await self._call_vision_api(images)
        except Exception as exc:
            return self._timed_result(
                start, [], [f"Vision API 호출 실패: {exc}"], [], [],
                cost_usd=0.02,
            )

        # JSON 파싱
        dimensions, issues, suggestions = self._parse_vision_response(result_json)

        return self._timed_result(
            start, dimensions, issues, suggestions, [],
            cost_usd=0.03,
            raw_data={"slide_count": len(images)},
        )

    async def _pptx_to_images(self, pptx_path: str) -> list[str]:
        """PPTX → PDF → PNG 변환, base64 인코딩된 이미지 목록 반환."""
        tmp_dir = tempfile.mkdtemp(prefix="im_vision_")

        try:
            # 1. PPTX → PDF (LibreOffice headless)
            pdf_path = await self._convert_to_pdf(pptx_path, tmp_dir)
            if not pdf_path:
                return []

            # 2. PDF → PNG (PyMuPDF)
            images = await asyncio.to_thread(self._pdf_to_pngs, pdf_path, tmp_dir)

            # 3. 전략적 샘플링
            sampled = self._sample_slides(images)

            # 4. base64 인코딩
            b64_images = []
            for img_path in sampled:
                with open(img_path, "rb") as f:
                    b64_images.append(base64.b64encode(f.read()).decode("utf-8"))

            return b64_images

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _convert_to_pdf(self, pptx_path: str, output_dir: str) -> str | None:
        """LibreOffice headless로 PPTX → PDF 변환."""
        process = await asyncio.create_subprocess_exec(
            "libreoffice", "--headless", "--convert-to", "pdf",
            "--outdir", output_dir, pptx_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()

        pdf_name = Path(pptx_path).stem + ".pdf"
        pdf_path = Path(output_dir) / pdf_name
        return str(pdf_path) if pdf_path.exists() else None

    def _pdf_to_pngs(self, pdf_path: str, output_dir: str) -> list[str]:
        """PyMuPDF로 PDF → PNG 변환."""
        try:
            import fitz
        except ImportError:
            logger.warning("PyMuPDF(fitz) 미설치 — Vision Gate 비활성")
            return []

        doc = fitz.open(pdf_path)
        paths: list[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x 해상도
            img_path = str(Path(output_dir) / f"slide_{page_num + 1:03d}.png")
            pix.save(img_path)
            paths.append(img_path)

        doc.close()
        return paths

    def _sample_slides(self, image_paths: list[str]) -> list[str]:
        """전략적 슬라이드 샘플링 — Cover + 중간 핵심 + 마지막."""
        if len(image_paths) <= self._max_slides:
            return image_paths

        indices = set()
        indices.add(0)  # Cover
        indices.add(len(image_paths) - 1)  # 마지막

        # 균등 간격으로 나머지 선택
        step = max(1, len(image_paths) // (self._max_slides - 2))
        for i in range(step, len(image_paths) - 1, step):
            indices.add(i)
            if len(indices) >= self._max_slides:
                break

        return [image_paths[i] for i in sorted(indices)]

    async def _call_vision_api(self, b64_images: list[str]) -> str:
        """GPT-4o Vision API 호출."""
        import openai

        client = openai.AsyncOpenAI(api_key=self._api_key)

        content: list[dict[str, Any]] = [
            {"type": "text", "text": f"다음 {len(b64_images)}장의 IM PPTX 슬라이드를 평가해주세요."},
        ]

        for i, b64 in enumerate(b64_images):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{b64}",
                    "detail": "high",
                },
            })

        response = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2000,
            temperature=0.2,
            messages=[
                {"role": "system", "content": IM_VISION_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
        )

        return response.choices[0].message.content or ""

    def _parse_vision_response(
        self, response_text: str,
    ) -> tuple[list[DimensionScore], list[str], list[str]]:
        """Vision API 응답을 파싱하여 DimensionScore 목록을 생성한다."""
        import json

        dimensions: list[DimensionScore] = []
        issues: list[str] = []
        suggestions: list[str] = []

        try:
            # JSON 블록 추출
            json_match = response_text
            if "```json" in response_text:
                json_match = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_match = response_text.split("```")[1].split("```")[0]

            data = json.loads(json_match)

            for dim_data in data.get("dimensions", []):
                dim_name = dim_data.get("name", "")
                if dim_name in IM_VISION_WEIGHTS:
                    weight, label = IM_VISION_WEIGHTS[dim_name]
                    score = float(dim_data.get("score", 3.0))
                    feedback = dim_data.get("feedback", "")

                    dimensions.append(DimensionScore(
                        name=dim_name,
                        label=label,
                        score=min(5.0, max(1.0, score)),
                        weight=weight,
                        feedback=feedback,
                    ))

                    if score < 3.0:
                        issues.append(f"{label}: {feedback}")
                    elif score < 4.0:
                        suggestions.append(f"{label} 개선: {feedback}")

            overall = data.get("overall_feedback", "")
            if overall:
                suggestions.append(f"[전체] {overall}")

        except (json.JSONDecodeError, KeyError, IndexError) as exc:
            logger.warning("Vision 응답 파싱 실패: %s", exc)
            # 파싱 실패 시 기본 점수
            for dim_name, (weight, label) in IM_VISION_WEIGHTS.items():
                dimensions.append(DimensionScore(
                    name=dim_name, label=label, score=3.0, weight=weight,
                    feedback="응답 파싱 실패 — 기본 점수 적용",
                ))

        return dimensions, issues, suggestions
