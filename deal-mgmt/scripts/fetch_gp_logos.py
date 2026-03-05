"""GP 공식 홈페이지 로고 URL 자동 수집 — MA_GP_v3.xlsx O열 채우기.

접근 방식:
1. 사전 정의된 GP명 → 도메인 매핑 (한국 주요 PE/VC/기관 ~130개)
2. 도메인 매핑 없으면 DuckDuckGo 검색 → 공식 홈페이지 도메인 자동 발견
3. Clearbit Logo API HEAD: https://logo.clearbit.com/{domain}?size=200
4. og:image 크롤링 (공식 홈페이지 메타태그 분석)

사용법:
    cd deal-mgmt
    python -m scripts.fetch_gp_logos [--dry-run] [--overwrite] [--no-search]
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import re
import sys
import time
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx
import openpyxl
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

EXCEL_PATH = Path(__file__).resolve().parent.parent / "data" / "MA_GP_v3.xlsx"
SHEET1_NAME = "GP별 관심 FI List"
DATA_START_ROW = 6  # 데이터 시작 행 (1-indexed)
LOGO_COL = 15  # O열 = 1-indexed (openpyxl)
LOGO_HEADER_ROW = 5  # 헤더 행 (데이터 시작 - 1)

# Azure Blob Storage
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
AZURE_CONTAINER = os.getenv("AZURE_VDR_CONTAINER_NAME", "amic-vdr")
LOGO_BLOB_PREFIX = "gp-logos"
SAS_EXPIRY_DAYS = 5 * 365  # 5년

REQUEST_TIMEOUT = 10.0
DELAY_BETWEEN = 0.3  # seconds between requests
DELAY_DDG = 1.5  # seconds between DuckDuckGo searches (rate limit 방지)

# DuckDuckGo 검색 결과에서 제외할 포털/뉴스 도메인
DDG_SKIP_DOMAINS = {
    "naver.com",
    "daum.net",
    "nate.com",
    "kakao.com",
    "mk.co.kr",
    "hankyung.com",
    "edaily.co.kr",
    "heraldcorp.com",
    "inews24.com",
    "news1.kr",
    "yonhap.co.kr",
    "yna.co.kr",
    "chosun.com",
    "joongang.co.kr",
    "donga.com",
    "hani.co.kr",
    "money.co.kr",
    "fnnews.com",
    "sedaily.com",
    "thebell.co.kr",
    "wikepedia.org",
    "wikipedia.org",
    "namu.wiki",
    "dart.fss.or.kr",
    "fss.or.kr",
    "ksfc.or.kr",
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "youtube.com",
    "linkedin.com",
    "instagram.com",
    "facebook.com",
}

DDG_URL_RE = re.compile(r'class="result__url"[^>]*>([^<\s]+)', re.IGNORECASE)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

# ─── 한국 GP 도메인 매핑 ──────────────────────────────────────────────────────
# 키: GP명 (raw_name 또는 부분 문자열), 값: 공식 도메인
GP_DOMAIN_MAP: dict[str, str] = {
    # ══ PE/PEF 전문 운용사 ══
    "MBK파트너스": "mbkpartners.com",
    "한앤컴퍼니": "hanhco.com",
    "IMM프라이빗에쿼티": "immpe.co.kr",
    "IMM PE": "immpe.co.kr",
    "IMM인베스트먼트": "imminvestment.co.kr",
    "스틱인베스트먼트": "stickinvestment.com",
    "STIC Investments": "stickinvestment.com",
    "UCK파트너스": "uck.co.kr",
    "어펄마캐피탈": "affirmacapital.com",
    "Affirma Capital": "affirmacapital.com",
    "글랜우드프라이빗에쿼티": "glenwood.co.kr",
    "글랜우드PE": "glenwood.co.kr",
    "파운틴헤드PE": "fountainheadpe.com",
    "파운틴헤드": "fountainheadpe.com",
    "케이스톤파트너스": "keystonepeco.com",
    "스카이레이크인베스트먼트": "skylakeinc.com",
    "스카이레이크에쿼티파트너스": "skylakeinc.com",
    "JKL파트너스": "jklpartners.com",
    "이스트브릿지파트너스": "eastbridgepartners.com",
    "웰투시인베스트먼트": "welltosi.com",
    "웰투시": "welltosi.com",
    "BKC파트너스": "bkcp.co.kr",
    "SG프라이빗에쿼티": "sgpe.co.kr",
    "SG PE": "sgpe.co.kr",
    "코스톤그룹": "kostongroup.com",
    "코스톤PE": "kostongroup.com",
    "프리미어파트너스": "premierpartners.co.kr",
    "맥쿼리자산운용": "macquarie.com",
    "맥쿼리": "macquarie.com",
    "보고펀드": "bogofund.co.kr",
    "큐캐피탈파트너스": "qcapital.co.kr",
    "KTB프라이빗에쿼티": "ktbpe.co.kr",
    "KTB PE": "ktbpe.co.kr",
    "아크로스파트너스": "acrosspartners.co.kr",
    "얼라인파트너스": "alignpartners.co.kr",
    "엠디엠PE": "mdmpe.co.kr",
    "MDM PE": "mdmpe.co.kr",
    "PEF앤코": "pefnco.com",
    "한국투자PE": "koreainvestment.co.kr",
    "신한PE": "shinhan.com",
    "우리PE": "wooriasset.com",
    "메리츠대체투자운용": "meritz.co.kr",
    "미래에셋PE": "miraeasset.com",
    "미래에셋대체투자": "miraeasset.com",
    "KKR": "kkr.com",
    "칼라일그룹": "carlyle.com",
    "Carlyle": "carlyle.com",
    "TPG": "tpg.com",
    "블랙스톤": "blackstone.com",
    "Blackstone": "blackstone.com",
    "어드밴티지어드바이저스": "advantage-ad.com",
    "한화에쿼티파트너스": "hanwha.com",
    "롯데PE": "lotte.co.kr",
    "포스코기술투자": "posco.co.kr",
    # ══ 자산운용사 ══
    "미래에셋자산운용": "miraeasset.com",
    "미래에셋": "miraeasset.com",
    "삼성자산운용": "samsungfund.co.kr",
    "KB자산운용": "kbam.co.kr",
    "한국투자신탁운용": "kitmc.com",
    "신한자산운용": "shinhanfund.com",
    "한화자산운용": "hanwhafund.co.kr",
    "하나대체투자자산운용": "hana-altinvestment.co.kr",
    "하나대체투자": "hana-altinvestment.co.kr",
    "NH아문디자산운용": "nhamundiam.co.kr",
    "이지스자산운용": "igis.co.kr",
    "브레인자산운용": "brainasset.co.kr",
    "교보AXA자산운용": "kyoboaxainv.co.kr",
    "우리자산운용": "wooriasset.com",
    "라이프자산운용": "lifeasset.co.kr",
    "멀티에셋자산운용": "multiasset.co.kr",
    "타임폴리오자산운용": "timefolio.com",
    "베어링자산운용": "baring.co.kr",
    "블랙록자산운용": "blackrock.com",
    "BlackRock": "blackrock.com",
    "VIP자산운용": "vipam.co.kr",
    "안다자산운용": "andafund.com",
    "현대인베스트먼트자산운용": "hdam.co.kr",
    "코람코자산운용": "koramco.com",
    "마스턴투자운용": "mastern.co.kr",
    "에이알인베스트자산운용": "arinvest.co.kr",
    "알파자산운용": "alphaasset.co.kr",
    "캡스톤자산운용": "capstoneasset.com",
    "키움자산운용": "kiwoomam.com",
    "신영자산운용": "shinyangam.com",
    "트러스톤자산운용": "trueston.com",
    "에셋플러스자산운용": "assetplus.com",
    "프랭클린템플턴투신운용": "franklintempleton.co.kr",
    "피델리티자산운용": "fidelity.co.kr",
    "슈로더투자신탁운용": "schroders.co.kr",
    "골드만삭스자산운용": "gsam.com",
    "JP모간자산운용": "jpmorganchase.com",
    "UBS자산운용": "ubs.com",
    # ══ 증권사 ══
    "미래에셋증권": "miraeasset.com",
    "삼성증권": "samsungsecurities.com",
    "키움증권": "kiwoom.com",
    "대신증권": "daishin.com",
    "한국투자증권": "truefriend.com",
    "신한투자증권": "shinhaninvest.com",
    "NH투자증권": "nhqv.com",
    "하나증권": "hanafn.com",
    "KB증권": "kbsec.com",
    "메리츠증권": "meritzfinance.com",
    "이베스트투자증권": "ebestsec.co.kr",
    "현대차증권": "hyundaifutures.com",
    "IBK투자증권": "ibksec.co.kr",
    "교보증권": "iprovest.com",
    "BNK투자증권": "bnkfn.com",
    "DB금융투자": "dbfi.co.kr",
    "SK증권": "sksec.co.kr",
    "유안타증권": "yuantasecurities.co.kr",
    "유진투자증권": "eugenefn.com",
    "한양증권": "hygood.co.kr",
    "부국증권": "bookook.co.kr",
    "흥국증권": "heungkukhm.com",
    "카카오페이증권": "kakaopaysec.com",
    "토스증권": "tosssecurities.com",
    "LS증권": "lssecurities.co.kr",
    "한화투자증권": "hanwhainvestment.com",
    # ══ 은행 ══
    "KB국민은행": "kbstar.com",
    "국민은행": "kbstar.com",
    "신한은행": "shinhan.com",
    "하나은행": "kebhana.com",
    "우리은행": "wooribank.com",
    "기업은행": "ibk.co.kr",
    "IBK기업은행": "ibk.co.kr",
    "NH농협은행": "nonghyup.com",
    "농협은행": "nonghyup.com",
    "수협은행": "suhyup.com",
    "SC제일은행": "standardchartered.co.kr",
    "한국씨티은행": "citi.co.kr",
    "씨티은행": "citi.co.kr",
    "대구은행": "dgb.co.kr",
    "부산은행": "busanbank.co.kr",
    "경남은행": "knbank.co.kr",
    "전북은행": "jeonbank.co.kr",
    "광주은행": "kjbank.co.kr",
    "제주은행": "jejubank.co.kr",
    "케이뱅크": "kbanknow.com",
    "카카오뱅크": "kakaobank.com",
    "토스뱅크": "tossbank.com",
    "KDB산업은행": "kdb.co.kr",
    "산업은행": "kdb.co.kr",
    "한국산업은행": "kdb.co.kr",
    # ══ 보험사 ══
    "삼성생명": "samsunglife.com",
    "한화생명": "hanwhalife.com",
    "교보생명": "kyobo.co.kr",
    "흥국생명": "heungkuklife.co.kr",
    "신한라이프": "slalife.co.kr",
    "신한생명": "slalife.co.kr",
    "KDB생명": "kdblife.co.kr",
    "ABL생명": "abllife.co.kr",
    "AIA생명": "aia.co.kr",
    "오렌지라이프": "orangelife.co.kr",
    "삼성화재": "samsungfire.com",
    "현대해상": "hi.co.kr",
    "DB손해보험": "db.co.kr",
    "KB손해보험": "kbinsure.co.kr",
    "메리츠화재": "meritzfire.com",
    "한화손해보험": "hwgeneralins.com",
    "롯데손해보험": "lotteinsurance.co.kr",
    "흥국화재": "heungkukfire.co.kr",
    "농협손해보험": "nonghyupfarm.com",
    "MG손해보험": "mggeneralins.com",
    "AXA손해보험": "axa.co.kr",
    "처브라이프": "chubb.com",
    "푸본현대생명": "fubonhyundai.com",
    # ══ 연기금/공제회 ══
    "국민연금공단": "nps.or.kr",
    "국민연금": "nps.or.kr",
    "공무원연금공단": "geps.or.kr",
    "사학연금": "tp.or.kr",
    "군인공제회": "koreasomac.or.kr",
    "경찰공제회": "psa.or.kr",
    "소방공제회": "www119.co.kr",
    "건설근로자공제회": "cwf.or.kr",
    "과학기술인공제회": "sema.or.kr",
    "우정사업본부": "koreapost.go.kr",
    "교직원공제회": "ktcu.or.kr",
    "한국교직원공제회": "ktcu.or.kr",
    "중소기업중앙회": "kbiz.or.kr",
    "행정공제회": "mopas.go.kr",
    # ══ VC/벤처투자 ══
    "한국벤처투자": "kvic.or.kr",
    "LB인베스트먼트": "lbinvestment.co.kr",
    "KB인베스트먼트": "kbinvestment.co.kr",
    "SV인베스트먼트": "sv.co.kr",
    "KTB벤처스": "ktbventures.com",
    "카카오벤처스": "kakaoventures.co.kr",
    "한국투자파트너스": "kip.co.kr",
    "신한벤처투자": "shinhanventure.com",
    "하나벤처스": "hanaventures.co.kr",
    "우리벤처파트너스": "woorientrepreneur.co.kr",
    "스파크랩": "sparklabs.co.kr",
    "에이티넘인베스트먼트": "atinum.com",
    "DSC인베스트먼트": "dscinvestment.com",
    "에이치엘비인베스트먼트": "hlbinvestment.co.kr",
    "스톤브릿지벤처스": "stonebridge.co.kr",
    "스마일게이트인베스트먼트": "smilegate.com",
    "인터베스트": "intervest.co.kr",
    "LSK인베스트먼트": "lskinvest.com",
    "키움인베스트먼트": "kiumis.com",
    # ══ 공공기관/정책금융 ══
    "신용보증기금": "kodit.or.kr",
    "기술보증기금": "kibo.or.kr",
    "중소기업진흥공단": "sbc.or.kr",
    "한국투자공사": "kic.kr",
    "KIC": "kic.kr",
    "한국자산관리공사": "kamco.or.kr",
    "KAMCO": "kamco.or.kr",
    "주택금융공사": "hf.go.kr",
    "예금보험공사": "kdic.or.kr",
    "한국무역보험공사": "ksure.or.kr",
    "한국수출입은행": "koreaexim.go.kr",
    "수출입은행": "koreaexim.go.kr",
    # ══ 그룹 금융계열사 ══
    "삼성": "samsung.com",
    "LG그룹": "lg.com",
    "SK그룹": "sk.com",
    "현대자동차그룹": "hyundai.com",
    "현대자동차": "hyundai.com",
    "롯데그룹": "lotte.co.kr",
    "포스코": "posco.co.kr",
    "한국전력공사": "kepco.co.kr",
    "KT": "kt.com",
    "SK텔레콤": "sktelecom.com",
    "CJ그룹": "cj.net",
    "LS그룹": "ls-electric.com",
    "두산그룹": "doosan.com",
    "효성그룹": "hyosung.com",
    "한화그룹": "hanwha.com",
    "GS그룹": "gsgroup.co.kr",
    "HDC": "hdcgrouphq.com",
    "코오롱그룹": "kolongroup.com",
    "OCI": "oci.co.kr",
    "보령제약": "boryung.co.kr",
    "종근당": "ckd.co.kr",
    "대웅제약": "daewoong.com",
    "셀트리온": "celltrion.com",
    # ══ 한글 음독 표기 — Excel GP명 완전 일치 ══
    # PE/PEF (영문 약어 음독)
    "엠비케이파트너스": "mbkpartners.com",
    "아이엠엠프라이빗에쿼티": "immpe.co.kr",
    "아이엠엠인베스트먼트": "imminvestment.co.kr",
    "아이엠엠자산운용": "imminvestment.co.kr",
    "아이엠엠크레딧앤솔루션": "immcns.com",
    "유씨케이파트너스": "uck.co.kr",
    "제이케이엘파트너스": "jklpartners.com",
    "제이케이엘크레딧인베스트먼트": "jklpartners.com",
    "에스티씨인베스트먼트": "stickinvestment.com",
    "스틱얼터너티브자산운용": "stickinvestment.com",
    "스틱벤처스": "stickinvestment.com",
    "글랜우드크레딧": "glenwood.co.kr",
    "브이아이지파트너스": "vigpartners.com",
    "에스지프라이빗에쿼티": "sgpe.co.kr",
    "케이디비인베스트먼트": "kdbi.co.kr",
    "에스비브이에이": "sbva.com",
    "아주아이비투자": "ajuib.co.kr",
    "에스브이인베스트먼트": "sv.co.kr",
    "코스톤아시아": "kostongroup.com",
    "스톤브릿지캐피탈": "stonebridge.co.kr",
    "케이티비프라이빗에쿼티": "ktbpe.co.kr",
    "케이티비벤처스": "ktbventures.com",
    # 금융지주 계열 (KB, NH, IBK, Hana, Woori 등)
    "케이비자산운용": "kbam.co.kr",
    "케이비인베스트먼트": "kbinvestment.co.kr",
    "케이비증권": "kbsec.com",
    "엔에이치투자증권": "nhqv.com",
    "아이비케이투자증권": "ibksec.co.kr",
    "아이비케이캐피탈": "ibk.co.kr",
    "산은캐피탈": "kdb.co.kr",
    "하나에프앤아이": "hanafni.co.kr",
    "우리프라이빗에퀴티자산운용": "wooriasset.com",
    "신한캐피탈": "shinhan.com",
    "우리금융에프앤아이": "wooriasset.com",
    # 대형 자산운용/증권 계열
    "엘비인베스트먼트": "lbinvestment.co.kr",
    "엘비프라이빗에쿼티": "lbinvestment.co.kr",
    "비엔케이투자증권": "bnkfn.com",
    "키움투자자산운용": "kiwoomam.com",
    "키움캐피탈": "kiwoomam.com",
    "키움프라이빗에쿼티": "kiwoom.com",
    "유진프라이빗에쿼티": "eugenefn.com",
    "유진자산운용": "eugenefn.com",
    "대신프라이빗에쿼티": "daishin.com",
    "마스턴파트너스": "mastern.co.kr",
    "이지스투자파트너스": "igis.co.kr",
    "한국투자프라이빗에쿼티": "koreainvestment.co.kr",
    # 기타 알려진 PE/VC (음독)
    "연합자산관리": "uamco.co.kr",
    "다올프라이빗에쿼티": "daolfs.co.kr",
    "파인트리자산운용": "finetreecap.com",
    "에이치앤큐에쿼티파트너스": "hnq.co.kr",
    "한앤브라더스": "hanhco.com",
    "엘엑스인베스트먼트": "lxholdings.co.kr",
    "현대투자파트너스": "hyundai.com",
    # ══ 웹 리서치 기반 추가 (2026-03-05) ══
    "에스제이엘파트너스": "sjlpartners.com",
    "큐리어스파트너스": "curiouspe.com",
    "도미누스인베스트먼트": "dominusinvestment.com",
    "센트로이드인베스트먼트파트너스": "centroidip.com",
    "크레센도에쿼티파트너스": "crescendoep.com",
    "이앤에프프라이빗에퀴티": "enfpe.com",
    "비엔더블유인베스트먼트": "bnwinv.com",
    "제이씨파트너스": "jcpartners.kr",
    "에스케이에스프라이빗에쿼티": "skspe.com",
    "에이스에쿼티파트너스": "acelp.co.kr",
    "에스씨로이코리아": "sclowy.com",
    "프랙시스캐피탈파트너스": "praxiscp.com",
    "앰버스톤": "amberstoneam.com",
    "이음프라이빗에쿼티": "eumpe.com",
    "제이앤프라이빗에쿼티": "jnpef.com",
    "유안타인베스트먼트": "yuantainvest.com",
    "원익투자파트너스": "wiipco.com",
    "알케미스트캐피탈파트너스코리아": "alchemistcap.com",
    "삼천리자산운용": "sig-fund.com",
    "파라투스인베스트먼트": "paratusinvestment.com",
    "이엠피벨스타": "empbelstar.com",
    "케이씨지아이": "kcgifund.com",
    "케이엘앤파트너스": "klnpartnerslp.kr",
    "포어러너캐피탈파트너스": "frcpartners.com",
    "라데팡스파트너스": "ldpartners.co.kr",
    "스텔라인베스트먼트": "stellainv.com",
    "하일랜드에쿼티파트너스": "highlandep.co.kr",
    "이앤인베스트먼트": "eninvestment.co.kr",
    "디에스프라이빗에쿼티": "dspe.kr",
    "케이클라비스": "kclavis.com",
    "에스비아이인베스트먼트": "sbik.co.kr",
    "헬리오스프라이빗에쿼티": "heliospe.com",
    "아크앤파트너스": "arknpartners.com",
    "브이엘인베스트먼트": "vlinvestment.com",
    "시냅틱인베스트먼트": "synaptic-investment.com",
    "유티씨인베스트먼트": "utc.co.kr",
    "노틱인베스트먼트": "nauticinv.com",
    "에이알에이코리아자산운용": "arak.co.kr",
    "어센트프라이빗에쿼티": "ascentpe.co.kr",
    "메티스톤에퀴티파트너스": "metistone.com",
    "에스케이에스크레딧": "skscredit.com",
    "린드먼아시아인베스트먼트": "laic.kr",
    "캐피탈랜드투자운용": "capitaland.com",
    "파라마크벤처스": "paramark.vc",
    "차파트너스자산운용": "tchapartners.com",
    "노앤파트너스": "nohnpartners.com",
    "아르게스프라이빗에쿼티": "arges.co.kr",
    "에버베스트파트너스": "everbestpartners.com",
    "화인자산운용": "fineinvestment.co.kr",
    "에이치자산운용": "hassetfund.com",
    "에이티유파트너스": "atupartners.com",
    "파빌리온프라이빗에쿼티": "pavilioninv.com",
    "피에스얼라이언스": "psalliance.co.kr",
    "포레스트파트너스": "forestgp.com",
    "엠씨파트너스": "mcpartners.co.kr",
    "그래비티프라이빗에쿼티": "gravitype.com",
    "피씨에이치캐피탈파트너스": "pchcaps.com",
    "에이티피인베스트먼트": "atpinv.com",
    "세마인베스트먼트": "semainv.com",
    "스타셋인베스트먼트": "stassetsinv.com",
    "원레이크파트너스": "onelakepartners.com",
    "타이키파트너스": "tychepartners.kr",
    "에이비즈파트너스": "avespartners.com",
    "메타인베스트먼트": "metainvestment.co.kr",
    "피에스캐피탈파트너스": "pscp.co.kr",
    "뱅커스트릿": "bankerstreet.com",
    "디에스자산운용": "dsasset.com",
    "위벤처스": "weventures.co.kr",
    "더블유더블유지자산운용": "wwg.kr",
    "그리니치프라이빗에쿼티": "greenwichpe.com",
    "라이노스자산운용": "rhinos.kr",
    "씨피파트너스": "cp-partners.co.kr",
    "티티유프라이빗에쿼티": "ttuprivateequity.com",
    "에벤투스파트너스": "eventuspe.com",
    "엠디엠자산운용": "mdmam.com",
    "엘케이투자파트너스": "lkpartners.co.kr",
    "엘리베이션에쿼티파트너스코리아": "elevationequity.com",
    "레이크브릿지에쿼티파트너스": "lakebridgeep.com",
    "로이투자파트너스": "ddinvest.co.kr",
    "민트벤처파트너스": "mintventures.bio",
    "노틱캐피탈코리아": "nautic.co.kr",
    "크로스로드파트너스": "krossroad.co.kr",
    "케이프투자증권": "capefn.com",
    "제이더블유앤파트너스": "jw-partners.com",
    "와이제이에이인베스트먼트": "yjai.co.kr",
    "제이커브인베스트먼트": "jcurveinvest.com",
    "시몬느인베스트먼트": "simonefg.co.kr",
    "다토즈파트너스": "dattoz.co",
    "오엔벤처투자": "onventure.co.kr",
    "인텔렉추얼디스커버리": "i-discovery.com",
    "비하이인베스트먼트": "behighvc.co.kr",
    "오라클벤처투자": "oraclevc.co.kr",
    "크레비스파트너스": "crevisse.com",
    "디비프라이빗에쿼티": "dbpe.co.kr",
    "윤진파트너스": "yoonjinpartners.com",
    "크레디언파트너스": "credpart.com",
    "모트프라이빗에쿼티": "moatpe.com",
    "티인베스트먼트": "tinvestment.co.kr",
    "아이디지캐피탈파트너스코리아": "idgcapital.co.kr",
    "더웰스인베스트먼트": "investwells.com",
    "코레이트자산운용": "koreitasset.com",
    "에버마운트캐피탈매니지먼트": "evermountcap.com",
    "하버브릭스파트너스": "harborbricks.co.kr",
    "고릴라피이": "gorillape.com",
    "더터닝포인트": "theturningpoint.co.kr",
    "오티엄캐피탈": "otiumcapital.co.kr",
    "에임인베스트먼트": "aim-inv.com",
    "피앤피인베스트먼트": "pnpinvest.co.kr",
    "피아이에이인베스트먼트파트너스": "piainvestment.com",
    "엠벤처투자": "m-vc.co.kr",
    "와디즈파트너스": "partners.wadiz.kr",
    "데일리파트너스": "dayli.partners",
    "씨에이씨파트너스": "cacpim.com",
    "티케인베스트먼트": "tychepe.com",
    "비케이피엘자산운용": "balbeckpl.com",
    "컴퍼니케이파트너스": "kpartners.co.kr",
    "인빅터스프라이빗에쿼티아시아": "invictusasia.com",
    "오픈워터인베스트먼트": "openwaterinv.co.kr",
    "쿨리지코너인베스트먼트": "ccvc.co.kr",
    "마그나인베스트먼트": "mgni.co.kr",
    "화인파트너스": "fine-partners.co.kr",
    "인마크에쿼티파트너스": "inmarkasset.com",
    "에이치투지파트너스": "nauticsep.com",
}

OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']'
    r'|<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    re.IGNORECASE | re.DOTALL,
)


def _find_domain(gp_name: str) -> str | None:
    """GP명으로 도메인 찾기 — 정확 매치 → 최장 부분 문자열 매치."""
    name = gp_name.strip()

    # 1. 정확 매치
    if name in GP_DOMAIN_MAP:
        return GP_DOMAIN_MAP[name]

    # 2. 키가 GP명 안에 포함 (더 긴 키 우선으로 오탐 방지)
    candidates = [(k, v) for k, v in GP_DOMAIN_MAP.items() if len(k) >= 4 and k in name]
    if candidates:
        return max(candidates, key=lambda x: len(x[0]))[1]

    return None


def _try_clearbit(domain: str, client: httpx.Client) -> str | None:
    """Clearbit Logo API HEAD 요청 — 200이면 URL 반환."""
    url = f"https://logo.clearbit.com/{domain}?size=200"
    try:
        resp = client.head(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            return url
    except Exception:
        pass
    return None


def _try_og_image(domain: str, client: httpx.Client) -> str | None:
    """공식 홈페이지에서 og:image 메타태그 추출."""
    attempts = [
        f"https://www.{domain}",
        f"https://{domain}",
        f"http://www.{domain}",
    ]
    for base_url in attempts:
        try:
            resp = client.get(base_url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
            if resp.status_code != 200:
                continue
            m = OG_IMAGE_RE.search(resp.text[:30000])
            if not m:
                continue
            raw = (m.group(1) or m.group(2) or "").strip()
            if not raw:
                continue
            # 상대 URL 보정
            if raw.startswith("//"):
                return f"https:{raw}"
            if raw.startswith("/"):
                parsed = urlparse(str(resp.url))
                return f"{parsed.scheme}://{parsed.netloc}{raw}"
            return raw
        except Exception:
            continue
    return None


def _search_domain_ddg(gp_name: str, client: httpx.Client) -> str | None:
    """DuckDuckGo HTML 검색으로 GP 공식 홈페이지 도메인 자동 발견."""
    query = f"{gp_name} 공식홈페이지"
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    try:
        resp = client.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return None
        matches = DDG_URL_RE.findall(resp.text)
        for raw in matches[:5]:  # 상위 5개 결과만 확인
            raw = raw.strip()
            # "www." 제거 후 첫 번째 경로 세그먼트만 취득
            raw = raw.removeprefix("www.")
            domain = raw.split("/")[0]
            if not domain or "." not in domain:
                continue
            # 포털/뉴스/SNS 도메인 제외
            if any(skip in domain for skip in DDG_SKIP_DOMAINS):
                continue
            logger.debug("  DDG 발견: %s → %s", gp_name, domain)
            return domain
    except Exception:
        pass
    return None


def _safe_blob_name(gp_name: str) -> str:
    """GP명을 Azure Blob 파일명으로 변환 (URL-safe ASCII, 16자 MD5)."""
    return hashlib.md5(gp_name.encode("utf-8")).hexdigest()[:16]


def _upload_image_to_blob(
    blob_service: BlobServiceClient,
    data: bytes,
    blob_name: str,
    content_type: str = "image/png",
) -> str | None:
    """이미지를 Azure Blob에 업로드하고 5년 SAS URL 반환."""
    try:
        account_name = blob_service.account_name
        account_key = blob_service.credential.account_key
        blob_client_obj = blob_service.get_blob_client(container=AZURE_CONTAINER, blob=blob_name)
        blob_client_obj.upload_blob(
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=AZURE_CONTAINER,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(tz=UTC) + timedelta(days=SAS_EXPIRY_DAYS),
        )
        return f"https://{account_name}.blob.core.windows.net/{AZURE_CONTAINER}/{blob_name}?{sas_token}"
    except Exception as e:
        logger.warning("Blob 업로드 실패: %s — %s", blob_name, e)
        return None


def _fetch_logo_url(gp_name: str, client: httpx.Client, search: bool = True) -> tuple[str | None, str]:
    """GP명에 대한 로고 URL과 취득 방법 반환 (내부용)."""
    domain = _find_domain(gp_name)

    # 도메인 매핑 없으면 DuckDuckGo 검색 시도
    if not domain and search:
        time.sleep(DELAY_DDG)
        domain = _search_domain_ddg(gp_name, client)
        if domain:
            url = _try_og_image(domain, client)
            if url:
                return url, "ddg_og_image"
            return None, "ddg_no_image"

    if not domain:
        return None, "no_domain"

    # Clearbit 먼저 시도 (빠름)
    url = _try_clearbit(domain, client)
    if url:
        return url, "clearbit"

    time.sleep(DELAY_BETWEEN)

    # og:image 크롤링
    url = _try_og_image(domain, client)
    if url:
        return url, "og_image"

    return None, "domain_only"  # 도메인은 있지만 로고 URL 못 찾음


def fetch_logo(
    gp_name: str,
    client: httpx.Client,
    blob_service: BlobServiceClient | None = None,
    search: bool = True,
) -> tuple[str | None, str]:
    """GP명에 대한 로고 URL과 취득 방법 반환. blob_service 있으면 Azure Blob에 업로드."""
    url, method = _fetch_logo_url(gp_name, client, search)

    if url and blob_service:
        try:
            img_resp = client.get(url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
            ct = img_resp.headers.get("content-type", "image/png").split(";")[0].strip()
            if img_resp.status_code == 200 and ct.startswith("image/"):
                blob_name = f"{LOGO_BLOB_PREFIX}/{_safe_blob_name(gp_name)}.png"
                blob_url = _upload_image_to_blob(blob_service, img_resp.content, blob_name, ct)
                if blob_url:
                    return blob_url, f"blob_{method}"
        except Exception as e:
            logger.warning("이미지 다운로드 실패: %s — %s", url, e)

    return url, method


def main(dry_run: bool = False, overwrite: bool = False, search: bool = True) -> None:
    if not EXCEL_PATH.exists():
        logger.error("파일 없음: %s", EXCEL_PATH)
        sys.exit(1)

    logger.info("Excel 로드: %s", EXCEL_PATH)
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)  # 쓰기 가능 모드

    try:
        ws = wb[SHEET1_NAME]
    except KeyError:
        logger.error("시트 '%s' 없음. 유효 시트: %s", SHEET1_NAME, wb.sheetnames)
        sys.exit(1)

    # 헤더 확인/추가 (5행 O열)
    header_cell = ws.cell(row=LOGO_HEADER_ROW, column=LOGO_COL)
    if not header_cell.value:
        header_cell.value = "logo_url"
        logger.info("헤더 'logo_url' 추가 (행%d, O열)", LOGO_HEADER_ROW)

    # GP 목록 수집
    gp_rows: list[tuple[int, str, str | None]] = []
    for row in ws.iter_rows(min_row=DATA_START_ROW):
        gp_cell = row[1] if len(row) > 1 else None  # B열 = index 1
        if not gp_cell or not gp_cell.value or not str(gp_cell.value).strip():
            continue
        logo_cell = row[14] if len(row) > 14 else None  # O열 = index 14
        existing = str(logo_cell.value).strip() if logo_cell and logo_cell.value else None
        if existing in ("None", "", "-"):
            existing = None
        gp_rows.append((gp_cell.row, str(gp_cell.value).strip(), existing))

    logger.info("GP %d개 발견", len(gp_rows))

    stats: dict[str, int] = {
        "clearbit": 0,
        "og_image": 0,
        "ddg_og_image": 0,
        "ddg_no_image": 0,
        "no_domain": 0,
        "domain_only": 0,
        "skipped": 0,
    }

    blob_service: BlobServiceClient | None = None
    if AZURE_CONNECTION_STRING and not dry_run:
        blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
        logger.info("Azure Blob Storage 연결 완료 (컨테이너: %s)", AZURE_CONTAINER)
    else:
        logger.warning("AZURE_STORAGE_CONNECTION_STRING 없음 또는 dry_run — Blob 업로드 스킵")

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        for excel_row, gp_name, existing_logo in gp_rows:
            if existing_logo and not overwrite:
                logger.debug("스킵 (이미 존재): %s", gp_name)
                stats["skipped"] += 1
                continue

            logger.info("[행%03d] %s", excel_row, gp_name)
            logo_url, method = fetch_logo(gp_name, client, blob_service=blob_service, search=search)

            if logo_url:
                short = logo_url[:80] + ("…" if len(logo_url) > 80 else "")
                logger.info("  ✓ [%s] %s", method, short)
                if not dry_run:
                    ws.cell(row=excel_row, column=LOGO_COL).value = logo_url
                stats[method] = stats.get(method, 0) + 1
            else:
                logger.info("  ✗ [%s]", method)
                stats[method] = stats.get(method, 0) + 1

            time.sleep(DELAY_BETWEEN)

    if not dry_run:
        wb.save(EXCEL_PATH)
        logger.info("저장 완료: %s", EXCEL_PATH)

    blob_count = sum(v for k, v in stats.items() if k.startswith("blob_"))
    total_found = stats.get("clearbit", 0) + stats.get("og_image", 0) + stats.get("ddg_og_image", 0) + blob_count
    logger.info(
        "완료 — 로고 발견 %d개 (Blob업로드=%d, Clearbit=%d, og:image=%d, DDG+og=%d) | DDG도메인없이=%d | 도메인없음=%d | 스킵=%d",
        total_found,
        blob_count,
        stats.get("clearbit", 0),
        stats.get("og_image", 0),
        stats.get("ddg_og_image", 0),
        stats.get("ddg_no_image", 0),
        stats.get("no_domain", 0),
        stats.get("skipped", 0),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GP 로고 URL 자동 수집")
    parser.add_argument("--dry-run", action="store_true", help="Excel 저장 없이 테스트 실행")
    parser.add_argument("--overwrite", action="store_true", help="기존 logo_url도 덮어씀")
    parser.add_argument("--no-search", action="store_true", help="DuckDuckGo 검색 비활성화 (매핑된 도메인만)")
    args = parser.parse_args()
    main(dry_run=args.dry_run, overwrite=args.overwrite, search=not args.no_search)
