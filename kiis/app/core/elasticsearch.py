"""ElasticSearch 클라이언트 라이프사이클 관리

Nori 한국어 분석기를 사용하여 한국어 텍스트 검색을 지원한다.
4개 인덱스(companies, funds, news, deals)를 자동 생성/관리한다.
"""

import logging

from elasticsearch import AsyncElasticsearch

from app.core.config import settings

logger = logging.getLogger(__name__)

es_client: AsyncElasticsearch | None = None

# Nori 한국어 분석기를 사용하는 인덱스 설정
INDEX_SETTINGS: dict = {
    "settings": {
        "analysis": {
            "tokenizer": {
                "nori_tokenizer": {"type": "nori_tokenizer"},
            },
            "filter": {
                "nori_posfilter": {
                    "type": "nori_part_of_speech",
                    "stoptags": [
                        "E",
                        "IC",
                        "J",
                        "MAG",
                        "MAJ",
                        "MM",
                        "SP",
                        "SSC",
                        "SSO",
                        "SC",
                        "SE",
                        "XPN",
                        "XSA",
                        "XSN",
                        "XSV",
                        "UNA",
                        "NA",
                        "VSV",
                    ],
                },
                "nori_readingform": {"type": "nori_readingform"},
            },
            "analyzer": {
                "korean": {
                    "type": "custom",
                    "tokenizer": "nori_tokenizer",
                    "filter": ["nori_posfilter", "nori_readingform", "lowercase"],
                },
            },
        },
    },
}

# 4개 인덱스 매핑
INDEX_MAPPINGS: dict[str, dict] = {
    "kiis_companies": {
        "properties": {
            "corp_code": {"type": "keyword"},
            "corp_name": {"type": "text", "analyzer": "korean"},
            "stock_name": {"type": "text", "analyzer": "korean"},
            "ceo_nm": {"type": "text", "analyzer": "korean"},
            "corp_cls": {"type": "keyword"},
            "induty_code": {"type": "keyword"},
        },
    },
    "kiis_funds": {
        "properties": {
            "fund_code": {"type": "keyword"},
            "fund_name": {"type": "text", "analyzer": "korean"},
            "company_name": {"type": "text", "analyzer": "korean"},
            "fund_type": {"type": "keyword"},
            "fund_category": {"type": "keyword"},
        },
    },
    "kiis_news": {
        "properties": {
            "title": {"type": "text", "analyzer": "korean"},
            "content": {"type": "text", "analyzer": "korean"},
            "source": {"type": "keyword"},
            "published_at": {"type": "date"},
            "sentiment_score": {"type": "float"},
        },
    },
    "kiis_deals": {
        "properties": {
            "target_company": {"type": "text", "analyzer": "korean"},
            "sector": {"type": "keyword"},
            "amount_display": {"type": "text"},
            "round_stage": {"type": "keyword"},
            "deal_year": {"type": "integer"},
        },
    },
}


async def init_elasticsearch() -> None:
    """ES 클라이언트를 초기화하고 인덱스가 없으면 생성한다."""
    global es_client
    if not settings.ELASTICSEARCH_URL:
        logger.info("ElasticSearch URL not configured, skipping")
        return

    es_client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)

    # 연결 확인
    try:
        info = await es_client.info()
        logger.info("Connected to ElasticSearch: %s", info["version"]["number"])
    except Exception:
        logger.warning("Failed to connect to ElasticSearch at %s", settings.ELASTICSEARCH_URL, exc_info=True)
        await es_client.close()
        es_client = None
        return

    # 인덱스 존재 확인 및 생성
    for index_name, mapping in INDEX_MAPPINGS.items():
        try:
            exists = await es_client.indices.exists(index=index_name)
            if not exists:
                await es_client.indices.create(
                    index=index_name,
                    body={**INDEX_SETTINGS, "mappings": mapping},
                )
                logger.info("Created ES index: %s", index_name)
        except Exception:
            logger.exception("Failed to create ES index: %s", index_name)


async def close_elasticsearch() -> None:
    """ES 클라이언트를 안전하게 종료한다."""
    global es_client
    if es_client:
        await es_client.close()
        es_client = None
        logger.info("ElasticSearch client closed")


def get_es_client() -> AsyncElasticsearch | None:
    """현재 ES 클라이언트 인스턴스를 반환한다. 미초기화 시 None."""
    return es_client
