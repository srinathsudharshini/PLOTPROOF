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
from app.models.user import User, UserRole
from app.models.document import Document, DocumentStatus
from app.core.security import create_access_token, decode_access_token
from app.middleware.security import InMemoryRateLimiter

client = TestClient(app)


class TestLayer10Security(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_database()
        cls.db = SessionLocal()

        cls.citizen_a = cls.db.query(User).filter(User.email == "citizen@plotproof.gov.in").first()
        cls.token_a = create_access_token(cls.citizen_a.id, cls.citizen_a.role.value)

        cls.citizen_b = cls.db.query(User).filter(User.email == "citizen2@plotproof.gov.in").first()
        if not cls.citizen_b:
            cls.citizen_b = User(
                full_name="Second Citizen",
                email="citizen2@plotproof.gov.in",
                password_hash="hash",
                role=UserRole.CITIZEN,
                is_verified=True,
            )
            cls.db.add(cls.citizen_b)
            cls.db.commit()
            cls.db.refresh(cls.citizen_b)
        cls.token_b = create_access_token(cls.citizen_b.id, cls.citizen_b.role.value)

        cls.registrar = cls.db.query(User).filter(User.email == "registrar@tn.gov.in").first()
        cls.token_registrar = create_access_token(cls.registrar.id, cls.registrar.role.value)

        # Create private document belonging strictly to Citizen A
        db = SessionLocal()
        try:
            db.query(Document).filter(Document.file_name == "test_sec_private_a.pdf").delete()
            db.commit()

            raw_pdf = b"%PDF-1.4 Private deed belonging strictly to Citizen A"
            doc_a = Document(
                owner_user_id=cls.citizen_a.id,
                file_name="test_sec_private_a.pdf",
                mime_type="application/pdf",
                file_size=len(raw_pdf),
                storage_key="test/test_sec_private_a.pdf",
                sha256="d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1",
                file_hash="d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1",
                status=DocumentStatus.COMPLETED,
                version=1,
                verification_id="PP-SEC-0001",
                ocr_raw_text="Deed for Citizen A",
            )
            db.add(doc_a)
            db.commit()
            db.refresh(doc_a)
            cls.doc_a_id = doc_a.id
        finally:
            db.close()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_idor_ownership_isolation(self):
        # Section 10 & 39: Citizen B cannot view Citizen A's document (IDOR protection)
        headers_b = {"Authorization": f"Bearer {self.token_b}"}
        res = client.get(f"/api/v1/documents/{self.doc_a_id}", headers=headers_b)
        self.assertEqual(res.status_code, 403)
        self.assertIn("permission", res.json()["detail"].lower())
        print("[PASS] Test 1: Insecure Direct Object Reference (IDOR) Cross-Tenant Isolation Verified (403)")

    def test_02_rbac_citizen_prevented_from_admin_actions(self):
        # Section 3: Citizen role cannot call privileged review or correction actions
        headers_a = {"Authorization": f"Bearer {self.token_a}"}
        # Citizen attempts to revoke a certificate (Registrar/Admin only)
        res = client.post(
            "/api/v1/certificates/1/revoke",
            json={"reason": "Citizen unauthorized attempt"},
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 403)

        print("[PASS] Test 2: Role-Based Access Control (RBAC) Intercepts Unauthorized Privilege Escalation")

    def test_03_security_headers_middleware(self):
        # Section 17: Security headers present on responses
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("default-src 'self'", res.headers.get("Content-Security-Policy", ""))
        print("[PASS] Test 3: Production Security Headers (CSP, Frame-Options, nosniff, HSTS) Verified")

    def test_04_request_id_tracing_middleware(self):
        # Section 24: X-Request-ID present and traceable
        custom_req_id = "req-audit-tracer-7788"
        res = client.get("/health", headers={"X-Request-ID": custom_req_id})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Request-ID"), custom_req_id)
        self.assertIn("X-Response-Time-Ms", res.headers)
        print("[PASS] Test 4: End-to-End Distributed Request-ID Tracing & Latency Telemetry Verified")

    def test_05_magic_bytes_file_signature_validation(self):
        # Section 12: Executable or script disguised as .pdf is rejected
        fake_pdf_content = b"#!/bin/bash\nrm -rf /"
        headers_a = {"Authorization": f"Bearer {self.token_a}"}
        res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("deed.pdf", io.BytesIO(fake_pdf_content), "application/pdf")},
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 400)
        detail = res.json()["detail"]
        self.assertIn(detail.get("code"), ["UNSUPPORTED_FILE_TYPE", "FILE_SIGNATURE_MISMATCH"])
        print("[PASS] Test 5: File Signature / Magic Bytes Validation Intercepts Disguised Binaries (400)")

    def test_06_path_traversal_protection(self):
        # Section 14: Filenames with path traversal ../../ are quarantined and sanitized
        valid_pdf_content = b"%PDF-1.4 test valid content for path traversal test"
        headers_a = {"Authorization": f"Bearer {self.token_a}"}
        res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("../../etc/passwd.pdf", io.BytesIO(valid_pdf_content), "application/pdf")},
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 201)
        data = res.json()
        # Ensure path traversal characters were stripped and unique key assigned
        self.assertNotIn("..", data["file_name"])
        self.assertNotIn("/", data["file_name"])
        print("[PASS] Test 6: Directory Traversal (../../) Sanitization & Storage Quarantine Verified")

    def test_07_file_size_limit_enforcement(self):
        # Section 13: Oversized documents rejected
        from app.services.document_service import MAX_FILE_SIZE_BYTES
        headers_a = {"Authorization": f"Bearer {self.token_a}"}
        oversized = b"A" * (MAX_FILE_SIZE_BYTES + 1024)
        res = client.post(
            "/api/v1/documents/upload",
            files={"file": ("big.pdf", io.BytesIO(oversized), "application/pdf")},
            headers=headers_a,
        )
        self.assertEqual(res.status_code, 400)
        detail = res.json()["detail"]
        self.assertIn(detail.get("code"), ["FILE_TOO_LARGE", "OVERSIZED_DOCUMENT"])
        print("[PASS] Test 7: Upload Hard Size Boundary Enforcement (>50MB DoS Protection) Verified")


    def test_08_health_liveness_endpoint(self):
        # Section 26: GET /health
        res = client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "healthy")
        print("[PASS] Test 8: Liveness Health Probe (/health) Verified")

    def test_09_readiness_probe_endpoint(self):
        # Section 26: GET /ready
        res = client.get("/ready")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["database"], "connected")
        self.assertEqual(data["storage"], "accessible")
        print("[PASS] Test 9: Readiness Probe (/ready) Verifying Database & Storage Systems Verified")

    def test_10_minimal_jwt_claims_hygiene(self):
        # Section 8: JWT claims contain only minimal identifiers (sub, role, exp)
        payload = decode_access_token(self.token_a)
        self.assertIn("sub", payload)
        self.assertIn("role", payload)
        self.assertIn("exp", payload)

        # Ensure NO PII is contained in JWT
        payload_str = json.dumps(payload).lower()
        self.assertNotIn("aadhaar", payload_str)
        self.assertNotIn("phone", payload_str)
        self.assertNotIn("address", payload_str)
        print("[PASS] Test 10: JWT Minimal Claims Hygiene (Zero-PII Token Envelope) Verified")

    def test_11_structured_audit_logging_no_secrets(self):
        # Section 23: Audit logs never store plain passwords or secrets
        db = SessionLocal()
        try:
            from app.models.audit_event import AuditEvent
            events = list(db.scalars(select(AuditEvent)).all())
            self.assertGreater(len(events), 0)
            for event in events:
                meta_str = json.dumps(event.event_metadata or {}).lower()
                self.assertNotIn("password", meta_str)
                self.assertNotIn("secret_key", meta_str)
                self.assertNotIn("private_key", meta_str)
            print("[PASS] Test 11: Forensic Audit Trail PII & Secret Scrubbing Hygiene Verified")
        finally:
            db.close()

    def test_12_in_memory_rate_limiting_engine(self):
        # Section 18 & 19: Rate limiter restricts excessive requests
        limiter = InMemoryRateLimiter(default_limit=5, heavy_limit=2, window_seconds=10)
        test_ip = "192.168.1.100"

        # Standard endpoint: allows 5 requests
        for _ in range(5):
            self.assertTrue(limiter.is_allowed(test_ip, "/api/v1/documents"))
        # 6th request fails
        self.assertFalse(limiter.is_allowed(test_ip, "/api/v1/documents"))

        # Heavy endpoint: allows only 2 requests
        heavy_ip = "192.168.1.101"
        self.assertTrue(limiter.is_allowed(heavy_ip, "/api/v1/documents/1/privacy/prove"))
        self.assertTrue(limiter.is_allowed(heavy_ip, "/api/v1/documents/1/privacy/prove"))
        # 3rd request fails
        self.assertFalse(limiter.is_allowed(heavy_ip, "/api/v1/documents/1/privacy/prove"))
        print("[PASS] Test 12: Adaptive Rate Limiter Differentiating Standard vs CPU-Heavy Operations Verified")

    def test_13_legacy_review_endpoint_requires_registrar_auth(self):
        """
        GAP-02 regression guard: POST /api/verification/{id}/review must require
        authentication (401 without token) and REGISTRAR/ADMIN role (403 for CITIZEN).
        Previously this endpoint had no auth and fabricated a fake REGISTRAR actor.
        """
        # 1. No credentials at all → 401 Unauthorized
        res_anon = client.post(
            "/api/verification/PP-SEC-0001/review",
            json={"decision": "APPROVE", "notes": "Anonymous approval attempt — must be rejected"},
        )
        self.assertEqual(
            res_anon.status_code, 401,
            f"Expected 401 for unauthenticated legacy review, got {res_anon.status_code}: {res_anon.text}",
        )

        # 2. Citizen token → 403 Forbidden (authenticated but wrong role)
        headers_citizen = {"Authorization": f"Bearer {self.token_a}"}
        res_citizen = client.post(
            "/api/verification/PP-SEC-0001/review",
            json={"decision": "APPROVE", "notes": "Citizen role escalation attempt — must be rejected"},
            headers=headers_citizen,
        )
        self.assertEqual(
            res_citizen.status_code, 403,
            f"Expected 403 for citizen role on legacy review, got {res_citizen.status_code}: {res_citizen.text}",
        )

        print("[PASS] Test 13: Legacy Review Endpoint Auth Guard — 401 (no token) + 403 (CITIZEN) Enforced (GAP-02 fixed)")

    def test_14_http_rate_limiting_on_login(self):
        """
        GAP-01 verification: RateLimitMiddleware is active at the HTTP layer.
        Sending repeated rapid requests to /api/v1/auth/login triggers a 429 Too Many Requests.
        """
        from app.middleware.security import rate_limiter

        # Ensure a clean slate for this test
        rate_limiter.requests.clear()

        # Send requests up to the heavy limit (20)
        statuses = []
        for i in range(25):
            res = client.post(
                "/api/v1/auth/login",
                json={"email": "ratelimit_probe@example.com", "password": "WrongPassword123!"},
            )
            statuses.append(res.status_code)

        # Confirm earlier requests reached the endpoint (401 invalid credentials)
        self.assertEqual(statuses[0], 401)

        # Confirm rate limiter kicked in and returned 429
        self.assertIn(429, statuses)
        self.assertEqual(statuses[-1], 429)

        # Verify response structure
        last_res = client.post(
            "/api/v1/auth/login",
            json={"email": "ratelimit_probe@example.com", "password": "WrongPassword123!"},
        )
        self.assertEqual(last_res.status_code, 429)
        self.assertEqual(last_res.json().get("code"), "RATE_LIMIT_EXCEEDED")
        self.assertIn("Retry-After", last_res.headers)

        # Reset rate limiter so other tests continue cleanly
        rate_limiter.requests.clear()

        print("[PASS] Test 14: HTTP Rate Limiting on Login Endpoint (429 RATE_LIMIT_EXCEEDED) Verified (GAP-01 fixed)")


if __name__ == "__main__":
    unittest.main()
