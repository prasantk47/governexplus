from .translator import TranslationService, get_translator
from .translations import (
    set_locale,
    get_locale,
    t,
    get_all_translations,
    get_supported_locales,
)

__all__ = [
    "TranslationService",
    "get_translator",
    "set_locale",
    "get_locale",
    "t",
    "get_all_translations",
    "get_supported_locales",
]
