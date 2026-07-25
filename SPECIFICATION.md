# VREP Protocol Specification
**Version:** 1.2.0-draft  
**Status:** Draft — Reference Implementation v0.2.0 Available  
**Category:** Epistemic Governance & Evidence Lifecycle Architecture  

---

## 1. Introduction

The Verified Research Evidence Protocol (VREP) is an epistemic governance framework for managing the lifecycle of scientific evidence. It defines:

- **Cryptographic identity** (UUID v4 + SHA-256) for each evidence item.
- **Immutable event log** with tamper-evident hash chain.
- **Event sourcing** architecture (Event Log as Single Source of Truth).
- **Registry layer** for indexing and lookup.
- **Reference Conformance Test Suite** (CTS) for verification (see Appendix A).

This document specifies the normative rules, structural invariants, and behavioral requirements of VREP. It is **independent of any programming language** and serves as the reference for any implementation claiming conformance.

---

## 2. Structural Invariants

The following invariants are **mandatory** for any VREP-compliant system:

| Invariant | Description |
|-----------|-------------|
| **INV-01** | The Epistemic Event Log is the **Single Source of Truth**. All state must be derived solely via event replay. |
| **INV-02** | Each evidence item must have a **unique identity** derived from UUID v4 and SHA-256 fingerprint of its metadata. |
| **INV-03** | Events in the log are **immutable**; they cannot be modified or deleted after creation. |
| **INV-04** | The event log maintains a **continuous hash chain** where each event's hash depends on the previous event's hash. |
| **INV-05** | State **projection** must be **deterministic**: the same sequence of events, in the same order, must always produce the same state. |
| **INV-06** | The Registry is a **cache/index projection** only. It is not authoritative and must not be used as the source of truth. |
| **INV-07** | Validation failures must raise **standard errors** (e.g., `InvalidTransitionError`, `MissingPreconditionError`, `HashMismatchError`) instead of returning boolean values. |

---

## 3. Evidence Identity

### 3.1. Identity Structure

Every evidence item must have a globally unique, cryptographically verifiable identity.

**Format:**
```

VER-EV-{UUID8}-{FINGERPRINT8}

```
Where:
- `UUID8`: First 8 characters of a UUID v4.
- `FINGERPRINT8`: First 8 characters of SHA-256(metadata).

### 3.2. Authoritative vs Display Identifiers

| Type | Purpose | Usage |
|------|---------|-------|
| **Authoritative** | Permanent identifier | Used for verification, lookup, and persistence |
| **Display** | Human-readable | Used only for display, logging, and debugging |

**Rules:**
- Authoritative identifiers must not change.
- Display identifiers may be derived from authoritative ones but must never be used for verification.

### 3.3. Metadata Fingerprint

The fingerprint is computed from the complete evidence metadata using **SHA-256**. Metadata must be serialized using a **deterministic canonical JSON** representation.

**Canonical JSON Requirements:**
- Keys sorted alphabetically.
- No spaces or newlines.
- `NaN` and `Infinity` are not allowed.
- Floating-point numbers are represented as decimals.

**Note:** This draft specification requires deterministic canonical serialization. The reference implementation currently uses sorted-key JSON serialization. Full RFC 8785 canonicalization is planned for the Production Profile.

---

## 4. Evidence Lifecycle States

| State | Description | Entry Condition |
|-------|-------------|-----------------|
| **Uninitialized** | Default initial state before any event is recorded. | System start. |
| **Candidate** | Proposed evidence with complete metadata. | Discovery event. |
| **Suspended** | Temporarily held for review. | Concern raised. |
| **Verified** | Methodologically and bibliographically verified. | Verification completed. |
| **Registered** | Officially registered in the governance system. | Registration event. |
| **Accepted** | Adopted as a scientific reference. | Scientific approval. |
| **Deprecated** | Withdrawn or invalidated with rationale. | Deprecation event. |

---

## 5. Governance Roles

| Role | Abbreviation | Authority |
|------|--------------|-----------|
| **Researcher** | RES | Create Candidate, Suspend, Flag for review |
| **Verifier** | VER | Verify Candidate, Suspend, Reject |
| **Registrar** | REG | Register Verified evidence |
| **Scientific Authority** | SCI | Accept Registered evidence |
| **Deprecation Authority** | DEP | Deprecate Accepted evidence |

---

## 6. Valid Transitions

| Rule ID | From | To | Required Authority | Preconditions |
|---------|------|----|--------------------|---------------|
| TR-001 | Candidate | Verified | Verifier | DOI verified, methodology sound, fingerprint computed |
| TR-002 | Candidate | Suspended | Verifier | concerns raised |
| TR-003 | Verified | Registered | Registrar | passed VER-GATE |
| TR-004 | Verified | Suspended | Verifier | post-verification concerns emerge |
| TR-005 | Registered | Accepted | Scientific Authority | scientific decision documented |
| TR-006 | Registered | Suspended | Scientific Authority | pre-acceptance concerns arise |
| TR-007 | Accepted | Deprecated | Deprecation Authority | retraction, flaw, or ethical violation |
| TR-008 | Suspended | Candidate | Researcher | investigation cleared, investigation_summary attached |
| TR-009 | Suspended | Verified | Verifier | investigation confirmed validity |
| TR-010 | Suspended | Deprecated | Deprecation Authority | investigation revealed flaws |

