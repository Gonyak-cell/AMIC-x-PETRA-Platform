"""파서 공통 데이터 모델."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedTable:
    """파싱된 표 데이터."""

    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class ParsedFile:
    """파싱된 파일 결과.

    모든 파서(Excel, PDF, DOCX, HWP)의 공통 출력 형식.
    """

    source_path: str  # 원본 파일 경로
    file_type: str  # excel, pdf, docx, hwp
    text: str = ""  # 추출된 전체 텍스트
    tables: list[ParsedTable] = field(default_factory=list)  # 추출된 표
    metadata: dict = field(default_factory=dict)  # 파일 메타데이터 (크기, 수정일 등)
    ddrl_sections: list[str] = field(default_factory=list)  # 매핑된 DDRL 섹션 타입
    parse_error: str | None = None  # 파싱 에러 메시지

    @property
    def is_valid(self) -> bool:
        return self.parse_error is None and (bool(self.text) or bool(self.tables))

    def summary(self, max_chars: int = 500) -> str:
        """LLM 입력용 요약 텍스트."""
        s = self.text[:max_chars]
        if self.tables:
            for t in self.tables[:3]:
                s += f"\n[표: {len(t.rows)}행 × {len(t.headers)}열]"
                if t.headers:
                    s += f" 헤더: {', '.join(h for h in t.headers[:5] if h is not None)}"
        return s
