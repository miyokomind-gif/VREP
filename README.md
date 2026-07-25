# VREP — Verified Research Evidence Protocol

**Reference Implementation:** v0.2.0  
**Specification:** 1.2.0-draft  
**Status:** Architectural Freeze  
**Production Profile:** Planned

---

## Overview

VREP is an epistemic governance protocol for managing the lifecycle of scientific evidence. It provides:

- Cryptographic identity (UUID v4 + SHA-256 fingerprint)
- Immutable event log with tamper-evident hash chain
- Event sourcing architecture (Event Log as Single Source of Truth)
- Registry layer with fingerprint-based lookup
- Conformance Test Suite (CTS-001 to CTS-017)

---

## Project Status

- **Reference Implementation:** v0.2.0 (Stable)
- **Specification:** 1.2.0-draft
- **Architectural State:** Frozen
- **Production Profile:** Planned (Ed25519, REST/gRPC, persistence)
- **Canonical JSON:** Current implementation uses `sort_keys` + `separators`. Full RFC 8785 compliance is planned for the Production Profile.

---

## Architecture

VREP is organized into three distinct layers:

1. Core Specification — Normative rules and structural invariants
2. Event Sourcing Engine — EpistemicEventLog as Single Source of Truth
3. Reference Implementation — Python executable with in-memory registry

---

## Quick Start

### Prerequisites

Python 3.9 or higher (standard library only)

### Installation

```bash
git clone https://github.com/YOUR-USERNAME/VREP.git
cd VREP
```

Run the Demo

```bash
python examples/cal001_end_to_end.py
```

Basic Usage

```python
from vrep.identity import EvidenceIdentityGenerator
from vrep.event_log import EpistemicEventLog
from vrep.registry import EvidenceRegistry

generator = EvidenceIdentityGenerator()
event_log = EpistemicEventLog()
registry = EvidenceRegistry(event_log)

metadata = {
    "title": "Experimental Analysis",
    "evidence_level": "E3",
    "year": 2026
}

identity = generator.generate_evidence_id(metadata)
registry.register(identity)

event_log.record_event(
    event_id=None,  # auto-generated
    actor="Researcher",
    authority="Researcher",
    event_type="Discovery",
    evidence_id=identity["authoritative_identifier"]["evidence_id"],
    description="Record created",
    previous_state=None,
    new_state="Candidate"
)

projection = registry.get_projected_state(
    identity["authoritative_identifier"]["evidence_id"]
)
print(projection.current_state.value)  # Candidate
```

---

Conformance Test Suite (CTS)

The test suite covers:

· CTS-005 to CTS-008: Immutability, version metadata, timezone awareness
· CTS-009 to CTS-011: Duplicate protection, chain integrity, tamper detection
· CTS-012 to CTS-014: Fingerprint lookup, replay determinism, import verification
· CTS-015 to CTS-017: Large replay, malformed JSON, unknown schema version

To run the tests:

```bash
pytest tests/test_cts.py -v
```

Reference CTS Suite: CTS-001 to CTS-017.

---

Disclaimer

VREP is an independent research protocol and reference implementation. It is not currently an official standard of ISO, IEEE, W3C, or any governmental standards body.

---

License

Distributed under the MIT License. See LICENSE file for details.

```
