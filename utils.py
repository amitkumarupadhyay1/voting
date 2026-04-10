"""
JB Academy Election Portal - Utilities
Common helper functions
"""

import random
import pandas as pd
from io import BytesIO
from typing import List, Tuple
from datetime import datetime
from models import Database, Student

class Utils:
    """Utility functions"""

    @staticmethod
    def generate_password() -> str:
        """Generate random 6-digit password"""
        return str(random.randint(100000, 999999))

    @staticmethod
    def create_password_file(students: List[Tuple]) -> bytes:
        """
        Create Excel file with student passwords
        Format: Admission No | Name | Password | Class | Section | House
        """
        if not students:
            return None

        data = []
        for student in students:
            data.append({
                'Admission No': student[0],
                'Name': student[1],
                'Password': student[6] if len(student) > 6 else 'N/A',
                'Class': student[2],
                'Section': student[3],
                'House': student[4],
            })

        df = pd.DataFrame(data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Passwords')

        return output.getvalue()

    @staticmethod
    def validate_student_data(row: dict) -> Tuple[bool, str, dict]:
        """
        Validate student row from Excel
        Returns: (is_valid, error_message, cleaned_data)
        """
        valid_houses = {'Taxila', 'Janata', 'Saachi', 'Nalanda'}
        valid_classes = {'7', '8', '9', '10', '11', '12'}
        valid_sections = {'A', 'B', 'C'}

        # Extract and clean data
        try:
            admission_no = str(row.get('admission_no', '')).strip().lower().split('.')[0]
            name = str(row.get('name', '')).strip()
            cls = str(row.get('class', '')).strip().split('.')[0]
            section = str(row.get('section', 'A')).strip().upper()
            house = str(row.get('house', '')).strip()

            # Validate
            if not admission_no or len(admission_no) < 2:
                return False, "Invalid admission number", {}

            if not name or len(name) < 2:
                return False, "Invalid student name", {}

            if cls not in valid_classes:
                return False, f"Invalid class (must be 7-12)", {}

            if section not in valid_sections:
                return False, f"Invalid section (must be A, B, or C)", {}

            if house not in valid_houses:
                return False, f"Invalid house", {}

            return True, "", {
                'admission_no': admission_no,
                'name': name,
                'class': cls,
                'section': section,
                'house': house
            }

        except Exception as e:
            return False, f"Error: {str(e)}", {}

    @staticmethod
    def import_students_from_excel(df: pd.DataFrame, db: Database) -> Tuple[int, int, List[str]]:
        """
        Import students from DataFrame
        Returns: (imported_count, error_count, error_messages)
        """
        imported = 0
        errors = []
        student_model = Student(db)

        # Normalize column names
        df.columns = [col.strip().lower() for col in df.columns]

        # Check required columns
        required = {'admission_no', 'name', 'class', 'section', 'house'}
        if not required.issubset(set(df.columns)):
            missing = required - set(df.columns)
            return 0, len(df), [f"Missing columns: {', '.join(missing)}"]

        for idx, row in df.iterrows():
            is_valid, error_msg, data = Utils.validate_student_data(row)

            if not is_valid:
                errors.append(f"Row {idx+2}: {error_msg}")
                continue

            # Check for duplicates
            if student_model.get(data['admission_no']):
                errors.append(f"Row {idx+2}: Student {data['admission_no']} already exists")
                continue

            # Generate password
            password = Utils.generate_password()
            from auth import Auth
            password_hash = Auth.hash_password(password)

            # Add to database
            if student_model.add(
                data['admission_no'],
                data['name'],
                data['class'],
                data['section'],
                data['house'],
                password_hash,
                password
            ):
                imported += 1
            else:
                errors.append(f"Row {idx+2}: Failed to import {data['admission_no']}")

        return imported, len(errors), errors

    @staticmethod
    def format_timestamp(ts: str) -> str:
        """Format ISO timestamp for display"""
        try:
            dt = datetime.fromisoformat(ts)
            return dt.strftime("%d-%m-%Y %H:%M:%S")
        except:
            return ts

    @staticmethod
    def get_vote_statistics(db: Database) -> dict:
        """Get detailed vote statistics"""
        from models import Election

        election = Election(db)
        stats = election.get_statistics()

        # Get data by committee
        committees_vote_count = {}
        results = db.execute('''
            SELECT committee_name, COUNT(*) as count
            FROM votes
            GROUP BY committee_name
        ''').fetchall()

        for committee, count in results:
            committees_vote_count[committee] = count

        stats['votes_by_committee'] = committees_vote_count

        return stats
