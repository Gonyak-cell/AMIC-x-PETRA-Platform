import enum


class DealType(enum.StrEnum):
    """거래 유형 — 코드명 접두사 기준."""

    MA = "MA"  # M&A (인수합병)
    PE = "PE"  # Private Equity
    RE = "RE"  # Real Estate
    IB = "IB"  # Investment Banking


class TransactionSide(enum.StrEnum):
    SELL = "SELL"
    BUY = "BUY"
    DUAL = "DUAL"


class TransactionPhase(enum.StrEnum):
    ENGAGEMENT = "ENGAGEMENT"
    PREPARATION = "PREPARATION"
    MARKETING = "MARKETING"
    BIDDING = "BIDDING"
    MOU_SIGNED = "MOU_SIGNED"  # deprecated: 마일스톤으로 전환, PG enum 제거 불가하여 유지
    MAIN_DUE_DILIGENCE = "MAIN_DUE_DILIGENCE"
    NEGOTIATION = "NEGOTIATION"
    CLOSING = "CLOSING"
    POST_CLOSING = "POST_CLOSING"


class TransactionStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


class DealStructure(enum.StrEnum):
    """MA Pipeline 거래 구조 — 6개 분류."""

    SHARE_ACQUISITION = "SHARE_ACQUISITION"
    ASSET_ACQUISITION = "ASSET_ACQUISITION"
    MERGER = "MERGER"
    CORPORATE_SPLIT = "CORPORATE_SPLIT"
    MBO = "MBO"
    OTHER = "OTHER"


class EngagementType(enum.StrEnum):
    EXCLUSIVE = "EXCLUSIVE"
    NON_EXCLUSIVE = "NON_EXCLUSIVE"
    CO_ADVISORY = "CO_ADVISORY"


class WorkingGroupRole(enum.StrEnum):
    LEAD_ADVISOR = "LEAD_ADVISOR"
    LEGAL_COUNSEL = "LEGAL_COUNSEL"
    ACCOUNTING_ADVISOR = "ACCOUNTING_ADVISOR"
    TAX_ADVISOR = "TAX_ADVISOR"
    INDUSTRY_EXPERT = "INDUSTRY_EXPERT"
    VALUATION_ADVISOR = "VALUATION_ADVISOR"
    OTHER = "OTHER"


class BuyerCandidateStatus(enum.StrEnum):
    IDENTIFIED = "IDENTIFIED"
    CONTACTED = "CONTACTED"
    NDA_SENT = "NDA_SENT"
    NDA_SIGNED = "NDA_SIGNED"
    CIM_SENT = "CIM_SENT"
    INTEREST_CONFIRMED = "INTEREST_CONFIRMED"
    IOI_RECEIVED = "IOI_RECEIVED"
    IOI_ACCEPTED = "IOI_ACCEPTED"
    DD_GRANTED = "DD_GRANTED"
    DD_IN_PROGRESS = "DD_IN_PROGRESS"
    LOI_RECEIVED = "LOI_RECEIVED"
    LOI_ACCEPTED = "LOI_ACCEPTED"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"
    BID_SUBMITTED = "BID_SUBMITTED"
    BID_NOT_SUBMITTED = "BID_NOT_SUBMITTED"
    BID_DROPPED = "BID_DROPPED"


class BuyerType(enum.StrEnum):
    STRATEGIC = "STRATEGIC"
    FINANCIAL_SPONSOR = "FINANCIAL_SPONSOR"
    FAMILY_OFFICE = "FAMILY_OFFICE"
    INDIVIDUAL = "INDIVIDUAL"
    OTHER = "OTHER"


class BuyerTier(enum.StrEnum):
    """Long-List Tier 분류 — 사용자 수동 지정."""

    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    NOT_TARGET = "NOT_TARGET"


