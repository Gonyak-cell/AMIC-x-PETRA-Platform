# 국내 사모펀드 운용사 데이터 자동수집을 위한 API·웹사이트 조사 및 클라우드 구현 계획

## Executive Summary

국내 사모펀드 운용사(예: 에이티유파트너스, MBK파트너스, IMM 등)의 **약정총액(Committed Capital)·최근 딜 소싱 내역·포트폴리오·금융제재(행정처분/제재) 내역**을 “코드로 자동 수집”하려면, **단일한 ‘공개(비회원) API’만으로는 목적 달성이 구조적으로 어렵습니다.** 그 이유는 (i) PEF의 약정(커밋)·LP 구성·펀드 조건이 계약/규제/영업비밀로 비공개인 경우가 많고, (ii) 국내 공식 공개 API는 주로 **공시(상장/공시대상 회사) 이벤트** 또는 **집계형 통계** 또는 **모태펀드/벤처펀드 영역**에 집중되어 있기 때문입니다. citeturn26view0turn37view1turn35search0

그럼에도 “자동화” 관점에서 실무적으로 바로 성과를 내는 축은 명확합니다.

공시 기반 딜 신호 자동화: Open DART 오픈API의 `list.json`(공시검색), `majorstock.json`(대량보유), `document.xml`(원문 ZIP) 등을 이용하면 **상장/공시대상 기업에서 발생하는 M&A·지분변동 이벤트를 기계적으로 수집**할 수 있습니다. 특히 `list.json`은 공시유형/상세유형, 기간, 페이지(최대 100건/페이지)를 지원하며, 고유번호(corp_code)가 없을 때 검색기간이 3개월로 제한되는 등 운영상 제약까지 문서에 명시돼 있어 파이프라인 설계가 가능합니다. citeturn26view0

공식 의결문서 기반 제재 자동화: “금융제재”는 단일 제재 API보다, 금융위원회·증권선물위원회가 공개하는 **의결정보 게시판의 의사록/안건/제재안건 의결서(PDF/ZIP)**를 수집·텍스트화·구조화하는 방식이 실무적으로 강합니다(원문 보존과 감사추적이 용이). citeturn22view0turn23view0

약정총액(Committed Capital) 현실적 확보: PEF GP별 약정총액은 공식 공개 API에서 정규필드로 제공되는 사례를 확인하기 어렵고, 대신 (a) 운용사 IR/보도자료 크롤링(펀드 클로징 공지, AUM 서술), (b) 상업 데이터피드/ API(Preqin/PitchBook 등), (c) 벤처 영역에 한해 한국벤처투자 펀드현황 Open API를 결합하는 것이 가장 현실적입니다. citeturn37view3turn32search0turn35search0

결론적으로, 빠른 PoC(2주)는 “공시 기반 딜 신호 + 의결문서 기반 제재/조치 추출 + (가능 범위) 운용사 포트폴리오 웹 수집”까지를 목표로 하고, 상용화(3개월)는 “상업 데이터 계약 + 명칭정규화/엔터티 해소 + 증거보존/감사추적 + 법적 준수 체크리스트 내재화”까지 포함하는 로드맵을 권고합니다. citeturn26view0turn22view0turn32search0turn37view3

## 목차

- 조사 범위와 가정  
- 국내 공식·공신력 데이터 소스 및 API/DB  
- 상업 데이터 제공업체 및 API·데이터피드  
- 운용사 IR/웹사이트 기반 자동수집 가능성  
- 클라우드 구현 설계, 데이터 모델, 개발 로드맵 및 비용·준수·우선순위 권고  

## 조사 범위와 가정

본 보고서는 국내 우선으로, 다음 4개 데이터 범주를 “자동수집 가능성” 기준으로 매핑합니다.

약정총액(Committed Capital): PEF 약정총액을 직접 제공하는 공개 API가 제한적일 가능성이 크므로, (i) 운용사/펀드 클로징 공지에서 추출, (ii) 상업 데이터로 보완, (iii) 벤처펀드(모태펀드 등) 영역에서는 한국벤처투자 API로 일부 자동화 가능한 구조를 가정합니다. citeturn35search0turn37view3turn32search0

딜 소싱 내역: “공시 이벤트(주요사항보고서/대량보유 등)→원문 추출→딜 데이터 레코드화”를 1차 자동화 축으로 두고, 운용사 사이트의 News/Press/Portfolio를 2차 보강 축으로 둡니다. citeturn26view0turn27view1

포트폴리오: 운용사 사이트의 포트폴리오 페이지(HTML/이미지 그리드/ PDF)에서 1차 추출 후, 상장/공시대상 피투자회사인 경우 Open DART 공시로 교차검증하는 방식을 기본으로 둡니다. citeturn26view0turn27view0

제재 내역: 제재/행정처분은 금융위원회·증권선물위원회 의결정보 게시판의 첨부문서(PDF/ZIP) 기반 자동수집을 기본으로 하고, AML/제재리스트 성격의 추가 수집처로 entity["organization","금융정보분석원","korean f iu"] 제재 공지를 병행하는 전략을 제시합니다. citeturn22view0turn23view0turn5search2

