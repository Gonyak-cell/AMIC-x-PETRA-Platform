"""Calculation engines — pure functions only.

Rules:
- NO import from sqlalchemy or app.database
- All functions return tuple[Result, list[EvidenceLinkData]]
- All amounts: Decimal only (NEVER float)
- Every output amount traceable via EvidenceLink
"""
