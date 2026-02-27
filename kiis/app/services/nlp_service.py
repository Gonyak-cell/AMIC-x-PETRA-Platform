import asyncio
import json
import logging
import re
from pathlib import Path

from kiwipiepy import Kiwi

logger = logging.getLogger(__name__)

# 데이터 파일 경로
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STOPWORDS_PATH = DATA_DIR / "stopwords_ko.txt"
SENTIMENT_DICT_PATH = DATA_DIR / "finance_sentiment_dict.json"

# 투자 정보 추출 정규식 패턴
AMOUNT_PATTERN = re.compile(r"(\d[\d,]*)\s*(억\s*원|만\s*원|조\s*원|원|달러|만\s*달러|억\s*달러)")
ROUND_PATTERN = re.compile(
    r"(시드|프리\s*시드|프리\s*시리즈\s*[A-Z]|시리즈\s*[A-Z]|프리\s*[A-Z]|Series\s*[A-Z]|Seed|Pre-?[A-Z]|브릿지|bridge|Pre-?IPO|프리\s*IPO)",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(r"(\d{4})\s*[년.\-/]\s*(\d{1,2})\s*[월.\-/]?\s*(\d{1,2})?\s*일?")


def _load_stopwords() -> set[str]:
    """불용어 사전을 로드한다."""
    if not STOPWORDS_PATH.exists():
        logger.warning("Stopwords file not found: %s", STOPWORDS_PATH)
        return set()
    words = set()
    for line in STOPWORDS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.add(line)
    return words


def _load_sentiment_dict() -> dict:
    """금융 감성 사전을 로드한다."""
    if not SENTIMENT_DICT_PATH.exists():
        logger.warning("Sentiment dictionary not found: %s", SENTIMENT_DICT_PATH)
        return {"positive": {}, "negative": {}}
    with open(SENTIMENT_DICT_PATH, encoding="utf-8") as f:
        return json.load(f)


class NLPService:
    """한국어 NLP 서비스

    - 형태소 분석: kiwipiepy (순수 Python, JDK 불필요)
    - 키워드 추출: 형태소 분석 → 불용어 제거 → TF-IDF 또는 빈도 기반
    - 감성 분석: 금융 도메인 감성 사전 기반
    - NER: 투자 뉴스에서 투자사/피투자사/금액/라운드/날짜 추출
    """

    def __init__(self) -> None:
        self.kiwi = Kiwi(num_workers=1)
        self.stopwords = _load_stopwords()
        self.sentiment_dict = _load_sentiment_dict()

    def extract_keywords(self, text: str, top_n: int = 10) -> list[dict]:
        """텍스트에서 키워드를 추출한다.

        형태소 분석 → 명사/고유명사 필터링 → 불용어 제거 → 빈도 기반 상위 N개

        Args:
            text: 분석할 텍스트
            top_n: 반환할 키워드 수

        Returns:
            [{"keyword": "투자", "count": 5, "pos": "NNG"}, ...]
        """
        if not text or not text.strip():
            return []

        tokens = self.kiwi.tokenize(text)

        # 명사 계열 태그만 추출: NNG(일반명사), NNP(고유명사), NNB(의존명사 제외)
        noun_tags = {"NNG", "NNP"}
        word_counts: dict[str, dict] = {}

        for token in tokens:
            word = token.form
            tag = token.tag

            if tag not in noun_tags:
                continue
            if len(word) < 2:  # 1글자 명사 제외
                continue
            if word in self.stopwords:
                continue

            if word in word_counts:
                word_counts[word]["count"] += 1
            else:
                word_counts[word] = {"keyword": word, "count": 1, "pos": tag}

        # 빈도 내림차순
        sorted_keywords = sorted(word_counts.values(), key=lambda x: x["count"], reverse=True)
        return sorted_keywords[:top_n]

    def analyze_sentiment(self, text: str) -> dict:
        """금융 감성 사전 기반으로 감성 점수를 산출한다.

        Args:
            text: 분석할 텍스트

        Returns:
            {
                "score": -1.0 ~ 1.0,
                "label": "positive" | "negative" | "neutral",
                "positive_matches": [{"term": ..., "weight": ...}],
                "negative_matches": [{"term": ..., "weight": ...}],
            }
        """
        if not text or not text.strip():
            return {
                "score": 0.0,
                "label": "neutral",
                "positive_matches": [],
                "negative_matches": [],
            }

        positive_matches = []
        negative_matches = []

        # 긍정어 매칭 (긴 키워드부터 매칭하여 부분 매칭 방지)
        for term, weight in sorted(
            self.sentiment_dict.get("positive", {}).items(),
            key=lambda x: len(x[0]),
            reverse=True,
        ):
            if term in text:
                positive_matches.append({"term": term, "weight": weight})

        # 부정어 매칭
        for term, weight in sorted(
            self.sentiment_dict.get("negative", {}).items(),
            key=lambda x: len(x[0]),
            reverse=True,
        ):
            if term in text:
                negative_matches.append({"term": term, "weight": abs(weight)})

        # 점수 계산: 매칭된 용어들의 가중 평균
        total_positive = sum(m["weight"] for m in positive_matches) if positive_matches else 0.0
        total_negative = sum(m["weight"] for m in negative_matches) if negative_matches else 0.0

        match_count = len(positive_matches) + len(negative_matches)
        score = 0.0 if match_count == 0 else (total_positive - total_negative) / match_count

        # -1.0 ~ 1.0 범위로 클램핑
        score = max(-1.0, min(1.0, score))

        if score > 0.1:
            label = "positive"
        elif score < -0.1:
            label = "negative"
        else:
            label = "neutral"

        return {
            "score": round(score, 4),
            "label": label,
            "positive_matches": positive_matches,
            "negative_matches": negative_matches,
        }

    def extract_investment_info(self, text: str) -> dict:
        """뉴스 텍스트에서 투자 정보를 추출한다 (규칙 기반 NER).

        추출 대상: 투자사, 피투자사, 투자금액, 투자 라운드, 날짜

        Args:
            text: 뉴스 기사 텍스트

        Returns:
            {
                "investors": ["한국투자파트너스", ...],
                "investees": ["스타트업A", ...],
                "amounts": [{"value": "100", "unit": "억원", "raw": "100억원"}],
                "round": "시리즈A" | None,
                "dates": [{"year": "2025", "month": "6", "day": "15"}],
            }
        """
        result: dict = {
            "investors": [],
            "investees": [],
            "amounts": [],
            "round": None,
            "dates": [],
        }

        if not text or not text.strip():
            return result

        # 투자금액 추출
        for match in AMOUNT_PATTERN.finditer(text):
            value = match.group(1).replace(",", "")
            unit = match.group(2).replace(" ", "")
            result["amounts"].append(
                {
                    "value": value,
                    "unit": unit,
                    "raw": match.group(0).strip(),
                }
            )

        # 투자 라운드 추출
        round_match = ROUND_PATTERN.search(text)
        if round_match:
            result["round"] = round_match.group(0).strip()

        # 날짜 추출
        for match in DATE_PATTERN.finditer(text):
            date_info: dict[str, str | None] = {
                "year": match.group(1),
                "month": match.group(2),
            }
            date_info["day"] = match.group(3) if match.group(3) else None
            result["dates"].append(date_info)

        # 투자사/피투자사 추출 (형태소 분석 + 패턴 기반)
        investors, investees = self._extract_entities(text)
        result["investors"] = investors
        result["investees"] = investees

        return result

    def _extract_entities(self, text: str) -> tuple[list[str], list[str]]:
        """투자사와 피투자사를 추출한다.

        패턴:
        - "A가 B에 투자" → A=투자사, B=피투자사
        - "B, A로부터 투자 유치" → A=투자사, B=피투자사
        - "A 등이 참여" → A=투자사
        """
        investors: list[str] = []
        investees: list[str] = []

        # 고유명사(NNP) 추출
        tokens = self.kiwi.tokenize(text)
        proper_nouns = []
        for token in tokens:
            if token.tag == "NNP" and len(token.form) >= 2:
                proper_nouns.append(token.form)

        # 투자 동사 패턴으로 역할 구분
        # "A가/은/는 ... 투자" → A = 투자사
        investor_patterns = [
            re.compile(
                r"([가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+)*)\s*(?:이|가|은|는)\s+.*?(?:투자(?:했|한|하)|참여|리드)"
            ),
            re.compile(r"([가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+)*)\s*(?:로부터|에서)\s+.*?(?:투자|유치)"),
        ]

        # "B에 ... 투자" → B = 피투자사
        investee_patterns = [
            re.compile(r"([가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+)*)\s*(?:에|에게)\s+.*?(?:투자)"),
            re.compile(r"([가-힣A-Za-z0-9]+(?:\s+[가-힣A-Za-z0-9]+)*)\s*,?\s*(?:시리즈|시드|투자\s*유치)"),
        ]

        for pattern in investor_patterns:
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                if len(name) >= 2 and name not in investors:
                    investors.append(name)

        for pattern in investee_patterns:
            for match in pattern.finditer(text):
                name = match.group(1).strip()
                if len(name) >= 2 and name not in investees:
                    investees.append(name)

        # 고유명사 중 투자사/피투자사에 미포함된 것을 후보로 기록
        # (역할이 불분명한 경우 고유명사 자체만 반환)
        if not investors and not investees and proper_nouns:
            # 첫 번째 고유명사를 피투자사 후보로 (뉴스 제목/본문의 주어)
            seen = set()
            for noun in proper_nouns:
                if noun not in seen:
                    seen.add(noun)
                    investees.append(noun)

        return investors[:5], investees[:5]

    def extract_keywords_tfidf(self, documents: list[str], top_n: int = 10) -> list[list[dict]]:
        """여러 문서에서 TF-IDF 기반 키워드를 추출한다.

        Args:
            documents: 문서 목록
            top_n: 문서별 반환할 키워드 수

        Returns:
            문서별 [{"keyword": ..., "tfidf_score": ...}, ...]
        """
        from sklearn.feature_extraction.text import TfidfVectorizer

        if not documents:
            return []

        # 형태소 분석 후 명사만 추출하여 공백으로 합친 문서
        processed_docs = []
        for doc in documents:
            nouns = self._extract_nouns(doc)
            processed_docs.append(" ".join(nouns))

        if not any(processed_docs):
            return [[] for _ in documents]

        vectorizer = TfidfVectorizer(max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(processed_docs)
        feature_names = vectorizer.get_feature_names_out()

        results = []
        for i in range(len(documents)):
            row = tfidf_matrix[i].toarray().flatten()
            top_indices = row.argsort()[::-1][:top_n]
            doc_keywords = []
            for idx in top_indices:
                if row[idx] > 0:
                    doc_keywords.append(
                        {
                            "keyword": feature_names[idx],
                            "tfidf_score": round(float(row[idx]), 4),
                        }
                    )
            results.append(doc_keywords)

        return results

    def _extract_nouns(self, text: str) -> list[str]:
        """텍스트에서 명사만 추출한다 (불용어 제거 포함)."""
        if not text:
            return []
        tokens = self.kiwi.tokenize(text)
        nouns = []
        for token in tokens:
            if token.tag in ("NNG", "NNP") and len(token.form) >= 2 and token.form not in self.stopwords:
                nouns.append(token.form)
        return nouns

    async def extract_keywords_async(self, text: str, top_n: int = 10) -> list[dict]:
        """extract_keywords의 async 래퍼 (asyncio 이벤트 루프 내에서 안전하게 호출)."""
        return await asyncio.to_thread(self.extract_keywords, text, top_n)

    async def extract_investment_info_async(self, text: str) -> dict:
        """extract_investment_info의 async 래퍼."""
        return await asyncio.to_thread(self.extract_investment_info, text)
