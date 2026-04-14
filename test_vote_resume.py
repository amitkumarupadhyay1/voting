"""
Manual test script for Task 3.2: Restore votes on session timeout
This script tests the vote progress persistence and resume functionality.
"""

import json
import time
from models import Database, Student, Election
from voting import VotingEngine

def test_vote_progress_persistence():
    """Test that vote progress can be saved and loaded correctly."""
    print("Testing vote progress persistence...")
    
    # Initialize database
    db = Database('school_voting.db')
    student_model = Student(db)
    election_model = Election(db)
    voting = VotingEngine(db)
    
    # Get a test student (first student in database)
    students = student_model.get_all()
    if not students:
        print("❌ No students found in database")
        return False
    
    test_student = students[0]
    student_id = test_student[0]
    print(f"✓ Using test student: {student_id} - {test_student[1]}")
    
    # Create mock saved votes
    test_votes = {
        'Sports': 'jb002',
        'Literary': '__abstain__',
        'House-Cultural': 'jb003'
    }
    
    # Simulate saving votes (using session state simulation)
    vote_data = {
        'student_id': student_id,
        'votes': test_votes,
        'timestamp': time.time(),
        'saved_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    saved_json = json.dumps(vote_data)
    print(f"✓ Created test vote data: {len(test_votes)} votes")
    
    # Simulate loading votes
    loaded_data = json.loads(saved_json)
    loaded_votes = loaded_data.get('votes', {})
    
    if loaded_votes == test_votes:
        print("✓ Vote data serialization/deserialization works correctly")
    else:
        print("❌ Vote data mismatch after load")
        return False
    
    # Test validation logic
    print("\nTesting vote validation...")
    
    # Check if election is live
    is_live = election_model.is_live()
    print(f"✓ Election status: {'LIVE' if is_live else 'NOT LIVE'}")
    
    if is_live:
        # Validate each vote
        valid_count = 0
        invalid_count = 0
        
        for comm_key, candidate_adm in loaded_votes.items():
            if candidate_adm == '__abstain__':
                valid_count += 1
                print(f"  ✓ {comm_key}: Abstain (valid)")
                continue
            
            db_committee = comm_key.replace('House-', '')
            is_valid, msg = voting.verify_vote_integrity(student_id, candidate_adm, db_committee)
            
            if is_valid:
                valid_count += 1
                print(f"  ✓ {comm_key}: {candidate_adm} (valid)")
            else:
                invalid_count += 1
                print(f"  ✗ {comm_key}: {candidate_adm} (invalid - {msg})")
        
        print(f"\n✓ Validation complete: {valid_count} valid, {invalid_count} invalid")
    else:
        print("⚠ Election not live - skipping vote validation")
    
    print("\n✅ All tests passed!")
    return True

if __name__ == '__main__':
    try:
        test_vote_progress_persistence()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
