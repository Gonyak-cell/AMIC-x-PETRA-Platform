"""Test configuration with dual-mode DB support.

Mode 1 (default): SQLite in-memory — fast, no Docker required.
Mode 2 (--use-pg): PostgreSQL via testcontainers — full compatibility.

Usage:
    pytest                        # SQLite mode (fast)
    pytest --use-pg               # PostgreSQL via testcontainers (Docker required)
    pytest -m "not db"            # Skip DB-dependent tests entirely
    pytest -m db --use-pg         # Only DB tests with PostgreSQL
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


# ──────────────────────────────────────────────
# CLI Option: --use-pg
# ──────────────────────────────────────────────
def pytest_addoption(parser):
    parser.addoption(
        "--use-pg",
        action="store_true",
        default=False,
        help="Use PostgreSQL via testcontainers instead of SQLite",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "db: tests requiring database")
    config.addinivalue_line("markers", "unit: pure unit tests without DB")
    config.addinivalue_line(
        "markers", "enable_auth: opt out of autouse auth disabling for security tests"
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests that use 'db' or 'client' fixtures as @pytest.mark.db."""
    for item in items:
        fixture_names = getattr(item, "fixturenames", [])
        if "db" in fixture_names or "client" in fixture_names:
            item.add_marker(pytest.mark.db)


# ──────────────────────────────────────────────
# Session-scoped PostgreSQL container (lazy)
# ──────────────────────────────────────────────
@pytest.fixture(scope="session")
def _pg_container(request):
    """Start PostgreSQL container once per session (only when --use-pg)."""
    if not request.config.getoption("--use-pg"):
        yield None
        return

    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip(
            "testcontainers not installed: pip install testcontainers[postgres]"
        )
        return

    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


# ──────────────────────────────────────────────
# DB Session Fixture (dual-mode)
# ──────────────────────────────────────────────
@pytest.fixture(name="db")
def db_session(request, _pg_container):
    """Function-scoped DB session with rollback.

    - SQLite mode: in-memory, StaticPool, SAVEPOINT emulation
    - PostgreSQL mode: testcontainers, real transactions
    """
    use_pg = request.config.getoption("--use-pg")

    if use_pg and _pg_container is not None:
        url = _pg_container.get_connection_url()
        engine = create_engine(url, echo=False)
    else:
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Enable SAVEPOINT support for SQLite nested transactions
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


