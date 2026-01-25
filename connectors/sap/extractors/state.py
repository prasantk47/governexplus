# SAP Extractor State Management
# Delta extraction with last-run timestamp persistence

"""
State management for SAP RFC extractors.

Provides:
- Last-run timestamp tracking for delta extraction
- Extraction state persistence (file and database backends)
- Checkpointing for long-running extractions
- State recovery after failures
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from threading import Lock
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ExtractionState:
    """
    State of an extraction run.

    Attributes:
        key: Unique identifier for this extraction
        last_run_timestamp: When extraction last completed successfully
        last_run_date: SAP date of last extraction (YYYYMMDD)
        last_run_time: SAP time of last extraction (HHMMSS)
        records_extracted: Total records in last run
        last_error: Last error message if failed
        consecutive_failures: Number of consecutive failures
        metadata: Additional state metadata
    """
    key: str
    last_run_timestamp: Optional[str] = None
    last_run_date: Optional[str] = None
    last_run_time: Optional[str] = None
    records_extracted: int = 0
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionState":
        return cls(**data)

    def get_last_run_datetime(self) -> Optional[datetime]:
        """Get last run as Python datetime."""
        if self.last_run_timestamp:
            try:
                return datetime.fromisoformat(self.last_run_timestamp)
            except:
                pass
        return None

    def get_sap_date_time(self) -> tuple:
        """Get last run as SAP date/time tuple."""
        return self.last_run_date, self.last_run_time


class StateBackend(ABC):
    """Abstract base class for state persistence backends."""

    @abstractmethod
    def load(self, key: str) -> Optional[ExtractionState]:
        """Load state for a key."""
        pass

    @abstractmethod
    def save(self, state: ExtractionState) -> None:
        """Save state."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete state for a key."""
        pass

    @abstractmethod
    def list_keys(self) -> list:
        """List all state keys."""
        pass