인증 자격은 미지정이므로, “비회원/공개 접근 우선”으로 설계하되, 계약형/참가요건형(상업 DB·SEIBro 오픈플랫폼 등)은 옵션으로 분리합니다. citeturn32search0turn35search2turn36search3turn37view3

## 국내 공식·공신력 데이터 소스 및 API/DB

### 공식 소스 맵과 “수집 가능 필드” 현실성

국내에서 “딜·제재”에 직접 연결되는 공개 데이터는 주로 “공시(이벤트)”와 “공식 의결문서(제재안건 포함)”입니다. Open DART는 공시유형/상세유형과 접수번호(rcept_no)를 제공하고, 원문 ZIP을 내려받아 내용 파싱까지 이어지게 설계되어 있습니다. citeturn26view0turn27view1

반면 “약정총액(Committed Capital)”은 PEF에서 표준 공개 필드로 제공되기 어렵기 때문에, 공식 채널에서는 “자산운용사 활동 통계(집계)” 또는 “벤처펀드 현황(모태펀드 등)” 같은 대체지표 레이어를 먼저 자동화하고, PEF 약정총액은 IR/상업 DB로 채우는 조합이 비용 대비 효과가 큽니다. citeturn37view1turn35search0turn37view3

### 공식·공신력 출처별 API/DB 목록 표

아래 표는 “공식/공신력 사이트 > 국내 상업 > 해외 상업” 우선순위 중 “공식/공신력” 영역을 먼저 정리했습니다.

| 출처 | 제공 형태 | 엔드포인트/접근 URL(예시) | 제공 데이터 필드(핵심) | 접근·인증 | 이용제한/쿼터·비용 |
|---|---|---|---|---|---|
| Open DART 오픈API | REST(JSON/XML) + ZIP 원문 | `https://opendart.fss.or.kr/api/list.json` (공시검색) citeturn26view0 | 공시목록: corp_name, corp_code, report_nm, rcept_no, flr_nm 등 citeturn26view0 | 인증키(crtfc_key) 필수 citeturn26view0turn8search8 | page_count 최대 100, corp_code 없으면 검색기간 3개월 제한 citeturn26view0 |
| Open DART 오픈API | REST | `https://opendart.fss.or.kr/api/majorstock.json` (대량보유) citeturn29view0 | 대표보고자(repror), 보유비율(stkrt), 보고사유(report_resn) 등 citeturn29view0 | 인증키 + corp_code 필수 citeturn29view0 | 요청제한 초과(020) 등 에러코드 문서화 citeturn29view0 |
| Open DART 오픈API | REST | `https://opendart.fss.or.kr/api/elestock.json` (임원·주요주주 소유) citeturn30view0 | 보고자, 소유수/비율, 증감 등 citeturn30view0 | 인증키 + corp_code 필수 citeturn30view0 | 요청제한 초과/접근제한 등 에러코드 문서화 citeturn30view0 |
| Open DART 오픈API | ZIP(binary) | `https://opendart.fss.or.kr/api/document.xml` (원문 ZIP) citeturn27view1 | 원문 ZIP(내부 XML/첨부) 다운로드 citeturn27view1 | 인증키 + rcept_no 필수 citeturn27view1 | 요청제한 초과(020) 등 문서화 citeturn27view1 |
| Open DART 오픈API | ZIP(binary) | `https://opendart.fss.or.kr/api/corpCode.xml` (고유번호 마스터) citeturn27view2 | corp_code, corp_name, stock_code, modify_date(최종변경일) citeturn27view2 | 인증키 필수 citeturn27view2 | ZIP(binary) 제공 citeturn27view2 |
| Open DART 오픈API | REST | `https://opendart.fss.or.kr/api/company.json` (회사개황) citeturn27view0 | hm_url(홈페이지), ir_url(IR 홈페이지), 사업자번호 등 citeturn27view0 | 인증키 + corp_code 필수 citeturn27view0 | 키 오류/사용불가 등 메시지 코드 문서화 citeturn27view0 |
| 금융위원회 의결정보(회의결과/의사록/제재안건) | 웹 + PDF/ZIP 첨부 | `https://www.fsc.go.kr/no020101` citeturn22view0 | “안건 및 제재안건 의결서” ZIP/PDF 게시 citeturn22view0 | 공개 접근(다운로드) citeturn22view0 | 파일 파싱 필요(PDF/ZIP) |
| entity["organization","증권선물위원회","korean securities commission"] 의결정보 | 웹 + PDF/ZIP 첨부 | `https://www.fsc.go.kr/no020102` citeturn23view0 | 회의결과/의사록/제재안건 의결서 ZIP/PDF citeturn23view0 | 공개 접근 citeturn23view0 | 자본시장 사건·제재 추출에 유용 |
| entity["organization","공공데이터포털","korea open data portal"] (금융위 제공) 자산운용사 영업활동통계 | REST OpenAPI | (서비스별 Swagger 제공) citeturn37view1turn35search6 | 증권/파생 거래현황, 투자일임 계약·수수료, 재산현황/재산운용 등 citeturn37view1 | data.go.kr 키 방식(서비스별) citeturn37view1 | 개발계정 트래픽 10,000 등(서비스별)·무료 citeturn35search6 |
| 한국벤처투자 펀드현황 Open API | REST | `https://www.kvic.or.kr/api/businessType` / `https://www.kvic.or.kr/api/fundType` citeturn35search0 | 펀드종류코드/명, 펀드현황(연도·분야 등 파라미터) citeturn35search0 | key 파라미터 필요 citeturn35search0 | 오류코드(인증키 오류 등) 문서 기재 citeturn35search0 |
| KOFIA OpenAPI | 오픈API 포털 | `https://openapi.kofia.or.kr/main.jsp` citeturn36search1 | 자본시장 정보 API 제공(세부 목록은 포털 UI) citeturn36search1turn37view0 | 이용신청→심사/등록→활용 안내 citeturn36search1 | 본 조사 환경에서 개별 API 목록/명세가 동적 로딩으로 제한됨(추가 확인 필요) citeturn37view0 |
| SEIBro 오픈플랫폼(예탁원) | 참가요건형 API 포털 | `www.openplatform.seibro.or.kr` (기사 언급) citeturn35search2turn36search3 | 기업/주식/채권/파생결합/외화증권 등 정보 제공(기사) citeturn35search2 | 참가요건/온라인 신청 언급 citeturn36search3 | (당시 기사 기준) 이용료 한시 면제 언급 등. 실제 요금/명세는 등록 후 확정 필요 citeturn35search2 |

