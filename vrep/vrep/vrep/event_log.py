"""
VREP Epistemic Event Log with Hash Chain
Implements tamper-evident event logging per VREP Specification 1.2.0-draft
"""

import hashlib
import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Tuple, List, Optional, Dict, Any
from vrep import VERSION_METADATA


# ---------- Event ID Generator ----------
class EventIDGenerator:
    """Generates unique event IDs with optional prefix."""
    _counter: int = 0

    @classmethod
    def generate(cls, prefix: str = "EVT") -> str:
        """Generate a unique event ID."""
        cls._counter += 1
        return f"{prefix}-{cls._counter:06d}"

    @classmethod
    def reset(cls) -> None:
        """Reset counter (for testing)."""
        cls._counter = 0


# ---------- Standard Exceptions ----------
class HashMismatchError(Exception):
    """Raised when event hash does not match recomputed hash."""
    pass


class PreviousHashMismatchError(Exception):
    """Raised when previous hash does not match chain."""
    pass


class ChainBrokenError(Exception):
    """Raised when hash chain integrity is violated."""
    pass


class DuplicateEventIDError(Exception):
    """Raised when event_id is already used in the log."""
    pass


@dataclass(frozen=True)
class EpistemicEvent:
    """Immutable event record."""
    event_id: str
    timestamp: str
    actor: str
    authority: str
    event_type: str
    evidence_id: str
    description: str
    previous_state: Optional[str]
    new_state: Optional[str]
    trigger: Optional[str]
    preconditions_met: Tuple[str, ...]
    postconditions_fulfilled: Tuple[str, ...]
    change_log_reference: Optional[str]
    event_hash: str
    previous_hash: str
    hash_algorithm: str
    implementation_version: str
    specification_version: str
    schema_version: str
    implementation_name: str


