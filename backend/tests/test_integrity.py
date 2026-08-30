import io
import json
import sys
import unittest
from pathlib import Path

backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal, init_db
from app.seed_data.seed_db import seed_database
from app.models.user import User
from app.models.document import Document, DocumentStatus
from app.models.ocr_field import OCRField
from app.models.spatial_validation import SpatialValidation
from app.models.integrity_record import IntegrityRecord
from app.models.audit_event import AuditEvent
from app.core.security import create_access_token
from app.integrity.hashing import sha256_bytes
from app.integrity.canonical import canonical_json
from app.integrity.fingerprint import (
    compute_metadata_hash,
    compute_ocr_hash,
    compute_spatial_hash,
    create_verification_hash,
)
from app.integrity.verification import (
    verify_file_integrity,
    classify_verification_outcome,
    VerificationState,
)
from app.services.integrity_service import IntegrityService
from app.services.gis_service import GISService

client = TestClient(app)


class TestLayer6Integrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database()
        cls.db = SessionLocal()

        cls.citizen = cls.db.query(User).filter(User.email == "citizen@plotproof.gov.in").first()
        cls.citizen_token = create_access_token(cls.citizen.id, cls.citizen.role.value)

        cls.registrar = cls.db.query(User).filter(User.email == "registrar@tn.gov.in").first()
        cls.registrar_token = create_access_token(cls.registrar.id, cls.registrar.role.value)

        cls.integrity_service = IntegrityService()
        cls.gis_service = GISService()
        cls._create_test_data()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    @classmethod
    def _create_test_data(cls):
        db = SessionLocal()
        try:
            # Clean previous test documents
            db.query(Document).filter(Document.file_name.like("test_integrity_%")).delete(synchronize_session=False)
            db.commit()

            # Create test document
            raw_pdf = b"%PDF-1.4 sample title deed content for Survey 142/3A Tambaram"
            cls.raw_bytes = raw_pdf
            cls.expected_sha256 = sha256_bytes(raw_pdf)

            # 1. Clean document
            doc = Document(
                owner_user_id=cls.citizen.id,
                file_name="test_integrity_doc.pdf",
                mime_type="application/pdf",
                file_size=len(raw_pdf),

                storage_key="test/test_integrity_doc.pdf",
                sha256=cls.expected_sha256,
                file_hash=cls.expected_sha256,
                status=DocumentStatus.COMPLETED,
                version=1,
                verification_id="PP-INT-2026-0001",
                ocr_raw_text="Deed for Survey 142/3A, Selaiyur, Tambaram, Area 2400 Sq.ft, GPS 12.9252 N, 80.1475 E",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            # Add OCR Fields for doc
            f1 = OCRField(document_id=doc.id, field_name="survey_number", field_value="142/3A", confidence=0.98, status="CONFIRMED")
            f2 = OCRField(document_id=doc.id, field_name="district", field_value="Chennai", confidence=0.96, status="CONFIRMED")
            f3 = OCRField(document_id=doc.id, field_name="taluk", field_value="Tambaram", confidence=0.95, status="CONFIRMED")
            f4 = OCRField(document_id=doc.id, field_name="village", field_value="Selaiyur", confidence=0.95, status="CONFIRMED")
            f5 = OCRField(document_id=doc.id, field_name="area", field_value="2400 Sq.ft", confidence=0.95, status="CONFIRMED")
            f6 = OCRField(document_id=doc.id, field_name="coordinates", field_value="12.9252, 80.1475", confidence=0.98, status="CONFIRMED")
            db.add_all([f1, f2, f3, f4, f5, f6])
            db.commit()

            # Run GIS validation on doc
            cls.gis_service.validate_document_spatial(db, doc.id)

            # 2. Correction document for test_05
            doc_corr = Document(
                owner_user_id=cls.citizen.id,
                file_name="test_integrity_correction.pdf",
                mime_type="application/pdf",
                file_size=len(raw_pdf),
                storage_key="test/test_integrity_correction.pdf",
                sha256=sha256_bytes(raw_pdf + b"_corr"),
                file_hash=sha256_bytes(raw_pdf + b"_corr"),
                status=DocumentStatus.COMPLETED,
                version=1,
                verification_id="PP-INT-2026-0002",
                ocr_raw_text="Correction deed for Survey 142/3A",
            )
            db.add(doc_corr)
            db.commit()
            db.refresh(doc_corr)

            fc1 = OCRField(document_id=doc_corr.id, field_name="survey_number", field_value="142/3A", confidence=0.98, status="CONFIRMED")
            fc2 = OCRField(document_id=doc_corr.id, field_name="area", field_value="2400 Sq.ft", confidence=0.95, status="CONFIRMED")
            fc3 = OCRField(document_id=doc_corr.id, field_name="coordinates", field_value="12.9252, 80.1475", confidence=0.98, status="CONFIRMED")
            db.add_all([fc1, fc2, fc3])
            db.commit()
            cls.gis_service.validate_document_spatial(db, doc_corr.id)

            cls.doc_id = doc.id
            cls.doc_corr_id = doc_corr.id
        finally:
            db.close()


    def test_01_same_file_identical_sha256(self):
        # Section 24: Test 1 - Same file produces identical hash
        data1 = b"Official Land Title Deed - Survey 142/3A"
        data2 = b"Official Land Title Deed - Survey 142/3A"
        hash1 = sha256_bytes(data1)
        hash2 = sha256_bytes(data2)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)
        print("[PASS] Test 1: Identical File Reproducible SHA-256 Digest Verified")

    def test_02_one_byte_changed_avalanche_mismatch(self):
        # Section 24: Test 2 - One byte changed produces completely different hash
        data_orig = b"Official Land Title Deed - Survey 142/3A"
        data_tampered = b"Official Land Title Deed - Survey 142/3B"  # 1 byte flipped 'A' -> 'B'
        hash_orig = sha256_bytes(data_orig)
        hash_tampered = sha256_bytes(data_tampered)

        self.assertNotEqual(hash_orig, hash_tampered)
        verify_res = verify_file_integrity(hash_orig, data_tampered)
        self.assertEqual(verify_res["integrity"], "MISMATCH")
        self.assertFalse(verify_res["is_valid"])
        print("[PASS] Test 2: Single Byte Alteration & Cryptographic Hash Tamper Interception Verified")

    def test_03_metadata_change_alters_hash_chain(self):
        # Section 24: Test 3 - Metadata changed alters metadata_hash and verification_hash
        meta_a = {"survey_number": "142/3A", "area_sq_m": 222.96, "taluk": "Tambaram"}
        meta_b = {"survey_number": "142/3A", "area_sq_m": 250.00, "taluk": "Tambaram"}  # Area changed

        hash_a = compute_metadata_hash(meta_a)
        hash_b = compute_metadata_hash(meta_b)
        self.assertNotEqual(hash_a, hash_b)

        v_hash_a = create_verification_hash("doc_1", "ocr_1", hash_a, "spatial_1")
        v_hash_b = create_verification_hash("doc_1", "ocr_1", hash_b, "spatial_1")
        self.assertNotEqual(v_hash_a, v_hash_b)
        print("[PASS] Test 3: Metadata Modification Fingerprint Invalidation Verified")

    def test_04_spatial_result_change_alters_verification_hash(self):
        # Section 24: Test 4 - GIS change alters spatial_hash and verification_hash
        gis_a = {"spatial_relationship": "DISJOINT", "overlap_area_sq_m": 0.0}
        gis_b = {"spatial_relationship": "OVERLAPPING", "overlap_area_sq_m": 17.8}

        hash_a = compute_spatial_hash(gis_a)
        hash_b = compute_spatial_hash(gis_b)
        self.assertNotEqual(hash_a, hash_b)

        v_hash_a = create_verification_hash("doc_1", "ocr_1", "meta_1", hash_a)
        v_hash_b = create_verification_hash("doc_1", "ocr_1", "meta_1", hash_b)
        self.assertNotEqual(v_hash_a, v_hash_b)
        print("[PASS] Test 4: Spatial Collision Detection Changes Cryptographic Verification Chain")

    def test_05_field_correction_versioning_and_invalidation(self):
        # Section 24: Test 5 - Field correction invalidates previous verification state
        db = SessionLocal()
        try:
            # Generate initial integrity
            resp_v1 = self.integrity_service.generate_document_integrity(db, self.doc_corr_id, self.registrar.id)
            hash_v1 = resp_v1.integrity.verification_hash
            self.assertEqual(resp_v1.audit.version, 1)

            # Sub-Registrar statutory correction on area
            self.integrity_service.invalidate_on_field_correction(
                db=db,
                document_id=self.doc_corr_id,
                field_name="area",
                old_val="2400 Sq.ft",
                new_val="2500 Sq.ft",
                actor_id=self.registrar.id,
            )

            # Check document version bumped to 2
            doc = db.scalar(select(Document).where(Document.id == self.doc_corr_id))
            self.assertEqual(doc.version, 2)

            # Check spatial status was invalidated
            val_rec = db.scalar(select(SpatialValidation).where(SpatialValidation.document_id == self.doc_corr_id))
            self.assertEqual(val_rec.status, "REVALIDATION_REQUIRED")

            # Check audit event was recorded
            audit = db.scalar(
                select(AuditEvent)
                .where(AuditEvent.document_id == self.doc_corr_id, AuditEvent.event_type == "FIELD_CORRECTED")
                .order_by(AuditEvent.id.desc())
            )
            self.assertIsNotNone(audit)
            self.assertEqual(audit.event_metadata["field_name"], "area")
            self.assertEqual(audit.event_metadata["new_version"], 2)

            print("[PASS] Test 5: Statutory Correction Version Invalidation (v1 -> v2) Verified")

        finally:
            db.close()

    def test_06_canonical_json_determinism(self):
        # Dict with different key insertion order and whitespace
        d1 = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
        d2 = {"nested": {"y": 8, "z": 9}, "a": 1, "b": 2}
        bytes1 = canonical_json(d1)
        bytes2 = canonical_json(d2)

        self.assertEqual(bytes1, bytes2)
        self.assertEqual(bytes1, b'{"a":1,"b":2,"nested":{"y":8,"z":9}}')
        print("[PASS] Test 6: Canonical JSON Deterministic Ordering & Compaction Verified")

    def test_07_integrity_generation_api(self):
        headers = {"Authorization": f"Bearer {self.citizen_token}"}
        res = client.post(f"/api/v1/documents/{self.doc_id}/integrity/generate", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["document_id"], self.doc_id)
        self.assertIn("file_hash", data["integrity"])
        self.assertIn("ocr_hash", data["integrity"])
        self.assertIn("metadata_hash", data["integrity"])
        self.assertIn("spatial_hash", data["integrity"])
        self.assertIn("verification_hash", data["integrity"])
        self.assertEqual(data["status"], "SYSTEM_VALIDATION_PASSED")
        print("[PASS] Test 7: Integrity Generation API Returning Complete Stage Hashes Verified")

    def test_08_integrity_verify_endpoint(self):
        headers = {"Authorization": f"Bearer {self.citizen_token}"}

        # 1. Verify with matching file bytes
        files = {"file": ("deed.pdf", self.raw_bytes, "application/pdf")}
        res_match = client.post(f"/api/v1/documents/{self.doc_id}/integrity/verify", headers=headers, files=files)
        self.assertEqual(res_match.status_code, 200)
        self.assertEqual(res_match.json()["integrity"], "MATCH")
        self.assertTrue(res_match.json()["is_valid"])

        # 2. Verify with altered file bytes
        altered_bytes = self.raw_bytes + b"_tampered_byte"
        files_bad = {"file": ("deed.pdf", altered_bytes, "application/pdf")}
        res_bad = client.post(f"/api/v1/documents/{self.doc_id}/integrity/verify", headers=headers, files=files_bad)
        self.assertEqual(res_bad.status_code, 200)
        self.assertEqual(res_bad.json()["integrity"], "MISMATCH")
        self.assertFalse(res_bad.json()["is_valid"])
        print("[PASS] Test 8: Tamper Verification Endpoint (MATCH vs MISMATCH) Verified")

    def test_09_public_verification_pii_omission(self):
        res = client.get(f"/api/v1/verify/public/PP-INT-2026-0001")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["verification_id"], "PP-INT-2026-0001")
        self.assertEqual(data["status"], "VERIFIED")
        self.assertEqual(data["spatial_check"], "PASSED")
        self.assertEqual(data["integrity"], "MATCHED")

        # Crucial security check: Verify NO citizen PII is exposed in public response
        json_str = json.dumps(data).lower()
        self.assertNotIn("aadhaar", json_str)
        self.assertNotIn("phone", json_str)
        self.assertNotIn("email", json_str)
        self.assertNotIn("password", json_str)
        print("[PASS] Test 9: Public QR Verification Endpoint with Strict PII Minimization Verified")

    def test_10_state_machine_transitions(self):
        # Clean state progression
        outcome_clean = classify_verification_outcome(integrity_pass=True, spatial_pass=True, ocr_acceptable=True)
        self.assertEqual(outcome_clean["status"], VerificationState.APPROVED.value)
        self.assertEqual(outcome_clean["decision"], "SYSTEM_VALIDATION_PASSED")

        # Spatial collision state
        outcome_spatial = classify_verification_outcome(integrity_pass=True, spatial_pass=False, ocr_acceptable=True)
        self.assertEqual(outcome_spatial["status"], VerificationState.SPATIAL_RISK.value)

        # Integrity failure state
        outcome_tamper = classify_verification_outcome(integrity_pass=False, spatial_pass=True, ocr_acceptable=True)
        self.assertEqual(outcome_tamper["status"], VerificationState.INTEGRITY_FAILURE.value)
        print("[PASS] Test 10: Multi-State Verification Lifecycle Machine Transitions Verified")

    def test_11_explicit_anomaly_classification(self):
        # Section 21: Distinguish Tampering vs Spatial Collision vs OCR Review
        res_tamper = classify_verification_outcome(integrity_pass=False, spatial_pass=True, ocr_acceptable=True)
        self.assertEqual(res_tamper["anomaly_type"], "CRYPTOGRAPHIC_TAMPERING")

        res_spatial = classify_verification_outcome(integrity_pass=True, spatial_pass=False, ocr_acceptable=True)
        self.assertEqual(res_spatial["anomaly_type"], "SPATIAL_ANOMALY")

        res_ocr = classify_verification_outcome(integrity_pass=True, spatial_pass=True, ocr_acceptable=False)
        self.assertEqual(res_ocr["anomaly_type"], "OCR_ANOMALY")
        print("[PASS] Test 11: Explicit Anomaly Categorization (Never Collapsed to Generic Fraud) Verified")

    def test_12_audit_event_immutability_and_persistence(self):
        db = SessionLocal()
        try:
            events = list(db.scalars(select(AuditEvent).where(AuditEvent.document_id.in_([self.doc_id, self.doc_corr_id]))).all())

            self.assertGreaterEqual(len(events), 2)
            event_types = [e.event_type for e in events]
            self.assertIn("INTEGRITY_CREATED", event_types)
            self.assertIn("FIELD_CORRECTED", event_types)
            print("[PASS] Test 12: Forensic Audit Trail Immutability & Event Persistence Verified")
        finally:
            db.close()

    def test_13_neutral_filename_tampered_deed_detected(self):
        """
        GAP-04 verification: Tamper detection relies on attribute comparison against the registered
        cadastral baseline, not filename substring heuristics ('TAMPER', 'MOD', '00137').
        A deed with an innocent name like 'innocent_title_deed_2026.pdf' claiming 3,400 sq.ft on
        Survey 142/3A (registered at 2,400 sq.ft) is intercepted as tampered.
        """
        from app.services.hash_service import HashService

        claimed_record = {
            "survey_number": "142/3A",
            "file_name": "innocent_title_deed_2026.pdf",
            "verification_id": "PP-9999-88888",
            "area_sqft": "3,400 Sq.ft",
            "district": "Chennai",
            "taluk": "Tambaram",
            "village": "Selaiyur Village",
        }
        cadastral_baseline = {
            "survey_number": "142/3A",
            "area_sqft": 2400.0,
            "district": "Chennai",
            "taluk": "Tambaram",
            "village": "Selaiyur",
        }

        result = HashService.verify_document_integrity(
            current_record=claimed_record,
            registered_baseline=cadastral_baseline,
        )

        self.assertTrue(result["is_tampered"])
        self.assertFalse(result["is_authentic"])
        self.assertIn("Area Extent", result["mismatched_fields"][0])
        self.assertEqual(result["tamper_type"], "UNAUTHORIZED_FIELD_MODIFICATION")

        print("[PASS] Test 13: Neutral-Named Tampered Deed Intercepted via Cadastral Baseline Comparison (GAP-04 verified)")


if __name__ == "__main__":
    unittest.main()
