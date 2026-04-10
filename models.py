"""
JB Academy Election Portal - Database Models
Handles all database operations and data integrity
"""

import sqlite3
import hashlib
from datetime import datetime
from typing import Optional, List, Tuple, Dict

class Database:
    """SQLite database wrapper"""

    def __init__(self, db_file='school_voting.db'):
        self.db_file = db_file
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.c = self.conn.cursor()
        self._initialize_schema()
        self._migrate_schema()

    def _initialize_schema(self):
        """Create tables if they don't exist"""
        self.c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            admission_no TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            class TEXT NOT NULL,
            section TEXT NOT NULL,
            house TEXT NOT NULL,
            password TEXT NOT NULL,
            generated_password TEXT,
            has_voted INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
        ''')

        self.c.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admission_no TEXT NOT NULL,
            committee_type TEXT NOT NULL,
            committee_name TEXT NOT NULL,
            scope_class TEXT,
            scope_house TEXT,
            section_group TEXT,
            created_at TEXT
        )
        ''')

        self.c.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_adm TEXT NOT NULL,
            candidate_adm TEXT NOT NULL,
            committee_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (voter_adm) REFERENCES students(admission_no),
            FOREIGN KEY (candidate_adm) REFERENCES students(admission_no)
        )
        ''')

        self.c.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            user_adm TEXT,
            details TEXT,
            created_at TEXT
        )
        ''')

        self.c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT
        )
        ''')

        self.conn.commit()

    def _migrate_schema(self):
        """Add missing columns to existing tables"""
        # Try to add columns if they don't exist
        columns_to_add = [
            ('students', 'generated_password', 'TEXT'),
            ('students', 'created_at', 'TEXT'),
            ('students', 'updated_at', 'TEXT'),
            ('candidates', 'created_at', 'TEXT'),
            ('settings', 'updated_at', 'TEXT'),
        ]

        for table, column, col_type in columns_to_add:
            try:
                self.c.execute(f'SELECT {column} FROM {table} LIMIT 1')
            except sqlite3.OperationalError:
                self.c.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}')
                self.conn.commit()

    def execute(self, query: str, params: tuple = ()) -> any:
        """Execute query and return result"""
        return self.c.execute(query, params)

    def commit(self):
        """Commit changes"""
        self.conn.commit()

    def close(self):
        """Close database connection"""
        self.conn.close()


class Student:
    """Student model"""

    def __init__(self, db: Database):
        self.db = db

    def add(self, admission_no: str, name: str, class_num: str,
            section: str, house: str, password_hash: str,
            password_plain: str) -> bool:
        """Add new student"""
        try:
            self.db.execute('''
            INSERT OR REPLACE INTO students
            (admission_no, name, class, section, house, password,
             generated_password, has_voted, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            ''', (admission_no, name, class_num, section, house,
                  password_hash, password_plain,
                  datetime.now().isoformat(), datetime.now().isoformat()))
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error adding student: {e}")
            return False

    def get(self, admission_no: str) -> Optional[Tuple]:
        """Get student by admission number"""
        admission_no = str(admission_no).strip().lower().split('.')[0]
        result = self.db.execute(
            'SELECT * FROM students WHERE LOWER(TRIM(admission_no))=?',
            (admission_no,)
        ).fetchone()
        return result

    def get_all(self) -> List[Tuple]:
        """Get all students"""
        return self.db.execute(
            'SELECT * FROM students ORDER BY admission_no'
        ).fetchall()

    def update(self, admission_no: str, name: str = None, class_num: str = None,
               section: str = None, house: str = None) -> bool:
        """Update student details"""
        try:
            updates = []
            params = []

            if name:
                updates.append('name=?')
                params.append(name)
            if class_num:
                updates.append('class=?')
                params.append(class_num)
            if section:
                updates.append('section=?')
                params.append(section)
            if house:
                updates.append('house=?')
                params.append(house)

            if not updates:
                return False

            updates.append('updated_at=?')
            params.append(datetime.now().isoformat())
            params.append(admission_no)

            query = f'UPDATE students SET {", ".join(updates)} WHERE admission_no=?'
            self.db.execute(query, tuple(params))
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error updating student: {e}")
            return False

    def delete(self, admission_no: str) -> bool:
        """Delete student (only if not voted)"""
        try:
            student = self.get(admission_no)
            if student and student[7] == 1:  # has_voted column
                return False

            self.db.execute('DELETE FROM students WHERE admission_no=?', (admission_no,))
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error deleting student: {e}")
            return False

    def reset_password(self, admission_no: str, password_hash: str,
                      password_plain: str) -> bool:
        """Reset student password"""
        try:
            self.db.execute('''
            UPDATE students
            SET password=?, generated_password=?, updated_at=?
            WHERE admission_no=?
            ''', (password_hash, password_plain,
                  datetime.now().isoformat(), admission_no))
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error resetting password: {e}")
            return False

    def mark_voted(self, admission_no: str) -> bool:
        """Mark student as voted (IMMUTABLE)"""
        try:
            self.db.execute(
                'UPDATE students SET has_voted=1, updated_at=? WHERE admission_no=?',
                (datetime.now().isoformat(), admission_no)
            )
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error marking voted: {e}")
            return False


class Vote:
    """Vote model - handles vote recording with audit trail"""

    def __init__(self, db: Database):
        self.db = db

    def cast(self, voter_adm: str, candidate_adm: str, committee_name: str) -> bool:
        """Cast a vote (with audit trail)"""
        try:
            election_time = datetime.now().isoformat()

            self.db.execute('''
            INSERT INTO votes (voter_adm, candidate_adm, committee_name, created_at)
            VALUES (?, ?, ?, ?)
            ''', (voter_adm, candidate_adm, committee_name, election_time))

            # Audit log
            self.db.execute('''
            INSERT INTO audit_log (action, user_adm, details, created_at)
            VALUES (?, ?, ?, ?)
            ''', ('VOTE_CAST', voter_adm,
                  f'Voted for {candidate_adm} in {committee_name}',
                  election_time))

            self.db.commit()
            return True
        except Exception as e:
            print(f"Error casting vote: {e}")
            return False

    def get_student_votes(self, voter_adm: str) -> List[Tuple]:
        """Get all votes by a student (for view-only after voting)"""
        return self.db.execute('''
            SELECT committee_name, candidate_adm, created_at
            FROM votes
            WHERE voter_adm = ?
            ORDER BY created_at
        ''', (voter_adm,)).fetchall()

    def get_vote_details(self, voter_adm: str) -> Dict[str, Tuple]:
        """Get vote details with candidate names for display"""
        votes = self.get_student_votes(voter_adm)
        result = {}
        for committee, candidate_adm, created_at in votes:
            result[committee] = {
                'candidate_adm': candidate_adm,
                'created_at': created_at
            }
        return result

    def get_all_votes(self) -> List[Tuple]:
        """Get all votes (admin only)"""
        return self.db.execute('''
            SELECT id, voter_adm, candidate_adm, committee_name, created_at
            FROM votes
            ORDER BY created_at DESC
        ''').fetchall()

    def get_votes_by_committee(self, committee: str) -> List[Tuple]:
        """Get all votes for a committee"""
        return self.db.execute('''
            SELECT candidate_adm, COUNT(*) as vote_count
            FROM votes
            WHERE committee_name = ?
            GROUP BY candidate_adm
            ORDER BY vote_count DESC
        ''', (committee,)).fetchall()


class Candidate:
    """Candidate model"""

    def __init__(self, db: Database):
        self.db = db

    def add(self, admission_no: str, committee_type: str, committee_name: str,
            scope_class: str = None, scope_house: str = None,
            section_group: str = None) -> bool:
        """Add candidate nomination"""
        try:
            self.db.execute('''
            INSERT INTO candidates
            (admission_no, committee_type, committee_name, scope_class,
             scope_house, section_group, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (admission_no, committee_type, committee_name, scope_class,
                  scope_house, section_group, datetime.now().isoformat()))
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error adding candidate: {e}")
            return False

    def get_all(self) -> List[Tuple]:
        """Get all candidates"""
        return self.db.execute(
            'SELECT * FROM candidates ORDER BY committee_name'
        ).fetchall()

    def get_by_committee(self, committee: str) -> List[Tuple]:
        """Get candidates for a committee"""
        return self.db.execute(
            'SELECT * FROM candidates WHERE committee_name = ?',
            (committee,)
        ).fetchall()


class Election:
    """Election management"""

    def __init__(self, db: Database):
        self.db = db

    def start(self) -> bool:
        """Start election"""
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO settings(key, value, updated_at) VALUES(?, ?, ?)",
                ('election_live', '1', datetime.now().isoformat())
            )
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error starting election: {e}")
            return False

    def stop(self) -> bool:
        """Stop election"""
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO settings(key, value, updated_at) VALUES(?, ?, ?)",
                ('election_live', '0', datetime.now().isoformat())
            )
            self.db.commit()
            return True
        except Exception as e:
            print(f"Error stopping election: {e}")
            return False

    def is_live(self) -> bool:
        """Check if election is live"""
        row = self.db.execute(
            "SELECT value FROM settings WHERE key='election_live'"
        ).fetchone()
        return row is not None and row[0] == '1'

    def get_statistics(self) -> Dict:
        """Get election statistics"""
        total_students = self.db.execute(
            'SELECT COUNT(*) FROM students'
        ).fetchone()[0]

        voted_students = self.db.execute(
            'SELECT COUNT(*) FROM students WHERE has_voted=1'
        ).fetchone()[0]

        total_votes = self.db.execute(
            'SELECT COUNT(*) FROM votes'
        ).fetchone()[0]

        return {
            'total_students': total_students,
            'voted_students': voted_students,
            'not_voted': total_students - voted_students,
            'total_votes': total_votes,
            'participation_rate': (voted_students / total_students * 100) if total_students > 0 else 0
        }


class AuditLog:
    """Audit logging for election integrity"""

    def __init__(self, db: Database):
        self.db = db

    def log(self, action: str, user_adm: str = None, details: str = None):
        """Log an action"""
        try:
            self.db.execute('''
            INSERT INTO audit_log (action, user_adm, details, created_at)
            VALUES (?, ?, ?, ?)
            ''', (action, user_adm, details, datetime.now().isoformat()))
            self.db.commit()
        except Exception as e:
            print(f"Error logging action: {e}")

    def get_all(self) -> List[Tuple]:
        """Get all audit logs"""
        return self.db.execute(
            'SELECT * FROM audit_log ORDER BY created_at DESC'
        ).fetchall()

    def get_by_user(self, user_adm: str) -> List[Tuple]:
        """Get audit logs for a user"""
        return self.db.execute(
            'SELECT * FROM audit_log WHERE user_adm = ? ORDER BY created_at DESC',
            (user_adm,)
        ).fetchall()
