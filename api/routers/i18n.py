"""
Internationalisation (i18n) API Router

Provides translation data to the frontend so the React app can display
the UI in the user's chosen language without a page refresh penalty.

Public endpoints (no auth required, intentionally):
    GET /i18n/locales          — list of supported locales with metadata
    GET /i18n/{locale}         — full translation dict for a locale
    GET /i18n/{locale}/{key}   — single key lookup (with optional ?fallback=)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from core.i18n import (
    get_all_translations,
    get_supported_locales,
    t as translate_key,
    TranslationService,
)

router = APIRouter(tags=["Internationalisation"])

_VALID_LOCALE_CODES = {loc["code"] for loc in get_supported_locales()}


def _validate_locale(locale: str) -> str:
    """Raise 400 for unsupported locale codes; return normalised value."""
    locale = locale.lower().strip()
    if locale not in _VALID_LOCALE_CODES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported locale '{locale}'. "
                f"Supported: {sorted(_VALID_LOCALE_CODES)}"
            ),
        )
    return locale


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/locales")
def list_locales():
    """
    Return metadata for all supported locales.

    Response example:
        [{"code": "en", "label": "English", "native": "English", "dir": "ltr"},
         {"code": "ar", "label": "Arabic",  "native": "العربية",  "dir": "rtl"}, ...]
    """
    return {"locales": get_supported_locales()}


@router.get("/{locale}")
def get_translations(locale: str):
    """
    Return the complete translation dictionary for *locale*.

    The frontend caches this response at app startup (or on locale switch)
    and stores it in ``window.__TRANSLATIONS__`` for the ``useTranslation``
    hook to consume.

    Falls back to English for any key that is missing in the target locale.
    """
    locale = _validate_locale(locale)
    svc = TranslationService()
    data = svc.get_all_translations(locale)
    locale_meta = next(
        (loc for loc in get_supported_locales() if loc["code"] == locale),
        {"code": locale, "dir": "ltr"},
    )
    return {
        "locale": locale,
        "dir": locale_meta.get("dir", "ltr"),
        "translations": data,
    }


@router.get("/{locale}/{key:path}")
def get_translation_key(
    locale: str,
    key: str,
    fallback: Optional[str] = Query(None, description="Value to return if key is missing"),
):
    """
    Return a single translated string for *key* in *locale*.

    *key* uses dot-notation (e.g. ``common.save``, ``nav.dashboard``).
    If the key is not found, returns *fallback* (if supplied) or the key itself.
    """
    locale = _validate_locale(locale)
    result = translate_key(key, locale=locale)
    # If translation service returned the raw key, use fallback instead
    if result == key and fallback is not None:
        result = fallback
    return {"locale": locale, "key": key, "value": result}
