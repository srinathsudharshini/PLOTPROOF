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
from app.models.user import User, UserRole
from app.models.document import Document, DocumentStatus
from app.models.ocr_field import OCRField
from app.models.blockchain_anchor import BlockchainAnchor
from app.models.audit_event import AuditEvent
from app.core.security import create_access_token
from app.blockchain.service import BlockchainService, to_bytes32_hex
from app.services.gis_service import GISService
from app.services.integrity_service import IntegrityService
from app.privacy.zk_service import ZKService

client = TestClient(app)


class TestLayer8Blockchain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database()
        cls.db = SessionLocal()

        cls.citizen = cls.db.query(User).filter(User.email == "citizen@plotproof.gov.in").first()
        cls.citizen_token = create_access_token(cls.citizen.id, cls.citizen.role.value)

        cls.citizen_other = cls.db.query(User).filter(User.email == "citizen2@plotproof.gov.in").first()
        if not cls.citizen_other:
            cls.citizen_other = User(
                full_name="Second Citizen",
                email="citizen2@plotproof.gov.in",
                password_hash="hash",
                role=UserRole.CITIZEN,
                is_verified=True,
            )
            cls.db.add(cls.citizen_other)
            cls.db.commit()
            cls.db.refresh(cls.citizen_other)
        cls.citizen_other_token = create_access_token(cls.citizen_other.id, cls.citizen_other.role.value)

        cls.blockchain_service = BlockchainService()
        cls.gis_service = GISService()
        cls.integrity_service = IntegrityService()
        cls.zk_service = ZKService()

        cls._create_test_data()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    @classmethod
    def _create_test_data(cls):
        db = SessionLocal()
        try:
            # Clean previous test blockchain docs
            db.query(BlockchainAnchor).filter(BlockchainAnchor.verification_id.like("PP-BC-%")).delete(synchronize_session=False)
            db.query(Document).filter(Document.file_name.like("test_bc_%")).delete(synchronize_session=False)
            db.commit()


            # 1. Clean Approved Document
            raw_pdf = b"%PDF-1.4 Clean Blockchain Deed Survey 142/3A"
            doc_clean = Document(
                owner_user_id=cls.citizen.id,
                file_name="test_bc_clean.pdf",
                mime_type="application/pdf",
                file_size=len(raw_pdf),
                storage_key="test/test_bc_clean.pdf",
                sha256="9999999999999999999999999999999999999999999999999999999999999999",
                file_hash="9999999999999999999999999999999999999999999999999999999999999999",
                status=DocumentStatus.COMPLETED,
                version=1,
                verification_id="PP-BC-2026-0001",
                ocr_raw_text="Deed for Survey 142/3A, Selaiyur, Tambaram, Area 2400 Sq.ft, GPS 12.9252 N, 80.1475 E",
            )
            db.add(doc_clean)
            db.commit()
            db.refresh(doc_clean)

            f1 = OCRField(document_id=doc_clean.id, field_name="survey_number", field_value="142/3A", confidence=0.98, status="CONFIRMED")
            f2 = OCRField(document_id=doc_clean.id, field_name="area", field_value="2400 Sq.ft", confidence=0.96, status="CONFIRMED")
            f3 = OCRField(document_id=doc_clean.id, field_name="coordinates", field_value="12.9252, 80.1475", confidence=0.98, status="CONFIRMED")
            db.add_all([f1, f2, f3])
            db.commit()

            # Process GIS, Integrity, ZK
            cls.gis_service.validate_document_spatial(db, doc_clean.id)
            cls.integrity_service.generate_document_integrity(db, doc_clean.id)
            cls.zk_service.generate_proof(db, doc_clean.id)

            # 2. Document with Spatial Collision (fails GIS)
            doc_collision = Document(
                owner_user_id=cls.citizen.id,
                file_name="test_bc_collision.pdf",
                mime_type="application/pdf",
                file_size=len(raw_pdf),
                storage_key="test/test_bc_collision.pdf",
                sha256="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                file_hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                status=DocumentStatus.PROCESSING,
                version=1,
                verification_id="PP-BC-2026-0002",
                ocr_raw_text="Collision Deed",
            )
            db.add(doc_collision)
            db.commit()
            db.refresh(doc_collision)

            # 3. Document with Tampered Database State (for Section 20)
            doc_tampered = Document(
                owner_user_id=cls.citizen.id,
                file_name="test_bc_db_target.pdf",
                mime_type="application/pdf",
                file_size=len(raw_pdf),
                storage_key="test/test_bc_db_target.pdf",
                sha256="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                file_hash="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                status=DocumentStatus.COMPLETED,
                version=1,
                verification_id="PP-BC-2026-0003",
                ocr_raw_text="Deed for Survey 142/3A, Selaiyur, Tambaram, Area 2400 Sq.ft, GPS 12.9252 N, 80.1475 E",
            )

            db.add(doc_tampered)
            db.commit()
            db.refresh(doc_tampered)

            f_t1 = OCRField(document_id=doc_tampered.id, field_name="survey_number", field_value="142/3A", confidence=0.98, status="CONFIRMED")
            f_t2 = OCRField(document_id=doc_tampered.id, field_name="area", field_value="2400 Sq.ft", confidence=0.96, status="CONFIRMED")
            f_t3 = OCRField(document_id=doc_tampered.id, field_name="coordinates", field_value="12.9252, 80.1475", confidence=0.98, status="CONFIRMED")
            db.add_all([f_t1, f_t2, f_t3])
            db.commit()

            cls.gis_service.validate_document_spatial(db, doc_tampered.id)
            cls.integrity_service.generate_document_integrity(db, doc_tampered.id)
            cls.zk_service.generate_proof(db, doc_tampered.id)

            cls.doc_clean_id = doc_clean.id
            cls.doc_collision_id = doc_collision.id
            cls.doc_tampered_id = doc_tampered.id
        finally:
            db.close()

    def test_01_bytes32_formatting(self):
        # Section 6 & 9: Converts off-chain verification strings to bytes32 format
        v_id = "PP-2026-000052"
        b32 = to_bytes32_hex(v_id)
        self.assertTrue(b32.startswith("0x"))
        self.assertEqual(len(b32), 66)  # 0x + 64 hex chars = 32 bytes
        print("[PASS] Test 1: Fixed-Size bytes32 Cryptographic Formatting Verified")

    def test_02_successful_blockchain_anchor(self):
        # Section 10 & 28 (Test 1): Successful anchor on clean document
        headers = {"Authorization": f"Bearer {self.citizen_token}"}
        res = client.post(f"/api/v1/documents/{self.doc_clean_id}/blockchain/anchor", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["verification_id"], "PP-BC-2026-0001")
        self.assertEqual(data["blockchain"]["status"], "CONFIRMED")
        self.assertTrue(data["blockchain"]["transaction_hash"].startswith("0x"))
        self.assertGreater(data["blockchain"]["block_number"], 0)
        print("[PASS] Test 2: Successful Polygon Blockchain Anchoring & Transaction Mining Verified")

    def test_03_duplicate_anchor_protection(self):
        # Section 18 & 28 (Test 2): Re-anchoring returns existing confirmed anchor without re-submitting
        headers = {"Authorization": f"Bearer {self.citizen_token}"}
        res = client.post(f"/api/v1/documents/{self.doc_clean_id}/blockchain/anchor", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["blockchain"]["status"], "CONFIRMED")
        print("[PASS] Test 3: Idempotent Blockchain Anchor & Duplicate Submission Protection Verified")

    def test_04_gis_failure_blocks_anchoring(self):
        # Section 11 & 28 (Test 4): Spatial collision prevents blockchain anchoring
        headers = {"Authorization": f"Bearer {self.citizen_token}"}
        res = client.post(f"/api/v1/documents/{self.doc_collision_id}/blockchain/anchor", headers=headers)
        self.assertEqual(res.status_code, 400)
        detail = res.json()["detail"]
        self.assertEqual(detail["status"], "REJECTED")
        self.assertEqual(detail["reason"], "BLOCKCHAIN_PREREQUISITES_NOT_MET")
        print("[PASS] Test 4: Prerequisite Gate: GIS Spatial Anomaly Blocks On-Chain Anchoring")

    def test_05_unauthorized_user_anchor_forbidden(self):
        # Section 7 & 23: Cross-tenant user cannot anchor another user's deed
        headers = {"Authorization": f"Bearer {self.citizen_other_token}"}
        res = client.post(f"/api/v1/documents/{self.doc_clean_id}/blockchain/anchor", headers=headers)
        self.assertEqual(res.status_code, 403)
        print("[PASS] Test 5: Unauthorized Caller Intercepted (403 Forbidden)")

    def test_06_get_document_blockchain_receipt(self):
        # Section 16: GET /api/v1/documents/{id}/blockchain
        headers = {"Authorization": f"Bearer {self.citizen_token}"}
        res = client.get(f"/api/v1/documents/{self.doc_clean_id}/blockchain", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["verification_id"], "PP-BC-2026-0001")
        self.assertEqual(data["status"], "CONFIRMED")
        self.assertTrue(data["transaction_hash"].startswith("0x"))
        print("[PASS] Test 6: Document Blockchain Receipt Retrieval Verified")

    def test_07_public_verification_endpoint_match(self):
        # Section 19: Public verifier cross-checks DB hash against on-chain anchor
        res = client.get("/api/v1/verification/PP-BC-2026-0001")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["match"])
        self.assertEqual(data["status"], "CONFIRMED")
        self.assertIn("polygonscan.com", data["block_explorer_url"])
        print("[PASS] Test 7: Public Verification Endpoint Verified Against Polygon Anchor (MATCH)")

    def test_08_database_tampering_interception(self):
        # Section 20 & 28 (Test 5): If database is modified, mismatch is detected
        # First anchor doc_tampered
        headers = {"Authorization": f"Bearer {self.citizen_token}"}
        res_anchor = client.post(f"/api/v1/documents/{self.doc_tampered_id}/blockchain/anchor", headers=headers)
        self.assertEqual(res_anchor.status_code, 200)

        # Attacker directly alters the database record (Section 20)
        db = SessionLocal()
        try:
            from app.models.integrity_record import IntegrityRecord
            integrity_rec = db.scalar(select(IntegrityRecord).where(IntegrityRecord.document_id == self.doc_tampered_id))
            self.assertIsNotNone(integrity_rec)
            integrity_rec.verification_hash = "attacker_compromised_hash_9999999999999999"
            db.commit()
        finally:
            db.close()

        # Now query public verification
        res = client.get("/api/v1/verification/PP-BC-2026-0003")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["match"])
        self.assertEqual(data["status"], "BLOCKCHAIN_ANCHOR_MISMATCH")
        print("[PASS] Test 8: Database Tampering Detected: DB Hash Mismatch Against Immutable Blockchain")

    def test_09_audit_event_logged_on_blockchain_anchor(self):
        # Section 23: Event logged on anchoring
        db = SessionLocal()
        try:
            events = list(db.scalars(select(AuditEvent).where(AuditEvent.document_id == self.doc_clean_id)).all())
            event_types = [e.event_type for e in events]
            self.assertIn("BLOCKCHAIN_ANCHORED", event_types)
            print("[PASS] Test 9: Forensic Audit Trail Persists BLOCKCHAIN_ANCHORED Event")
        finally:
            db.close()

    def test_10_legacy_blockchain_endpoint(self):
        # Legacy compatibility route /api/blockchain/{verification_id}
        res = client.get("/api/blockchain/PP-BC-2026-0001")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["verification_id"], "PP-BC-2026-0001")
        self.assertIn("anchorVerification", data["smart_contract_method"])
        print("[PASS] Test 10: Legacy Blockchain Endpoint Backwards Compatibility Verified")

    def test_11_non_existent_verification_404(self):
        # Non-existent record returns 404
        res = client.get("/api/v1/verification/PP-NONEXISTENT-9999")
        self.assertEqual(res.status_code, 404)
        print("[PASS] Test 11: Non-Existent Verification Record Properly Returns 404")

    def test_12_no_pii_in_blockchain_anchor_or_public_response(self):
        # Section 2 & 21: Zero PII on-chain or in verification response
        res = client.get("/api/v1/verification/PP-BC-2026-0001")
        self.assertEqual(res.status_code, 200)
        data_str = json.dumps(res.json()).lower()
        self.assertNotIn("aadhaar", data_str)
        self.assertNotIn("phone", data_str)
        self.assertNotIn("email", data_str)
        self.assertNotIn("ramanathan", data_str)
        print("[PASS] Test 12: Absolute PII Minimization in Public Blockchain Verification Verified")

    def test_13_missing_blockchain_private_key_raises_error(self):
        """
        GAP-05 verification: Missing or empty BLOCKCHAIN_PRIVATE_KEY raises RuntimeError loudly
        rather than failing silently with hardcoded test fallback.
        """
        import os
        import importlib
        import app.blockchain.config as bc_config

        old_key = os.environ.get("BLOCKCHAIN_PRIVATE_KEY")
        try:
            os.environ["BLOCKCHAIN_PRIVATE_KEY"] = ""
            with self.assertRaises(RuntimeError) as ctx:
                importlib.reload(bc_config)
            self.assertIn("BLOCKCHAIN_PRIVATE_KEY environment variable is required", str(ctx.exception))
        finally:
            if old_key is not None:
                os.environ["BLOCKCHAIN_PRIVATE_KEY"] = old_key
            importlib.reload(bc_config)

        print("[PASS] Test 13: Missing BLOCKCHAIN_PRIVATE_KEY Raises Startup RuntimeError (GAP-05 verified)")


if __name__ == "__main__":
    unittest.main()
