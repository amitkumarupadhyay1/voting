"""
JB Academy Election Portal - Voting Engine
Phase-aware, race-condition-proof, self-vote blocked.
"""

from typing import Dict, List, Tuple

from models import Committee, Database, Election, Student, Vote, VoteToken


class VotingEngine:
    @property
    def HOUSES(self) -> List[str]:
        from models import Config

        return Config(self.db).get_houses()

    def __init__(self, db: Database):
        self.db = db
        self._student = Student(db)
        self._vote = Vote(db)
        self._token = VoteToken(db)
        self._election = Election(db)
        self._committee = Committee(db)

    # ── phase helpers ──────────────────────────────────────────────────────────

    @property
    def phase(self) -> str:
        return self._election.get_phase()

    def nominations_open(self) -> bool:
        return self._election.is_setup()

    def voting_open(self) -> bool:
        return self._election.is_live()

    def results_public(self) -> bool:
        return self._election.is_closed()

    # ── committee lists (cached per render via caller) ─────────────────────────

    @property
    def SCHOOL_COMMITTEES(self) -> List[str]:
        return self._committee.get_by_type("School")

    @property
    def HOUSE_COMMITTEES(self) -> List[str]:
        return self._committee.get_by_type("House")

    # ── eligibility ────────────────────────────────────────────────────────────

    def get_eligible_house_group(self, student_class: str) -> str:
        try:
            return "Junior" if int(student_class) in [7, 8] else "Senior"
        except ValueError:
            return "Senior"

    def can_vote(self, student: tuple) -> Tuple[bool, str]:
        if not self._election.is_live():
            return False, "Election is not currently live"
        if student[7] == 1:
            return False, "You have already voted"
        return True, "OK"

    # ── integrity check (per vote choice) ─────────────────────────────────────

    def verify_vote_integrity(
        self, voter_adm: str, candidate_adm: str, committee: str
    ) -> Tuple[bool, str]:
        if candidate_adm == "__abstain__":
            return True, "OK"
        if candidate_adm.strip().lower() == voter_adm.strip().lower():
            return False, "You cannot vote for yourself"
        if not self._student.get(candidate_adm):
            return False, "Candidate not found"
        nominated = self.db.execute(
            "SELECT id FROM candidates WHERE LOWER(TRIM(admission_no))=? "
            'AND committee_name=? AND status="approved"',
            (candidate_adm.strip().lower(), committee),
        ).fetchone()
        if not nominated:
            return False, "Candidate not approved for this committee"
        return True, "OK"

    # ── atomic vote submission ─────────────────────────────────────────────────

    def submit_votes(
        self, voter_adm: str, votes_dict: Dict[str, str]
    ) -> Tuple[bool, str]:
        """
        votes_dict: {committee_key: candidate_adm | '__abstain__'}
        All checks then one atomic DB write.
        """
        student = self._student.get(voter_adm)
        if not student:
            return False, "Student not found"
        can, reason = self.can_vote(student)
        if not can:
            return False, reason

        for committee, candidate_adm in votes_dict.items():
            # Strip 'House-' prefix used as UI key
            db_committee = committee.replace("House-", "")
            valid, msg = self.verify_vote_integrity(
                voter_adm, candidate_adm, db_committee
            )
            if not valid:
                return False, f"{db_committee}: {msg}"

        actual = {
            c.replace("House-", ""): a
            for c, a in votes_dict.items()
            if a != "__abstain__"
        }

        token = self._token.get_unused(voter_adm) or self._token.generate_token(
            voter_adm
        )
        if not token:
            return False, "Failed to generate vote token — please try again"

        success, msg = self._vote.cast_all(token, voter_adm, actual)
        if not success:
            return False, f"Failed to record votes: {msg}"

        abstained = len(votes_dict) - len(actual)
        result_msg = f"Recorded {len(actual)} vote(s)"
        if abstained:
            result_msg += f", abstained from {abstained} committee(s)"
        return True, result_msg

    # ── post-vote read-only display ────────────────────────────────────────────

    def get_student_votes(self, voter_adm: str) -> Dict[str, Dict]:
        name_cache: Dict[str, tuple] = {}

        def _get_student(adm: str) -> tuple:
            if adm not in name_cache:
                name_cache[adm] = self._student.get(adm)
            return name_cache[adm]

        result = {}
        for committee, candidate_adm, created_at in self._vote.get_student_votes(
            voter_adm
        ):
            cand = _get_student(candidate_adm)
            result[committee] = {
                "candidate_name": cand[1] if cand else "Unknown",
                "candidate_class": cand[2] if cand else "N/A",
                "voted_at": created_at,
            }
        return result

    # ── results (single query, max_winners aware) ──────────────────────────────

    def get_results(self) -> Dict:
        """
        Single JOIN query → structured dict:
        {
          committee_type: {
            committee_name: {
              'total_votes': int,
              'max_winners': int,
              'candidates':  [{adm, name, class, section, house, votes, pct, is_winner, is_tied}]
            }
          }
        }
        """
        rows = self._vote.get_results_all()
        meta_map = self._committee.get_meta_map()  # one query for all committee meta
        results: Dict = {}

        for row in rows:
            ctype, cname, _, _, adm, name, cls, section, house, vc = row
            results.setdefault(ctype, {})
            results[ctype].setdefault(
                cname,
                {
                    "total_votes": 0,
                    "max_winners": meta_map.get(cname, {}).get("max_winners", 1),
                    "candidates": [],
                },
            )
            results[ctype][cname]["candidates"].append(
                {
                    "adm": adm,
                    "name": name or adm,
                    "class": cls or "?",
                    "section": section or "?",
                    "house": house or "?",
                    "votes": int(vc),
                }
            )

        for ctype in results:
            for cname, data in results[ctype].items():
                cands = data["candidates"]
                total = sum(c["votes"] for c in cands)
                max_w = data["max_winners"]
                data["total_votes"] = total

                if not cands or total == 0:
                    for c in cands:
                        c.update(pct=0, is_winner=False, is_tied=False)
                    continue

                # Determine winners up to max_winners positions
                sorted_votes = sorted({c["votes"] for c in cands}, reverse=True)
                winner_threshold = sorted_votes[min(max_w, len(sorted_votes)) - 1]
                top_count = sum(1 for c in cands if c["votes"] >= winner_threshold)
                is_tied = top_count > max_w and winner_threshold > 0

                for c in cands:
                    c["pct"] = round(c["votes"] / total * 100, 1)
                    c["is_winner"] = c["votes"] >= winner_threshold and c["votes"] > 0
                    c["is_tied"] = is_tied and c["is_winner"]

        return results
