"""DB 모델 테스트 (T-I03, T-I04).

> 마지막 수정: 2026-02-10 16:29:08

ORM 모델 정의, 컬럼 타입, 제약조건, 관계를 검증한다.
"""

from __future__ import annotations


from src.api.db.base import Base
from src.api.db.models import APIKey, Company, Document, DocumentStatus, User


class TestBase:
    """SQLAlchemy Base 테스트."""

    def test_base_has_metadata(self) -> None:
        """Base가 MetaData를 갖는다."""
        assert Base.metadata is not None

    def test_naming_convention(self) -> None:
        """Naming convention이 설정되어 있다."""
        nc = Base.metadata.naming_convention
        assert "ix" in nc
        assert "uq" in nc
        assert "fk" in nc
        assert "pk" in nc


class TestDocumentStatus:
    """DocumentStatus enum 테스트."""

    def test_all_statuses_defined(self) -> None:
        """7개 상태가 정의되어 있다."""
        statuses = list(DocumentStatus)
        assert len(statuses) == 7

    def test_status_values(self) -> None:
        """각 상태 값이 올바르다."""
        assert DocumentStatus.PENDING.value == "PENDING"
        assert DocumentStatus.COLLECTING.value == "COLLECTING"
        assert DocumentStatus.ANALYZING.value == "ANALYZING"
        assert DocumentStatus.GENERATING.value == "GENERATING"
        assert DocumentStatus.RENDERING.value == "RENDERING"
        assert DocumentStatus.COMPLETED.value == "COMPLETED"
        assert DocumentStatus.FAILED.value == "FAILED"


class TestUserModel:
    """User 모델 테스트."""

    def test_tablename(self) -> None:
        """테이블 이름이 'users'이다."""
        assert User.__tablename__ == "users"

    def test_columns_exist(self) -> None:
        """필수 컬럼이 존재한다."""
        columns = {c.name for c in User.__table__.columns}
        expected = {
            "id",
            "email",
            "hashed_password",
            "full_name",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        }
        assert expected.issubset(columns)

    def test_email_is_unique(self) -> None:
        """email 컬럼에 unique 제약이 있다."""
        col = User.__table__.columns["email"]
        assert col.unique is True

    def test_role_default(self) -> None:
        """role 기본값이 'USER'이다."""
        col = User.__table__.columns["role"]
        assert col.default.arg == "USER"


class TestDocumentModel:
    """Document 모델 테스트."""

    def test_tablename(self) -> None:
        """테이블 이름이 'documents'이다."""
        assert Document.__tablename__ == "documents"

    def test_columns_exist(self) -> None:
        """필수 컬럼이 존재한다."""
        columns = {c.name for c in Document.__table__.columns}
        expected = {
            "id",
            "owner_id",
            "corp_code",
            "company_name",
            "im_style",
            "status",
            "progress_pct",
            "celery_task_id",
            "pptx_path",
            "pdf_path",
            "created_at",
        }
        assert expected.issubset(columns)

    def test_status_default(self) -> None:
        """status 기본값이 'PENDING'이다."""
        col = Document.__table__.columns["status"]
        assert col.default.arg == "PENDING"

    def test_jsonb_columns(self) -> None:
        """JSONB 컬럼이 존재한다."""
        columns = {c.name for c in Document.__table__.columns}
        assert "sections" in columns
        assert "generation_config" in columns
        assert "stage_details" in columns

    def test_composite_index_exists(self) -> None:
        """owner_id + status 복합 인덱스가 존재한다."""
        index_names = {idx.name for idx in Document.__table__.indexes}
        assert "ix_documents_owner_status" in index_names

    def test_created_at_index_exists(self) -> None:
        """created_at 인덱스가 존재한다."""
        index_names = {idx.name for idx in Document.__table__.indexes}
        assert "ix_documents_created_at" in index_names


class TestCompanyModel:
    """Company 모델 테스트."""

    def test_tablename(self) -> None:
        """테이블 이름이 'companies'이다."""
        assert Company.__tablename__ == "companies"

    def test_corp_code_unique(self) -> None:
        """corp_code에 unique 제약이 있다."""
        col = Company.__table__.columns["corp_code"]
        assert col.unique is True

    def test_jsonb_columns(self) -> None:
        """JSONB 컬럼이 존재한다."""
        columns = {c.name for c in Company.__table__.columns}
        assert "dart_data" in columns
        assert "financial_summary" in columns
        assert "brand_assets" in columns

    def test_cache_columns(self) -> None:
        """캐시 관련 컬럼이 존재한다."""
        columns = {c.name for c in Company.__table__.columns}
        assert "last_fetched_at" in columns
        assert "cache_expires_at" in columns
        assert "fetch_status" in columns


class TestAPIKeyModel:
    """APIKey 모델 테스트."""

    def test_tablename(self) -> None:
        """테이블 이름이 'api_keys'이다."""
        assert APIKey.__tablename__ == "api_keys"

    def test_key_hash_unique(self) -> None:
        """key_hash에 unique 제약이 있다."""
        col = APIKey.__table__.columns["key_hash"]
        assert col.unique is True

    def test_user_id_foreign_key(self) -> None:
        """user_id가 users.id를 참조한다."""
        col = APIKey.__table__.columns["user_id"]
        fk = list(col.foreign_keys)
        assert len(fk) == 1
        assert "users.id" in str(fk[0])

    def test_columns_exist(self) -> None:
        """필수 컬럼이 존재한다."""
        columns = {c.name for c in APIKey.__table__.columns}
        expected = {
            "id",
            "user_id",
            "key_hash",
            "name",
            "is_active",
            "last_used_at",
            "expires_at",
            "created_at",
        }
        assert expected.issubset(columns)


class TestModelRelationships:
    """모델 간 관계 테스트."""

    def test_user_has_documents_relationship(self) -> None:
        """User가 documents 관계를 갖는다."""
        assert hasattr(User, "documents")

    def test_user_has_api_keys_relationship(self) -> None:
        """User가 api_keys 관계를 갖는다."""
        assert hasattr(User, "api_keys")

    def test_document_has_owner_relationship(self) -> None:
        """Document가 owner 관계를 갖는다."""
        assert hasattr(Document, "owner")

    def test_api_key_has_user_relationship(self) -> None:
        """APIKey가 user 관계를 갖는다."""
        assert hasattr(APIKey, "user")


class TestSessionModule:
    """DB 세션 모듈 테스트."""

    def test_init_engine_creates_engine(self, test_config) -> None:
        """init_engine이 엔진을 생성한다."""
        from src.api.db import session

        # 기존 상태 저장 후 복원
        orig_engine = session.async_engine
        orig_factory = session.AsyncSessionFactory

        try:
            engine = session.init_engine(test_config)
            assert engine is not None
            assert session.async_engine is not None
            assert session.AsyncSessionFactory is not None
        finally:
            session.async_engine = orig_engine
            session.AsyncSessionFactory = orig_factory

    def test_init_engine_uses_config_values(self, test_config) -> None:
        """init_engine이 config 값을 사용한다."""
        from src.api.db import session

        orig_engine = session.async_engine
        orig_factory = session.AsyncSessionFactory

        try:
            engine = session.init_engine(test_config)
            # SQLAlchemy가 비밀번호를 마스킹하므로 호스트와 DB명으로 확인
            url_str = str(engine.url)
            assert "localhost:5434" in url_str
            assert "imgen_test" in url_str
            assert "asyncpg" in url_str
        finally:
            session.async_engine = orig_engine
            session.AsyncSessionFactory = orig_factory
