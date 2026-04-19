"""
Test script to verify Task 4.4: Voting timeline (hourly trends) implementation
"""

import sqlite3
from datetime import datetime, timedelta
import random

def setup_test_data():
    """Create sample voting data for testing the timeline feature"""
    conn = sqlite3.connect('school_voting.db')
    cursor = conn.cursor()
    
    # Check if we already have votes
    existing_votes = cursor.execute('SELECT COUNT(*) FROM votes').fetchone()[0]
    
    if existing_votes > 0:
        print(f"✓ Database already has {existing_votes} votes")
        return existing_votes
    
    # Check if we have students
    students = cursor.execute('SELECT admission_no FROM students LIMIT 50').fetchall()
    
    if not students:
        print("⚠ No students found in database. Please import students first.")
        return 0
    
    # Check if we have committees
    committees = cursor.execute('SELECT name FROM committees WHERE committee_type="School" LIMIT 3').fetchall()
    
    if not committees:
        print("⚠ No committees found in database.")
        return 0
    
    print(f"Creating sample voting data with {len(students)} students and {len(committees)} committees...")
    
    # Create votes spread across different hours
    base_time = datetime.now() - timedelta(hours=8)
    votes_created = 0
    
    for i, student in enumerate(students[:30]):  # Use first 30 students
        student_adm = student[0]
        
        # Generate a token for this student
        token = f"test_token_{student_adm}_{i}"
        
        # Insert token
        cursor.execute(
            'INSERT OR IGNORE INTO vote_tokens (token, admission_no, is_used, created_at) VALUES (?, ?, 1, ?)',
            (token, student_adm, base_time.isoformat())
        )
        
        # Create votes at different hours (simulate realistic voting pattern)
        # More votes during peak hours (10 AM - 2 PM)
        hour_offset = random.choice([0, 1, 2, 2, 3, 3, 3, 4, 4, 5, 6, 7])  # Weighted towards middle hours
        vote_time = base_time + timedelta(hours=hour_offset, minutes=random.randint(0, 59))
        
        # Vote for a random committee
        committee = random.choice(committees)[0]
        
        # Get a candidate for this committee (or use a dummy)
        candidate = cursor.execute(
            'SELECT admission_no FROM candidates WHERE committee_name=? AND status="approved" LIMIT 1',
            (committee,)
        ).fetchone()
        
        if candidate:
            candidate_adm = candidate[0]
        else:
            # Use another student as candidate
            candidate_adm = students[(i + 1) % len(students)][0]
        
        # Insert vote
        cursor.execute(
            'INSERT INTO votes (vote_token, candidate_adm, committee_name, created_at) VALUES (?, ?, ?, ?)',
            (token, candidate_adm, committee, vote_time.isoformat())
        )
        
        votes_created += 1
    
    conn.commit()
    conn.close()
    
    print(f"✓ Created {votes_created} sample votes")
    return votes_created


def verify_implementation():
    """Verify that Task 4.4 is properly implemented in app.py"""
    
    print("\n" + "="*70)
    print("TASK 4.4 VERIFICATION: Voting Timeline (Hourly Trends)")
    print("="*70 + "\n")
    
    # Read app.py
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ app.py not found")
        return False
    
    # Check for all sub-tasks
    checks = {
        '4.4.1': {
            'name': 'Parse vote timestamps by hour',
            'patterns': [
                'SELECT created_at',
                'FROM votes',
                'df_votes[\'hour\']',
                'date_hour'
            ]
        },
        '4.4.2': {
            'name': 'Create line chart showing votes over time',
            'patterns': [
                'go.Scatter',
                'mode=\'lines+markers\'',
                'Voting Activity Over Time',
                'fig_timeline'
            ]
        },
        '4.4.3': {
            'name': 'Highlight peak voting hours',
            'patterns': [
                'peak_hour',
                'idxmax',
                'Peak Voting Hours',
                'peak_votes'
            ]
        },
        '4.4.4': {
            'name': 'Show average votes per hour',
            'patterns': [
                'avg_votes_per_hour',
                'Avg Votes/Hour',
                'add_hline',
                'Average:'
            ]
        }
    }
    
    all_passed = True
    
    for task_id, check in checks.items():
        print(f"Checking {task_id}: {check['name']}")
        
        missing_patterns = []
        for pattern in check['patterns']:
            if pattern not in content:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            print(f"  ❌ FAILED - Missing patterns: {', '.join(missing_patterns)}")
            all_passed = False
        else:
            print(f"  ✓ PASSED")
    
    print("\n" + "-"*70)
    
    if all_passed:
        print("\n✅ All sub-tasks are implemented in app.py!")
        print("\nLocation: app.py, Analytics tab (after house-wise participation)")
        print("\nFeatures implemented:")
        print("- 4.4.1: Parse vote timestamps by hour ✓")
        print("- 4.4.2: Create line chart showing votes over time ✓")
        print("- 4.4.3: Highlight peak voting hours ✓")
        print("- 4.4.4: Show average votes per hour ✓")
        print("\nThe voting timeline feature is now live in the Analytics tab!")
    else:
        print("\n❌ Some sub-tasks are missing or incomplete")
    
    return all_passed


def main():
    """Main test execution"""
    
    # First verify the implementation
    implementation_ok = verify_implementation()
    
    if not implementation_ok:
        print("\n⚠ Implementation verification failed. Please check the code.")
        return
    
    # Setup test data
    print("\n" + "="*70)
    print("SETTING UP TEST DATA")
    print("="*70 + "\n")
    
    votes_count = setup_test_data()
    
    if votes_count > 0:
        print("\n" + "="*70)
        print("TEST DATA READY")
        print("="*70)
        print(f"\n✓ {votes_count} votes available for timeline visualization")
        print("\nTo view the voting timeline:")
        print("1. Run: streamlit run app.py")
        print("2. Login as admin (admin/admin)")
        print("3. Navigate to the 'Analytics' tab")
        print("4. Scroll down to 'Voting Timeline (Hourly Trends)'")
        print("\nYou should see:")
        print("  • Total votes, average votes/hour, and peak hour metrics")
        print("  • Line chart showing voting activity over time")
        print("  • Peak voting hours highlighted with medals")
        print("  • Detailed hourly breakdown table")
    else:
        print("\n⚠ No test data created. The timeline will show 'No voting data available'")
        print("This is expected behavior when there are no votes yet.")


if __name__ == '__main__':
    try:
        main()
        print("\n" + "="*70)
        print("VERIFICATION COMPLETE")
        print("="*70 + "\n")
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