class FileStateBackend(StateBackend):
    """
    File-based state persistence.

    Stores state in a JSON file.
    """

    def __init__(self, state_file: str = "extractor_state.json"):
        """
        Initialize file backend.

        Args:
            state_file: Path to state file
        """
        self.state_file = Path(state_file)
        self._lock = Lock()
        self._ensure_file()

    def _ensure_file(self):
        """Ensure state file exists."""
        if not self.state_file.exists():
            self.state_file.write_text("{}")

    def _read_all(self) -> Dict[str, Dict]:
        """Read all states from file."""
        try:
            return json.loads(self.state_file.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _write_all(self, states: Dict[str, Dict]):
        """Write all states to file."""
        self.state_file.write_text(json.dumps(states, indent=2))

    def load(self, key: str) -> Optional[ExtractionState]:
        """Load state for a key."""
        with self._lock:
            states = self._read_all()
            data = states.get(key)
            if data:
                return ExtractionState.from_dict(data)
            return None

    def save(self, state: ExtractionState) -> None:
        """Save state."""
        with self._lock:
            states = self._read_all()
            states[state.key] = state.to_dict()
            self._write_all(states)

    def delete(self, key: str) -> None:
        """Delete state for a key."""
        with self._lock:
            states = self._read_all()
            if key in states:
                del states[key]
                self._write_all(states)

    def list_keys(self) -> list:
        """List all state keys."""
        return list(self._read_all().keys())


class MemoryStateBackend(StateBackend):
    """
    In-memory state persistence.

    Useful for testing or stateless operation.
    """

    def __init__(self):
        self._states: Dict[str, ExtractionState] = {}
        self._lock = Lock()

    def load(self, key: str) -> Optional[ExtractionState]:
        with self._lock:
            return self._states.get(key)

    def save(self, state: ExtractionState) -> None:
        with self._lock:
            self._states[state.key] = state

    def delete(self, key: str) -> None:
        with self._lock:
            if key in self._states:
                del self._states[key]

    def list_keys(self) -> list:
        return list(self._states.keys())


class ExtractionStateManager:
    """
    Manages extraction state for delta processing.

    Provides high-level methods for tracking extraction progress
    and enabling delta/incremental extraction.
    """

    def __init__(
        self,
        backend: Optional[StateBackend] = None,
        state_file: str = "extractor_state.json"
    ):
        """
        Initialize state manager.

        Args:
            backend: State backend (default: FileStateBackend)
            state_file: State file path (used if backend not provided)
        """
        self.backend = backend or FileStateBackend(state_file)

    def get_last_run(self, key: str) -> Optional[datetime]:
        """
        Get last successful run timestamp.

        Args:
            key: Extraction identifier

        Returns:
            Last run datetime or None if never run
        """
        state = self.backend.load(key)
        if state:
            return state.get_last_run_datetime()
        return None

    def get_delta_window(
        self,
        key: str,
        default_days: int = 7
    ) -> tuple:
        """
        Get delta extraction window.

        Returns SAP date/time boundaries for delta extraction.

        Args:
            key: Extraction identifier
            default_days: Days to look back if no previous run

        Returns:
            Tuple of (from_date, from_time, to_date, to_time) in SAP format
        """
        state = self.backend.load(key)

        now = datetime.utcnow()
        to_date = now.strftime("%Y%m%d")
        to_time = now.strftime("%H%M%S")

        if state and state.last_run_date and state.last_run_time:
            from_date = state.last_run_date
            from_time = state.last_run_time
        else:
            # Default: look back N days
            default_start = now - timedelta(days=default_days)
            from_date = default_start.strftime("%Y%m%d")
            from_time = "000000"

        return from_date, from_time, to_date, to_time

    def record_success(
        self,
        key: str,
        records_extracted: int = 0,
        metadata: Dict[str, Any] = None
    ):
        """
        Record successful extraction.

        Args:
            key: Extraction identifier
            records_extracted: Number of records extracted
            metadata: Optional additional metadata
        """
        now = datetime.utcnow()

        # Load existing state or create new
        state = self.backend.load(key) or ExtractionState(key=key)

        # Update state
        state.last_run_timestamp = now.isoformat()
        state.last_run_date = now.strftime("%Y%m%d")
        state.last_run_time = now.strftime("%H%M%S")
        state.records_extracted = records_extracted
        state.last_error = None
        state.consecutive_failures = 0

        if metadata:
            state.metadata.update(metadata)

        self.backend.save(state)
        logger.info(f"Recorded successful extraction for {key}: {records_extracted} records")

    def record_failure(self, key: str, error: str):
        """
        Record failed extraction.

        Args:
            key: Extraction identifier
            error: Error message
        """
        state = self.backend.load(key) or ExtractionState(key=key)

        state.last_error = error
        state.consecutive_failures += 1

        self.backend.save(state)
        logger.warning(f"Recorded extraction failure for {key}: {error}")

    def should_retry(self, key: str, max_failures: int = 5) -> bool:
        """
        Check if extraction should be retried.

        Args:
            key: Extraction identifier
            max_failures: Maximum consecutive failures allowed

        Returns:
            True if should retry, False if too many failures
        """
        state = self.backend.load(key)
        if not state:
            return True

        return state.consecutive_failures < max_failures

    def reset_state(self, key: str):
        """
        Reset extraction state.

        Args:
            key: Extraction identifier
        """
        self.backend.delete(key)
        logger.info(f"Reset extraction state for {key}")

    def get_state(self, key: str) -> Optional[ExtractionState]:
        """
        Get full extraction state.

        Args:
            key: Extraction identifier

        Returns:
            ExtractionState or None
        """
        return self.backend.load(key)

    def list_extractions(self) -> list:
        """
        List all tracked extractions.

        Returns:
            List of extraction keys
        """
        return self.backend.list_keys()

    def get_all_states(self) -> Dict[str, ExtractionState]:
        """
        Get all extraction states.

        Returns:
            Dictionary of key -> ExtractionState
        """
        return {
            key: self.backend.load(key)
            for key in self.backend.list_keys()
        }


# =============================================================================
# Convenience Functions
# =============================================================================

# Global state manager instance
_state_manager: Optional[ExtractionStateManager] = None


def get_state_manager() -> ExtractionStateManager:
    """Get or create global state manager."""
    global _state_manager
    if _state_manager is None:
        _state_manager = ExtractionStateManager()
    return _state_manager


def set_state_manager(manager: ExtractionStateManager):
    """Set global state manager."""
    global _state_manager
    _state_manager = manager


def get_last_run(key: str) -> Optional[datetime]:
    """Get last successful run timestamp."""
    return get_state_manager().get_last_run(key)


def update_last_run(key: str, records: int = 0):
    """Update last run timestamp after successful extraction."""
    get_state_manager().record_success(key, records)


def get_delta_window(key: str, default_days: int = 7) -> tuple:
    """Get delta extraction window in SAP date/time format."""
    return get_state_manager().get_delta_window(key, default_days)


def record_failure(key: str, error: str):
    """Record extraction failure."""
    get_state_manager().record_failure(key, error)