class DealRole(enum.StrEnum):
    """매수자 딜 역할 — 컨소시엄 구조 분류."""

    SOLE_BUYER = "SOLE_BUYER"
    CONSORTIUM_LEAD = "CONSORTIUM_LEAD"
    CO_INVESTOR = "CO_INVESTOR"
    FINANCING_PROVIDER = "FINANCING_PROVIDER"


class ConsortiumStatus(enum.StrEnum):
    """컨소시엄 참여 상태."""

    TAPPING = "TAPPING"
    CONFIRMED = "CONFIRMED"
    DROPPED = "DROPPED"


class MarketingStage(enum.StrEnum):
    """Short-List 마케팅 활동 6단계."""

    IDENTIFIED = "IDENTIFIED"  # 식별
    EMAIL_SENT = "EMAIL_SENT"  # 메일전송
    PHONE_CALL = "PHONE_CALL"  # 전화
    ADVISOR_MEETING = "ADVISOR_MEETING"  # 자문사 미팅
    NDA_SIGNED = "NDA_SIGNED"  # NDA 체결
    TARGET_MEETING = "TARGET_MEETING"  # 대상회사 미팅


# ── Phase 2: NDA ───────────────────────────────────────
class NdaType(enum.StrEnum):
    ONE_WAY = "ONE_WAY"
    MUTUAL = "MUTUAL"


class NdaStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    SIGNED = "SIGNED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


# ── Phase 2: Bid (IOI / LOI / Final Offer) ────────────
class BidType(enum.StrEnum):
    IOI = "IOI"
    LOI = "LOI"
    FINAL_OFFER = "FINAL_OFFER"


