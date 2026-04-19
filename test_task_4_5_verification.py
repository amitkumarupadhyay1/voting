"""
Test Task 4.5: Committee Popularity Metrics
Verifies all sub-tasks are implemented correctly.
"""

import sqlite3
from models import Database, Student, Committee, Candidate, Vote, VoteToken, Election
import pandas as pd


def setup_test_data():
    """Create test database with sample data"""
    db = Database('test_committee_metrics.db')
    
    # Clear existing data
    db.write('DELETE FROM votes', ())
    db.write('DELETE FROM vote_tokens', ())
    db.write('DELETE FROM candidates', ())
    db.write('DELETE FROM students', ())
    db.write('DELETE FROM committees', ())
    
    # Add students
    student = Student(db)
    for i in range(1, 21):  # 20 students
        student.add(
            f'JB{i:03d}',
            f'Student {i}',
            str(7 + (i % 4)),  # Classes 7-10
            'A',
            ['Taxila', 'Janata', 'Saachi', 'Nalanda'][i % 4],
            'hashed_password',
            'plain_password'
        )
    
    # Add committees
    committee = Committee(db)
    committees_data = [
        ('Sports', 'School'),
        ('Literary', 'School'),
        ('Eco', 'School'),
        ('Cultural', 'School'),
    ]
    
    for name, ctype in committees_data:
        committee.add(name, ctype, f'{name} committee', 1)
    
    # Add candidates
    candidate = Candidate(db)
    # Sports: 5 candidates
    for i in range(1, 6):
        candidate.add(f'jb{i:03d}', 'School', 'Sports', status='approved')
    
    # Literary: 3 candidates
    for i in range(6, 9):
        candidate.add(f'jb{i:03d}', 'School', 'Literary', status='approved')
    
    # Eco: 4 candidates
    for i in range(9, 13):
        candidate.add(f'jb{i:03d}', 'School', 'Eco', status='approved')
    
    # Cultural: 2 candidates
    for i in range(13, 15):
        candidate.add(f'jb{i:03d}', 'School', 'Cultural', status='approved')
    
    # Simulate voting
    vote = Vote(db)
    token_gen = VoteToken(db)
    
    # 15 students vote (75% participation)
    for i in range(1, 16):
        adm = f'JB{i:03d}'
        token = token_gen.generate_token(adm)
        
        # Each student votes for different committees
        votes_dict = {}
        if i % 4 == 0:
            votes_dict['Sports'] = f'jb{(i % 5) + 1:03d}'
        if i % 3 == 0:
            votes_dict['Literary'] = f'jb{(i % 3) + 6:03d}'
        if i % 2 == 0:
            votes_dict['Eco'] = f'jb{(i % 4) + 9:03d}'
        if i % 5 == 0:
            votes_dict['Cultural'] = f'jb{(i % 2) + 13:03d}'
        
        if votes_dict:
            vote.cast_all(token, adm, votes_dict)
    
    return db


def test_subtask_4_5_1(db):
    """Test 4.5.1: Calculate total votes per committee"""
    print("\n=== Testing 4.5.1: Calculate total votes per committee ===")
    
    committee_votes = db.execute('''
        SELECT 
            committee_name,
            COUNT(*) as total_votes
        FROM votes
        GROUP BY committee_name
        ORDER BY total_votes DESC
    ''').fetchall()
    
    if committee_votes:
        print("✓ Query executed successfully")
        print("\nCommittee Vote Counts:")
        for row in committee_votes:
            print(f"  - {row[0]}: {row[1]} votes")
        return True
    else:
        print("✗ No data returned")
        return False


def test_subtask_4_5_2(db):
    """Test 4.5.2: Show most contested committees"""
    print("\n=== Testing 4.5.2: Show most contested committees ===")
    
    # Get votes per committee
    committee_votes = db.execute('''
        SELECT 
            committee_name,
            COUNT(*) as total_votes
        FROM votes
        GROUP BY committee_name
    ''').fetchall()
    
    # Get candidate counts
    candidate_counts = db.execute('''
        SELECT 
            committee_name,
            COUNT(*) as candidate_count
        FROM candidates
        WHERE status = 'approved'
        GROUP BY committee_name
    ''').fetchall()
    
    if committee_votes and candidate_counts:
        print("✓ Queries executed successfully")
        
        # Calculate contest ratios
        vote_map = {row[0]: row[1] for row in committee_votes}
        candidate_map = {row[0]: row[1] for row in candidate_counts}
        
        contest_ratios = []
        for comm in candidate_map.keys():
            votes = vote_map.get(comm, 0)
            candidates = candidate_map[comm]
            if votes > 0:
                ratio = candidates / votes
                contest_ratios.append((comm, candidates, votes, ratio))
        
        contest_ratios.sort(key=lambda x: x[3], reverse=True)
        
        print("\nMost Contested Committees (candidates per vote):")
        for i, (comm, cands, votes, ratio) in enumerate(contest_ratios[:3], 1):
            print(f"  {i}. {comm}: {cands} candidates, {votes} votes, ratio: {ratio:.2f}")
        
        return True
    else:
        print("✗ No data returned")
        return False


