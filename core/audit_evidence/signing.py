"""
Audit Log Tamper Protection
Provides HMAC-SHA256 signing and chain verification for audit log entries.

Usage:
    signer = AuditSigner()
    sig = signer.sign_entry(entry_data)
    valid = signer.verify_entry(entry_data, sig)
"""

import os
import hmac
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple


def get_signing_key() -> bytes:
    """
    Retrieve the signing key for HMAC operations.

    Priority:
    1. AUDIT_SIGNING_KEY environment variable (raw or hex-encoded)
    2. JWT_SECRET environment variable (derive via SHA-256)
    3. Error — at least one must be set in production.
    """
    audit_key = os.getenv("AUDIT_SIGNING_KEY", "")
    if audit_key:
        # Accept raw string; encode to bytes
        return audit_key.encode("utf-8")

    jwt_secret = os.getenv("JWT_SECRET", "")
    if jwt_secret:
        # Derive a separate key for audit signing so it is never the same
        # as the JWT signing key
        derived = hashlib.sha256(
            f"audit-signing-v1:{jwt_secret}".encode("utf-8")
        ).digest()
        return derived

    # Neither key is set — use a deterministic but insecure fallback so the
    # module does not crash during development.  This MUST NOT reach production.
    import warnings
    warnings.warn(
        "Neither AUDIT_SIGNING_KEY nor JWT_SECRET is set. "
        "Audit log signatures are NOT secure. Set AUDIT_SIGNING_KEY in production.",
        RuntimeWarning,
        stacklevel=2,
    )
    return b"insecure-dev-signing-key-replace-in-production"


def _canonical_bytes(entry_data: Any) -> bytes:
    """
    Produce a stable, canonical byte representation of entry_data for signing.
    Dict keys are sorted; datetimes serialised as ISO strings.
    """
    return json.dumps(entry_data, sort_keys=True, default=str).encode("utf-8")


class AuditSigner:
    """
    HMAC-SHA256 signer for individual audit log entries and chains.
    """

    def __init__(self, key: Optional[bytes] = None) -> None:
        self._key: bytes = key if key is not None else get_signing_key()

    # ------------------------------------------------------------------
    # Single-entry operations
    # ------------------------------------------------------------------

    def sign_entry(self, entry_data: Any) -> str:
        """
        Produce an HMAC-SHA256 hex-digest signature for a single audit entry.

        The signature covers the canonical JSON representation of entry_data.
        """
        message = _canonical_bytes(entry_data)
        sig = hmac.new(self._key, message, hashlib.sha256).hexdigest()
        return sig

    def verify_entry(self, entry_data: Any, signature: str) -> bool:
        """
        Verify that signature matches entry_data.

        Returns True if the signature is valid; False otherwise.
        Uses constant-time comparison to prevent timing attacks.
        """
        expected = self.sign_entry(entry_data)
        return hmac.compare_digest(expected, signature)

    # ------------------------------------------------------------------
    # Chain operations
    # ------------------------------------------------------------------

    def sign_batch(
        self, entries: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Sign multiple audit entries using chain hashing.

        Each entry is signed over:
            HMAC(key, canonical(entry) + previous_chain_hash)

        This means any tampering with or reordering of an entry invalidates
        all subsequent signatures in the chain.

        Returns a list of dicts:
            {
                "entry":      <original entry>,
                "signature":  <hex HMAC>,
                "chain_hash": <SHA-256 of this entry's signature>,
                "position":   <0-based index>,
            }
        """
        result: List[Dict[str, Any]] = []
        prev_hash: str = "0" * 64  # genesis hash

        for index, entry in enumerate(entries):
            # Sign over (entry content + previous chain hash)
            combined = _canonical_bytes({"entry": entry, "prev": prev_hash})
            sig = hmac.new(self._key, combined, hashlib.sha256).hexdigest()
            # The chain hash is SHA-256 of the signature, chained forward
            chain_hash = hashlib.sha256(sig.encode("utf-8")).hexdigest()

            result.append({
                "entry": entry,
                "signature": sig,
                "chain_hash": chain_hash,
                "prev_hash": prev_hash,
                "position": index,
            })

            prev_hash = chain_hash

        return result

    def verify_chain(
        self, entries_with_signatures: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Verify the integrity of a signed chain produced by sign_batch().

        Checks that:
        - Each signature is valid for its entry given the previous chain hash.
        - The chain hashes link correctly from position 0 onwards.

        Returns:
            {
                "valid":          bool,
                "total_entries":  int,
                "verified":       int,
                "failed_at":      list of 0-based positions where verification failed,
                "details":        list of per-entry results,
            }
        """
        failed_positions: List[int] = []
        details: List[Dict[str, Any]] = []
        prev_hash: str = "0" * 64
        verified_count = 0

        for item in entries_with_signatures:
            entry = item.get("entry")
            sig = item.get("signature", "")
            stored_prev = item.get("prev_hash", "")
            position = item.get("position", len(details))

            # Recompute signature
            combined = _canonical_bytes({"entry": entry, "prev": prev_hash})
            expected_sig = hmac.new(self._key, combined, hashlib.sha256).hexdigest()

            sig_valid = hmac.compare_digest(expected_sig, sig)
            chain_valid = stored_prev == prev_hash

            entry_ok = sig_valid and chain_valid

            details.append({
                "position": position,
                "valid": entry_ok,
                "signature_valid": sig_valid,
                "chain_link_valid": chain_valid,
            })

            if entry_ok:
                verified_count += 1
                prev_hash = item.get("chain_hash", "")
            else:
                failed_positions.append(position)
                # Still advance prev_hash using the stored chain_hash so we
                # can surface all failures, not just the first one.
                prev_hash = item.get("chain_hash", "")

        total = len(entries_with_signatures)
        return {
            "valid": len(failed_positions) == 0,
            "total_entries": total,
            "verified": verified_count,
            "failed_at": failed_positions,
            "details": details,
        }


# Module-level convenience functions using a shared signer instance
_default_signer: Optional[AuditSigner] = None


def _get_signer() -> AuditSigner:
    global _default_signer
    if _default_signer is None:
        _default_signer = AuditSigner()
    return _default_signer


def sign_entry(entry_data: Any) -> str:
    """Sign a single audit entry. Module-level convenience wrapper."""
    return _get_signer().sign_entry(entry_data)


def verify_entry(entry_data: Any, signature: str) -> bool:
    """Verify a single audit entry signature. Module-level convenience wrapper."""
    return _get_signer().verify_entry(entry_data, signature)


def sign_batch(entries: List[Any]) -> List[Dict[str, Any]]:
    """Sign a batch of entries as a chain. Module-level convenience wrapper."""
    return _get_signer().sign_batch(entries)


def verify_chain(entries_with_signatures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verify a signed chain. Module-level convenience wrapper."""
    return _get_signer().verify_chain(entries_with_signatures)
