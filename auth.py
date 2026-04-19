"""
JB Academy Election Portal - Authentication
- DB-persisted login attempt tracking (survives restarts)
- PBKDF2-HMAC-SHA256 password hashing (replaces bare SHA-256)
- Backward-compatible: old SHA-256 hashes still work on first login,
  then get upgraded automatically
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Tuple

from models import Database, Student

MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 10


class Auth:
    def __init__(self, db: Database):
        self.db = db
        self.student_model = Student(db)
        self.ADMIN_ID = os.environ.get("ADMIN_ID", "admin")
        self.ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

        # If no env var set, check DB for stored admin hash; else use default
        if not self.ADMIN_PASSWORD:
            row = self.db.execute(
                "SELECT value FROM settings WHERE key='admin_password_hash'"
            ).fetchone()
            self._admin_hash = row[0] if row else self._legacy_hash("JB2026Secure")
        else:
            self._admin_hash = self._pbkdf2_hash(self.ADMIN_PASSWORD)

    # ── hashing ────────────────────────────────────────────────────────────────

    @staticmethod
    def _legacy_hash(password: str) -> str:
        """Old SHA-256 hash — used only for migration detection."""
        return hashlib.sha256(str(password).encode()).hexdigest()

    @staticmethod
    def _pbkdf2_hash(password: str, salt: str = None) -> str:
        """
        PBKDF2-HMAC-SHA256 with a random salt.
        Stored as  pbkdf2$<salt_hex>$<hash_hex>
        """
        if salt is None:
            salt = secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
        return f"pbkdf2${salt}${dk.hex()}"

    @staticmethod
    def _verify_password(plain: str, stored: str) -> bool:
        """Verify against both pbkdf2 and legacy sha256 formats."""
        if stored.startswith("pbkdf2$"):
            _, salt, _ = stored.split("$", 2)
            expected = Auth._pbkdf2_hash(plain, salt)
            return hmac.compare_digest(stored, expected)
        # Legacy SHA-256
        return hmac.compare_digest(stored, hashlib.sha256(plain.encode()).hexdigest())

    @classmethod
    def hash_password(cls, password: str) -> str:
        """Public API — always returns pbkdf2 hash."""
        return cls._pbkdf2_hash(password)

    # ── lockout (DB-backed) ────────────────────────────────────────────────────

    def _recent_failures(self, user_id: str) -> int:
        cutoff = (datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
        row = self.db.execute(
            """SELECT COUNT(*) FROM login_attempts
               WHERE user_id=? AND success=0 AND attempted_at>?""",
            (user_id, cutoff),
        ).fetchone()
        return row[0] if row else 0

    def _is_locked(self, user_id: str) -> Tuple[bool, int]:
        cutoff = (datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
        row = self.db.execute(
            """SELECT MIN(attempted_at) FROM login_attempts
               WHERE user_id=? AND success=0 AND attempted_at>?""",
            (user_id, cutoff),
        ).fetchone()
        failures = self._recent_failures(user_id)
        if failures >= MAX_ATTEMPTS and row and row[0]:
            unlock_at = datetime.fromisoformat(row[0]) + timedelta(
                minutes=LOCKOUT_MINUTES
            )
            remaining = max(0, int((unlock_at - datetime.now()).total_seconds()))
            return True, remaining
        return False, 0

    def _record_attempt(self, user_id: str, success: bool):
        self.db.write_many(
            [
                (
                    "INSERT INTO login_attempts (user_id,attempted_at,success) VALUES (?,?,?)",
                    (user_id, datetime.now().isoformat(), 1 if success else 0),
                )
            ]
        )
        # Prune old records (keep last 30 days)
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        self.db.write_many(
            [("DELETE FROM login_attempts WHERE attempted_at<?", (cutoff,))]
        )

    # ── admin password management ──────────────────────────────────────────────

    def set_admin_password(self, new_password: str) -> bool:
        new_hash = self._pbkdf2_hash(new_password)
        return self.db.write_many(
            [
                (
                    "INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,?)",
                    ("admin_password_hash", new_hash, datetime.now().isoformat()),
                )
            ]
        )

    # ── main validation ────────────────────────────────────────────────────────

    def validate_credentials(self, user_id: str, password: str) -> dict:
        user_id = str(user_id).strip().lower()

        locked, remaining = self._is_locked(user_id)
        if locked:
            mins = remaining // 60
            secs = remaining % 60
            return {
                "type": "locked",
                "data": None,
                "message": f"Account locked. Try again in {mins}m {secs}s.",
            }

        # Admin check
        if user_id == self.ADMIN_ID.lower():
            if self._verify_password(password, self._admin_hash):
                self._record_attempt(user_id, True)
                return {"type": "admin", "data": None, "message": ""}
            self._record_attempt(user_id, False)
            failures = self._recent_failures(user_id)
            left = max(0, MAX_ATTEMPTS - failures)
            return {
                "type": "invalid",
                "data": None,
                "message": f"Invalid credentials. {left} attempt(s) remaining.",
            }

        # Student check
        student = self.student_model.get(user_id)
        if student and self._verify_password(password, student[5]):
            # Upgrade legacy hash silently
            if not student[5].startswith("pbkdf2$"):
                self.student_model.reset_password(
                    user_id, self._pbkdf2_hash(password), student[6] or ""
                )
            self._record_attempt(user_id, True)
            return {"type": "student", "data": student, "message": ""}

        self._record_attempt(user_id, False)
        locked, remaining = self._is_locked(user_id)
        if locked:
            msg = (
                f"Too many failed attempts. "
                f"Locked for {remaining // 60}m {remaining % 60}s."
            )
            return {
                "type": "locked",
                "data": None,
                "message": msg,
            }
        failures = self._recent_failures(user_id)
        left = max(0, MAX_ATTEMPTS - failures)
        return {
            "type": "invalid",
            "data": None,
            "message": f"Invalid credentials. {left} attempt(s) remaining.",
        }

    @staticmethod
    def normalize_admission(admission_no: str) -> str:
        return str(admission_no).strip().lower().split(".")[0]
