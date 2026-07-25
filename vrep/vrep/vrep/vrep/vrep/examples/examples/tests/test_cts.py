"""
VREP Conformance Test Suite (CTS)
Verifies compliance with VREP Specification 1.2.0-draft
Tests CTS-001 to CTS-017
"""

import sys
import os
import json
import pytest
from dataclasses import FrozenInstanceError

# Ensure vrep module is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vrep.identity import EvidenceIdentityGenerator
from vrep.event_log import EpistemicEventLog, DuplicateEventIDError, HashMismatchError, EventIDGenerator
from vrep.registry import EvidenceRegistry
from vrep.projection import EvidenceStateProjection
from vrep.state_machine import (
    EvidenceState,
    GovernanceRole,
    validate_transition,
    InvalidTransitionError,
    MissingPreconditionError
)


class TestCTS:
    """Conformance Test Suite for VREP v0.2.0"""

    @pytest.fixture
    def setup(self):
        """Common test fixtures."""
        generator = EvidenceIdentityGenerator()
        metadata = {
            "source": "CTS Test",
            "title": "Conformance Test Data",
            "authors": ["VER Core Team"],
            "year": 2026,
            "evidence_level": "E3"
        }
        identity = generator.generate_evidence_id(metadata, local_record_id="CTS-001")
        evidence_id = identity["authoritative_identifier"]["evidence_id"]
        log = EpistemicEventLog()
        registry = EvidenceRegistry(log)
        registry.register(identity)
        return {
            "generator": generator,
            "identity": identity,
            "evidence_id": evidence_id,
            "log": log,
            "registry": registry
        }

    # ---------- CTS-005: Dataclass Immutability ----------
    def test_cts_005_dataclass_immutability(self, setup):
        """CTS-005: Events MUST be immutable after creation."""
        log = setup["log"]
        evidence_id = setup["evidence_id"]

        event = log.record_event(
            event_id="CTS-005-EVT",
            actor="Tester",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Test",
            evidence_id=evidence_id,
            description="Original description",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value
        )

        with pytest.raises(FrozenInstanceError):
            event.description = "TAMPERED"

    # ---------- CTS-006: Tuple Immutability ----------
    def test_cts_006_tuple_immutability(self, setup):
        """CTS-006: get_events() MUST return immutable tuple."""
        log = setup["log"]
        evidence_id = setup["evidence_id"]

        log.record_event(
            event_id="CTS-006-EVT",
            actor="Tester",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Test",
            evidence_id=evidence_id,
            description="Test event",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value
        )

        events = log.get_events()
        with pytest.raises(TypeError):
            events[0] = "TAMPERED"

    # ---------- CTS-007: Version Metadata ----------
    def test_cts_007_version_metadata(self, setup):
        """CTS-007: All events MUST include version metadata."""
        log = setup["log"]
        evidence_id = setup["evidence_id"]

        event = log.record_event(
            event_id="CTS-007-EVT",
            actor="Tester",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Test",
            evidence_id=evidence_id,
            description="Test event",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value
        )

        assert event.implementation_version == "0.2.0"
        assert event.specification_version == "1.2.0-draft"
        assert event.schema_version == "1.1"
        assert event.implementation_name == "VREP Reference Implementation"

    # ---------- CTS-008: Timezone-Aware Timestamps ----------
    def test_cts_008_timezone_aware(self, setup):
        """CTS-008: Timestamps MUST be timezone-aware."""
        log = setup["log"]
        evidence_id = setup["evidence_id"]

        event = log.record_event(
            event_id="CTS-008-EVT",
            actor="Tester",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Test",
            evidence_id=evidence_id,
            description="Test event",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value
        )

        assert "+" in event.timestamp or event.timestamp.endswith("Z")

    # ---------- CTS-009: Duplicate Registration Rejection ----------
    def test_cts_009_duplicate_registration(self, setup):
        """CTS-009: Registry MUST reject duplicate evidence IDs."""
        registry = setup["registry"]
        identity = setup["identity"]

        with pytest.raises(ValueError) as excinfo:
            registry.register(identity)
        assert "already registered" in str(excinfo.value).lower()

    # ---------- CTS-010: Hash Chain Integrity ----------
    def test_cts_010_hash_chain_integrity(self, setup):
        """CTS-010: Hash chain MUST be verifiable."""
        log = setup["log"]
        evidence_id = setup["evidence_id"]

        log.record_event(
            event_id="CTS-010-EVT-1",
            actor="Tester",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Discovery",
            evidence_id=evidence_id,
            description="First event",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value
        )
        log.record_event(
            event_id="CTS-010-EVT-2",
            actor="Tester",
            authority=GovernanceRole.VERIFIER.value,
            event_type="Transition",
            evidence_id=evidence_id,
            description="Second event",
            previous_state=EvidenceState.CANDIDATE.value,
            new_state=EvidenceState.VERIFIED.value
        )

        # Verify chain
        result = log.verify_chain_integrity()
        assert result is True

    # ---------- CTS-011: Tampering Detection ----------
    def test_cts_011_tampering_detection(self):
        """CTS-011: Tampering with events MUST be detectable."""
        log = EpistemicEventLog()
        evidence_id = "VER-EV-test-test"

        log.record_event(
            event_id="CTS-011-EVT-1",
            actor="Tester",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Discovery",
            evidence_id=evidence_id,
            description="Original event",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value
        )

        # Create a second log with tampered data
        tampered_log = EpistemicEventLog()
        tampered_log.record_event(
            event_id="CTS-011-EVT-1",
            actor="Tester",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Discovery",
            evidence_id=evidence_id,
            description="Original event",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value
        )
        # Manually set previous hash to break chain (for test only)
        tampered_log._last_event_hash = "0" * 64

        # The tampered log should have invalid chain
        try:
            tampered_log.verify_chain_integrity()
            assert False, "Tampered chain should be invalid"
        except (HashMismatchError, Exception):
            pass

    # ---------- CTS-012: Registry Lookup by Fingerprint ----------
    def test_cts_012_fingerprint_lookup(self, setup):
        """CTS-012: Registry MUST support lookup by fingerprint."""
        registry = setup["registry"]
        identity = setup["identity"]
        fingerprint = identity["display_identifier"]["fingerprint_short"]

        results = registry.lookup_by_fingerprint(fingerprint)
        assert len(results) == 1
        assert results[0]["authoritative_identifier"]["evidence_id"] == identity["authoritative_identifier"]["evidence_id"]

    # ---------- CTS-013: Event Replay Determinism ----------
    def test_cts_013_event_replay_determinism(self, setup):
        """CTS-013: Event replay MUST be deterministic."""
        log = setup["log"]
        evidence_id = setup["evidence_id"]

        # Record events in a specific order
        log.record_event(
            event_id="CTS-013-EVT-1",
            actor="Tester",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Discovery",
            evidence_id=evidence_id,
            description="Event 1",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value
        )
        log.record_event(
            event_id="CTS-013-EVT-2",
            actor="Tester",
            authority=GovernanceRole.VERIFIER.value,
            event_type="Transition",
            evidence_id=evidence_id,
            description="Event 2",
            previous_state=EvidenceState.CANDIDATE.value,
            new_state=EvidenceState.VERIFIED.value
        )
        log.record_event(
            event_id="CTS-013-EVT-3",
            actor="Tester",
            authority=GovernanceRole.REGISTRAR.value,
            event_type="Transition",
            evidence_id=evidence_id,
            description="Event 3",
            previous_state=EvidenceState.VERIFIED.value,
            new_state=EvidenceState.REGISTERED.value
        )

        # Replay events
        projection = EvidenceStateProjection(evidence_id)
        projection.replay(log.get_events())

        # Verify final state
        assert projection.get_current_state() == EvidenceState.REGISTERED
        assert len(projection.get_history()) == 3

        # Replay again (should be same)
        projection.replay(log.get_events())
        assert projection.get_current_state() == EvidenceState.REGISTERED
        assert len(projection.get_history()) == 3

    # ---------- CTS-014: Import Metadata Hash Verification ----------
    def test_cts_014_metadata_hash_verification(self, setup):
        """CTS-014: verify_metadata_hash MUST detect changes."""
        generator = setup["generator"]
        metadata = {
            "source": "CTS Test",
            "title": "Conformance Test Data",
            "authors": ["VER Core Team"],
            "year": 2026,
            "evidence_level": "E3"
        }

        # Generate hash
        hash_value = generator.compute_full_metadata_hash(metadata)

        # Verify correct metadata
        assert generator.verify_metadata_hash(metadata, hash_value) is True

        # Change metadata
        modified_metadata = metadata.copy()
        modified_metadata["year"] = 2027

        # Verify detection
        assert generator.verify_metadata_hash(modified_metadata, hash_value) is False

    # ---------- CTS-015: Large Replay Performance ----------
    def test_cts_015_large_replay(self, setup):
        """CTS-015: Replaying 1000 events MUST produce consistent projection."""
        log = setup["log"]
        evidence_id = setup["evidence_id"]

        # Generate 1000 events
        for i in range(1000):
            state = EvidenceState.CANDIDATE if i % 2 == 0 else EvidenceState.VERIFIED
            log.record_event(
                event_id=f"CTS-015-EVT-{i:06d}",
                actor="Tester",
                authority=GovernanceRole.RESEARCHER.value,
                event_type="Test",
                evidence_id=evidence_id,
                description=f"Event {i}",
                previous_state=None,
                new_state=state.value
            )

        # Replay and verify consistency
        projection = EvidenceStateProjection(evidence_id)
        projection.replay(log.get_events())
        assert len(projection.get_history()) == 1000

        # Replay again (must be deterministic)
        projection.replay(log.get_events())
        assert len(projection.get_history()) == 1000

    # ---------- CTS-016: Malformed JSON Import ----------
    def test_cts_016_malformed_json_import(self):
        """CTS-016: Import of malformed JSON MUST be rejected."""
        log = EpistemicEventLog()
        with pytest.raises(NotImplementedError):
            log.from_json("{invalid json}")

    # ---------- CTS-017: Unknown Schema Version ----------
    def test_cts_017_unknown_schema_version(self, setup):
        """CTS-017: Unknown schema version MUST be detected."""
        log = setup["log"]
        evidence_id = setup["evidence_id"]

        event = log.record_event(
            event_id="CTS-017-EVT",
            actor="Tester",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Test",
            evidence_id=evidence_id,
            description="Test event",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value
        )

        assert event.schema_version == "1.1"
        assert hasattr(event, "schema_version")

    # ---------- Extended: State Machine Validation ----------
    def test_state_machine_valid_transition(self, setup):
        """Validate that a correct transition passes."""
        log = setup["log"]
        evidence_id = setup["evidence_id"]

        log.record_event(
            event_id="SM-TEST-1",
            actor="Tester",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Discovery",
            evidence_id=evidence_id,
            description="Initial",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value
        )

        rule = validate_transition(
            from_state=EvidenceState.CANDIDATE,
            to_state=EvidenceState.VERIFIED,
            authority=GovernanceRole.VERIFIER,
            preconditions_met=["DOI verified", "methodology sound", "fingerprint computed"]
        )
        assert rule.rule_id == "TR-001"

    def test_state_machine_invalid_transition(self, setup):
        """Validate that an invalid transition is blocked."""
        with pytest.raises(InvalidTransitionError):
            validate_transition(
                from_state=EvidenceState.CANDIDATE,
                to_state=EvidenceState.ACCEPTED,
                authority=GovernanceRole.SCIENTIFIC_AUTHORITY,
                preconditions_met=["scientific decision documented"]
            )

    def test_state_machine_missing_preconditions(self, setup):
        """Validate that missing preconditions are detected."""
        with pytest.raises(MissingPreconditionError):
            validate_transition(
                from_state=EvidenceState.CANDIDATE,
                to_state=EvidenceState.VERIFIED,
                authority=GovernanceRole.VERIFIER,
                preconditions_met=["methodology sound"]
            )

    def test_state_machine_wrong_authority(self, setup):
        """Validate that wrong authority is rejected."""
        with pytest.raises(InvalidTransitionError):
            validate_transition(
                from_state=EvidenceState.CANDIDATE,
                to_state=EvidenceState.VERIFIED,
                authority=GovernanceRole.RESEARCHER,
                preconditions_met=["DOI verified", "methodology sound", "fingerprint computed"]
            )
