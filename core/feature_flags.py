"""
Feature flags for GovernexPlus.

Flags are read from environment variables at import time.
Default values are appropriate for development; production sets them
explicitly via the deployment config or .env.

Usage:
    from core.feature_flags import flags

    if flags.TEMPLATE_LIBRARY:
        ...
"""

import os


class FeatureFlags:
    """Singleton-style feature flag reader."""

    def _bool(self, name: str, default: bool) -> bool:
        val = os.getenv(name, "").strip().lower()
        if val in ("1", "true", "yes", "on"):
            return True
        if val in ("0", "false", "no", "off"):
            return False
        return default

    @property
    def TEMPLATE_LIBRARY(self) -> bool:
        """
        Enable the Template Library & Guided Deployment feature.
        Default: ON in all environments.
        Set TEMPLATE_LIBRARY=off to disable (e.g. while migrating a large tenant).
        """
        return self._bool("TEMPLATE_LIBRARY", default=True)

    @property
    def TEMPLATE_LIBRARY_COPY_ON_WRITE(self) -> bool:
        """
        Enable copy-on-write resolution in risk engine, request routing,
        and test-plan generation.  Requires TEMPLATE_LIBRARY=on.
        Default: ON.
        """
        return self.TEMPLATE_LIBRARY and self._bool("TEMPLATE_LIBRARY_COW", default=True)

    @property
    def TEMPLATE_LIBRARY_AUTO_ACTIVATE_STARTER(self) -> bool:
        """
        On new tenant creation, auto-activate the minimal starter set
        (default workflows + notification templates).
        Default: ON.
        """
        return self.TEMPLATE_LIBRARY and self._bool("TEMPLATE_LIBRARY_AUTO_ACTIVATE", default=True)


flags = FeatureFlags()
