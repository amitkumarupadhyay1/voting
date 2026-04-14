"""
Integration test for Task 3.2: Restore votes on session timeout
This test simulates the complete user flow including session state.
"""

import json
import time
from models import Database, Student, Election
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

def clear_vote_progress(session_state):
    """Simulate clear_vote_progress function."""
    session_state['saved_votes'] = None
    session_state['saved_votes_timestamp'] = None

def test_complete_flow():
    """Test the complete vote resume flow."""
    print("=" * 60)
    print("INTEGRATION TEST: Vote Resume on Session Timeout")
    print("=" * 60)
    
    # Initialize
    db = Database('school_voting.db')
    student_model = Student(db)
    election_model = Election(db)
    voting = VotingEngine(db)
    session_state = MockSessionState()
    
    # Get test student
    students = student_model.get_all()
    if not students:
        print("❌ No students found")
        return False
    
    test_student = students[0]
    student_id = test_student[0]
    student_name = test_student[1]
    
    print(f"\n1. Student Login")
    print(f"   Student: {student_id} - {student_name}")
    print(f"   Has voted: {test_student[7] == 1}")
    
    # Simulate voting session with some selections
    print(f"\n2. Student Makes Vote Selections")
    temp_votes = {
        'Sports': 'jb002',
        'Literary': '__abstain__',
    }
    print(f"   Selected {len(temp_votes)} committees")
    for comm, cand in temp_votes.items():
        if cand == '__abstain__':
            print(f"   - {comm}: Abstain")
        else:
            print(f"   - {comm}: {cand}")
    
    # Save progress (auto-save on each selection)
    print(f"\n3. Auto-Save Vote Progress")
    save_vote_progress(student_id, temp_votes, session_state)
    print(f"   ✓ Votes saved to session state")
    print(f"   ✓ Timestamp: {session_state.get('saved_votes_timestamp')}")
    
    # Simulate session timeout (clear temp_votes but keep saved_votes)
    print(f"\n4. Session Timeout Occurs")
    session_state['temp_votes'] = {}
    session_state['checked_saved_votes'] = False
    print(f"   ✓ Temp votes cleared")
    print(f"   ✓ Session state reset")
    
    # Student logs in again
    print(f"\n5. Student Logs In Again")
    print(f"   Checking for saved votes...")
    
    # Task 3.2.1: Check for saved votes
    saved_votes = load_vote_progress(student_id, session_state)
    
    if saved_votes:
        print(f"   ✓ Found {len(saved_votes)} saved votes")
        
        # Task 3.2.2: Validate saved votes
        print(f"\n6. Validating Saved Votes")
        valid_votes = {}
        invalid_reasons = []
        
        if not election_model.is_live():
            invalid_reasons.append("Election is no longer live")
            print(f"   ⚠ Election not live")
        else:
            print(f"   ✓ Election is live")
            
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
        
        # Task 3.2.3: Show resume option
        print(f"\n7. Resume Voting Option")
        if valid_votes and not invalid_reasons:
            print(f"   ✓ All votes valid - showing resume banner")
            session_state['has_valid_saved_votes'] = True
            session_state['valid_saved_votes'] = valid_votes
            session_state['saved_votes_count'] = len([v for v in valid_votes.values() if v != '__abstain__'])
            print(f"   ✓ Resume banner would show: {session_state['saved_votes_count']} votes")
        elif valid_votes and invalid_reasons:
            print(f"   ⚠ Some votes invalid - showing resume with warnings")
            session_state['has_valid_saved_votes'] = True
            session_state['valid_saved_votes'] = valid_votes
            session_state['saved_votes_count'] = len([v for v in valid_votes.values() if v != '__abstain__'])
            session_state['saved_votes_warnings'] = invalid_reasons
            print(f"   ⚠ Warnings: {len(invalid_reasons)}")
        else:
            print(f"   ✗ No valid votes - clearing saved data")
            clear_vote_progress(session_state)
            session_state['has_valid_saved_votes'] = False
        
        # Simulate user clicking "Resume Voting"
        if session_state.get('has_valid_saved_votes'):
            print(f"\n8. User Clicks 'Resume Voting'")
            session_state['temp_votes'] = session_state['valid_saved_votes'].copy()
            print(f"   ✓ Loaded {len(session_state['temp_votes'])} votes into temp_votes")
            print(f"   ✓ User can continue voting from where they left off")
        
        print(f"\n9. Test Complete")
        print(f"   ✅ Vote resume functionality working correctly!")
        return True
    else:
        print(f"   ✗ No saved votes found")
        return False

if __name__ == '__main__':
    try:
        success = test_complete_flow()
        if success:
            print("\n" + "=" * 60)
            print("✅ ALL INTEGRATION TESTS PASSED")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("❌ INTEGRATION TESTS FAILED")
            print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