### Open DART로 “딜 소싱 내역”을 만드는 실제 접근

Open DART `list.json`은 공시유형(pblntf_ty)과 상세유형(pblntf_detail_ty)을 제공하며, 지분공시(D001: 주식등의대량보유상황보고서) 및 주요사항보고서(B001 등)의 식별이 가능합니다. citeturn26view0  
운용사/펀드의 “직접 공시”가 아니더라도, **피투자회사가 공시대상(상장/기타 공시대상)인 경우**에는 다음의 “딜 신호”를 구성할 수 있습니다.

- 지분 취득/감소 신호: `majorstock.json`의 대표보고자(repror), 보유비율(stkrt), 보고사유(report_resn) citeturn29view0  
- 거래 구조/조건 신호: `document.xml`로 원문 ZIP을 내려받아, 주요사항보고서/대량보유보고서 본문에서 금액·상대방·조건을 파싱 citeturn27view1turn26view0  
- “운용사·펀드·SPC 명칭” 매칭: 공시 제출인명(flr_nm)·대표보고자 등 문자열을 정규화해 운용사 마스터에 연결 citeturn26view0turn29view0  

Open DART API는 요청 제한 초과(020), 접근 불가 IP(012) 등 운영상 에러코드도 문서화되어 있어, 레이트리밋/재시도 정책을 코드로 강제하기 용이합니다. citeturn27view1turn29view0

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["Open DART list.json response example","majorstock.json Open DART 화면","금융위원회 증권선물위원회 의결정보 제재안건 의결서 PDF","SEIBro openplatform.seibro.or.kr 소개"],"num_per_query":1}

### “샘플 호출·예시 응답(JSON)” (가상 샘플, 문서 기반 필드로 구성)

아래 예시는 문서에 기재된 필드/파라미터를 기반으로 한 **가상 샘플 JSON**입니다(실제 응답은 조건/시점에 따라 상이). citeturn26view0turn29view0turn35search0

| 구분 | 내용 |
|---|---|
| Open DART 공시검색(list) 요청 예시 | `GET https://opendart.fss.or.kr/api/list.json?crtfc_key=발급키&bgn_de=20260101&end_de=20260226&pblntf_ty=D&pblntf_detail_ty=D001&page_no=1&page_count=100` citeturn26view0 |
| Open DART 공시검색(list) 예시 응답(가상) | { "status":"000","message":"정상","page_no":1,"page_count":100,"total_count":2,"total_page":1, "list":[ {"corp_cls":"Y","corp_name":"예시상장사A","corp_code":"00126380","stock_code":"123456","report_nm":"주식등의대량보유상황보고서","rcept_no":"20260226001234","flr_nm":"예시투자목적회사(유)"}, {"corp_cls":"K","corp_name":"예시상장사B","corp_code":"00999999","stock_code":"654321","report_nm":"주요사항보고서(타법인 주식 및 출자증권 양수결정)","rcept_no":"20260215004567","flr_nm":"예시PEF투자조합"} ] } citeturn26view0 |
| Open DART 대량보유(majorstock) 요청 예시 | `GET https://opendart.fss.or.kr/api/majorstock.json?crtfc_key=발급키&corp_code=00126380` citeturn29view0 |
| Open DART 대량보유(majorstock) 예시 응답(가상) | { "status":"000","message":"정상","list":[ {"rcept_no":"20260226001234","rcept_dt":"20260226","corp_code":"00126380","corp_name":"예시상장사A","report_tp":"신규","repror":"예시투자목적회사(유)","stkqy":"1000000","stkrt":"7.50","report_resn":"주식취득"} ] } citeturn29view0 |
| 한국벤처투자 펀드종류 조회(businessType) 문서 예시 | `GET https://www.kvic.or.kr/api/businessType?bType=0&of=1&key=<인증키>` (응답필드: fundName, fundCode) citeturn35search0 |