class BidStatus(enum.StrEnum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


class ValuationMethod(enum.StrEnum):
    EV_EBITDA = "EV_EBITDA"
    EV_REVENUE = "EV_REVENUE"
    PRICE_BOOK = "PRICE_BOOK"
    DCF = "DCF"
    COMPARABLE = "COMPARABLE"
    OTHER = "OTHER"


# ── Phase 2: DD Checklist ──────────────────────────────
class DDWorkstream(enum.StrEnum):
    # FDD (재무실사)
    FDD_FINANCIAL_STATEMENTS = "FDD_FINANCIAL_STATEMENTS"
    FDD_REVENUE = "FDD_REVENUE"
    FDD_WORKING_CAPITAL = "FDD_WORKING_CAPITAL"
    FDD_DEBT_CASH = "FDD_DEBT_CASH"
    FDD_PROJECTIONS = "FDD_PROJECTIONS"
    # LDD (법률실사)
    LDD_CORPORATE = "LDD_CORPORATE"
    LDD_PERMITS = "LDD_PERMITS"
    LDD_CONTRACTS = "LDD_CONTRACTS"
    LDD_ASSETS = "LDD_ASSETS"
    LDD_LABOR = "LDD_LABOR"
    LDD_LITIGATION = "LDD_LITIGATION"
    LDD_IP = "LDD_IP"
    LDD_INSURANCE = "LDD_INSURANCE"
    LDD_ENVIRONMENT = "LDD_ENVIRONMENT"
    # TDD (세무실사)
    TDD_CORPORATE_TAX = "TDD_CORPORATE_TAX"
    TDD_VAT = "TDD_VAT"
    TDD_TRANSFER_PRICING = "TDD_TRANSFER_PRICING"
    TDD_WITHHOLDING = "TDD_WITHHOLDING"
    TDD_TAX_INCENTIVES = "TDD_TAX_INCENTIVES"
    # 기타
    OTHER = "OTHER"


class DDChecklistStatus(enum.StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ── Phase 3: Contract / SPA ──────────────────────────
class ContractType(enum.StrEnum):
    SPA = "SPA"
    AMENDMENT = "AMENDMENT"
    SIDE_LETTER = "SIDE_LETTER"
    SHAREHOLDERS_AGREEMENT = "SHAREHOLDERS_AGREEMENT"
    ESCROW_AGREEMENT = "ESCROW_AGREEMENT"
    BTA = "BTA"  # Business Transfer Agreement (영업양수도계약)
    SSA = "SSA"  # Share Subscription Agreement (신주인수계약)
    OTHER = "OTHER"


class ContractStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    PENDING_SIGNATURE = "PENDING_SIGNATURE"
    PARTIALLY_SIGNED = "PARTIALLY_SIGNED"
    FULLY_EXECUTED = "FULLY_EXECUTED"
    TERMINATED = "TERMINATED"


class SignatureStatus(enum.StrEnum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    SIGNED = "SIGNED"
    DECLINED = "DECLINED"


class ClosingCategory(enum.StrEnum):
    REGULATORY = "REGULATORY"
    LEGAL = "LEGAL"
    FINANCIAL = "FINANCIAL"
    CORPORATE = "CORPORATE"
    CONDITION_PRECEDENT = "CONDITION_PRECEDENT"
    FUND_FLOW = "FUND_FLOW"
    OTHER = "OTHER"


class ClosingConditionStatus(enum.StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    WAIVED = "WAIVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ── Phase 4: PMI ─────────────────────────────────────
class PMICategory(enum.StrEnum):
    INTEGRATION_PLAN = "INTEGRATION_PLAN"
    DAY_ONE = "DAY_ONE"
    FIRST_100_DAYS = "FIRST_100_DAYS"
    SYNERGY = "SYNERGY"
    CULTURE = "CULTURE"
    IT_SYSTEMS = "IT_SYSTEMS"
    HR = "HR"
    COMMUNICATION = "COMMUNICATION"
    OTHER = "OTHER"


class PMITaskStatus(enum.StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"


class PMIPriority(enum.StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Phase 4: Earnout ─────────────────────────────────
class EarnoutStatus(enum.StrEnum):
    PENDING = "PENDING"
    MEASUREMENT_PERIOD = "MEASUREMENT_PERIOD"
    ACHIEVED = "ACHIEVED"
    PARTIALLY_ACHIEVED = "PARTIALLY_ACHIEVED"
    MISSED = "MISSED"
    DISPUTED = "DISPUTED"


class EarnoutMetric(enum.StrEnum):
    REVENUE = "REVENUE"
    EBITDA = "EBITDA"
    NET_INCOME = "NET_INCOME"
    CUSTOMER_COUNT = "CUSTOMER_COUNT"
    CONTRACT_VALUE = "CONTRACT_VALUE"
    WORKING_CAPITAL = "WORKING_CAPITAL"
    OTHER = "OTHER"


# ── Phase 5A: Notes ──────────────────────────────────
class NoteType(enum.StrEnum):
    COMMENT = "COMMENT"
    DECISION = "DECISION"
    QUESTION = "QUESTION"
    ACTION_ITEM = "ACTION_ITEM"


# ── Phase 5A: Approval ──────────────────────────────
class ApprovalType(enum.StrEnum):
    PHASE_ADVANCE = "PHASE_ADVANCE"
    STATUS_CHANGE = "STATUS_CHANGE"
    CONTRACT_SIGN = "CONTRACT_SIGN"
    DEAL_TERMS = "DEAL_TERMS"


class ApprovalStatus(enum.StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# ── Phase 5B: Risk ─────────────────────────────────────
class RiskCategory(enum.StrEnum):
    REGULATORY = "REGULATORY"
    FINANCIAL = "FINANCIAL"
    LEGAL = "LEGAL"
    OPERATIONAL = "OPERATIONAL"
    REPUTATIONAL = "REPUTATIONAL"
    TAX = "TAX"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    MARKET = "MARKET"
    OTHER = "OTHER"


class RiskSeverity(enum.StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskLikelihood(enum.StrEnum):
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


class RiskStatus(enum.StrEnum):
    IDENTIFIED = "IDENTIFIED"
    ASSESSING = "ASSESSING"
    MITIGATING = "MITIGATING"
    MITIGATED = "MITIGATED"
    ACCEPTED = "ACCEPTED"
    CLOSED = "CLOSED"


# ── Phase 5B: Compliance ──────────────────────────────
class ComplianceCategory(enum.StrEnum):
    ANTITRUST = "ANTITRUST"
    FOREIGN_INVESTMENT = "FOREIGN_INVESTMENT"
    SECURITIES = "SECURITIES"
    DATA_PRIVACY = "DATA_PRIVACY"
    ANTI_CORRUPTION = "ANTI_CORRUPTION"
    SANCTIONS = "SANCTIONS"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    LABOR = "LABOR"
    TAX = "TAX"
    PERMITS = "PERMITS"
    OTHER = "OTHER"


class ComplianceStatus(enum.StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_REVIEW = "IN_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    FLAGGED = "FLAGGED"
    NON_COMPLIANT = "NON_COMPLIANT"
    WAIVED = "WAIVED"


# ── Phase 6: Legal Documents ──────────────────────────
class LegalDocType(enum.StrEnum):
    SPA = "SPA"  # 주식매매계약
    SHA = "SHA"  # 주주간계약
    BTA = "BTA"  # 영업양수도계약
    SSA = "SSA"  # 신주인수계약
    MOU = "MOU"  # 양해각서


class LegalDocStatus(enum.StrEnum):
    DRAFT = "DRAFT"  # 파라미터 저장 완료, 렌더링 전
    GENERATING = "GENERATING"  # docxtpl 렌더링 중
    READY = "READY"  # 다운로드 가능
    FAILED = "FAILED"  # 렌더링 실패


# ── Marketing Materials (TM / DM / IM) ───────────────
class MarketingDocType(enum.StrEnum):
    TM = "TM"  # Teaser Memorandum — 매수자 접촉 전 익명 요약 PPTX
    DM = "DM"  # Discussion Memo — 논의 사항 정리 PPTX (단계 무관)
    IM = "IM"  # Information Memorandum — NDA 후 상세 투자 안내 PPTX


class MarketingDocStatus(enum.StrEnum):
    DRAFT = "DRAFT"  # 파라미터 저장 완료, 생성 전
    GENERATING = "GENERATING"  # PPTX 렌더링 중
    READY = "READY"  # 다운로드 가능
    FAILED = "FAILED"  # 생성 실패


# ── Phase 7: LDD (Legal Due Diligence) Reports ────────
class LDDDealType(enum.StrEnum):
    """LDD 보고서 거래유형 — 템플릿 선택 기준."""

    STOCK_ACQUISITION = "STOCK_ACQUISITION"  # 주식인수
    REAL_ESTATE = "REAL_ESTATE"  # 부동산
    IPO = "IPO"  # IPO (기업공개)
    CORPORATE_SPLIT = "CORPORATE_SPLIT"  # 회사분할
    PREFERRED_STOCK = "PREFERRED_STOCK"  # 종류주식투자
    ASSET_ACQUISITION = "ASSET_ACQUISITION"  # 사업양수도


class LDDReportStatus(enum.StrEnum):
    DRAFT = "DRAFT"  # 파라미터 저장 완료, 렌더링 전
    ANALYZING = "ANALYZING"  # Ralph Loop #1: VDR 기반 AI 초안 분석 중
    REVIEW = "REVIEW"  # 사용자 체크리스트 리뷰 대기
    FINALIZING = "FINALIZING"  # Ralph Loop #2: 사용자 피드백 반영 최종 Refine 중
    GENERATING = "GENERATING"  # docxtpl 렌더링 중
    READY = "READY"  # 다운로드 가능
    FAILED = "FAILED"  # 렌더링 실패


class LDDReportType(enum.StrEnum):
    FULL = "FULL"  # 정식 전체 LDD 보고서 (10개 섹션)
    REDFLAG = "REDFLAG"  # Redflag DD — Executive Summary + Red/Amber 이슈만
    LAW_FIRM = "LAW_FIRM"  # 법무법인 표준 양식 (I~VIII 대목차, 3단 서술, A/B/C/D 라벨링)


class LDDItemStatus(enum.StrEnum):
    OK = "OK"  # 이슈 없음
    ISSUE = "ISSUE"  # 이슈 발견
    NA = "NA"  # 해당 없음
    PENDING = "PENDING"  # 미검토 (추후 확인 필요)


class LDDIssueLevel(enum.StrEnum):
    CRITICAL = "CRITICAL"  # 거래 중단/재구조화 필요 → Red
    HIGH = "HIGH"  # 가격/조건 조정 필요 → Amber
    MEDIUM = "MEDIUM"  # 진술보장/계약 반영 → Amber
    LOW = "LOW"  # 경미, 모니터링 → Green


class LDDSectionType(enum.StrEnum):
    GOVERNANCE = "GOVERNANCE"  # 기업 일반 및 지배구조
    CAPITAL = "CAPITAL"  # 자본구조 및 주주협약
    CONTRACTS = "CONTRACTS"  # 주요 계약
    LITIGATION = "LITIGATION"  # 소송 및 분쟁
    LABOR = "LABOR"  # 인사 및 노무
    IP = "IP"  # 지식재산권
    REAL_ESTATE = "REAL_ESTATE"  # 부동산 및 환경
    PERMITS = "PERMITS"  # 인허가 및 규제
    TAX = "TAX"  # 조세
    DATA_IT = "DATA_IT"  # 개인정보 및 IT


# ── Audit ─────────────────────────────────────────────
class AuditAction(enum.StrEnum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    PHASE_TRANSITION = "PHASE_TRANSITION"
    STATUS_CHANGE = "STATUS_CHANGE"
    MEMBER_ADDED = "MEMBER_ADDED"
    MEMBER_REMOVED = "MEMBER_REMOVED"
    SERVICE_LINKED = "SERVICE_LINKED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_DECIDED = "APPROVAL_DECIDED"
    NOTE_CREATED = "NOTE_CREATED"
    CLIENT_ASSIGNED = "CLIENT_ASSIGNED"
    CLIENT_REMOVED = "CLIENT_REMOVED"


# ── VDR (Virtual Data Room) ──────────────────────────
class VdrFolderCategory(enum.StrEnum):
    """M&A VDR 기본 폴더 카테고리."""

    CORPORATE = "CORPORATE"  # 기업 일반 (정관, 등기부 등)
    FINANCIAL = "FINANCIAL"  # 재무 자료
    LEGAL = "LEGAL"  # 법률 자료
    TAX = "TAX"  # 세무 자료
    HR = "HR"  # 인사/노무
    TECHNICAL = "TECHNICAL"  # 기술/IT
    COMMERCIAL = "COMMERCIAL"  # 영업/마케팅
    REAL_ESTATE = "REAL_ESTATE"  # 부동산/자산
    ENVIRONMENT = "ENVIRONMENT"  # 환경
    IP = "IP"  # 지식재산권
    INSURANCE = "INSURANCE"  # 보험
    MARKET_RESEARCH = "MARKET_RESEARCH"  # 시장자료
    CUSTOM = "CUSTOM"  # 사용자 생성 폴더


class VdrDocumentStatus(enum.StrEnum):
    """VDR 문서 상태."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class VdrClassificationStatus(enum.StrEnum):
    """VDR 문서 자동 분류 상태."""

    DIRECT = "DIRECT"  # 1차 심사(메타데이터)로 확정 (Early Exit)
    PENDING_REVIEW = "PENDING_REVIEW"  # 2차 심사(본문 LLM) 대기 중
    CLASSIFIED = "CLASSIFIED"  # 2차 심사 완료 → 재분류됨
    MANUAL_REVIEW = "MANUAL_REVIEW"  # 2차 심사 실패 → 수동 확인 필요
    MANUAL = "MANUAL"  # 사용자가 폴더를 직접 지정


# ── Meeting Logs (마케팅/협상 미팅 로그) ────────────────
class MeetingPhase(enum.StrEnum):
    MARKETING = "MARKETING"
    NEGOTIATION = "NEGOTIATION"


class MeetingChannel(enum.StrEnum):
    IN_PERSON = "IN_PERSON"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    VIDEO = "VIDEO"
    HYBRID = "HYBRID"


class MeetingStatus(enum.StrEnum):
    SCHEDULED = "SCHEDULED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    POSTPONED = "POSTPONED"


class AttendeeRole(enum.StrEnum):
    SELLER_ADVISOR = "SELLER_ADVISOR"
    BUYER_ADVISOR = "BUYER_ADVISOR"
    LEGAL_COUNSEL = "LEGAL_COUNSEL"
    CLIENT_REPRESENTATIVE = "CLIENT_REPRESENTATIVE"
    COUNTERPARTY = "COUNTERPARTY"
    OBSERVER = "OBSERVER"
    OTHER = "OTHER"


class ActionItemStatus(enum.StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# 마케팅 전용
class BuyerReaction(enum.StrEnum):
    VERY_POSITIVE = "VERY_POSITIVE"
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"
    VERY_NEGATIVE = "VERY_NEGATIVE"


class ConditionMatchLevel(enum.StrEnum):
    FULL_MATCH = "FULL_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISMATCH = "MISMATCH"
    NOT_ASSESSED = "NOT_ASSESSED"


# 협상 전용 — 의사결정 상태
class IssueDecisionStatus(enum.StrEnum):
    PENDING = "PENDING"  # 미결정 (gray)
    CONSIDER_ACCEPTING = "CONSIDER_ACCEPTING"  # 수용 검토 (yellow/green)
    CANNOT_ACCEPT = "CANNOT_ACCEPT"  # 수용 불가 (red)


class NegotiationIssueStatus(enum.StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    AGREED = "AGREED"
    DEFERRED = "DEFERRED"
    DEADLOCKED = "DEADLOCKED"


class NegotiationIssuePriority(enum.StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Permit Analysis (인허가 분석) ────────────────────────
class PermitFilingType(enum.StrEnum):
    """신고/허가 유형."""

    CHANGE_NOTIFICATION = "CHANGE_NOTIFICATION"  # 변경신고
    CHANGE_APPROVAL = "CHANGE_APPROVAL"  # 변경허가
    NEW_REGISTRATION = "NEW_REGISTRATION"  # 신규등록/허가
    RENEWAL = "RENEWAL"  # 갱신


class PermitTimingType(enum.StrEnum):
    """사전/사후 신고 구분."""

    PRE_FILING = "PRE_FILING"  # 사전신고 (거래 전)
    POST_FILING = "POST_FILING"  # 사후신고 (거래 후)
    BOTH = "BOTH"  # 사전+사후 (단계별)


class TranscriptionJobStatus(enum.StrEnum):
    """녹음 변환 작업 상태."""

    PENDING = "PENDING"
    TRANSCRIBING = "TRANSCRIBING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    APPROVED = "APPROVED"
    FAILED = "FAILED"


class PermitAnalysisStatus(enum.StrEnum):
    """인허가 분석 상태."""

    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    MANUALLY_REVIEWED = "MANUALLY_REVIEWED"


class PermitRequirementStatus(enum.StrEnum):
    """개별 인허가 요건 처리 상태."""

    IDENTIFIED = "IDENTIFIED"
    DOCUMENTS_PREPARING = "DOCUMENTS_PREPARING"
    FILED = "FILED"
    APPROVED = "APPROVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ── Financial Model (재무모델) ─────────────────────────
class FinancialModelType(enum.StrEnum):
    DCF = "DCF"  # Discounted Cash Flow
    LBO = "LBO"  # Leveraged Buyout
    COMPS = "COMPS"  # Trading Multiples (GPCM)
    TRANSACTION_COMPS = "TRANSACTION_COMPS"  # Transaction Multiples (GTM)
    PROJECTION = "PROJECTION"  # Business Projection / FS Model
    FULL = "FULL"  # Full Valuation (DCF + Comps + Sensitivity)


class FinancialModelStatus(enum.StrEnum):
    DRAFT = "DRAFT"  # 파라미터 저장 완료, 생성 전
    GENERATING = "GENERATING"  # Ralph Loop Pass 1: 초안 생성 중
    PENDING_REVIEW = "PENDING_REVIEW"  # 체크리스트 리뷰 대기
    FINALIZING = "FINALIZING"  # Ralph Loop Pass 2: 최종 생성 중
    READY = "READY"  # 다운로드 가능
    FAILED = "FAILED"  # 생성 실패


class FMChecklistStatus(enum.StrEnum):
    GENERATING = "GENERATING"  # Reserved — DB enum 호환용, 서비스에서 미사용 (즉시 PENDING_REVIEW)
    PENDING_REVIEW = "PENDING_REVIEW"  # 사용자 리뷰 대기
    REVIEWED = "REVIEWED"  # Reserved — DB enum 호환용, 서비스에서 미사용 (PENDING_REVIEW → FINALIZED 직접 전환)
    FINALIZED = "FINALIZED"  # 확정 → 최종 Excel 생성 트리거


class FMChecklistItemStatus(enum.StrEnum):
    AUTO_GENERATED = "AUTO_GENERATED"  # 자동 추출 (미리뷰)
    CONFIRMED = "CONFIRMED"  # 사용자 확인
    CORRECTED = "CORRECTED"  # 사용자 수정
    FLAGGED = "FLAGGED"  # 이슈 플래그
    NOT_APPLICABLE = "NOT_APPLICABLE"  # 해당 없음


class FMChecklistCategory(enum.StrEnum):
    # Revenue & Growth
    REVENUE_FORECAST = "REVENUE_FORECAST"
    GROWTH_ASSUMPTIONS = "GROWTH_ASSUMPTIONS"
    VOLUME_PRICE_MIX = "VOLUME_PRICE_MIX"
    # Cost Structure
    COGS_FORECAST = "COGS_FORECAST"
    SGA_FORECAST = "SGA_FORECAST"
    DEPRECIATION_AMORT = "DEPRECIATION_AMORT"
    CAPEX_FORECAST = "CAPEX_FORECAST"
    # Working Capital & Cash Flow
    NWC_ASSUMPTIONS = "NWC_ASSUMPTIONS"
    FCF_DERIVATION = "FCF_DERIVATION"
    # Capital Structure & WACC
    FM_DEBT_SCHEDULE = "FM_DEBT_SCHEDULE"
    WACC_COMPONENTS = "WACC_COMPONENTS"
    TAX_RATE = "TAX_RATE"
    # Valuation
    DCF_PARAMETERS = "DCF_PARAMETERS"
    TRADING_MULTIPLES = "TRADING_MULTIPLES"
    TRANSACTION_MULTIPLES = "TRANSACTION_MULTIPLES"
    # Scenarios & Sensitivity
    BASE_SCENARIO = "BASE_SCENARIO"
    UPSIDE_SCENARIO = "UPSIDE_SCENARIO"
    DOWNSIDE_SCENARIO = "DOWNSIDE_SCENARIO"
    SENSITIVITY_MATRIX = "SENSITIVITY_MATRIX"


class FMChecklistSeverity(enum.StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


# ── RFI V2 (Request for Information — 질의 원장 + 스레드 이력) ──


class RFIItemStatusV2(enum.StrEnum):
    OPEN = "OPEN"
    ANSWERED = "ANSWERED"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"
    CLOSED = "CLOSED"


class RFICategoryV2(enum.StrEnum):
    FINANCIAL = "FINANCIAL"
    LEGAL = "LEGAL"
    OPERATIONAL = "OPERATIONAL"
    COMMERCIAL = "COMMERCIAL"
    HR = "HR"
    IT = "IT"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    INSURANCE = "INSURANCE"
    IP = "IP"
    REAL_ESTATE = "REAL_ESTATE"
    VALUATION = "VALUATION"
    CORPORATE = "CORPORATE"
    TAX = "TAX"
    OTHER = "OTHER"


class RFIPriority(enum.StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RFIAuthorRole(enum.StrEnum):
    ADVISOR = "ADVISOR"
    TARGET = "TARGET"


# ── Document Extraction (AI 문서 분류/추출) ──────────────


class DocExtractionCategory(enum.StrEnum):
    """업로드 문서 AI 분류 카테고리."""

    NDA = "NDA"  # 비밀유지계약서
    LOI_MOU = "LOI_MOU"  # LOI, MOU, IOI
    SPA_BTA = "SPA_BTA"  # SPA, SHA, BTA, SSA
    CORPORATE_DOCS = "CORPORATE_DOCS"  # 등기부등본, 사업자등록증 (레거시 — 두 종류 혼합)
    REGISTRY_DOCS = "REGISTRY_DOCS"  # 법인등기부등본
    BIZ_REG_DOCS = "BIZ_REG_DOCS"  # 사업자등록증
    TAX_FILING = "TAX_FILING"  # 세무신고서, 법인세 신고서
    TEASER_IM = "TEASER_IM"  # Teaser, IM, CIM (향후 확장)
    DD_REPORT = "DD_REPORT"  # FDD/LDD/TDD 보고서 (향후 확장)
    RFI_RESPONSE = "RFI_RESPONSE"  # RFI 답변서 (향후 확장)
    REFERENCE_ONLY = "REFERENCE_ONLY"  # 기타 참고용 (추출 불필요)


class AttachmentEntityType(enum.StrEnum):
    """범용 첨부파일 대상 엔티티 타입."""

    MARKETING_MATERIAL = "MARKETING_MATERIAL"
    FINANCIAL_MODEL = "FINANCIAL_MODEL"
    NDA = "NDA"
    BID = "BID"
    DD_CHECKLIST = "DD_CHECKLIST"
    CONTRACT = "CONTRACT"
    CLOSING = "CLOSING"
    PMI = "PMI"
    EARNOUT = "EARNOUT"
    MARKETING_LOG = "MARKETING_LOG"
    MILESTONE = "MILESTONE"  # 마일스톤 문서 (Executed MOU, SPA 등)


# ── SI Mapping ────────────────────────────────────────
class SICompanyRelation(enum.StrEnum):
    """SI 기업과 타겟 기업 간의 산업 관계 유형."""

    DIRECT = "DIRECT"  # 동일 KSIC (동종업계)
    BACKWARD = "BACKWARD"  # 공급자 (후방연관)
    FORWARD = "FORWARD"  # 수요자 (전방연관)


class ExtractionStatus(enum.StrEnum):
    """문서 AI 추출 작업 상태."""

    PENDING = "PENDING"  # 대기
    CLASSIFYING = "CLASSIFYING"  # 분류 중
    EXTRACTING = "EXTRACTING"  # 데이터 추출 중
    COMPLETED = "COMPLETED"  # 추출 완료 (사용자 검토 대기)
    FAILED = "FAILED"  # 실패
    CONFIRMED = "CONFIRMED"  # 사용자 검토 확정


class TableStyleTheme(enum.StrEnum):
    """플랫폼 전역 테이블 스타일 테마."""

    DEFAULT = "DEFAULT"  # AMIC Forest 스타일
    MODERN_GREEN = "MODERN_GREEN"  # 연녹색 헤더 (#65A765), 점선 구분


# ── Contract Template (계약서 템플릿 자동 생성) ───────────


class TemplateVariableInputType(enum.StrEnum):
    """템플릿 변수 입력 유형."""

    TEXT = "TEXT"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    DATE = "DATE"
    SELECT = "SELECT"
    BOOLEAN = "BOOLEAN"
    CURRENCY = "CURRENCY"
    PERCENTAGE = "PERCENTAGE"


class ContractTemplateStatus(enum.StrEnum):
    """계약서 템플릿 상태."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
