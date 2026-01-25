# SAP RFC Extractor Utilities
# Retry, error handling, and metrics for production reliability

"""
Utility functions for SAP RFC extractors.

Provides:
- Automatic retry with exponential backoff
- Error counting and classification
- Performance metrics (Prometheus-compatible)
- Rate limiting for SAP system protection
- Logging helpers
"""

import time
import logging
from functools import wraps
from typing import Callable, Optional, Dict, Any, Type
from datetime import datetime
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)

# Try to import prometheus_client, make it optional
try:
    from prometheus_client import Summary, Counter, Gauge, Histogram
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False
    logger.info("prometheus_client not installed. Using internal metrics only.")


# =============================================================================
# Internal Metrics Store (fallback when Prometheus not available)
# =============================================================================

class InternalMetrics:
    """Thread-safe internal metrics store."""

    def __init__(self):
        self._lock = Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._summaries: Dict[str, list] = defaultdict(list)
        self._gauges: Dict[str, float] = {}

    def inc_counter(self, name: str, labels: Dict[str, str] = None, value: int = 1):
        """Increment a counter."""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value

    def observe_summary(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a summary observation."""
        key = self._make_key(name, labels)
        with self._lock:
            self._summaries[key].append(value)
            # Keep last 1000 observations
            if len(self._summaries[key]) > 1000:
                self._summaries[key] = self._summaries[key][-1000:]

    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge value."""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value

    def get_counter(self, name: str, labels: Dict[str, str] = None) -> int:
        """Get counter value."""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0)

    def get_summary_stats(self, name: str, labels: Dict[str, str] = None) -> Dict[str, float]:
        """Get summary statistics."""
        key = self._make_key(name, labels)
        values = self._summaries.get(key, [])
        if not values:
            return {"count": 0, "sum": 0, "avg": 0, "min": 0, "max": 0}

        return {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "summaries": {k: self.get_summary_stats(k) for k in self._summaries.keys()},
                "gauges": dict(self._gauges),
            }

    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create metric key from name and labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


# Global internal metrics instance
_internal_metrics = InternalMetrics()


# =============================================================================
# Prometheus Metrics (when available)
# =============================================================================

if HAS_PROMETHEUS:
    # RFC call metrics
    RFC_CALL_DURATION = Histogram(
        "sap_rfc_call_duration_seconds",
        "Duration of SAP RFC calls",
        ["function_name"],
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
    )

    RFC_CALL_ERRORS = Counter(
        "sap_rfc_errors_total",
        "Total SAP RFC errors",
        ["function_name", "error_type"]
    )

    RFC_CALL_RETRIES = Counter(
        "sap_rfc_retries_total",
        "Total SAP RFC retry attempts",
        ["function_name"]
    )

    # Extraction metrics
    EXTRACTION_DURATION = Summary(
        "sap_extraction_duration_seconds",
        "Duration of SAP data extraction",
        ["extractor", "table"]
    )

    EXTRACTION_RECORDS = Counter(
        "sap_extraction_records_total",
        "Total records extracted from SAP",
        ["extractor", "table"]
    )

    # Connection pool metrics
    CONNECTION_POOL_SIZE = Gauge(
        "sap_connection_pool_size",
        "Current SAP connection pool size"
    )

    CONNECTION_POOL_ACTIVE = Gauge(
        "sap_connection_pool_active",
        "Active SAP connections"
    )


# =============================================================================
# Retry Decorator
# =============================================================================

class SAPRetryError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, function_name: str, attempts: int, last_error: Exception):
        self.function_name = function_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Function {function_name} failed after {attempts} attempts. "
            f"Last error: {last_error}"
        )


def retry(
    max_attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        max_delay: Maximum delay cap (seconds)
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback called before each retry

    Usage:
        @retry(max_attempts=3, delay=1)
        def call_sap():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            wait = delay
            last_exception = None

            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    last_exception = e

                    # Record metrics
                    _record_retry_error(func.__name__, e, attempts)

                    if attempts >= max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {attempts} attempts: {e}"
                        )
                        raise SAPRetryError(func.__name__, attempts, e)

                    # Log retry
                    logger.warning(
                        f"Retry {attempts}/{max_attempts} for {func.__name__}: {e}. "
                        f"Waiting {wait:.1f}s..."
                    )

                    # Callback
                    if on_retry:
                        on_retry(func.__name__, attempts, e)

                    # Wait with backoff
                    time.sleep(wait)
                    wait = min(wait * backoff, max_delay)

            # Should not reach here, but just in case
            raise SAPRetryError(func.__name__, attempts, last_exception)

        return wrapper
    return decorator


def _record_retry_error(function_name: str, error: Exception, attempt: int):
    """Record retry error in metrics."""
    error_type = type(error).__name__

    if HAS_PROMETHEUS:
        RFC_CALL_ERRORS.labels(
            function_name=function_name,
            error_type=error_type
        ).inc()
        RFC_CALL_RETRIES.labels(function_name=function_name).inc()

    _internal_metrics.inc_counter(
        "sap_rfc_errors_total",
        {"function_name": function_name, "error_type": error_type}
    )
    _internal_metrics.inc_counter(
        "sap_rfc_retries_total",
        {"function_name": function_name}
    )


# =============================================================================
# Metrics Decorator
# =============================================================================