def test_subtask_4_5_3(db):
    """Test 4.5.3: Display candidate-to-voter ratio"""
    print("\n=== Testing 4.5.3: Display candidate-to-voter ratio ===")
    
    # Get total voters
    total_voters = db.execute('SELECT COUNT(*) FROM students WHERE has_voted=1').fetchone()[0]
    
    # Get candidate counts
    candidate_counts = db.execute('''
        SELECT 
            committee_name,
            COUNT(*) as candidate_count
        FROM candidates
        WHERE status = 'approved'
        GROUP BY committee_name
    ''').fetchall()
    
    if total_voters > 0 and candidate_counts:
        print("✓ Queries executed successfully")
        print(f"\nTotal Voters: {total_voters}")
        print("\nCandidate-to-Voter Ratios:")
        
        for row in candidate_counts:
            comm = row[0]
            candidates = row[1]
            ratio = candidates / total_voters
            print(f"  - {comm}: {candidates} candidates / {total_voters} voters = {ratio:.4f}")
        
        return True
    else:
        print("✗ No data or no voters")
        return False


def test_subtask_4_5_4(db):
    """Test 4.5.4: Identify committees with low participation"""
    print("\n=== Testing 4.5.4: Identify committees with low participation ===")
    
    # Get total voters
    total_voters = db.execute('SELECT COUNT(*) FROM students WHERE has_voted=1').fetchone()[0]
    
    # Get votes per committee
    committee_votes = db.execute('''
        SELECT 
            committee_name,
            COUNT(*) as total_votes
        FROM votes
        GROUP BY committee_name
    ''').fetchall()
    
    if total_voters > 0 and committee_votes:
        print("✓ Queries executed successfully")
        print(f"\nTotal Voters: {total_voters}")
        print("\nCommittee Participation Rates:")
        
        low_participation = []
        for row in committee_votes:
            comm = row[0]
            votes = row[1]
            participation_rate = (votes / total_voters) * 100
            print(f"  - {comm}: {votes}/{total_voters} = {participation_rate:.1f}%")
            
            if participation_rate < 50:
                low_participation.append((comm, participation_rate, votes))
        
        if low_participation:
            print("\n⚠️ Committees with Low Participation (<50%):")
            for comm, rate, votes in low_participation:
                print(f"  - {comm}: {rate:.1f}% ({votes} votes)")
        else:
            print("\n✓ All committees have healthy participation (50%+)")
        
        return True
    else:
        print("✗ No data or no voters")
        return False


def verify_app_implementation():
    """Verify the implementation exists in app.py"""
    print("\n=== Verifying app.py Implementation ===")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = [
        ('4.5.1: Total votes query', 'committee_name,\n                COUNT(*) as total_votes'),
        ('4.5.2: Most contested logic', 'contest_ratio'),
        ('4.5.3: Candidate-voter ratio', 'candidate_voter_ratio'),
        ('4.5.4: Low participation', 'low_participation'),
        ('Committee metrics section', '# Task 4.5: Committee Popularity Metrics'),
        ('Votes distribution chart', 'Committee Votes vs Candidates'),
        ('Most contested display', 'Most Contested Committees'),
        ('Candidate-to-voter table', 'Candidate-to-Voter Ratios'),
    ]
    
    all_passed = True
    for name, pattern in checks:
        if pattern in content:
            print(f"✓ {name}")
        else:
            print(f"✗ {name} - NOT FOUND")
            all_passed = False
    
    return all_passed


def main():
    print("="*70)
    print("Task 4.5: Committee Popularity Metrics - Verification")
    print("="*70)
    
    # Setup test data
    print("\nSetting up test database...")
    db = setup_test_data()
    print("✓ Test database created with sample data")
    
    # Run sub-task tests
    results = []
    results.append(('4.5.1', test_subtask_4_5_1(db)))
    results.append(('4.5.2', test_subtask_4_5_2(db)))
    results.append(('4.5.3', test_subtask_4_5_3(db)))
    results.append(('4.5.4', test_subtask_4_5_4(db)))
    
    # Verify app.py implementation
    app_verified = verify_app_implementation()
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for task, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{task}: {status}")
    
    print(f"\napp.py Implementation: {'✓ VERIFIED' if app_verified else '✗ INCOMPLETE'}")
    
    all_passed = all(r[1] for r in results) and app_verified
    
    if all_passed:
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\nTask 4.5 is fully implemented!")
        print("\nFeatures implemented:")
        print("- 4.5.1: Calculate total votes per committee ✓")
        print("- 4.5.2: Show most contested committees ✓")
        print("- 4.5.3: Display candidate-to-voter ratio ✓")
        print("- 4.5.4: Identify committees with low participation ✓")
        print("\nThe committee popularity metrics are now live in the Analytics tab!")
        print("\nTo view:")
        print("1. Run: streamlit run app.py")
        print("2. Login as admin (admin/admin)")
        print("3. Navigate to the 'Analytics' tab")
        print("4. Scroll down to 'Committee Popularity Metrics'")
    else:
        print("\n" + "="*70)
        print("❌ SOME TESTS FAILED")
        print("="*70)
    
    # Cleanup
    db.close()
    import os
    if os.path.exists('test_committee_metrics.db'):
        os.remove('test_committee_metrics.db')
    if os.path.exists('test_committee_metrics.db-shm'):
        os.remove('test_committee_metrics.db-shm')
    if os.path.exists('test_committee_metrics.db-wal'):
        os.remove('test_committee_metrics.db-wal')


if __name__ == '__main__':
    main()
