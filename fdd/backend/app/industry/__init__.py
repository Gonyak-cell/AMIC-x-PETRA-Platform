"""FDD 산업 모듈 패키지.

이 패키지를 import하면 모든 산업 모듈이 레지스트리에 등록된다.

Usage::

    from app.industry.registry import get_fdd_industry_module_safe

    module = get_fdd_industry_module_safe("tech")
    ctx = module.get_context()
"""

# 산업 모듈 import → @register_fdd_industry 데코레이터로 자동 등록
from app.industry import (  # noqa: F401
    financial_services,
    general,
    healthcare,
    logistics,
    manufacturing,
    tech_saas,
)
from app.industry.registry import (  # noqa: F401
    get_fdd_industry_module,
    get_fdd_industry_module_safe,
    list_industries,
)
