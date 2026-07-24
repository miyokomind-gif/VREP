"""
VREP Evidence Identity Generator
Generates cryptographically verifiable evidence IDs per VREP Specification 1.2.0-draft
"""

import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from vrep import VERSION_METADATA


class EvidenceIdentityGenerator:
    """Generates VREP-compliant evidence identities."""

    def __init__(self):
        self.uuid_version = 4

    def generate_uuid(self) -> str:
        """Generate RFC 4122 Version 4 UUID."""
        return str(uuid.uuid4())

    def compute_fingerprint(self, metadata: Dict[str, Any]) -> str:
        """
        Compute SHA-256 fingerprint of evidence metadata.
        Uses canonical JSON serialization.
        """
        canonical = json.dumps(
            metadata,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":")
        )
        hash_hex = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
        return hash_hex[:8]

    def compute_full_metadata_hash(self, metadata: Dict[str, Any]) -> str:
        """Compute full SHA-256 hash of metadata for integrity verification."""
        canonical = json.dumps(
            metadata,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def verify_metadata_hash(self, metadata: Dict[str, Any], expected_hash: str) -> bool:
        """Verify metadata hash on import."""
        recomputed = self.compute_full_metadata_hash(metadata)
        return recomputed == expected_hash

    def generate_evidence_id(
        self,
        metadata: Dict[str, Any],
        local_record_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate complete VREP evidence identity record.
        Separates authoritative identifiers from display identifiers.
        """
        full_uuid = self.generate_uuid()
        uuid_short = full_uuid.split('-')[0]

        fingerprint_short = self.compute_fingerprint(metadata)
        metadata_hash_full = self.compute_full_metadata_hash(metadata)

        evidence_id = f"VER-EV-{uuid_short}-{fingerprint_short}"

        return {
            "authoritative_identifier": {
                "evidence_id": evidence_id,
                "uuid": full_uuid,
                "metadata_hash": metadata_hash_full,
                "fingerprint_algorithm": "SHA256"
            },
            "display_identifier": {
                "uuid_short": uuid_short,
                "fingerprint_short": fingerprint_short,
                "local_record_id": local_record_id
            },
            "metadata_snapshot": metadata,
            **VERSION_METADATA,
            "created": datetime.now(timezone.utc).isoformat(),
            "created_by": "VREP Reference Implementation v0.2.0"
        }
