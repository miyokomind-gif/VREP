# Changelog

All notable changes to VREP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.2.0] — 2026-07-25

### Added
- Cryptographic identity generator (UUID v4 + SHA-256 fingerprint)
- Immutable event log with tamper-evident hash chain
- Stateless transition validator
- Event sourcing state projection
- In-memory registry with fingerprint-based lookup
- Conformance Test Suite (CTS-005 to CTS-017)
- End-to-end reference workflow (`cal001_end_to_end.py`)
- MIT License
- README with Project Status and Quick Start
- GitHub Actions CI for automated testing
- CITATION.cff for academic citation

### Changed
- Refactored state machine to stateless validator (aligned with Event Sourcing)
- Added EventIDGenerator for automatic event IDs
- Expanded CTS coverage to 17 tests
- Updated README with RFC 8785 clarification

### Fixed
- Fixed UTC timestamp handling (timezone-aware)
- Fixed FrozenInstanceError handling in immutability tests
- Removed duplicate state storage between Event Log and State Machine

### Known Limitations
- Specification remains in Draft status (1.2.0-draft)
- Full INV-07 (Standard Errors) coverage planned for v0.3.0
- Production Profile (RFC 8785, Ed25519, REST/gRPC) not yet implemented

---

## [v0.1.0] — 2026-07-20

### Added
- Initial concept: Evidence identity, state machine, event log
- Basic CTS (CTS-005 to CTS-008)
- CAL-001 pilot simulation

### Removed
- This version was replaced by v0.2.0 with architectural redesign

---

## [Unreleased] — v0.3.0 (Planned)

### Planned
- Full INV-07 implementation in all modules
- RFC 8785 canonical JSON
- Digital signatures (Ed25519)
- Persistent storage (SQLite/PostgreSQL)
- REST/gRPC interfaces
- Import/export improvements