## 상업 데이터 제공업체 및 API·데이터피드

### 국내 상업 데이터(우선)

entity["company","NICE디앤비","credit bureau seoul"]는 국내외 기업정보 Open API 서비스를 제공하며, 브로슈어에서 “국내외 기업정보 API 상품(다수)”과 개발자 지원도구(문서/가이드 등)를 언급합니다. citeturn33search49turn33search48  
또한 해외기업정보 API(D&B Direct+)의 기능 구성을 “MATCH/DATA ENRICH/MONITOR”로 소개하고, 모니터링 결과를 REST(JSON) API로 제공하는 방식 등을 설명합니다. citeturn33search2turn33search1  
이 계열 데이터는 “PEF 약정총액” 자체보다, **포트폴리오 회사의 기업정보·관계도(UBO)·컴플라이언스 스크리닝(제재/PEP/Adverse media 등)** 결합에서 특히 실효성이 큽니다. citeturn33search1turn33search2

(별도 서비스로) 기업정보 API를 표방하는 나이스비즈라인 계열 페이지도 존재합니다. citeturn33search0

### 해외 상업 데이터(별도 섹션)

Preqin은 “Preqin DB를 시스템에 직접 연결”하는 데이터피드를 제공하며, 표준 CSV로 대량 데이터를 필요 빈도에 맞추어 전달하는 방식을 강조합니다. 또한 100개 이상의 피드에서 GPs/LPs/funds/deals/transactions/ESG 등을 포괄한다고 명시합니다. citeturn37view3

PitchBook은 API가 플랫폼과 별도 계약(standalone contract)이고 REST 기반이며, Base URL을 `https://api.pitchbook.com`으로 안내합니다. citeturn32search0

Refinitiv/LSEG 계열(Eikon/Workspace)은 데스크톱 API 문서에서 **EULA가 데이터 재배포를 금지**한다고 명시하고, 재배포가 필요하면 플랫폼 제품을 고려하라고 안내합니다. 또한 “데이터가 데스크톱을 벗어나지 않는 범위”와 그 이상을 구분합니다. citeturn32search2turn32search10

| 업체 | 제공 형태 | 데이터 범위(사모펀드 관점) | 가격대(추정) | 라이선스 핵심 리스크 |
|---|---|---|---|---|
| Preqin | 데이터피드(CSV, 대량) citeturn37view3 | GP/LP/펀드/성과/딜/거래/ESG 등 대체투자 전반 citeturn37view3 | 고가(엔터프라이즈 협상형) | 저장·2차가공·재배포 범위는 계약이 절대적(내부 데이터레이크 허용 범위 명확화 필요) |
| PitchBook | REST API(별도 계약) citeturn32search0 | 딜/투자자/펀드/LP 등(엔드포인트 구성은 계약·문서에 따름) citeturn32search0 | 고가(엔터프라이즈 협상형) | 크롤링 대체 목적이면 계약 범위(필드/호출량/저장)를 선확정 |
| Refinitiv/LSEG | 데스크톱 API/플랫폼 API citeturn32search2turn32search10 | 시장·뉴스·리서치 등(PE/VC 커버는 상품별 상이) | 고가 | EULA 상 재배포 금지/제한 명시(특히 데스크톱 API) citeturn32search2 |

※ 가격대는 “정가 공개가 아니라는 시장 관행”을 전제로 한 **추정 구간**입니다(실제는 사용자 수/권한/데이터 범위/재배포 권리 등에 따라 편차가 큼).

## 운용사 IR/웹사이트 기반 자동수집 가능성

### 현실 체크

운용사 웹/IR은 포트폴리오 페이지가 존재해도 “로고 그리드(이미지)” 형태로 제공되는 경우가 많아, HTML 파싱만으로는 부족하고 이미지의 alt 텍스트/링크 구조를 추가로 분석해야 하는 경우가 많습니다(스캔 PDF와 유사한 난이도). 반면 운용사 사이트의 News/Press는 텍스트 기반인 경우가 많아, “딜 발표/클로징” 이벤트 추출에는 오히려 적합합니다.

금융제재 내역은 운용사 자체 IR에 누적 정리되는 경우가 흔치 않으므로, 공식 의결문서(금융위/증선위) 기반 역추적이 더 신뢰성이 높습니다. citeturn22view0turn23view0

### 주요 운용사 20곳 이상 “초기 타깃 매핑 표”

중요한 제한을 먼저 명시합니다.  
본 조사 환경에서는 일부 국내 사이트 접속 제약이 확인되어, 각 운용사 사이트의 “정확 URL/공시 위치”를 본문에서 모두 확정·인용하기 어려웠습니다. 따라서 아래 표는 **PoC 착수용 타깃 리스트(상위권 PEF/대체투자 운용사 가정)**이며, URL/세부 위치는 프로젝트 착수 시 1~2일 내 “수동 확정(또는 자동 발견 크롤러)”로 보완하는 것을 전제로 합니다. (확정 불가 항목은 ‘확인 필요’로 표기)

