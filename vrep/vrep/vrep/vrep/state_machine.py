"""
VREP Transition Validator (Policy Engine)
Implements transition validation per VREP Specification 1.2.0-draft
Design Note: This is a stateless validator, not a state holder.
The current state is derived from the Event Log via projection (Event Sourcing).
"""

from enum import Enum
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass


# ---------- Standard Exceptions ----------
class InvalidTransitionError(Exception):
    """Raised when a transition is not allowed."""
    pass


class MissingPreconditionError(Exception):
    """Raised when required preconditions are not met."""
    pass


# ---------- States and Roles ----------
class EvidenceState(Enum):
    """Evidence lifecycle states per VREP Specification."""
    UNINITIALIZED = "Uninitialized"
    CANDIDATE = "Candidate"
    SUSPENDED = "Suspended"
    VERIFIED = "Verified"
    REGISTERED = "Registered"
    ACCEPTED = "Accepted"
    DEPRECATED = "Deprecated"


class GovernanceRole(Enum):
    """Governance roles per VREP Specification."""
    RESEARCHER = "Researcher"
    VERIFIER = "Verifier"
    REGISTRAR = "Registrar"
    SCIENTIFIC_AUTHORITY = "Scientific Authority"
    DEPRECATION_AUTHORITY = "Deprecation Authority"


@dataclass(frozen=True)
class TransitionRule:
    """
    Definition of a valid state transition.
    rule_id follows format: TR-XXX
    """
    rule_id: str
    from_state: EvidenceState
    to_state: EvidenceState
    authority: GovernanceRole
    preconditions: Tuple[str, ...]
    postconditions: Tuple[str, ...]


# ---------- Valid Transitions Database ----------
VALID_TRANSITIONS: Tuple[TransitionRule, ...] = (
    # Candidate → Verified (TR-001)
    TransitionRule(
        rule_id="TR-001",
        from_state=EvidenceState.CANDIDATE,
        to_state=EvidenceState.VERIFIED,
        authority=GovernanceRole.VERIFIER,
        preconditions=("DOI verified", "methodology sound", "fingerprint computed"),
        postconditions=("verification_date recorded", "fingerprint stored")
    ),
    # Candidate → Suspended (TR-002)
    TransitionRule(
        rule_id="TR-002",
        from_state=EvidenceState.CANDIDATE,
        to_state=EvidenceState.SUSPENDED,
        authority=GovernanceRole.VERIFIER,
        preconditions=("concerns raised",),
        postconditions=("suspension_record created",)
    ),
    # Verified → Registered (TR-003)
    TransitionRule(
        rule_id="TR-003",
        from_state=EvidenceState.VERIFIED,
        to_state=EvidenceState.REGISTERED,
        authority=GovernanceRole.REGISTRAR,
        preconditions=("passed VER-GATE",),
        postconditions=("registration_date recorded", "evidence ID assigned")
    ),
    # Verified → Suspended (TR-004)
    TransitionRule(
        rule_id="TR-004",
        from_state=EvidenceState.VERIFIED,
        to_state=EvidenceState.SUSPENDED,
        authority=GovernanceRole.VERIFIER,
        preconditions=("post-verification concerns emerge",),
        postconditions=("suspension_record created",)
    ),
    # Registered → Accepted (TR-005)
    TransitionRule(
        rule_id="TR-005",
        from_state=EvidenceState.REGISTERED,
        to_state=EvidenceState.ACCEPTED,
        authority=GovernanceRole.SCIENTIFIC_AUTHORITY,
        preconditions=("scientific decision documented",),
        postconditions=("acceptance_date recorded", "acceptance_rationale documented")
    ),
    # Registered → Suspended (TR-006)
    TransitionRule(
        rule_id="TR-006",
        from_state=EvidenceState.REGISTERED,
        to_state=EvidenceState.SUSPENDED,
        authority=GovernanceRole.SCIENTIFIC_AUTHORITY,
        preconditions=("pre-acceptance concerns arise",),
        postconditions=("suspension_record created",)
    ),
    # Accepted → Deprecated (TR-007)
    TransitionRule(
        rule_id="TR-007",
        from_state=EvidenceState.ACCEPTED,
        to_state=EvidenceState.DEPRECATED,
        authority=GovernanceRole.DEPRECATION_AUTHORITY,
        preconditions=("retraction", "flaw", "ethical violation"),
        postconditions=("deprecation_record created", "affected documents notified")
    ),
    # Suspended → Candidate (TR-008)
    TransitionRule(
        rule_id="TR-008",
        from_state=EvidenceState.SUSPENDED,
        to_state=EvidenceState.CANDIDATE,
        authority=GovernanceRole.RESEARCHER,
        preconditions=("investigation cleared", "investigation_summary attached"),
        postconditions=("suspension_record resolved",)
    ),
    # Suspended → Verified (TR-009)
    TransitionRule(
        rule_id="TR-009",
        from_state=EvidenceState.SUSPENDED,
        to_state=EvidenceState.VERIFIED,
        authority=GovernanceRole.VERIFIER,
        preconditions=("investigation confirmed validity",),
        postconditions=("suspension_record resolved",)
    ),
    # Suspended → Deprecated (TR-010)
    TransitionRule(
        rule_id="TR-010",
        from_state=EvidenceState.SUSPENDED,
        to_state=EvidenceState.DEPRECATED,
        authority=GovernanceRole.DEPRECATION_AUTHORITY,
        preconditions=("investigation revealed flaws",),
        postconditions=("deprecation_record created",)
    ),
)


