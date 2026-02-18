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


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    PHASE_TRANSITION = "PHASE_TRANSITION"
    STATUS_CHANGE = "STATUS_CHANGE"
    MEMBER_ADDED = "MEMBER_ADDED"
    MEMBER_REMOVED = "MEMBER_REMOVED"
    SERVICE_LINKED = "SERVICE_LINKED"