| 운용사(예시) | 사이트 URL | 공시/IR/Portfolio 위치(가정) | 데이터 형식(주로) | 크롤링 난이도(추정) | 로그인/인증(추정) | 자동수집 대상(우선순위) |
|---|---|---|---|---|---|---|
| 에이티유파트너스 | 확인 필요 | Portfolio / News | HTML | 중 | 낮음 | 포트폴리오, 딜 뉴스 |
| MBK파트너스 | 확인 필요 | Portfolio / News | HTML | 중~상 | 낮음 | 포트폴리오(로고형 가능) |
| IMM | 확인 필요 | Portfolio / News / AUM | HTML/PDF | 중 | 낮음 | AUM/펀드 언급, 딜 뉴스 |
| 한앤컴퍼니 | 확인 필요 | Portfolio / News | HTML | 중 | 낮음 | 포트폴리오 |
| 스틱인베스트먼트 | 확인 필요 | IR/공시(상장사 IR) | HTML/PDF | 중 | 낮음 | IR 공지 + 포트폴리오 |
| VIG파트너스 | 확인 필요 | Portfolio | HTML | 중 | 낮음 | 포트폴리오 |
| JKL파트너스 | 확인 필요 | Portfolio / News | HTML | 중 | 낮음 | 딜 뉴스 |
| 스카이레이크 | 확인 필요 | Portfolio | HTML | 중 | 낮음 | 포트폴리오 |
| KCGI | 확인 필요 | 공지/IR/포트폴리오 | HTML/PDF | 중 | 낮음 | 공지 기반 이벤트 |
| 큐캐피탈 | 확인 필요 | Portfolio / News | HTML | 중 | 낮음 | 딜 뉴스 |
| UCK파트너스 | 확인 필요 | Portfolio | HTML | 중 | 낮음 | 포트폴리오 |
| 스마일게이트인베스트먼트 | 확인 필요 | Portfolio / News | HTML | 중 | 낮음 | 투자/회수 이벤트 |
| (금융지주/증권사 계열) 미래에셋 대체투자/PE | 확인 필요 | 그룹/계열사 IR 분산 | HTML/PDF | 상 | 중(일부) | AUM/조직/투자사례 |
| KB 계열 대체투자/PE | 확인 필요 | 그룹/계열사 IR 분산 | HTML/PDF | 상 | 중(일부) | AUM/투자사례 |
| 신한 계열 대체투자/PE | 확인 필요 | 그룹/계열사 IR 분산 | HTML/PDF | 상 | 중(일부) | AUM/투자사례 |
| 하나 계열 대체투자/PE | 확인 필요 | 그룹/계열사 IR 분산 | HTML/PDF | 상 | 중(일부) | AUM/투자사례 |
| NH 계열 대체투자/PE | 확인 필요 | 그룹/계열사 IR 분산 | HTML/PDF | 상 | 중(일부) | AUM/투자사례 |
| 한국투자 계열 대체투자/PE | 확인 필요 | 그룹/계열사 IR 분산 | HTML/PDF | 상 | 중(일부) | AUM/투자사례 |
| 삼성 계열 대체투자/PE | 확인 필요 | 그룹/계열사 IR 분산 | HTML/PDF | 상 | 중(일부) | AUM/투자사례 |
| (대형 VC) 주요 VC 1~2곳(벤처펀드 참고) | 확인 필요 | 공지/포트폴리오 | HTML | 중 | 낮음 | 벤처펀드 연계(한국벤처투자 API와 결합) citeturn35search0 |

URL 자동확정(권고): DART 공시대상 법인의 경우 `company.json`에 hm_url/ir_url 필드가 존재하므로, corp_code를 확보하면 홈페이지/IR URL을 자동수집할 수 있습니다. citeturn27view0  
반면, 공시대상이 아닌 운용사(유한회사/합자조합 등)는 이 경로가 막힐 수 있으므로 “검색 기반 시드 + 수동 확정 1회 + 이후 자동 갱신” 전략이 필요합니다.

## 클라우드 구현 설계, 데이터 모델, 개발 로드맵 및 비용·준수·우선순위 권고

### 기술적 설계(클라우드 아키텍처)

권고 아키텍처는 “수집층(Ingestion)–원문보관(Immutable Raw)–추출/정규화(Processing)–서빙(Analytics/API)” 4계층입니다.

수집층  
- API 클라이언트: Open DART, 한국벤처투자 Open API, data.go.kr OpenAPI 등  
- 크롤러: Playwright(Headless)로 운용사 사이트/의결정보 게시판 크롤링  
- 레이트리밋/재시도: Open DART 에러코드(020 요청제한, 012 IP 접근제한 등)를 기준으로 공통 미들웨어 구현 citeturn27view1turn29view0  

원문보관(증거보존)  
- 객체스토리지(S3/GCS/Blob)에 “원문 ZIP/PDF/HTML 스냅샷”을 해시 기반 경로로 저장  
- 메타데이터(수집시각, URL, 해시, 파서버전)를 별도 테이블로 관리(감사추적)

