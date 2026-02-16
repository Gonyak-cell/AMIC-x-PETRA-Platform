"""Template Service Package."""

from app.services.template.template_service import (
    create_template,
    delete_template,
    detect_slots_from_pptx,
    get_template,
    get_template_by_template_id,
    list_templates,
    update_template,
    validate_template_contract,
    validate_template_file,
)

__all__ = [
    "create_template",
    "delete_template",
    "detect_slots_from_pptx",
    "get_template",
    "get_template_by_template_id",
    "list_templates",
    "update_template",
    "validate_template_contract",
    "validate_template_file",
]