# ---------- Lookup Map (O(1) validation) ----------
_TRANSITION_MAP: Dict[Tuple[EvidenceState, EvidenceState], TransitionRule] = {
    (t.from_state, t.to_state): t
    for t in VALID_TRANSITIONS
}


# ---------- Public Validator ----------
def validate_transition(
    from_state: EvidenceState,
    to_state: EvidenceState,
    authority: GovernanceRole,
    preconditions_met: Optional[List[str]] = None
) -> TransitionRule:
    """
    Validate a state transition against the governance policy.

    Args:
        from_state: Current state of the evidence.
        to_state: Target state to transition to.
        authority: Governance role attempting the transition.
        preconditions_met: List of fulfilled preconditions.

    Returns:
        TransitionRule: The validated transition rule.

    Raises:
        InvalidTransitionError: If transition is not defined or authority is wrong.
        MissingPreconditionError: If required preconditions are not met.
    """
    # Look up transition rule
    rule = _TRANSITION_MAP.get((from_state, to_state))

    if rule is None:
        raise InvalidTransitionError(
            f"Transition '{from_state.value} → {to_state.value}' is not defined."
        )

    # Validate authority
    if rule.authority != authority:
        raise InvalidTransitionError(
            f"Transition '{from_state.value} → {to_state.value}' "
            f"requires authority '{rule.authority.value}', got '{authority.value}'."
        )

    # Validate preconditions
    if preconditions_met is None:
        preconditions_met = []

    preconditions_set = set(preconditions_met)
    missing = [p for p in rule.preconditions if p not in preconditions_set]

    if missing:
        raise MissingPreconditionError(
            f"Missing preconditions for transition "
            f"'{from_state.value} → {to_state.value}': {missing}"
        )

    return rule


def get_allowed_transitions(
    from_state: EvidenceState,
    authority: GovernanceRole
) -> List[TransitionRule]:
    """Get all allowed transitions from a given state for a given authority."""
    result = []
    for t in VALID_TRANSITIONS:
        if t.from_state == from_state and t.authority == authority:
            result.append(t)
    return result


def is_transition_allowed(
    from_state: EvidenceState,
    to_state: EvidenceState,
    authority: GovernanceRole
) -> bool:
    """Check if a transition is allowed (returns boolean, no exceptions)."""
    rule = _TRANSITION_MAP.get((from_state, to_state))
    if rule is None:
        return False
    return rule.authority == authority