추출/정규화  
- PDF 텍스트/표 추출: pdfplumber(표), PyMuPDF(텍스트), 실패 시 OCR(Tesseract) 순(스캔 PDF 대비)  
- 명칭 정규화: (주) 제거, 공백/특수문자 정리, 영문/국문 병기 처리  
- 엔터티 매칭: rapidfuzz로 유사도 매칭 + 사전(운용사·펀드·SPC 별칭) 혼합

저장/서빙  
- DB: Postgres + JSONB(원문 파싱 결과의 가변 필드 대응)  
- 원문 검색(옵션): OpenSearch/Elastic(문서全文 검색)  
- 대시보드(옵션): BI 도구(메타/딜 타임라인/제재 히트맵)

클라우드 서비스 매핑(예시; 특정 클라우드 종속을 피하는 공통 설계)

| 구성요소 | AWS | GCP | Azure |
|---|---|---|---|
| 스케줄러 | EventBridge Scheduler | Cloud Scheduler | Azure Scheduler/Logic Apps |
| 실행(Runtime) | Lambda(경량) / ECS/Fargate(브라우저) | Cloud Functions(경량) / Cloud Run(브라우저) | Azure Functions / Container Apps |
| 큐/재시도 | SQS | Pub/Sub | Service Bus |
| 원문 저장 | S3 | GCS | Blob Storage |
| DB | RDS(Postgres) | Cloud SQL(Postgres) | Azure Database for PostgreSQL |
| 모니터링 | CloudWatch | Cloud Monitoring | Azure Monitor |
| 비밀관리 | Secrets Manager | Secret Manager | Key Vault |

### 클라우드 코드 개발 계획(구체)

#### PoC (1인, 2주) 권고 범위

목표: “운용사 20개 타깃 중 최소 5개는 포트폴리오/뉴스 자동수집 성공”, “Open DART로 딜 신호 2종 이상 자동 생성”, “금융위/증선위 제재안건 ZIP/PDF 자동 다운로드 및 텍스트 추출”을 정의합니다. citeturn26view0turn22view0turn23view0

작업 항목(권고 순서)  
- Day 1~2: Open DART 인증키 발급/키 관리(약관 동의 및 발급 프로세스 확인) citeturn8search8turn24view0  
- Day 3~5: corpCode 다운로드→회사 마스터 구축→list/majorstock 수집  
- Day 6~8: 금융위/증선위 의결정보 게시판 크롤러 + PDF/ZIP 다운로드 + 텍스트 추출  
- Day 9~12: 운용사 사이트 5개 선정(구조 다양화) 후 Playwright 크롤러/파서 프로토타입  
- Day 13~14: 스키마 정리, 품질지표(완전성/신선도) 대시보드(최소 메트릭) 구성

#### 상용화 (팀, 3개월) 권고 범위

- 데이터 소스 확장(운용사 50~100개), 파서 템플릿화(사이트별 어댑터 패턴)  
- 상업 데이터 도입(Preqin/PitchBook 중 1~2개) 및 라이선스 준수 자동 체크(저장/재배포 범위) citeturn37view3turn32search0  
- 엔터티 매칭 고도화(운용사↔SPC↔펀드↔포트폴리오 연결), 인명/개인정보 마스킹 정책 구현  
- 운영 안정화(레이트리밋, IP 차단 대응, 장애 알림)

### 샘플 코드 스니펫(한국어 주석 포함, 코드블록 미사용)

아래는 “복사/붙여넣기용” 예시이며, 표 형태로 제공하니 실제 사용 시 줄번호/구분열을 제거해 사용하시기 바랍니다.

#### 예시 1: Open DART corpCode ZIP 다운로드 → XML 파싱(기본 구조)

(문서상 corpCode는 ZIP(binary)이며, 리스트에 corp_code/corp_name/stock_code/modify_date가 포함됩니다.) citeturn27view2

| 줄 | 코드 |
|---|---|
| 1 | import io, zipfile |
| 2 | import requests |
| 3 | from xml.etree import ElementTree as ET |
| 4 |  |
| 5 | def fetch_corp_codes(crtfc_key: str) -> list[dict]: |
| 6 |     # Open DART 고유번호(corpCode) ZIP 다운로드 |
| 7 |     url = "https://opendart.fss.or.kr/api/corpCode.xml" |
| 8 |     r = requests.get(url, params={"crtfc_key": crtfc_key}, timeout=60) |
| 9 |     r.raise_for_status() |
|10 |     z = zipfile.ZipFile(io.BytesIO(r.content)) |
|11 |     # ZIP 내부에는 XML 1개가 들어있는 형태가 일반적 |
|12 |     xml_name = [n for n in z.namelist() if n.lower().endswith(".xml")][0] |
|13 |     xml_bytes = z.read(xml_name) |
|14 |     root = ET.fromstring(xml_bytes) |
|15 |     out = [] |
|16 |     for item in root.findall(".//list"): |
|17 |         out.append({ |
|18 |             "corp_code": (item.findtext("corp_code") or "").strip(), |
|19 |             "corp_name": (item.findtext("corp_name") or "").strip(), |
|20 |             "stock_code": (item.findtext("stock_code") or "").strip(), |
|21 |             "modify_date": (item.findtext("modify_date") or "").strip(), |
|22 |         }) |
|23 |     return out |

