"""
JB Academy Election Portal - Authentication Module
Handles student and admin authentication with vote integrity
"""

import hashlib
from typing import Optional, Tuple
from models import Database, Student

class Auth:
    """Authentication handler"""

    def __init__(self, db: Database):
        self.db = db
        self.student_model = Student(db)
        self.ADMIN_ID = 'admin'
        self.ADMIN_PASSWORD = 'JB2026Secure'

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(str(password).encode()).hexdigest()

    @staticmethod
    def normalize_admission(admission_no: str) -> str:
        """Normalize admission number"""
        return str(admission_no).strip().lower().split('.')[0]

    def authenticate_admin(self, user_id: str, password: str) -> bool:
        """Authenticate admin user"""
        return user_id == self.ADMIN_ID and password == self.ADMIN_PASSWORD

    def authenticate_student(self, admission_no: str, password: str) -> Optional[Tuple]:
        """Authenticate student and return student data if valid"""
        student = self.student_model.get(admission_no)

        if student and self.hash_password(password) == student[5]:  # student[5] is password hash
            return student
        return None

    def validate_credentials(self, user_id: str, password: str) -> dict:
        """
        Validate credentials and determine user type
        Returns: {'type': 'admin'|'student'|'invalid', 'data': student_tuple or None}
        """
        user_id = user_id.strip().lower()

        # Try admin login
        if self.authenticate_admin(user_id, password):
            return {'type': 'admin', 'data': None}

        # Try student login
        student = self.authenticate_student(user_id, password)
        if student:
            return {'type': 'student', 'data': student}

        return {'type': 'invalid', 'data': None}
