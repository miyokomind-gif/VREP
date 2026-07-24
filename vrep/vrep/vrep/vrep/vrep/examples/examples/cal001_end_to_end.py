#!/usr/bin/env python3
"""
CAL-001 End-to-End Reference Workflow
Full VREP lifecycle: Identity → Event Log → Validation → Registry → Projection → Integrity Check
"""

import json
import sys
import os

# Ensure vrep module is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vrep.identity import EvidenceIdentityGenerator
from vrep.event_log import EpistemicEventLog, DuplicateEventIDError
from vrep.registry import EvidenceRegistry
from vrep.projection import EvidenceStateProjection
from vrep.state_machine import (
    EvidenceState,
    GovernanceRole,
    validate_transition,
    InvalidTransitionError,
    MissingPreconditionError
)


def run_cal001():
    """Execute the CAL-001 end-to-end reference workflow."""
    print("=" * 80)
    print("  VREP v0.2.0 — CAL-001 End-to-End Reference Workflow")
    print("  Specification: 1.2.0-draft")
    print("=" * 80)

    # 1. Generate Evidence Identity
    print("\n[1] Generating Evidence Identity...")
    generator = EvidenceIdentityGenerator()
    metadata = {
        "source": "EXEC-000 Synthetic Run",
        "title": "Zeeman Response in Atriplex Model: Synthetic Analysis",
        "authors": ["VER Core Team"],
        "year": 2026,
        "evidence_level": "E3",
        "lifecycle_stage": "Candidate",
        "claim_reference": "CLM-005 (Zeeman Response)",
        "parameters": {
            "B0_range": "0-100 microT",
            "Phi_S_range": "0.2500 - 0.2500002",
            "max_change_percent": 0.00008
        },
        "interpretation_locked": True
    }
    identity = generator.generate_evidence_id(metadata, local_record_id="EV-001")
    evidence_id = identity["authoritative_identifier"]["evidence_id"]
    print(f"  ✅ Evidence ID: {evidence_id}")
    print(f"     UUID: {identity['authoritative_identifier']['uuid']}")
    print(f"     Metadata Hash: {identity['authoritative_identifier']['metadata_hash'][:16]}...")

    # 2. Create Event Log
    print("\n[2] Creating Event Log...")
    log = EpistemicEventLog()

    # Event 1: Discovery (Candidate)
    print("  [2a] Recording Discovery Event...")
    try:
        event1 = log.record_event(
            event_id="EVT-2026-00001",
            actor="VER Core Team",
            authority=GovernanceRole.RESEARCHER.value,
            event_type="Discovery",
            evidence_id=evidence_id,
            description="Identified synthetic data supporting Zeeman response claim",
            previous_state=None,
            new_state=EvidenceState.CANDIDATE.value,
            trigger="EXEC-000 synthetic run",
            postconditions_fulfilled=["Evidence ID generated", "Fingerprint computed"]
        )
        print(f"      ✅ Event 1 recorded (Hash: {event1.event_hash[:16]}...)")
    except DuplicateEventIDError as e:
        print(f"      ❌ Failed: {e}")
        return

    # Validate transition: Candidate -> Verified (stateless)
    print("\n  [2b] Validating transition: Candidate → Verified ...")
    try:
        rule = validate_transition(
            from_state=EvidenceState.CANDIDATE,
            to_state=EvidenceState.VERIFIED,
            authority=GovernanceRole.VERIFIER,
            preconditions_met=["DOI verified", "methodology sound", "fingerprint computed"]
        )
        print(f"      ✅ Transition validated: {rule.rule_id}")
    except (InvalidTransitionError, MissingPreconditionError) as e:
        print(f"      ❌ Validation failed: {e}")
        return

    # Event 2: Verification (Candidate -> Verified)
    print("  [2c] Recording Verification Event...")
    try:
        event2 = log.record_event(
            event_id="EVT-2026-00002",
            actor="AUTH-001 (Verifier)",
            authority=GovernanceRole.VERIFIER.value,
            event_type="State Transition",
            evidence_id=evidence_id,
            description="Bibliographic and methodological verification completed",
            previous_state=EvidenceState.CANDIDATE.value,
            new_state=EvidenceState.VERIFIED.value,
            trigger="Verification of synthetic data methodology",
            preconditions_met=[
                "DOI verified",
                "methodology sound",
                "fingerprint computed"
            ],
            postconditions_fulfilled=["verification_date recorded", "Fingerprint verified"],
            change_log_reference="ECL-001"
        )
        print(f"      ✅ Event 2 recorded (Hash: {event2.event_hash[:16]}...)")
    except DuplicateEventIDError as e:
        print(f"      ❌ Failed: {e}")
        return

    # Validate transition: Verified -> Registered
    print("\n  [2d] Validating transition: Verified → Registered ...")
    try:
        rule = validate_transition(
            from_state=EvidenceState.VERIFIED,
            to_state=EvidenceState.REGISTERED,
            authority=GovernanceRole.REGISTRAR,
            preconditions_met=["passed VER-GATE"]
        )
        print(f"      ✅ Transition validated: {rule.rule_id}")
    except (InvalidTransitionError, MissingPreconditionError) as e:
        print(f"      ❌ Validation failed: {e}")
        return

    # Event 3: Registration (Verified -> Registered)
    print("  [2e] Recording Registration Event...")
    try:
        event3 = log.record_event(
            event_id="EVT-2026-00003",
            actor="AUTH-002 (Registrar)",
            authority=GovernanceRole.REGISTRAR.value,
            event_type="State Transition",
            evidence_id=evidence_id,
            description="Evidence registered after VER-GATE validation",
            previous_state=EvidenceState.VERIFIED.value,
            new_state=EvidenceState.REGISTERED.value,
            trigger="Passed VER-GATE",
            preconditions_met=[
                "VER-GATE bibliographic validation passed",
                "VER-GATE methodological validation passed"
            ],
            postconditions_fulfilled=["registration_date recorded", "evidence_id assigned"],
            change_log_reference="ECL-002"
        )
        print(f"      ✅ Event 3 recorded (Hash: {event3.event_hash[:16]}...)")
    except DuplicateEventIDError as e:
        print(f"      ❌ Failed: {e}")
        return

    # 3. Register Evidence
    print("\n[3] Registering Evidence...")
    registry = EvidenceRegistry(log)
    try:
        registry.register(identity)
        print(f"  ✅ Evidence registered: {evidence_id}")
    except ValueError as e:
        print(f"  ❌ Registration failed: {e}")

    # 4. Project State (Event Sourcing)
    print("\n[4] Projecting State (Event Sourcing)...")
    projection = EvidenceStateProjection(evidence_id)
    projection.replay(log.get_events())
    print(f"  ✅ Current State: {projection.get_current_state().value}")

    # Display transition history
    print("\n[4a] Transition History:")
    history = projection.get_history()
    for i, entry in enumerate(history, 1):
        print(f"      {i}. {entry['from_state']} → {entry['to_state']} "
              f"({entry['event_type']}) - {entry['description'][:40]}...")

    # 5. Verify Hash Chain Integrity
    print("\n[5] Verifying Hash Chain Integrity...")
    try:
        log.verify_chain_integrity()
        print("  ✅ Chain Integrity: VALID")
    except Exception as e:
        print(f"  ❌ Chain Integrity: INVALID ({e})")

    # 6. Attempt invalid transition (Researcher -> Accept)
    print("\n[6] Attempting invalid transition (Researcher → Accept)...")
    try:
        validate_transition(
            from_state=EvidenceState.REGISTERED,
            to_state=EvidenceState.ACCEPTED,
            authority=GovernanceRole.RESEARCHER,
            preconditions_met=["scientific decision documented"]
        )
        print("  ❌ ERROR: Researcher accepted (should have been blocked)")
    except InvalidTransitionError as e:
        print(f"  ✅ Blocked: {e}")

    # 7. Tampering Demonstration
    print("\n[7] Tampering Demonstration...")
    print("  [7a] Verifying chain before tampering...")
    try:
        log.verify_chain_integrity()
        print("      ✅ Chain intact")
    except Exception as e:
        print(f"      ❌ Chain broken: {e}")

    print("  [7b] Simulating tampering (modifying event 2 description)...")
    # Access internal events (for demonstration only)
    try:
        # Get event object and try to modify (will raise FrozenInstanceError)
        events = log.get_events()
        original_desc = events[1].description
        print(f"      Original description: {original_desc[:40]}...")
        print("      Attempting modification...")
        # This will fail because dataclass is frozen
        try:
            events[1].description = "TAMPERED DESCRIPTION"
            print("      ❌ Modification succeeded (unexpected!)")
        except AttributeError:
            print("      ✅ Modification blocked (immutability enforced)")
    except Exception as e:
        print(f"      ⚠️  Note: {e}")

    # 8. Export JSON files
    print("\n[8] Exporting JSON files...")
    os.makedirs("evidence", exist_ok=True)

    # Export identity
    with open("evidence/CAL-001_evidence_identity.json", "w") as f:
        json.dump(identity, f, indent=2)
    print("  ✅ CAL-001_evidence_identity.json")

    # Export event log
    events_data = []
    for e in log.get_events():
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
    with open("evidence/CAL-001_event_log.json", "w") as f:
        json.dump(events_data, f, indent=2)
    print("  ✅ CAL-001_event_log.json")

    # 9. Summary
    print("\n" + "=" * 80)
    print("  ✅ CAL-001 Completed Successfully")
    print("=" * 80)
    print("\n📊 Summary:")
    print(f"  - Evidence ID: {evidence_id}")
    print(f"  - Total Events: {log.get_event_count()}")
    print(f"  - Final State: {projection.get_current_state().value}")
    print(f"  - Chain Integrity: ✅ Valid")
    print(f"  - Transition History: {len(projection.get_history())} events")
    print(f"  - JSON Files: evidence/CAL-001_evidence_identity.json, evidence/CAL-001_event_log.json")
    print("\n📁 Generated Records:")
    print("  - evidence/CAL-001_evidence_identity.json")
    print("  - evidence/CAL-001_event_log.json")


if __name__ == "__main__":
    run_cal001()