#### 예시 2: Open DART list.json으로 “지분공시(대량보유)”만 수집(일간 배치)

(문서상 corp_code가 없으면 검색기간 3개월 제한, page_count 최대 100 등) citeturn26view0

| 줄 | 코드 |
|---|---|
| 1 | import requests |
| 2 | from datetime import date, timedelta |
| 3 |  |
| 4 | def fetch_major_disclosures(crtfc_key: str, bgn: date, end: date, page_no: int = 1): |
| 5 |     url = "https://opendart.fss.or.kr/api/list.json" |
| 6 |     params = { |
| 7 |         "crtfc_key": crtfc_key, |
| 8 |         "bgn_de": bgn.strftime("%Y%m%d"), |
| 9 |         "end_de": end.strftime("%Y%m%d"), |
|10 |         "pblntf_ty": "D",        # 지분공시 |
|11 |         "pblntf_detail_ty": "D001",  # 대량보유상황보고서 |
|12 |         "page_no": str(page_no), |
|13 |         "page_count": "100"     # 문서상 최대 100 |
|14 |     } |
|15 |     r = requests.get(url, params=params, timeout=30) |
|16 |     r.raise_for_status() |
|17 |     data = r.json() |
|18 |     if data.get("status") != "000": |
|19 |         # status/message는 문서 키로 응답됨 |
|20 |         raise RuntimeError(f"OpenDART error {data.get('status')}: {data.get('message')}") |
|21 |     return data |

#### 예시 3: “클라우드 함수 핸들러” 형태(예: Lambda/Cloud Function 공통 개념)

| 줄 | 코드 |
|---|---|
| 1 | def handler(event, context): |
| 2 |     # event: 스케줄러가 넘기는 파라미터(예: 조회 기간) |
| 3 |     # context: 런타임 컨텍스트 |
| 4 |     # 실제 배포 시 crtfc_key 등은 Secret Manager/Key Vault에서 로드 |
| 5 |     crtfc_key = load_secret("OPENDART_KEY") |
| 6 |     bgn = parse_date(event.get("bgn")) |
| 7 |     end = parse_date(event.get("end")) |
| 8 |     data = fetch_major_disclosures(crtfc_key, bgn, end) |
| 9 |     # 원문보관: S3/GCS/Blob에 JSON 저장 |
|10 |     put_object("raw/opendart/list/", data) |
|11 |     # 파싱/정규화: 별도 워커(컨테이너)로 큐잉하는 구조 권장 |
|12 |     enqueue("parse-queue", {"type": "opendart_list", "payload_ref": "..."}) |
|13 |     return {"ok": True, "count": data.get("total_count")} |

### 데이터 모델(샘플 스키마) 및 ER 다이어그램(mermaid 텍스트)

아래는 “권장 스키마(초기)”입니다. 실제 상업데이터 도입 여부에 따라 확장합니다.

- fund_manager: 운용사 마스터(국문명/영문명/별칭/웹사이트/정규화키)  
- fund_vehicle: 펀드/조합/SPC(법형/빈티지/전략/약정총액/통화)  
- portfolio_company: 피투자회사(법인명/식별자/국가/산업/상장여부)  
- deal_event: 거래 이벤트(발표일/종결일/유형/가치/출처)  
- sanction_event: 제재 이벤트(기관/일자/제재유형/근거/문서링크/원문해시)  
- source_document: 원문(HTML/PDF/ZIP) 메타(출처URL, 수집시각, 해시, 저장경로, 파서버전)

Mermaid ER 다이어그램(텍스트; 코드블록 없이 제공)

