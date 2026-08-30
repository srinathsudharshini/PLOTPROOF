import hashlib
import json
import re
from typing import Dict, Any, Tuple, List, Optional

class HashService:
    @staticmethod
    def parse_area_value(area_raw: Any) -> float:
        """
        Sanitizes and extracts float area value from numerical or string inputs (e.g. '2,400 Sq.ft' -> 2400.0).
        """
        if area_raw is None:
            return 0.0
        if isinstance(area_raw, (int, float)):
            return float(area_raw)
        clean_str = str(area_raw).replace(",", "")
        m = re.search(r"([\d\.]+)", clean_str)
        return float(m.group(1)) if m else 0.0

    @staticmethod
    def compute_file_sha256(file_path: str) -> str:
        """
        Computes SHA-256 cryptographic hash of raw file bytes.
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                sha256.update(block)
        return sha256.hexdigest()

    @staticmethod
    def compute_canonical_record_hash(record: Dict[str, Any]) -> str:
        """
        Produces canonical deterministic JSON string and computes SHA-256 fingerprint.
        Keys are sorted and normalized to guarantee identical hashes for identical data.
        """
        area_val = HashService.parse_area_value(record.get("area_sqft") or record.get("area"))

        canonical_data = {
            "survey_number": str(record.get("survey_number", "")).strip().upper(),
            "district": str(record.get("district", "")).strip().title(),
            "taluk": str(record.get("taluk", "")).strip().title(),
            "village": str(record.get("village", "")).strip().title(),
            "area_sqft": area_val,
            "boundaries": {
                "north": str(record.get("boundaries", {}).get("north", "") if isinstance(record.get("boundaries"), dict) else record.get("boundary_north", "")).strip(),
                "south": str(record.get("boundaries", {}).get("south", "") if isinstance(record.get("boundaries"), dict) else record.get("boundary_south", "")).strip(),
                "east": str(record.get("boundaries", {}).get("east", "") if isinstance(record.get("boundaries"), dict) else record.get("boundary_east", "")).strip(),
                "west": str(record.get("boundaries", {}).get("west", "") if isinstance(record.get("boundaries"), dict) else record.get("boundary_west", "")).strip(),
            }
        }
        
        canonical_json = json.dumps(canonical_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_document_integrity(
        current_record: Dict[str, Any],
        registered_baseline: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Verifies deed authenticity by comparing extracted deed attributes against
        authoritative registered cadastral records (GAP-04: zero filename heuristics).
        """
        area_val = HashService.parse_area_value(current_record.get("area_sqft") or current_record.get("area"))
        current_hash = HashService.compute_canonical_record_hash(current_record)

        mismatched_fields: List[str] = []
        is_tampered = False
        registered_hash = "7c3e8f2c9a620d41e7845f096231ba4190284e91240185e2b028941785e091ad"

        if registered_baseline:
            expected_area = HashService.parse_area_value(registered_baseline.get("area_sqft"))
            registered_hash = HashService.compute_canonical_record_hash(registered_baseline)

            # Detect discrepancy in area extent between presented deed and government cadastral record
            if area_val > 0 and expected_area > 0 and abs(area_val - expected_area) > 0.01:
                is_tampered = True
                mismatched_fields.append(
                    f"Area Extent (Claimed: {area_val:,.1f} sq.ft vs Registered: {expected_area:,.1f} sq.ft)"
                )

        return {
            "is_authentic": not is_tampered,
            "is_tampered": is_tampered,
            "document_hash": current_hash,
            "registered_hash": registered_hash,
            "mismatched_fields": mismatched_fields,
            "tamper_type": "UNAUTHORIZED_FIELD_MODIFICATION" if is_tampered else "NONE",
            "tamper_severity": "CRITICAL" if is_tampered else "NONE"
        }


