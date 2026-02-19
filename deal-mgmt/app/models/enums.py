import enum


class TransactionSide(str, enum.Enum):
    SELL = "SELL"
    BUY = "BUY"
    DUAL = "DUAL"


class TransactionPhase(str, enum.Enum):
    ENGAGEMENT = "ENGAGEMENT"
    PREPARATION = "PREPARATION"
    MARKETING = "MARKETING"
    BIDDING_DD = "BIDDING_DD"
    NEGOTIATION = "NEGOTIATION"
    CLOSING = "CLOSING"
    POST_CLOSING = "POST_CLOSING"


class TransactionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


class EngagementType(str, enum.Enum):
    EXCLUSIVE = "EXCLUSIVE"
    NON_EXCLUSIVE = "NON_EXCLUSIVE"
    CO_ADVISORY = "CO_ADVISORY"


class WorkingGroupRole(str, enum.Enum):
    LEAD_ADVISOR = "LEAD_ADVISOR"
    LEGAL_COUNSEL = "LEGAL_COUNSEL"
    ACCOUNTING_ADVISOR = "ACCOUNTING_ADVISOR"
    TAX_ADVISOR = "TAX_ADVISOR"
    INDUSTRY_EXPERT = "INDUSTRY_EXPERT"
    VALUATION_ADVISOR = "VALUATION_ADVISOR"
    OTHER = "OTHER"


class BuyerCandidateStatus(str, enum.Enum):
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


class BuyerType(str, enum.Enum):
    STRATEGIC = "STRATEGIC"
    FINANCIAL_SPONSOR = "FINANCIAL_SPONSOR"
    FAMILY_OFFICE = "FAMILY_OFFICE"
    INDIVIDUAL = "INDIVIDUAL"
    OTHER = "OTHER"


# ── Phase 2: NDA ───────────────────────────────────────
class NdaType(str, enum.Enum):
    ONE_WAY = "ONE_WAY"
    MUTUAL = "MUTUAL"


class NdaStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    SIGNED = "SIGNED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


# ── Phase 2: Bid (IOI / LOI / Final Offer) ────────────
class BidType(str, enum.Enum):
    IOI = "IOI"
    LOI = "LOI"
    FINAL_OFFER = "FINAL_OFFER"


class BidStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"


class ValuationMethod(str, enum.Enum):
    EV_EBITDA = "EV_EBITDA"
    EV_REVENUE = "EV_REVENUE"
    PRICE_BOOK = "PRICE_BOOK"
    DCF = "DCF"
    COMPARABLE = "COMPARABLE"
    OTHER = "OTHER"


# ── Phase 2: DD Checklist ──────────────────────────────
class DDWorkstream(str, enum.Enum):
    FINANCIAL = "FINANCIAL"
    LEGAL = "LEGAL"
    TAX = "TAX"
    COMMERCIAL = "COMMERCIAL"
    IT = "IT"
    HR = "HR"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    INSURANCE = "INSURANCE"
    OTHER = "OTHER"


class DDChecklistStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ── Phase 3: Contract / SPA ──────────────────────────
class ContractType(str, enum.Enum):
    SPA = "SPA"
    AMENDMENT = "AMENDMENT"
    SIDE_LETTER = "SIDE_LETTER"
    SHAREHOLDERS_AGREEMENT = "SHAREHOLDERS_AGREEMENT"
    ESCROW_AGREEMENT = "ESCROW_AGREEMENT"
    OTHER = "OTHER"


class ContractStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    UNDER_REVIEW = "UNDER_REVIEW"
    PENDING_SIGNATURE = "PENDING_SIGNATURE"
    PARTIALLY_SIGNED = "PARTIALLY_SIGNED"
    FULLY_EXECUTED = "FULLY_EXECUTED"
    TERMINATED = "TERMINATED"


class SignatureStatus(str, enum.Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    SIGNED = "SIGNED"
    DECLINED = "DECLINED"


class ClosingCategory(str, enum.Enum):
    REGULATORY = "REGULATORY"
    LEGAL = "LEGAL"
    FINANCIAL = "FINANCIAL"
    CORPORATE = "CORPORATE"
    CONDITION_PRECEDENT = "CONDITION_PRECEDENT"
    FUND_FLOW = "FUND_FLOW"
    OTHER = "OTHER"


class ClosingConditionStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    WAIVED = "WAIVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ── Phase 4: PMI ─────────────────────────────────────
class PMICategory(str, enum.Enum):
    INTEGRATION_PLAN = "INTEGRATION_PLAN"
    DAY_ONE = "DAY_ONE"
    FIRST_100_DAYS = "FIRST_100_DAYS"
    SYNERGY = "SYNERGY"
    CULTURE = "CULTURE"
    IT_SYSTEMS = "IT_SYSTEMS"
    HR = "HR"
    COMMUNICATION = "COMMUNICATION"
    OTHER = "OTHER"


class PMITaskStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    DEFERRED = "DEFERRED"


class PMIPriority(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Phase 4: Earnout ─────────────────────────────────
class EarnoutStatus(str, enum.Enum):
    PENDING = "PENDING"
    MEASUREMENT_PERIOD = "MEASUREMENT_PERIOD"
    ACHIEVED = "ACHIEVED"
    PARTIALLY_ACHIEVED = "PARTIALLY_ACHIEVED"
    MISSED = "MISSED"
    DISPUTED = "DISPUTED"


class EarnoutMetric(str, enum.Enum):
    REVENUE = "REVENUE"
    EBITDA = "EBITDA"
    NET_INCOME = "NET_INCOME"
    CUSTOMER_COUNT = "CUSTOMER_COUNT"
    CONTRACT_VALUE = "CONTRACT_VALUE"
    WORKING_CAPITAL = "WORKING_CAPITAL"
    OTHER = "OTHER"


# ── Audit ─────────────────────────────────────────────
class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    PHASE_TRANSITION = "PHASE_TRANSITION"
    STATUS_CHANGE = "STATUS_CHANGE"
    MEMBER_ADDED = "MEMBER_ADDED"
    MEMBER_REMOVED = "MEMBER_REMOVED"
    SERVICE_LINKED = "SERVICE_LINKED"
