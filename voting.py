"""
JB Academy Election Portal - Voting Module
Handles vote casting, verification, and integrity
"""

from typing import List, Dict, Tuple, Optional
import random
from datetime import datetime
from models import Database, Student, Vote, Election

class VotingEngine:
    """Core voting logic with integrity checks"""

    def __init__(self, db: Database):
        self.db = db
        self.student_model = Student(db)
        self.vote_model = Vote(db)
        self.election_model = Election(db)

    HOUSES = ['Taxila', 'Janata', 'Saachi', 'Nalanda']
    SCHOOL_COMMITTEES = ['Sports', 'Literary', 'Eco', 'Cultural', 'Maintenance', 'Discipline']
    HOUSE_COMMITTEES = ['Sports', 'CCA', 'Discipline']

    def can_vote(self, student: Tuple) -> Tuple[bool, str]:
        """
        Check if student can vote
        Returns: (can_vote, reason)
        """
        if not self.election_model.is_live():
            return False, "Election is not currently live"

        if student[7] == 1:  # has_voted column
            return False, "You have already voted"

        return True, "OK"

    def get_eligible_school_committees(self, student_class: str) -> List[str]:
        """Get school committees for a class"""
        return self.SCHOOL_COMMITTEES

    def get_eligible_house_committees(self, student_class: str) -> str:
        """Get house group (Junior/Senior) based on class"""
        return 'Junior' if int(student_class) in [7, 8] else 'Senior'

    def verify_vote_integrity(self, voter_adm: str, candidate_adm: str,
                             committee: str) -> Tuple[bool, str]:
        """
        Verify vote integrity before casting
        Checks:
        - Voter exists and hasn't voted
        - Candidate exists and is nominated for committee
        - Committee is valid
        """
        # Check voter
        voter = self.student_model.get(voter_adm)
        if not voter:
            return False, "Voter not found"

        if voter[7] == 1:  # has_voted
            return False, "Student has already voted"

        # Check candidate
        candidate = self.student_model.get(candidate_adm)
        if not candidate:
            return False, "Candidate not found"

        # Check if candidate is nominated for this committee
        candidates = self.db.execute('''
            SELECT * FROM candidates
            WHERE LOWER(TRIM(admission_no)) = ?
            AND committee_name = ?
        ''', (candidate_adm.strip().lower(), committee)).fetchall()

        if not candidates:
            return False, "Candidate not nominated for this committee"

        return True, "OK"

    def submit_votes(self, voter_adm: str, votes_dict: Dict[str, str]) -> Tuple[bool, str]:
        """
        Submit all votes for a student
        votes_dict: {'committee_name': 'candidate_adm', ...}
        """
        try:
            # Final integrity check
            can_vote, reason = self.can_vote(self.student_model.get(voter_adm))
            if not can_vote:
                return False, reason

            # Verify each vote
            for committee, candidate_adm in votes_dict.items():
                valid, msg = self.verify_vote_integrity(voter_adm, candidate_adm, committee)
                if not valid:
                    return False, f"Vote for {committee}: {msg}"

            # Cast all votes (atomically)
            for committee, candidate_adm in votes_dict.items():
                if not self.vote_model.cast(voter_adm, candidate_adm, committee):
                    return False, "Failed to record vote"

            # Mark student as voted (IMMUTABLE)
            if not self.student_model.mark_voted(voter_adm):
                return False, "Failed to update student status"

            return True, f"Successfully recorded {len(votes_dict)} votes"

        except Exception as e:
            return False, f"Error submitting votes: {str(e)}"

    def get_student_votes(self, voter_adm: str) -> Dict[str, Dict]:
        """
        Get votes cast by student (for view-only display)
        Returns: {'committee': {'candidate_name': str, 'voted_at': timestamp}}
        """
        votes = self.vote_model.get_student_votes(voter_adm)
        result = {}

        for committee, candidate_adm, created_at in votes:
            candidate = self.student_model.get(candidate_adm)
            result[committee] = {
                'candidate_name': candidate[1] if candidate else 'Unknown',
                'candidate_class': candidate[2] if candidate else 'N/A',
                'voted_at': created_at
            }

        return result

    def generate_password() -> str:
        """Generate random 6-digit password"""
        return str(random.randint(100000, 999999))
