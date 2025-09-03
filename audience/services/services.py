from rest_framework.fields import BooleanField
from rest_framework.exceptions import ValidationError
from typing import Any



_BOOL = BooleanField()

def include_contacts(value : Any) -> bool:
    """Robust boolean parsing for query params."""
    if value is None:
        return False
    try:
        return _BOOL.to_internal_value(value)
    except ValidationError:
        return False  # or raise to enforce strictness