def metrics(name: str, labels: Optional[Dict[str, str]] = None):
    """
    Decorator to record function duration metrics.

    Args:
        name: Metric name
        labels: Optional static labels

    Usage:
        @metrics("stad_extract_duration")
        def extract_stad():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time

                # Record to Prometheus if available
                if HAS_PROMETHEUS:
                    EXTRACTION_DURATION.labels(
                        extractor=labels.get("extractor", "unknown") if labels else "unknown",
                        table=labels.get("table", "unknown") if labels else "unknown"
                    ).observe(duration)

                # Always record to internal metrics
                _internal_metrics.observe_summary(name, duration, labels)

                logger.debug(f"{func.__name__} completed in {duration:.3f}s")

        return wrapper
    return decorator


def timed(func: Callable) -> Callable:
    """
    Simple timing decorator using function name as metric.

    Usage:
        @timed
        def my_function():
            ...
    """
    return metrics(f"{func.__module__}.{func.__name__}_duration")(func)


# =============================================================================
# Rate Limiter
# =============================================================================

class RateLimiter:
    """
    Token bucket rate limiter for SAP system protection.

    Limits the rate of RFC calls to prevent overwhelming the SAP system.
    """

    def __init__(
        self,
        calls_per_second: float = 10.0,
        burst: int = 20
    ):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum sustained rate
            burst: Maximum burst size
        """
        self.rate = calls_per_second
        self.burst = burst
        self.tokens = burst
        self.last_update = time.time()
        self._lock = Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        """
        Acquire a token, blocking if necessary.

        Args:
            timeout: Maximum time to wait for a token

        Returns:
            True if token acquired, False if timeout
        """
        start_time = time.time()

        while True:
            with self._lock:
                # Replenish tokens
                now = time.time()
                elapsed = now - self.last_update
                self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
                self.last_update = now

                # Try to acquire
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True

            # Check timeout
            if time.time() - start_time >= timeout:
                return False

            # Wait a bit
            time.sleep(0.1)

    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            raise TimeoutError("Rate limiter timeout")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        return False


# Global rate limiter (can be configured)
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> Optional[RateLimiter]:
    """Get the global rate limiter."""
    return _global_rate_limiter


def set_rate_limiter(limiter: RateLimiter):
    """Set the global rate limiter."""
    global _global_rate_limiter
    _global_rate_limiter = limiter


def rate_limited(func: Callable) -> Callable:
    """
    Decorator to apply rate limiting to a function.

    Usage:
        @rate_limited
        def call_sap():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        limiter = get_rate_limiter()
        if limiter:
            with limiter:
                return func(*args, **kwargs)
        return func(*args, **kwargs)

    return wrapper


# =============================================================================
# Error Classification
# =============================================================================

class SAPErrorClassifier:
    """Classify SAP RFC errors for better handling."""

    # Transient errors that should be retried
    TRANSIENT_ERRORS = [
        "COMMUNICATION_FAILURE",
        "SYSTEM_FAILURE",
        "RFC_TIMEOUT",
        "RFC_CONNECTION_CLOSED",
        "BUFFER_OVERFLOW",
    ]

    # Authorization errors
    AUTH_ERRORS = [
        "NO_AUTHORITY",
        "NOT_AUTHORIZED",
        "AUTHORIZATION_FAILURE",
    ]

    # Data errors
    DATA_ERRORS = [
        "TABLE_NOT_FOUND",
        "FIELD_NOT_FOUND",
        "DATA_BUFFER_EXCEEDED",
    ]

    @classmethod
    def classify(cls, error: Exception) -> str:
        """
        Classify an error.

        Returns:
            "transient", "auth", "data", or "unknown"
        """
        error_str = str(error).upper()

        for pattern in cls.TRANSIENT_ERRORS:
            if pattern in error_str:
                return "transient"

        for pattern in cls.AUTH_ERRORS:
            if pattern in error_str:
                return "auth"

        for pattern in cls.DATA_ERRORS:
            if pattern in error_str:
                return "data"

        return "unknown"

    @classmethod
    def is_retryable(cls, error: Exception) -> bool:
        """Check if error is retryable."""
        return cls.classify(error) == "transient"


# =============================================================================
# Metrics Access Functions
# =============================================================================

def get_metrics() -> Dict[str, Any]:
    """
    Get all collected metrics.

    Returns both Prometheus and internal metrics.
    """
    result = {
        "internal": _internal_metrics.get_all_metrics(),
        "prometheus_available": HAS_PROMETHEUS,
    }

    return result


def record_extraction_count(extractor: str, table: str, count: int):
    """Record extraction record count."""
    if HAS_PROMETHEUS:
        EXTRACTION_RECORDS.labels(extractor=extractor, table=table).inc(count)

    _internal_metrics.inc_counter(
        "sap_extraction_records_total",
        {"extractor": extractor, "table": table},
        count
    )


def record_connection_pool_stats(pool_size: int, active: int):
    """Record connection pool statistics."""
    if HAS_PROMETHEUS:
        CONNECTION_POOL_SIZE.set(pool_size)
        CONNECTION_POOL_ACTIVE.set(active)

    _internal_metrics.set_gauge("sap_connection_pool_size", pool_size)
    _internal_metrics.set_gauge("sap_connection_pool_active", active)
