"""Email preference Pydantic schemas — Phase 5."""

from pydantic import BaseModel


class EmailPreferenceRead(BaseModel):
    deal_updates: bool
    watchlist_alerts: bool
    im_completion: bool
    weekly_digest: bool

    model_config = {"from_attributes": True}


class EmailPreferenceUpdate(BaseModel):
    deal_updates: bool
    watchlist_alerts: bool
    im_completion: bool
    weekly_digest: bool
