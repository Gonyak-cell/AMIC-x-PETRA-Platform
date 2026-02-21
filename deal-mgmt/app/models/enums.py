import enum


class TransactionSide(enum.StrEnum):
    SELL = "SELL"
    BUY = "BUY"
    DUAL = "DUAL"


class TransactionPhase(enum.StrEnum):
    ENGAGEMENT = "ENGAGEMENT"
    PREPARATION = "PREPARATION"
    MARKETING = "MARKETING"
    BIDDING_DD = "BIDDING_DD"
    NEGOTIATION = "NEGOTIATION"
    CLOSING = "CLOSING"
    POST_CLOSING = "POST_CLOSING"


class TransactionStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


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


class BuyerType(enum.StrEnum):
    STRATEGIC = "STRATEGIC"
    FINANCIAL_SPONSOR = "FINANCIAL_SPONSOR"
    FAMILY_OFFICE = "FAMILY_OFFICE"
    INDIVIDUAL = "INDIVIDUAL"
    OTHER = "OTHER"


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
    FINANCIAL = "FINANCIAL"
    LEGAL = "LEGAL"
    TAX = "TAX"
    COMMERCIAL = "COMMERCIAL"
    IT = "IT"
    HR = "HR"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    INSURANCE = "INSURANCE"
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


# ── Audit ─────────────────────────────────────────────
class AuditAction(enum.StrEnum):
    CREATE = "CREATE"
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
