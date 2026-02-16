from pydantic import BaseModel, ConfigDict, Field


class EntityResolveRequest(BaseModel):
    """Entity Resolution 요청"""

    name: str = Field(..., min_length=1, description="식별할 기업명 (약칭, 정식명칭 등)")
    threshold: float = Field(0.75, ge=0.0, le=1.0, description="유사도 임계값 (0.0~1.0)")
    max_candidates: int = Field(5, ge=1, le=20, description="후보 최대 수")


class EntityMatchItem(BaseModel):
    """Entity Resolution 매칭 결과"""

    corp_code: str = Field(..., description="DART 고유번호")
    corp_name: str = Field(..., description="정식 기업명")
    similarity: float = Field(..., description="유사도 점수 (0.0~1.0)")
    matched_by: str | None = Field(None, description="매칭 방식 (alias, exact, similarity)")


class EntityResolveResponse(BaseModel):
    """Entity Resolution 응답"""

    query: str = Field(..., description="입력된 원본 이름")
    normalized: str = Field(..., description="정규화된 이름")
    match: EntityMatchItem | None = Field(None, description="최종 매칭 결과")
    candidates: list[EntityMatchItem] = Field(default_factory=list, description="유사 기업 후보 목록")


class AliasCreateRequest(BaseModel):
    """별칭 등록 요청"""

    alias_name: str = Field(..., min_length=1, description="등록할 별칭")
    corp_code: str = Field(..., description="매핑할 기업의 DART 고유번호")


class AliasItem(BaseModel):
    """별칭 정보"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    alias_name: str = Field(..., description="별칭")
    company_id: int = Field(..., description="매핑된 기업 ID")
    is_manual: bool = Field(..., description="수동 등록 여부")
    corp_code: str | None = Field(None, description="기업 DART 고유번호")
    corp_name: str | None = Field(None, description="기업 정식명칭")


class AliasListResponse(BaseModel):
    """별칭 목록 응답"""

    total: int
    items: list[AliasItem]
