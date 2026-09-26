/**
 * useTranslation — lightweight i18n hook for Governex+
 *
 * The hook reads from ``window.__TRANSLATIONS__`` which is populated at app
 * startup by ``initTranslations()`` (called once in main.tsx / App.tsx after
 * the app mounts).
 *
 * Locale is persisted in localStorage so it survives page reloads.
 * Changing locale triggers a full page reload so every component picks up
 * the new language without needing React context / provider complexity.
 *
 * RTL support: switching to ``ar`` sets ``document.documentElement.dir = "rtl"``
 * which activates the ``[dir="rtl"]`` CSS rules defined in index.css.
 */

import { useCallback } from 'react';

// ─── Constants ───────────────────────────────────────────────────────────────

const LOCALE_KEY = 'governex_locale';

/** Locales that flow right-to-left. */
const RTL_LOCALES = new Set(['ar', 'he', 'fa', 'ur']);

/** Base URL of the backend API (matches vite proxy config). */
const API_BASE =
  (import.meta as any).env?.VITE_API_URL || '';

// ─── Initialisation (called once at app startup) ──────────────────────────

/**
 * Fetch translation data from the backend and cache it on ``window``.
 * Must be awaited before the first render that needs translations.
 *
 * @param locale - BCP-47 language code, e.g. ``"en"`` or ``"ar"``
 */
export async function initTranslations(locale?: string): Promise<void> {
  const loc = locale || localStorage.getItem(LOCALE_KEY) || 'en';

  // Apply direction immediately so there is no flash of wrong-direction text
  const isRTL = RTL_LOCALES.has(loc);
  document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
  document.documentElement.lang = loc;

  try {
    const response = await fetch(`${API_BASE}/i18n/${loc}`);
    if (!response.ok) {
      return;
    }
    const data: { locale: string; dir: string; translations: Record<string, unknown> } =
      await response.json();

    // Flatten nested JSON translation objects into dot-notation keys
    // so the hook can do a simple flat-map lookup.
    (window as any).__TRANSLATIONS__ = _flatten(data.translations || {});
    (window as any).__LOCALE__ = data.locale;
    (window as any).__LOCALE_DIR__ = data.dir || (isRTL ? 'rtl' : 'ltr');
  } catch {
    // silently fall back to key-name mode when translation API is unreachable
  }
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export interface UseTranslationReturn {
  /** Translate a dot-notation key, with optional fallback string. */
  t: (key: string, fallback?: string) => string;
  /** Active locale code, e.g. ``"en"`` or ``"ar"``. */
  locale: string;
  /** True when the active locale is right-to-left. */
  isRTL: boolean;
  /**
   * Switch the UI language.  Persists the choice and reloads the page so
   * the new locale is applied cleanly throughout the app.
   */
  setLocale: (newLocale: string) => void;
}

export function useTranslation(): UseTranslationReturn {
  const locale = (window as any).__LOCALE__ || localStorage.getItem(LOCALE_KEY) || 'en';
  const isRTL = RTL_LOCALES.has(locale);

  const t = useCallback(
    (key: string, fallback?: string): string => {
      const translations: Record<string, string> = (window as any).__TRANSLATIONS__ || {};
      return translations[key] ?? fallback ?? key;
    },
    // The translations object is set once on page load; no reactive deps needed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const setLocale = useCallback((newLocale: string): void => {
    localStorage.setItem(LOCALE_KEY, newLocale);
    document.documentElement.dir = RTL_LOCALES.has(newLocale) ? 'rtl' : 'ltr';
    document.documentElement.lang = newLocale;
    // Full reload so every component and CSS variable picks up the new locale
    window.location.reload();
  }, []);

  return { t, locale, isRTL, setLocale };
}

// ─── Utility: flatten nested translation object ───────────────────────────

function _flatten(
  obj: Record<string, unknown>,
  prefix = '',
  result: Record<string, string> = {},
): Record<string, string> {
  for (const [key, value] of Object.entries(obj)) {
    const dotKey = prefix ? `${prefix}.${key}` : key;
    if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
      _flatten(value as Record<string, unknown>, dotKey, result);
    } else {
      result[dotKey] = String(value ?? '');
    }
  }
  return result;
}
