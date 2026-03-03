#!/usr/bin/env python3
"""Dependency audit: import ↔ pyproject.toml 동기화 검증 스크립트.

Usage:
    python check_deps.py deal-mgmt
    python check_deps.py all
"""

import ast
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 프로젝트 루트 자동 탐지 (스크립트 위치 기준)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = (
    SCRIPT_DIR.parent.parent.parent.parent
)  # .claude/skills/dep-audit/scripts → root

# ---------------------------------------------------------------------------
# 모듈 경로 매핑
# ---------------------------------------------------------------------------
MODULE_PATHS: dict[str, dict[str, str]] = {
    "deal-mgmt": {
        "src": "deal-mgmt/app",
        "pyproject": "deal-mgmt/pyproject.toml",
        "local_packages": ["app", "tests", "conftest", "scripts"],
    },
    "kiis": {
        "src": "kiis/app",
        "pyproject": "kiis/pyproject.toml",
        "local_packages": ["app", "tests", "conftest", "scripts"],
    },
    "im": {
        "src": "im/src",
        "pyproject": "im/pyproject.toml",
        "local_packages": [
            "src",
            "api",
            "models",
            "chart_engine",
            "narrative_generator",
            "tests",
            "conftest",
        ],
    },
    "fdd": {
        "src": "fdd/backend/app",
        "pyproject": "fdd/backend/pyproject.toml",
        "local_packages": ["app", "tests", "conftest", "scripts"],
    },
}

# ---------------------------------------------------------------------------
# import명 → pyproject.toml 패키지명 매핑 (불일치 해소)
# ---------------------------------------------------------------------------
IMPORT_TO_PACKAGE: dict[str, str] = {
    "PIL": "Pillow",
    "bs4": "beautifulsoup4",
    "cv2": "opencv-python",
    "yaml": "pyyaml",
    "sklearn": "scikit-learn",
    "fitz": "PyMuPDF",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "jose": "python-jose",
    "dotenv": "python-dotenv",
    "jwt": "PyJWT",
    "dateutil": "python-dateutil",
    "attr": "attrs",
    "lxml": "lxml",
    "google": "google-generativeai",
    "azure": "azure-storage-blob",
    "rapidfuzz": "rapidfuzz",
    "kiwipiepy": "kiwipiepy",
    "feedparser": "feedparser",
    "celery": "celery",
    "docxtpl": "docxtpl",
    "olefile": "olefile",
    "pdfplumber": "pdfplumber",
    "kaleido": "kaleido",
    "plotly": "plotly",
    "anthropic": "anthropic",
    "openai": "openai",
    "apscheduler": "apscheduler",
    "aiosmtplib": "aiosmtplib",
    "slack_sdk": "slack-sdk",
    "elasticsearch": "elasticsearch",
    "hwp5": "pyhwp",
    "xlrd": "xlrd",
    "multipart": "python-multipart",
}

# ---------------------------------------------------------------------------
# FastAPI 등 프레임워크의 하위 의존성 (import 가능하지만 직접 등록 불필요)
# ---------------------------------------------------------------------------
TRANSITIVE_DEPS: set[str] = {
    "starlette",  # FastAPI
    "anyio",  # starlette/httpx
    "sniffio",  # anyio
    "certifi",  # httpx
    "h11",  # uvicorn
    "click",  # uvicorn
    "idna",  # httpx
    "annotated_types",  # pydantic
    "pydantic_core",  # pydantic
    "greenlet",  # sqlalchemy
    "markupsafe",  # jinja2
    "passlib",  # auth
    "bcrypt",  # passlib
    "six",  # various
    "wrapt",  # various
    "kombu",  # celery
    "vine",  # celery
    "amqp",  # celery
    "billiard",  # celery
}

