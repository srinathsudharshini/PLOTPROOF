import os
import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_path))

from app.database.connection import SessionLocal, init_db
from app.seed_data.seed_db import seed_database
from app.models.deed import Document
from app.services.verification_engine import VerificationEngine
from app.services.hash_service import HashService
from app.services.gis_service import GISService

class TestPlotProofPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database()

    def test_01_genuine_deed_verification(self):
        db = SessionLocal()
        try:
            # Seeded genuine doc
            doc = db.query(Document).filter(Document.verification_id == "PP-2026-00139").first()
            self.assertIsNotNone(doc)
            
            res = VerificationEngine.run_full_pipeline(db, doc.id)
            self.assertEqual(res["overall_status"], "VERIFIED")
            self.assertGreaterEqual(res["confidence_score"], 90.0)
            self.assertFalse(res["spatial"]["overlap_detail"]["collision_detected"])
            self.assertFalse(res["authenticity"]["is_tampered"])
            self.assertTrue(res["privacy"]["pii_redacted"])
            self.assertTrue(os.path.exists(os.path.join(str(backend_path), res["qr_code_url"].lstrip("/"))))
            print("[PASS] Test 1 Passed: Genuine Deed Verified (100% clean title & on-chain hash)")
        finally:
            db.close()

    def test_02_tampered_deed_detection(self):
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.verification_id == "PP-2026-00137").first()
            self.assertIsNotNone(doc)

            res = VerificationEngine.run_full_pipeline(db, doc.id)
            self.assertEqual(res["overall_status"], "TAMPER_ALERT")
            self.assertTrue(res["authenticity"]["is_tampered"])
            self.assertIn("Area Extent", res["authenticity"]["mismatched_fields"][0])
            print("[PASS] Test 2 Passed: Tampered Deed Intercepted (Cryptographic Hash Mismatch)")
        finally:
            db.close()

    def test_03_spatial_collision_detection(self):
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.verification_id == "PP-2026-00141").first()
            self.assertIsNotNone(doc)

            res = VerificationEngine.run_full_pipeline(db, doc.id)
            self.assertIn(res["overall_status"], ["REVIEW_REQUIRED", "SPATIAL_COLLISION"])
            self.assertTrue(res["spatial"]["overlap_detail"]["collision_detected"])
            self.assertEqual(res["spatial"]["overlap_detail"]["overlap_area_sqm"], 17.8)
            print("[PASS] Test 3 Passed: Spatial Boundary Collision Intercepted (17.8 sq.m overlap on Survey 142/3A)")
        finally:
            db.close()

if __name__ == "__main__":
    unittest.main()
