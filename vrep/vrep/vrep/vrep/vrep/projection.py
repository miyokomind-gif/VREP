"""
VREP State Projection (Event Sourcing)
Derives current state by replaying events from the Event Log
per VREP Specification 1.2.0-draft

Design Note: This implements INV-05 (Deterministic Projection).
The Event Log is the Single Source of Truth (INV-01).
State projections are disposable artifacts. They MAY be recomputed at any time
from the Event Log and SHALL NOT be treated as authoritative storage.
"""

from typing import Tuple, List, Dict, Any, Optional
from vrep.event_log import EpistemicEvent
from vrep.state_machine import EvidenceState, UnknownStateError


class EvidenceStateProjection:
    """
    Projection of an evidence's state derived from Event Log replay.

    This is a read-only projection. State is never stored here,
    only computed from the event sequence.
    """

    def __init__(self, evidence_id: str):
        """
        Initialize projection for a specific evidence ID.

        Args:
            evidence_id: The evidence ID to project.
        """
        self.evidence_id = evidence_id
        self.current_state: EvidenceState = EvidenceState.UNINITIALIZED
        self.history: List[Dict[str, Any]] = []

    def replay(self, events: Tuple[EpistemicEvent, ...]) -> None:
        """
        Replay events to build the current state projection.

        This method processes all events in chronological order.
        It is deterministic: same events + same order = same state.

        IMPORTANT: The caller MUST provide events in chronological order.
        If events are not ordered, the projection will be non-deterministic.
        No internal sorting is performed to preserve performance and
        to make the caller explicitly responsible for order.

        Args:
            events: Tuple of EpistemicEvent objects (from Event Log).

        Raises:
            UnknownStateError: If an event contains an unknown state value.
        """
        # Reset projection
        self.current_state = EvidenceState.UNINITIALIZED
        self.history.clear()

        # Process only events matching this evidence_id
        for event in events:
            if event.evidence_id == self.evidence_id:
                # Update state if new_state is provided
                if event.new_state:
                    try:
                        self.current_state = EvidenceState(event.new_state)
                    except ValueError:
                        # Raise explicit error for unknown states
                        raise UnknownStateError(
                            f"Event {event.event_id} references unknown state '{event.new_state}'. "
                            f"Expected one of: {[s.value for s in EvidenceState]}"
                        )

                # Record history entry
                self.history.append({
                    "timestamp": event.timestamp,
                    "actor": event.actor,
                    "authority": event.authority,
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                    "from_state": event.previous_state,
                    "to_state": event.new_state,
                    "description": event.description,
                    "event_hash": event.event_hash,
                    "previous_hash": event.previous_hash,
                    "hash_algorithm": event.hash_algorithm
                })

    def get_current_state(self) -> EvidenceState:
        """Get the current projected state."""
        return self.current_state

    def get_history(self) -> List[Dict[str, Any]]:
        """Get the full transition history for this evidence."""
        return self.history.copy()

    def get_last_state_change(self) -> Optional[Dict[str, Any]]:
        """Get the last state change event (if any)."""
        if self.history:
            return self.history[-1]
        return None

    def is_in_state(self, state: EvidenceState) -> bool:
        """Check if current state matches the given state."""
        return self.current_state == state

    def replay_until(self, events: Tuple[EpistemicEvent, ...], target_event_id: str) -> None:
        """
        Replay events only up to a specific event ID (for historical audits).

        This is useful for reconstructing the state at a specific point in time.

        Args:
            events: Tuple of EpistemicEvent objects.
            target_event_id: Stop replay after this event.

        Raises:
            ValueError: If target_event_id is not found in the event sequence.
        """
        # Reset projection first
        self.current_state = EvidenceState.UNINITIALIZED
        self.history.clear()

        found = False
        for event in events:
            if event.evidence_id == self.evidence_id:
                # Process event normally
                if event.new_state:
                    try:
                        self.current_state = EvidenceState(event.new_state)
                    except ValueError:
                        raise UnknownStateError(
                            f"Event {event.event_id} references unknown state '{event.new_state}'"
                        )

                self.history.append({
                    "timestamp": event.timestamp,
                    "actor": event.actor,
                    "authority": event.authority,
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                    "from_state": event.previous_state,
                    "to_state": event.new_state,
                    "description": event.description,
                    "event_hash": event.event_hash,
                    "previous_hash": event.previous_hash,
                    "hash_algorithm": event.hash_algorithm
                })

                # Stop if we've reached the target event
                if event.event_id == target_event_id:
                    found = True
                    break

        if not found:
            raise ValueError(f"Target event '{target_event_id}' not found in the provided events.")

    def __repr__(self) -> str:
        return f"EvidenceStateProjection(evidence_id={self.evidence_id}, state={self.current_state.value})"
