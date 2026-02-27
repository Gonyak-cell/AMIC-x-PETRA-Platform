"""시각화 엔진 전용 예외 클래스."""


class TemplateEngineError(Exception):
    """시각화 엔진 기본 예외."""


class ShapeNotFoundError(TemplateEngineError):
    """지정된 이름의 shape를 슬라이드에서 찾을 수 없음."""


class ChartShapeError(TemplateEngineError):
    """shape에 차트가 없거나 차트 데이터 교체 실패."""


class TableShapeError(TemplateEngineError):
    """shape에 테이블이 없거나 테이블 조작 실패."""


class TextShapeError(TemplateEngineError):
    """shape에 text_frame이 없거나 텍스트 교체 실패."""


class ImagePlacementError(TemplateEngineError):
    """이미지 삽입 실패 (파일 누락, 디코딩 실패 등)."""


class DataValidationError(TemplateEngineError):
    """입력 데이터 검증 실패 (카테고리/시리즈 길이 불일치 등)."""
