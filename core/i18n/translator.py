"""
GovernexPlus Translation Service
Thread-safe singleton that loads locale JSON files and provides dot-notation lookups
with {placeholder} interpolation and English fallback.
"""

import json
import os
import re
import threading
from typing import Any

# ---------------------------------------------------------------------------
# Supported locales metadata
# ---------------------------------------------------------------------------
SUPPORTED_LOCALES: list[dict] = [
    {"code": "en",  "label": "English",             "native": "English",              "dir": "ltr"},
    {"code": "ar",  "label": "Arabic",              "native": "العربية",              "dir": "rtl"},
    {"code": "fr",  "label": "French",              "native": "Français",             "dir": "ltr"},
    {"code": "de",  "label": "German",              "native": "Deutsch",              "dir": "ltr"},
    {"code": "es",  "label": "Spanish",             "native": "Español",              "dir": "ltr"},
    {"code": "pt",  "label": "Portuguese",          "native": "Português",            "dir": "ltr"},
    {"code": "ja",  "label": "Japanese",            "native": "日本語",               "dir": "ltr"},
    {"code": "zh",  "label": "Chinese (Simplified)","native": "中文（简体）",          "dir": "ltr"},
    {"code": "ko",  "label": "Korean",              "native": "한국어",               "dir": "ltr"},
    {"code": "hi",  "label": "Hindi",               "native": "हिन्दी",              "dir": "ltr"},
    {"code": "tr",  "label": "Turkish",             "native": "Türkçe",               "dir": "ltr"},
    {"code": "nl",  "label": "Dutch",               "native": "Nederlands",           "dir": "ltr"},
    {"code": "it",  "label": "Italian",             "native": "Italiano",             "dir": "ltr"},
    {"code": "ru",  "label": "Russian",             "native": "Русский",              "dir": "ltr"},
    {"code": "pl",  "label": "Polish",              "native": "Polski",               "dir": "ltr"},
]

_LOCALE_CODES = {loc["code"] for loc in SUPPORTED_LOCALES}

LOCALES_DIR = os.path.join(os.path.dirname(__file__), "locales")


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _load_file(locale: str) -> dict:
    """Load and parse a locale JSON file. Returns empty dict on failure."""
    path = os.path.join(LOCALES_DIR, f"{locale}.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _resolve_key(data: dict, key: str) -> Any:
    """Resolve a dot-notation key against a nested dict. Returns None if missing."""
    parts = key.split(".")
    node: Any = data
    for part in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _interpolate(text: str, kwargs: dict) -> str:
    """Replace {placeholder} tokens in text with values from kwargs."""
    if not kwargs:
        return text
    for name, value in kwargs.items():
        text = text.replace(f"{{{name}}}", str(value))
    return text


# ---------------------------------------------------------------------------
# TranslationService singleton
# ---------------------------------------------------------------------------

class TranslationService:
    """
    Thread-safe singleton translation service.

    Usage:
        svc = TranslationService()
        svc.translate("common.save", "fr")
        svc.translate("common.page_of", "en", page=2, total=10)
    """

    _instance: "TranslationService | None" = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "TranslationService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._cache: dict[str, dict] = {}
                    instance._cache_lock = threading.RLock()
                    cls._instance = instance
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_translations(self, locale: str) -> dict:
        """Return (cached) translation dict for *locale*."""
        with self._cache_lock:
            if locale not in self._cache:
                self._cache[locale] = _load_file(locale)
            return self._cache[locale]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def translate(self, key: str, locale: str = "en", **kwargs) -> str:
        """
        Resolve *key* (dot-notation) in *locale*.
        Falls back to English when the key is absent in the target locale.
        Applies {placeholder} interpolation using **kwargs.
        """
        if locale not in _LOCALE_CODES:
            locale = "en"

        data = self._get_translations(locale)
        value = _resolve_key(data, key)

        # Fallback to English
        if value is None and locale != "en":
            en_data = self._get_translations("en")
            value = _resolve_key(en_data, key)

        # Last resort: return the key itself
        if not isinstance(value, str):
            value = key

        return _interpolate(value, kwargs)

    def get_all_translations(self, locale: str) -> dict:
        """Return the full translation dict for *locale*."""
        if locale not in _LOCALE_CODES:
            locale = "en"
        return dict(self._get_translations(locale))

    def get_supported_locales(self) -> list[dict]:
        """Return list of supported locale metadata dicts."""
        return list(SUPPORTED_LOCALES)

    def reload(self) -> None:
        """Clear translation cache (e.g. after locale files are updated at runtime)."""
        with self._cache_lock:
            self._cache.clear()


# ---------------------------------------------------------------------------
# Module-level convenience accessor
# ---------------------------------------------------------------------------

def get_translator() -> TranslationService:
    """Return the singleton TranslationService instance."""
    return TranslationService()