---

## 7. Event Standard

### 7.1. Event Structure

Each event must include the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | String | Unique event identifier |
| `timestamp` | ISO 8601 | UTC timestamp with timezone offset (+00:00) |
| `actor` | String | Who performed the action |
| `authority` | String | Governance role (Researcher, Verifier, Registrar, etc.) |
| `event_type` | String | Discovery, State Transition, Deprecation |
| `evidence_id` | String | Evidence ID (VER-EV-...) |
| `description` | String | Human-readable description |
| `previous_state` | String | State before event (or null) |
| `new_state` | String | State after event (or null) |
| `trigger` | String | What triggered the event |
| `preconditions_met` | Array | List of satisfied preconditions |
| `postconditions_fulfilled` | Array | List of fulfilled postconditions |
| `change_log_reference` | String | Reference to change log entry (optional) |
| `event_hash` | String | Hash of this event (hex only) |
| `previous_hash` | String | Hash of the previous event (hex only) |
| `hash_algorithm` | String | Hash algorithm used (e.g., SHA-256) |

### 7.2. Hash Chain Continuity

Each event must contain:
- `event_hash` computed from the event data and the `previous_hash`.
- `previous_hash` equal to the `event_hash` of the immediately preceding event in the log.

If `previous_hash` does not match the previous event's `event_hash`, the chain is **broken** and the log is invalid.

---

## 8. State Projection (Event Sourcing)

State must be derived **solely** from replaying events. Implementations must:

1. Start with `Uninitialized` state.
2. Process events in **chronological order**.
3. Update state according to the `new_state` field of each event.
4. Record transition history for audit purposes.

**Requirement:** The same sequence of events, in the same order, must always produce the same final state. This is **INV-05 (Deterministic Projection)**.

---

## 9. Registry Requirements

The Registry is a **cache/index layer** only. It may:

- Index evidence by ID and fingerprint.
- Provide fast lookup.
- Cache identity records.

The Registry **must not**:
- Be used as the authoritative source of truth.
- Modify or override Event Log data.
- Persist state independently of the Event Log.

---

## 10. Error Handling (INV-07)

Validation failures must raise **specific errors**:

| Error | Condition |
|-------|-----------|
| `InvalidTransitionError` | Transition is not defined or authority is wrong |
| `MissingPreconditionError` | Required preconditions are not met |
| `HashMismatchError` | Event hash does not match recomputed hash |
| `PreviousHashMismatchError` | Previous hash does not match chain |
| `ChainBrokenError` | Hash chain integrity is violated |
| `DuplicateEventIDError` | Event ID is already used in the log |

---

## 11. Versioning and Release Lifecycle

| Version | Status | Description |
|---------|--------|-------------|
| **1.2.0-draft** | Draft | Current specification, aligned with Reference Implementation v0.2.0 |
| **1.2.0** | Planned | Final specification, aligned with v1.0.0 production release |

---

## 12. Production Profile (Future)

The following features are **not part of this specification** but are planned for the **Production Profile**:

- RFC 8785 canonical JSON encoding.
- Digital signatures (Ed25519) for event authenticity.
- Persistent storage and database integration.
- REST/gRPC interfaces.
- Certificate-based authority management.

---

## Appendix A: Reference Conformance Test Suite (CTS)

The following tests are provided by the Reference Implementation to verify conformance. They are **informative**; implementations may adopt equivalent test strategies.

| Test ID | Description |
|---------|-------------|
| CTS-005 | Dataclass immutability enforcement |
| CTS-006 | Tuple immutability enforcement |
| CTS-007 | Version metadata completeness |
| CTS-008 | Timezone-aware timestamps |
| CTS-009 | Duplicate registration rejection |
| CTS-010 | Hash chain integrity verification |
| CTS-011 | Tampering detection |
| CTS-012 | Registry lookup by fingerprint |
| CTS-013 | Event replay determinism |
| CTS-014 | Import metadata hash verification |
| CTS-015 | Large replay consistency |
| CTS-016 | Malformed JSON import rejection |
| CTS-017 | Unknown schema version detection |

---

## Appendix B: Reference Implementation

A reference implementation is available at:

- Repository: [https://github.com/miyokomind-gif/VREP](https://github.com/miyokomind-gif/VREP)
- Release: [v0.2.0](https://github.com/miyokomind-gif/VREP/releases/tag/v0.2.0)

This implementation provides a Python-based proof of concept that demonstrates conformance with this specification.

---

**End of Specification**
```