# ---------------------------------------------------------------------------
# Python 표준 라이브러리 (3.11 기준, 주요 모듈)
# ---------------------------------------------------------------------------
STDLIB_MODULES: set[str] = {
    "__future__",
    "abc",
    "aifc",
    "argparse",
    "array",
    "ast",
    "asyncio",
    "atexit",
    "base64",
    "binascii",
    "bisect",
    "builtins",
    "bz2",
    "calendar",
    "cgi",
    "cgitb",
    "chunk",
    "cmath",
    "cmd",
    "code",
    "codecs",
    "codeop",
    "collections",
    "colorsys",
    "compileall",
    "concurrent",
    "configparser",
    "contextlib",
    "contextvars",
    "copy",
    "copyreg",
    "cProfile",
    "csv",
    "ctypes",
    "curses",
    "dataclasses",
    "datetime",
    "dbm",
    "decimal",
    "difflib",
    "dis",
    "distutils",
    "doctest",
    "email",
    "encodings",
    "enum",
    "errno",
    "faulthandler",
    "fcntl",
    "filecmp",
    "fileinput",
    "fnmatch",
    "fractions",
    "ftplib",
    "functools",
    "gc",
    "getopt",
    "getpass",
    "gettext",
    "glob",
    "graphlib",
    "grp",
    "gzip",
    "hashlib",
    "heapq",
    "hmac",
    "html",
    "http",
    "idlelib",
    "imaplib",
    "imghdr",
    "imp",
    "importlib",
    "inspect",
    "io",
    "ipaddress",
    "itertools",
    "json",
    "keyword",
    "lib2to3",
    "linecache",
    "locale",
    "logging",
    "lzma",
    "mailbox",
    "mailcap",
    "marshal",
    "math",
    "mimetypes",
    "mmap",
    "modulefinder",
    "multiprocessing",
    "netrc",
    "nis",
    "nntplib",
    "numbers",
    "operator",
    "optparse",
    "os",
    "ossaudiodev",
    "pathlib",
    "pdb",
    "pickle",
    "pickletools",
    "pipes",
    "pkgutil",
    "platform",
    "plistlib",
    "poplib",
    "posix",
    "posixpath",
    "pprint",
    "profile",
    "pstats",
    "pty",
    "pwd",
    "py_compile",
    "pyclbr",
    "pydoc",
    "queue",
    "quopri",
    "random",
    "re",
    "readline",
    "reprlib",
    "resource",
    "rlcompleter",
    "runpy",
    "sched",
    "secrets",
    "select",
    "selectors",
    "shelve",
    "shlex",
    "shutil",
    "signal",
    "site",
    "smtpd",
    "smtplib",
    "sndhdr",
    "socket",
    "socketserver",
    "sqlite3",
    "ssl",
    "stat",
    "statistics",
    "string",
    "stringprep",
    "struct",
    "subprocess",
    "sunau",
    "symtable",
    "sys",
    "sysconfig",
    "syslog",
    "tabnanny",
    "tarfile",
    "telnetlib",
    "tempfile",
    "termios",
    "test",
    "textwrap",
    "threading",
    "time",
    "timeit",
    "tkinter",
    "token",
    "tokenize",
    "tomllib",
    "trace",
    "traceback",
    "tracemalloc",
    "tty",
    "turtle",
    "turtledemo",
    "types",
    "typing",
    "unicodedata",
    "unittest",
    "urllib",
    "uu",
    "uuid",
    "venv",
    "warnings",
    "wave",
    "weakref",
    "webbrowser",
    "winreg",
    "winsound",
    "wsgiref",
    "xdrlib",
    "xml",
    "xmlrpc",
    "zipapp",
    "zipfile",
    "zipimport",
    "zlib",
    "_thread",
    "typing_extensions",
}


def normalize_package_name(name: str) -> str:
    """패키지명 정규화: 소문자, - → _, extras 제거."""
    # "fastapi[standard]" → "fastapi"
    name = name.split("[")[0]
    # ">=1.0" 등 버전 제거
    for sep in (">=", "<=", "==", "!=", "~=", ">", "<"):
        name = name.split(sep)[0]
    return name.strip().lower().replace("-", "_")


def parse_pyproject_deps(pyproject_path: Path) -> set[str]:
    """pyproject.toml에서 등록된 의존성 집합 추출 (tomllib 사용)."""
    import tomllib as _tomllib  # noqa: F811 — Python 3.11+ stdlib

    if not pyproject_path.exists():
        return set()

    with open(pyproject_path, "rb") as f:
        data = _tomllib.load(f)

    deps: set[str] = set()

    # [project].dependencies
    for dep in data.get("project", {}).get("dependencies", []):
        deps.add(normalize_package_name(dep))

    # [project.optional-dependencies] — 모든 그룹 (dev, test 등)
    for _group, group_deps in (
        data.get("project", {}).get("optional-dependencies", {}).items()
    ):
        for dep in group_deps:
            deps.add(normalize_package_name(dep))

    return deps


