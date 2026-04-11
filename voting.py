"""
JB Academy Election Portal - Voting Engine
- Fully atomic vote submission (race-condition proof)
- Self-voting blocked
- Nominations locked once election goes live
- Tie detection
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime
from models import Database, Student, Vote, VoteToken, Election, Committee, Candidate


class VotingEngine:
    def __init__(self, db: Database):
        self.db              = db
        self.student_model   = Student(db)
        self.vote_model      = Vote(db)
        self.token_model     = VoteToken(db)
        self.election_model  = Election(db)
        self.committee_model = Committee(db)

    HOUSES = ['Taxila', 'Janata', 'Saachi', 'Nalanda']

    @property
    def SCHOOL_COMMITTEES(self) -> List[str]:
        return self.committee_model.get_by_type('School')

    @property
    def HOUSE_COMMITTEES(self) -> List[str]:
        return self.committee_model.get_by_type('House')

    def can_vote(self, student: Tuple) -> Tuple[bool, str]:
        if not self.election_model.is_live():
            return False, "Election is not currently live"
        if student[7] == 1:
            return False, "You have already voted"
        return True, "OK"

    def nominations_open(self) -> bool:
        """Nominations are only open when election is NOT live."""
        return not self.election_model.is_live()

    def get_eligible_house_group(self, student_class: str) -> str:
        try:
            return 'Junior' if int(student_class) in [7, 8] else 'Senior'
        except ValueError:
            return 'Senior'

    def verify_vote_integrity(self, voter_adm: str, candidate_adm: str,
                              committee: str) -> Tuple[bool, str]:
        """Validate a single vote choice before submission."""
        voter = self.student_model.get(voter_adm)
        if not voter:
            return False, "Voter not found"
        if voter[7] == 1:
            return False, "Student has already voted"

        if candidate_adm == '__abstain__':
            return True, "OK"

        # Block self-voting
        if candidate_adm.strip().lower() == voter_adm.strip().lower():
            return False, "You cannot vote for yourself"

        candidate = self.student_model.get(candidate_adm)
        if not candidate:
            return False, "Candidate not found"

        nominated = self.db.execute(
            '''SELECT id FROM candidates
               WHERE LOWER(TRIM(admission_no))=? AND committee_name=? AND status="approved"''',
            (candidate_adm.strip().lower(), committee)
        ).fetchone()
        if not nominated:
            return False, "Candidate not nominated / approved for this committee"

        return True, "OK"

    def submit_votes(self, voter_adm: str,
                     votes_dict: Dict[str, str]) -> Tuple[bool, str]:
        """
        Submit all votes atomically.
        votes_dict: {committee_name: candidate_adm}  ('__abstain__' to skip)
        """
        student = self.student_model.get(voter_adm)
        if not student:
            return False, "Student not found"

        can, reason = self.can_vote(student)
        if not can:
            return False, reason

        # Verify all choices before touching the DB
        for committee, candidate_adm in votes_dict.items():
            valid, msg = self.verify_vote_integrity(voter_adm, candidate_adm, committee)
            if not valid:
                return False, f"{committee}: {msg}"

        # Filter abstains — don't record them
        actual_votes = {c: a for c, a in votes_dict.items() if a != '__abstain__'}

        # Get or create token (UNIQUE constraint is a second guard)
        vote_token = self.token_model.get_unused(voter_adm)
        if not vote_token:
            vote_token = self.token_model.generate_token(voter_adm)
            if not vote_token:
                return False, "Failed to generate vote token — please try again"

        # Atomic: re-check has_voted + insert votes + mark voted (all in one lock)
        success, msg = self.vote_model.cast_all(vote_token, voter_adm, actual_votes)
        if not success:
            return False, f"Failed to record votes: {msg}"

        abstained = len(votes_dict) - len(actual_votes)
        result_msg = f"Recorded {len(actual_votes)} vote(s)"
        if abstained:
            result_msg += f", abstained from {abstained} committee(s)"
        return True, result_msg

    def get_student_votes(self, voter_adm: str) -> Dict[str, Dict]:
        """Post-vote read-only display of what the student voted."""
        votes = self.vote_model.get_student_votes(voter_adm)
        result = {}
        for committee, candidate_adm, created_at in votes:
            candidate = self.student_model.get(candidate_adm)
            result[committee] = {
                'candidate_name':  candidate[1] if candidate else 'Unknown',
                'candidate_class': candidate[2] if candidate else 'N/A',
                'voted_at':        created_at,
            }
        return result

    def get_results(self) -> Dict:
        """
        Returns structured results dict:
        {
          committee_type: {
            committee_name: {
              'total_votes': int,
              'candidates': [
                {'adm','name','class','house','votes','pct','is_winner','is_tied'}
              ]
            }
          }
        }
        """
        rows = self.vote_model.get_results_all()
        results: Dict = {}

        for row in rows:
            ctype, cname, scope_house, section_group, adm, name, cls, house, vc = row
            if ctype not in results:
                results[ctype] = {}
            if cname not in results[ctype]:
                results[ctype][cname] = {'total_votes': 0, 'candidates': []}

            results[ctype][cname]['candidates'].append({
                'adm':   adm,
                'name':  name or adm,
                'class': cls or '?',
                'house': house or '?',
                'votes': int(vc),
            })

        # Compute totals, percentages, winner, tie flags
        for ctype in results:
            for cname in results[ctype]:
                cands = results[ctype][cname]['candidates']
                total = sum(c['votes'] for c in cands)
                results[ctype][cname]['total_votes'] = total
                max_votes = cands[0]['votes'] if cands else 0
                winners   = [c for c in cands if c['votes'] == max_votes and max_votes > 0]
                is_tied   = len(winners) > 1

                for c in cands:
                    c['pct']       = round(c['votes'] / total * 100, 1) if total > 0 else 0
                    c['is_winner'] = (c['votes'] == max_votes and max_votes > 0)
                    c['is_tied']   = is_tied and c['is_winner']

        return results