class EpistemicEventLog:
    """
    VREP Epistemic Event Log with cryptographic hash chain.
    Implements tamper-evident audit trail.
    """

    def __init__(self):
        self._events: List[EpistemicEvent] = []
        self._last_event_hash = "0" * 64
        self._event_ids: set = set()

    def _compute_event_hash(self, event_data: dict, previous_hash: str) -> str:
        """
        Compute SHA-256 hash of event data + previous hash.
        Note: This uses a simplified canonical JSON (sort_keys, separators).
        Full RFC 8785 canonicalization is planned for Production Profile.
        """
        canonical = json.dumps(
            event_data,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":")
        )
        chain_data = canonical + previous_hash
        return hashlib.sha256(chain_data.encode('utf-8')).hexdigest()

    def _validate_event_id(self, event_id: str) -> None:
        """Raise DuplicateEventIDError if event_id already exists."""
        if event_id in self._event_ids:
            raise DuplicateEventIDError(f"Event ID '{event_id}' already exists in the log.")

    def record_event(
        self,
        event_id: Optional[str],
        actor: str,
        authority: str,
        event_type: str,
        evidence_id: str,
        description: str,
        previous_state: Optional[str] = None,
        new_state: Optional[str] = None,
        trigger: Optional[str] = None,
        preconditions_met: Optional[List[str]] = None,
        postconditions_fulfilled: Optional[List[str]] = None,
        change_log_reference: Optional[str] = None,
        transition_validator: Optional[callable] = None
    ) -> EpistemicEvent:
        """
        Record an immutable event with automatic hash chain computation.
        If event_id is not provided, one will be generated automatically.
        """
        # Generate event_id if not provided
        if event_id is None:
            event_id = EventIDGenerator.generate()

        # Validate event ID uniqueness
        self._validate_event_id(event_id)

        # Optional transition validation if validator provided
        if transition_validator and previous_state and new_state:
            transition_validator(previous_state, new_state, authority)

        timestamp = datetime.now(timezone.utc).isoformat()

        event_data = {
            "event_id": event_id,
            "timestamp": timestamp,
            "actor": actor,
            "authority": authority,
            "event_type": event_type,
            "evidence_id": evidence_id,
            "description": description,
            "previous_state": previous_state,
            "new_state": new_state,
            "trigger": trigger,
            "preconditions_met": tuple(preconditions_met or []),
            "postconditions_fulfilled": tuple(postconditions_fulfilled or []),
            "change_log_reference": change_log_reference,
            **VERSION_METADATA
        }

        # Compute hash chain
        event_hash = self._compute_event_hash(event_data, self._last_event_hash)

        # Create immutable event
        event = EpistemicEvent(
            **event_data,
            event_hash=event_hash,
            previous_hash=self._last_event_hash,
            hash_algorithm="SHA-256"
        )

        # Store event
        self._events.append(event)
        self._event_ids.add(event_id)
        self._last_event_hash = event_hash

        return event

    def get_events(self) -> Tuple[EpistemicEvent, ...]:
        """Return immutable tuple of events."""
        return tuple(self._events)

    def get_event_count(self) -> int:
        """Return total number of events."""
        return len(self._events)

    def get_last_hash(self) -> str:
        """Return current last hash in the chain."""
        return self._last_event_hash

    def verify_chain_integrity(self) -> bool:
        """
        Verify hash chain integrity.
        Raises detailed exceptions on failure.
        """
        if not self._events:
            return True

        temp_prev = "0" * 64

        for event in self._events:
            # Verify previous hash matches chain
            if event.previous_hash != temp_prev:
                raise PreviousHashMismatchError(
                    f"Event {event.event_id}: expected previous_hash '{temp_prev}', "
                    f"got '{event.previous_hash}'"
                )

            # Rebuild event data for hash recomputation
            event_data = {
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "actor": event.actor,
                "authority": event.authority,
                "event_type": event.event_type,
                "evidence_id": event.evidence_id,
                "description": event.description,
                "previous_state": event.previous_state,
                "new_state": event.new_state,
                "trigger": event.trigger,
                "preconditions_met": event.preconditions_met,
                "postconditions_fulfilled": event.postconditions_fulfilled,
                "change_log_reference": event.change_log_reference,
                "implementation_version": event.implementation_version,
                "specification_version": event.specification_version,
                "schema_version": event.schema_version,
                "implementation_name": event.implementation_name
            }

            recomputed = self._compute_event_hash(event_data, temp_prev)

            # Verify event hash matches recomputed
            if recomputed != event.event_hash:
                raise HashMismatchError(
                    f"Event {event.event_id}: hash mismatch. "
                    f"Expected '{recomputed}', got '{event.event_hash}'"
                )

            # Update for next iteration
            temp_prev = event.event_hash

        return True

    def verify_chain_integrity_silent(self) -> bool:
        """Silent version for CTS compatibility."""
        try:
            return self.verify_chain_integrity()
        except (HashMismatchError, PreviousHashMismatchError, ChainBrokenError):
            return False

    def to_json(self) -> str:
        """Export Event Log as JSON (for archival)."""
        events_data = []
        for e in self._events:
            events_data.append({
                "event_id": e.event_id,
                "timestamp": e.timestamp,
                "actor": e.actor,
                "authority": e.authority,
                "event_type": e.event_type,
                "evidence_id": e.evidence_id,
                "description": e.description,
                "previous_state": e.previous_state,
                "new_state": e.new_state,
                "trigger": e.trigger,
                "preconditions_met": list(e.preconditions_met),
                "postconditions_fulfilled": list(e.postconditions_fulfilled),
                "change_log_reference": e.change_log_reference,
                "event_hash": e.event_hash,
                "previous_hash": e.previous_hash,
                "hash_algorithm": e.hash_algorithm,
                "implementation_version": e.implementation_version,
                "specification_version": e.specification_version,
                "schema_version": e.schema_version,
                "implementation_name": e.implementation_name
            })
        return json.dumps({
            "version": "1.0",
            "last_hash": self._last_event_hash,
            "event_count": len(self._events),
            "events": events_data
        }, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "EpistemicEventLog":
        """Import Event Log from JSON (planned for v0.3)."""
        raise NotImplementedError("Import from JSON will be available in v0.3")