erDiagram
FUND_MANAGER ||--o{ FUND_VEHICLE : manages
FUND_VEHICLE }o--o{ DEAL_EVENT : participates
FUND_VEHICLE }o--o{ PORTFOLIO_COMPANY : holds
FUND_MANAGER ||--o{ SANCTION_EVENT : subject_of
DEAL_EVENT ||--o{ SOURCE_DOCUMENT : evidenced_by
SANCTION_EVENT ||--o{ SOURCE_DOCUMENT : evidenced_by

### 데이터 품질 지표 및 정규화 전략

정확도(Accuracy): 공시/의결문서처럼 공식 원문이 존재하는 데이터는 “원문 기반 필드 추출”로 정확도를 올리고, 추출값 옆에 원문 좌표(페이지/문단/표 위치)를 저장합니다. citeturn22view0turn23view0turn27view1

완전성(Completeness): 포트폴리오/딜은 운용사 사이트만으로 누락 가능성이 높으므로, Open DART 공시 이벤트(대량보유/주요사항보고서)를 보조 채널로 사용해 누락률을 측정합니다. citeturn26view0turn29view0

신선도(Freshness):  
- 공시/의결정보: 일간(영업일 기준) 또는 주간  
- 운용사 IR/Portfolio: 주간~월간(변경 감지 기반)  
- 벤처펀드 현황: 월간 또는 분기(출처 업데이트 주기 맞춤) citeturn35search0

### 기술적·법적 제약 및 합법적 대응

robots.txt/이용약관: 크롤링 대상(운용사 사이트, 의결정보 게시판, 오픈플랫폼 등)은 robots 및 이용약관 준수 여부를 사전 체크하고, “허용되지 않는 대량수집”은 API/계약/허가로 전환해야 합니다.

저작권: 뉴스 기사/리서치 리포트는 무단 저장·재배포 위험이 크므로, “링크+메타데이터(제목/일자/요약 1~2문장)” 수준으로 제한하고, 원문 저장은 최소화합니다(특히 AI 학습 금지 문구가 있는 경우). (본 보고서의 SEIBro 관련 출처도 기사 기반이므로 저장/재배포 주의) citeturn35search2turn36search3

개인정보·명예훼손: 제재문서에서 개인(임직원) 실명이 등장할 수 있으므로, 내부 시스템의 표시/검색에서 개인식별정보 마스킹 정책을 마련하고, 외부 공유 시 법무 검토를 거치도록 설계합니다.

금융규제 리스크: 제재 데이터는 “사실 적시”여도 표현 방식/맥락/최신성에 따라 분쟁 가능성이 있으므로, (i) 문서 원문 링크/해시 보존, (ii) 정정/변경 공지 추적, (iii) ‘진행중/확정’ 상태값을 분리하는 구조가 안전합니다. citeturn22view0turn23view0

기술적 난제와 합법적 우회  
- 동적 로딩: KOFIA OpenAPI 포털처럼 목록이 동적 로딩인 경우, Playwright 기반 렌더링 크롤 또는 “공식 자료(명세서 다운로드)”를 우선 활용해야 합니다. citeturn36search1turn37view0  
- IP 차단/요청 제한: Open DART는 요청 제한(020)·IP 접근 제한(012) 등 에러코드가 문서화되어 있어, 레이트리밋·백오프·키 분리(개인/법인 계정 정책 준수)를 설계합니다. citeturn27view1turn29view0turn8search8  
- PDF 파싱: 표/스캔 이미지 혼재 시 OCR은 비용·오류가 크므로 (1) 텍스트 추출 (2) 표 추출 (3) OCR 순으로 단계화하고, OCR은 실패 케이스에만 제한적으로 적용합니다.

### 비용·시간 추정(표)

아래 비용은 “예산 미지정”을 전제로 한 **추정 범위**이며, 실제는 인건비 단가/상업데이터 계약/트래픽에 따라 크게 달라집니다.

| 구분 | 기간/인력 | 범위(기능) | 클라우드 비용(월) | 상업데이터(월) | 총비용(추정) |
|---|---|---|---|---|---|
| PoC | 1인·2주 | Open DART 딜신호(지분공시/주요사항 일부) + 금융위/증선위 문서 수집 + 운용사 5곳 사이트 수집 | 저가(수만원~수십만원) | 0(미도입) | 인건비 + 소액 인프라 |
| 상용화(기본) | 4~5인·3개월 | 운용사 50+ 확장, 파서 템플릿화, 품질지표/모니터링, 증거보존 | 중가(수십~수백만원) | 선택(국내 기업정보 API 등) | 인건비 + 중간 인프라 + 계약형 데이터 |
| 상용화(고급) | 6~8인·3개월 | Preqin/PitchBook 등 1~2개 도입, 엔터티 매칭 고도화, 검색/대시보드, 컴플라이언스(마스킹/감사) | 중~고가 | 고가(엔터프라이즈 협상) citeturn37view3turn32search0 | 인건비 + 고급 인프라 + 고가 데이터 |

### 우선순위 권고

빠르게 시작할 수 있는 소스(공개·공식 우선)

Open DART 오픈API: 딜 신호/지분 변동/원문 확보까지 일관된 파이프라인이 가능하고, 운영 제약(3개월 제한, page_count 최대, 에러코드)이 문서화되어 있습니다. citeturn26view0turn27view1turn29view0

금융위원회·증권선물위원회 의결정보 게시판: 제재안건 의결서 ZIP/PDF를 공식 문서로 확보할 수 있어 “제재 내역” 자동수집의 증거 기반이 됩니다. citeturn22view0turn23view0

한국벤처투자 펀드현황 Open API: PEF 전체는 아니지만, 벤처/모태펀드 영역에서는 “펀드현황”을 API로 제공하므로 약정에 준하는 지표 자동화의 발판이 됩니다. citeturn35search0

장기적으로 확보할 가치가 큰 소스(상업 데이터 포함)

Preqin 데이터피드: GP/펀드/딜 정규화 레이어를 대체투자 전반으로 제공한다는 점에서 “약정총액/펀드 이력” 공백을 메우는 효과가 큽니다. citeturn37view3

PitchBook API: REST API 기반으로 내부 CRM/데이터레이크에 엔터티 연계를 구축하기 좋고, 딜/펀드/LP 등 엔터티형 데이터 연동에 강점이 있습니다. citeturn32search0

SEIBro 오픈플랫폼: 참가요건형이지만, 증권정보·비상장 유통추정 등 기사에서 언급되는 범위가 넓어, 포트폴리오(증권화/비상장 포함)补完 채널로 장기 검토 가치가 있습니다. citeturn35search2turn36search3