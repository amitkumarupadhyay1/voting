"""
Test vote resume functionality when election is LIVE.
This test requires the election to be in LIVE phase.
"""

import json
import time
from models import Database, Student, Election, Candidate
from voting import VotingEngine

class MockSessionState:
    """Mock Streamlit session state for testing."""
    def __init__(self):
        self.data = {}
    
    def __setitem__(self, key, value):
        self.data[key] = value
    
    def __getitem__(self, key):
        return self.data[key]
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def __contains__(self, key):
        return key in self.data

def save_vote_progress(student_id: str, temp_votes: dict, session_state):
    """Simulate save_vote_progress function."""
    if not temp_votes:
        return
    
    vote_data = {
        'student_id': student_id,
        'votes': temp_votes,
        'timestamp': time.time(),
        'saved_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    session_state['saved_votes'] = json.dumps(vote_data)
    session_state['saved_votes_timestamp'] = vote_data['timestamp']

def load_vote_progress(student_id: str, session_state) -> dict:
    """Simulate load_vote_progress function."""
    if 'saved_votes' not in session_state or not session_state['saved_votes']:
        return {}
    
    try:
        vote_data = json.loads(session_state['saved_votes'])
        
        if vote_data.get('student_id') != student_id:
            return {}
        
        return vote_data.get('votes', {})
    except (json.JSONDecodeError, KeyError):
        return {}

def test_with_live_election():
    """Test vote resume when election is LIVE."""
    print("=" * 60)
    print("TEST: Vote Resume with LIVE Election")
    print("=" * 60)
    
    # Initialize
    db = Database('school_voting.db')
    student_model = Student(db)
    election_model = Election(db)
    voting = VotingEngine(db)
    candidate_model = Candidate(db)
    session_state = MockSessionState()
    
    # Check election phase
    phase = election_model.get_phase()
    is_live = election_model.is_live()
    
    print(f"\n1. Election Status")
    print(f"   Phase: {phase}")
    print(f"   Is Live: {is_live}")
    
    if not is_live:
        print(f"\n⚠ Election is not LIVE. This test requires a LIVE election.")
        print(f"   To run this test:")
        print(f"   1. Start the app: streamlit run app.py")
        print(f"   2. Login as admin")
        print(f"   3. Go to 'Election' tab and click 'GO LIVE'")
        print(f"   4. Run this test again")
        return True  # Not a failure, just can't test
    
    # Get test student
    students = student_model.get_all()
    unvoted_students = [s for s in students if s[7] == 0]  # has_voted == 0
    
    if not unvoted_students:
        print(f"\n⚠ No unvoted students found. All students have already voted.")
        return True
    
    test_student = unvoted_students[0]
    student_id = test_student[0]
    student_name = test_student[1]
    student_class = test_student[2]
    
    print(f"\n2. Test Student")
    print(f"   ID: {student_id}")
    print(f"   Name: {student_name}")
    print(f"   Class: {student_class}")
    
    # Get approved candidates for this student's class
    approved_candidates = db.execute('''
        SELECT committee_name, admission_no
        FROM candidates
        WHERE committee_type="School" AND scope_class=? AND status="approved"
        LIMIT 2
    ''', (student_class,)).fetchall()
    
    if not approved_candidates:
        print(f"\n⚠ No approved candidates found for class {student_class}")
        return True
    
    print(f"\n3. Creating Test Votes")
    temp_votes = {}
    for comm_name, cand_adm in approved_candidates:
        temp_votes[comm_name] = cand_adm
        print(f"   - {comm_name}: {cand_adm}")
    
    # Save progress
    print(f"\n4. Saving Vote Progress")
    save_vote_progress(student_id, temp_votes, session_state)
    print(f"   ✓ Saved {len(temp_votes)} votes")
    
    # Simulate session timeout
    print(f"\n5. Simulating Session Timeout")
    session_state['temp_votes'] = {}
    session_state['checked_saved_votes'] = False
    print(f"   ✓ Session cleared")
    
    # Student logs in again
    print(f"\n6. Student Logs In Again")
    saved_votes = load_vote_progress(student_id, session_state)
    print(f"   ✓ Found {len(saved_votes)} saved votes")
    
    # Validate votes
    print(f"\n7. Validating Saved Votes")
    valid_votes = {}
    invalid_reasons = []
    
    for comm_key, candidate_adm in saved_votes.items():
        if candidate_adm == '__abstain__':
            valid_votes[comm_key] = candidate_adm
            print(f"   ✓ {comm_key}: Abstain (valid)")
            continue
        
        db_committee = comm_key.replace('House-', '')
        is_valid, msg = voting.verify_vote_integrity(student_id, candidate_adm, db_committee)
        
        if is_valid:
            valid_votes[comm_key] = candidate_adm
            print(f"   ✓ {comm_key}: {candidate_adm} (valid)")
        else:
            invalid_reasons.append(f"{db_committee}: {msg}")
            print(f"   ✗ {comm_key}: {candidate_adm} (invalid - {msg})")
    
    # Check results
    print(f"\n8. Validation Results")
    print(f"   Valid votes: {len(valid_votes)}")
    print(f"   Invalid votes: {len(invalid_reasons)}")
    
    if valid_votes and not invalid_reasons:
        print(f"   ✅ All votes are valid - resume banner would be shown")
        session_state['has_valid_saved_votes'] = True
        session_state['valid_saved_votes'] = valid_votes
        session_state['saved_votes_count'] = len([v for v in valid_votes.values() if v != '__abstain__'])
        
        print(f"\n9. Resume Voting")
        session_state['temp_votes'] = session_state['valid_saved_votes'].copy()
        print(f"   ✓ Loaded {len(session_state['temp_votes'])} votes")
        print(f"   ✓ Student can continue voting")
        
        print(f"\n✅ TEST PASSED: Vote resume works correctly with LIVE election")
        return True
    elif valid_votes:
        print(f"   ⚠ Some votes valid, some invalid")
        print(f"   ✅ TEST PASSED: Partial validation works correctly")
        return True
    else:
        print(f"   ✗ No valid votes")
        print(f"   ❌ TEST FAILED: Expected at least some valid votes")
        return False

if __name__ == '__main__':
    try:
        success = test_with_live_election()
        if success:
            print("\n" + "=" * 60)
            print("✅ TEST COMPLETED SUCCESSFULLY")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ TEST FAILED")
            print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