# ──────────────────────────────────────────────
# FastAPI TestClient
# ──────────────────────────────────────────────
@pytest.fixture(name="client")
def test_client(db: Session):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ──────────────────────────────────────────────
# Auth: 테스트 환경 기본 인증 비활성화
# ──────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _disable_auth(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """모든 테스트에서 인증을 비활성화.

    대부분의 테스트가 auth_enabled=False를 가정하고 작성되어 있으므로
    autouse로 일괄 적용한다. @pytest.mark.enable_auth 마커가 있는
    보안 테스트는 인증을 유지한다.
    """
    if request.node.get_closest_marker("enable_auth"):
        return
    from app.config import settings

    monkeypatch.setattr(settings, "auth_enabled", False)


# ──────────────────────────────────────────────
# Auth Fixtures
# ──────────────────────────────────────────────
@pytest.fixture
def test_user(db: Session):
    """Create a test user (Analyst role)."""
    from app.auth.password import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="test@autofdd.dev",
        hashed_password=hash_password("testpassword123"),
        display_name="Test User",
        role=UserRole.ANALYST,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db: Session):
    """Create an admin user."""
    from app.auth.password import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="admin@autofdd.dev",
        hashed_password=hash_password("adminpassword123"),
        display_name="Admin User",
        role=UserRole.ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def viewer_user(db: Session):
    """Create a viewer user."""
    from app.auth.password import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="viewer@autofdd.dev",
        hashed_password=hash_password("viewerpassword123"),
        display_name="Viewer User",
        role=UserRole.VIEWER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Generate auth headers for a test user (Analyst)."""
    from app.auth.token import create_access_token

    token = create_access_token(test_user.id, test_user.email, test_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(admin_user):
    """Generate auth headers for an admin user."""
    from app.auth.token import create_access_token

    token = create_access_token(admin_user.id, admin_user.email, admin_user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers(viewer_user):
    """Generate auth headers for a viewer user."""
    from app.auth.token import create_access_token

    token = create_access_token(
        viewer_user.id, viewer_user.email, viewer_user.role.value
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def upload_dir(tmp_path):
    """Override upload directory for tests."""
    test_dir = str(tmp_path / "uploads")
    os.makedirs(test_dir, exist_ok=True)
    from app.config import settings

    original = settings.upload_dir
    settings.upload_dir = test_dir
    yield test_dir
    settings.upload_dir = original


# ──────────────────────────────────────────────
# Sample Excel File Fixtures
# ──────────────────────────────────────────────
@pytest.fixture
def sample_tb_file():
    """Create a temporary TB Excel file with Korean headers."""
    wb = Workbook()
    ws = wb.active
    ws.title = "시산표"
    ws.append(["계정코드", "계정명", "차변", "대변", "잔액"])
    ws.append(["1110", "현금", 1000000, 0, 1000000])
    ws.append(["1120", "보통예금", 5000000, 0, 5000000])
    ws.append(["2110", "매입채무", 0, 3000000, -3000000])
    ws.append(["4100", "매출", 0, 3000000, -3000000])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_gl_file():
    """Create a temporary GL Excel file with Korean headers."""
    wb = Workbook()
    ws = wb.active
    ws.title = "총계정원장"
    ws.append(
        ["전표번호", "전표일자", "계정코드", "계정명", "차변", "대변", "적요", "거래처"]
    )
    ws.append(["GL-001", "2025-01-15", "1110", "현금", 500000, 0, "매출입금", "ABC사"])
    ws.append(["GL-001", "2025-01-15", "4100", "매출", 0, 500000, "매출입금", "ABC사"])
    ws.append(
        ["GL-002", "2025-01-20", "1120", "보통예금", 200000, 0, "이자수익", "은행"]
    )
    ws.append(
        ["GL-002", "2025-01-20", "1120", "이자수익", 0, 200000, "이자수익", "은행"]
    )

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_tb_no_amounts():
    """TB file missing debit/credit/balance columns."""
    wb = Workbook()
    ws = wb.active
    ws.title = "시산표"
    ws.append(["계정코드", "계정명"])
    ws.append(["1110", "현금"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_file_string_amounts():
    """TB file where money columns contain non-numeric strings."""
    wb = Workbook()
    ws = wb.active
    ws.title = "TB"
    ws.append(["계정코드", "계정명", "차변", "대변", "잔액"])
    ws.append(["1110", "현금", "백만원", "0원", "1,000,000원"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_ar_file():
    """Create a temporary AR Excel file."""
    wb = Workbook()
    ws = wb.active
    ws.title = "매출채권"
    ws.append(["거래처", "금액", "만기일", "비고"])
    ws.append(["ABC사", 5000000, "2025-03-31", "매출분"])
    ws.append(["DEF사", 3000000, "2025-04-15", "용역분"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_bank_file():
    """Create a temporary BANK Excel file."""
    wb = Workbook()
    ws = wb.active
    ws.title = "은행"
    ws.append(["거래일", "적요", "금액", "잔액"])
    ws.append(["2025-01-10", "매출입금", 10000000, 10000000])
    ws.append(["2025-01-15", "임차료", -2000000, 8000000])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_debt_file():
    """Create a temporary DEBT Excel file."""
    wb = Workbook()
    ws = wb.active
    ws.title = "차입금"
    ws.append(["대출기관", "원금", "이자율", "만기"])
    ws.append(["국민은행", 500000000, "3.5%", "2026-06-30"])
    ws.append(["신한은행", 300000000, "4.0%", "2027-12-31"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_empty_headers_file():
    """Excel file with no headers (completely empty sheet)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Empty"

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_gl_no_amounts_file():
    """GL file missing debit/credit/amount columns."""
    wb = Workbook()
    ws = wb.active
    ws.title = "총계정원장"
    ws.append(["전표번호", "전표일자", "계정코드", "계정명", "적요"])
    ws.append(["GL-001", "2025-01-15", "1110", "현금", "입금"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_file_bad_dates():
    """GL file with unparseable date formats."""
    wb = Workbook()
    ws = wb.active
    ws.title = "총계정원장"
    ws.append(["전표번호", "전표일자", "계정코드", "차변", "대변"])
    ws.append(["GL-001", "Jan 15, 2025", "1110", 100000, 0])
    ws.append(["GL-002", "15/01/2025", "1120", 0, 100000])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_tb_with_extra_cols_file():
    """TB file with extra non-standard columns."""
    wb = Workbook()
    ws = wb.active
    ws.title = "시산표"
    ws.append(["계정코드", "계정명", "차변", "대변", "잔액", "부서", "프로젝트코드"])
    ws.append(["1110", "현금", 1000000, 0, 1000000, "재무팀", "PRJ-001"])
    ws.append(["1120", "보통예금", 5000000, 0, 5000000, "재무팀", "PRJ-002"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_empty_data_file():
    """TB file with headers but all empty data rows."""
    wb = Workbook()
    ws = wb.active
    ws.title = "시산표"
    ws.append(["계정코드", "계정명", "차변", "대변", "잔액"])
    for _ in range(10):
        ws.append([None, None, None, None, None])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_tb_large_file():
    """TB file with 6000+ rows to test batch commit."""
    wb = Workbook()
    ws = wb.active
    ws.title = "시산표"
    ws.append(["계정코드", "계정명", "차변", "대변", "잔액"])
    for i in range(6000):
        ws.append([f"{1000 + i}", f"계정{i}", i * 100, 0, i * 100])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_ap_file():
    """Create a temporary AP Excel file."""
    wb = Workbook()
    ws = wb.active
    ws.title = "매입채무"
    ws.append(["공급자명", "금액", "만기일", "비고"])
    ws.append(["GHI사", 8000000, "2025-05-31", "자재구매"])
    ws.append(["JKL사", 2000000, "2025-06-15", "용역비"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_lease_file():
    """Create a temporary LEASE Excel file."""
    wb = Workbook()
    ws = wb.active
    ws.title = "리스"
    ws.append(["리스료", "리스시작일", "비고"])
    ws.append([1200000, "2025-01-01", "사무실 임차"])
    ws.append([500000, "2025-03-01", "차량 리스"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_tb_debit_only_file():
    """TB file with debit column only."""
    wb = Workbook()
    ws = wb.active
    ws.title = "시산표"
    ws.append(["계정코드", "계정명", "차변"])
    ws.append(["1110", "현금", 1000000])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_gl_debit_only_file():
    """GL file with debit column only."""
    wb = Workbook()
    ws = wb.active
    ws.title = "총계정원장"
    ws.append(["전표번호", "전표일자", "계정코드", "차변"])
    ws.append(["GL-001", "2025-01-15", "1110", 500000])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_money_currency_symbol_file():
    """TB file with currency symbols in money fields."""
    wb = Workbook()
    ws = wb.active
    ws.title = "시산표"
    ws.append(["계정코드", "계정명", "차변", "대변", "잔액"])
    ws.append(["1110", "현금", "₩1,000,000", "₩0", "₩1,000,000"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_money_dash_file():
    """TB file with dash '-' in money fields (valid, means zero)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "시산표"
    ws.append(["계정코드", "계정명", "차변", "대변", "잔액"])
    ws.append(["1110", "현금", 1000000, "-", 1000000])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_multi_money_string_file():
    """TB file with non-numeric strings in multiple money columns."""
    wb = Workbook()
    ws = wb.active
    ws.title = "시산표"
    ws.append(["계정코드", "계정명", "차변", "대변", "잔액"])
    ws.append(["1110", "현금", "일백만", "영", "일백만"])

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        wb.save(f.name)
        yield f.name
    os.unlink(f.name)


# ──────────────────────────────────────────────
# Byte-content Fixtures (for API upload tests)
# ──────────────────────────────────────────────
@pytest.fixture
def sample_tb_bytes(sample_tb_file):
    with open(sample_tb_file, "rb") as f:
        return f.read()


@pytest.fixture
def sample_gl_bytes(sample_gl_file):
    with open(sample_gl_file, "rb") as f:
        return f.read()


@pytest.fixture
def sample_ar_bytes(sample_ar_file):
    with open(sample_ar_file, "rb") as f:
        return f.read()


@pytest.fixture
def sample_empty_data_bytes(sample_empty_data_file):
    with open(sample_empty_data_file, "rb") as f:
        return f.read()


@pytest.fixture
def sample_tb_with_extra_cols_bytes(sample_tb_with_extra_cols_file):
    with open(sample_tb_with_extra_cols_file, "rb") as f:
        return f.read()


@pytest.fixture
def sample_tb_large_bytes(sample_tb_large_file):
    with open(sample_tb_large_file, "rb") as f:
        return f.read()


@pytest.fixture
def sample_bank_bytes(sample_bank_file):
    with open(sample_bank_file, "rb") as f:
        return f.read()


@pytest.fixture
def sample_debt_bytes(sample_debt_file):
    with open(sample_debt_file, "rb") as f:
        return f.read()


@pytest.fixture
def sample_ap_bytes(sample_ap_file):
    with open(sample_ap_file, "rb") as f:
        return f.read()