def extract_imports(py_file: Path) -> list[dict[str, str | int]]:
    """Python 파일에서 import 문 추출 (AST 기반)."""
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports: list[dict[str, str | int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(
                    {
                        "module": alias.name.split(".")[0],
                        "full": alias.name,
                        "line": node.lineno,
                    }
                )
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:  # 절대 import만
                imports.append(
                    {
                        "module": node.module.split(".")[0],
                        "full": node.module,
                        "line": node.lineno,
                    }
                )
    return imports


def resolve_package_name(import_name: str) -> str:
    """import명을 pyproject.toml 패키지명으로 변환."""
    if import_name in IMPORT_TO_PACKAGE:
        return normalize_package_name(IMPORT_TO_PACKAGE[import_name])
    return normalize_package_name(import_name)


def audit_module(module_name: str) -> dict:
    """단일 모듈의 import ↔ pyproject.toml 대조."""
    config = MODULE_PATHS[module_name]
    src_dir = PROJECT_ROOT / config["src"]
    pyproject_path = PROJECT_ROOT / config["pyproject"]
    local_packages = set(config.get("local_packages", []))

    # 1. pyproject.toml 의존성 수집
    registered = parse_pyproject_deps(pyproject_path)

    # 2. 소스 파일 스캔
    if not src_dir.exists():
        return {
            "module": module_name,
            "error": f"Source directory not found: {src_dir}",
        }

    py_files = list(src_dir.rglob("*.py"))

    # tests 디렉토리도 스캔 (dev 의존성 검증)
    test_dir = PROJECT_ROOT / config["src"].rsplit("/", 1)[0] / "tests"
    if test_dir.exists():
        py_files.extend(test_dir.rglob("*.py"))

    # 3. import 수집
    all_imports: dict[str, list[str]] = {}  # package → [file:line, ...]
    for py_file in py_files:
        rel_path = py_file.relative_to(PROJECT_ROOT / config["src"].rsplit("/", 1)[0])
        for imp in extract_imports(py_file):
            module = imp["module"]

            # 필터링: stdlib, 로컬 패키지, transitive deps
            if module in STDLIB_MODULES:
                continue
            if module in local_packages:
                continue
            if module.startswith("_"):
                continue
            if normalize_package_name(module) in TRANSITIVE_DEPS:
                continue

            pkg_name = resolve_package_name(module)
            location = f"{rel_path}:{imp['line']}"
            if pkg_name not in all_imports:
                all_imports[pkg_name] = []
            all_imports[pkg_name].append(location)

    # 4. 비교
    imported_set = set(all_imports.keys())
    missing = imported_set - registered
    unused = registered - imported_set

    # 직접 import 없지만 런타임에 필요한 의존성 제외
    implicit_deps = {
        # ASGI 서버 / 드라이버
        "uvicorn",
        "gunicorn",
        "uvloop",
        "httptools",
        "watchfiles",
        "asyncpg",
        "psycopg2_binary",
        "aiosqlite",
        # Alembic (CLI 사용, import 불필요)
        "alembic",
        # pydantic-settings가 자동 로드
        "python_dotenv",
        # FastAPI form 파싱 (런타임 필요, 직접 import 드묾)
        "python_multipart",
        # pytest 플러그인 (fixture 기반, 직접 import 불필요)
        "pytest_asyncio",
        "pytest_cov",
        "pytest_httpx",
        # 린터/포맷터 (CLI 도구, import 불필요)
        "ruff",
        "black",
        "isort",
        "mypy",
    }
    unused = unused - implicit_deps

    missing_details = []
    for pkg in sorted(missing):
        missing_details.append(
            {
                "package": pkg,
                "import_name": pkg,
                "files": sorted(all_imports[pkg])[:5],  # 상위 5개만
            }
        )

    return {
        "module": module_name,
        "pyproject": str(pyproject_path.relative_to(PROJECT_ROOT)),
        "registered_count": len(registered),
        "imported_count": len(imported_set),
        "registered": sorted(registered),
        "imported": sorted(imported_set),
        "missing": missing_details,
        "unused": sorted(unused),
        "summary": {
            "total_registered": len(registered),
            "total_imported": len(imported_set),
            "missing": len(missing),
            "unused": len(unused),
        },
    }


def main() -> None:
    """메인 실행."""
    if len(sys.argv) < 2:
        target = "all"
    else:
        target = sys.argv[1].strip()

    if target == "all":
        modules = list(MODULE_PATHS.keys())
    elif target in MODULE_PATHS:
        modules = [target]
    else:
        print(
            json.dumps(
                {
                    "error": f"Unknown module: {target}. Valid: {list(MODULE_PATHS.keys())} or 'all'"
                }
            )
        )
        sys.exit(1)

    results = []
    for mod in modules:
        results.append(audit_module(mod))

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
