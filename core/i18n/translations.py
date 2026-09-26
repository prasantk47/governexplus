"""
Internationalization support — English + Arabic (and beyond).

This module provides a flat-key translation dict backed by the same
locale JSON files already used by the TranslationService singleton.
It exposes a simple ContextVar-based locale, a t() convenience
function, and a get_all_translations() bulk export used by the
/i18n/{locale} REST endpoint.
"""

from contextvars import ContextVar
from typing import Dict, Optional

from core.i18n.translator import TranslationService, SUPPORTED_LOCALES

# ---------------------------------------------------------------------------
# ContextVar — one locale per async request context
# ---------------------------------------------------------------------------

_current_locale: ContextVar[str] = ContextVar("locale", default="en")


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def set_locale(locale: str) -> None:
    """Set the locale for the current async context."""
    _current_locale.set(locale)


def get_locale() -> str:
    """Return the locale currently active in this async context."""
    return _current_locale.get()


def t(key: str, locale: Optional[str] = None, **kwargs) -> str:
    """
    Translate *key* (dot-notation) into *locale*.

    Falls back to the ContextVar locale, then to English.
    Supports {placeholder} interpolation via **kwargs.
    """
    loc = locale or get_locale()
    svc = TranslationService()
    return svc.translate(key, loc, **kwargs)


def get_all_translations(locale: Optional[str] = None) -> Dict[str, object]:
    """
    Return the full flat translation dict for *locale*.

    The JSON files use nested objects; this returns them as-is so the
    frontend can navigate with dot-notation at the call site, or the
    caller can flatten if needed.
    """
    loc = locale or get_locale()
    svc = TranslationService()
    return svc.get_all_translations(loc)


def get_supported_locales() -> list:
    """Return metadata list for all supported locales."""
    return list(SUPPORTED_LOCALES)
