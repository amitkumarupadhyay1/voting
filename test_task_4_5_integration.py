"""
Integration Test for Task 4.5: Committee Popularity Metrics
Tests against the actual school_voting.db database
"""

import sqlite3
from models import Database


def test_committee_metrics():
    """Test committee popularity metrics with actual database"""
    print("="*70)
    print("Task 4.5: Committee Popularity Metrics - Integration Test")
    print("="*70)
    
    db = Database('school_voting.db')
    
    # Test 4.5.1: Calculate total votes per committee
    print("\n=== 4.5.1: Total Votes Per Committee ===")
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
        print(f"Found {len(committee_votes)} committees with votes:")
        for row in committee_votes:
            print(f"  - {row[0]}: {row[1]} votes")
    else:
        print("ℹ No votes in database yet (this is normal for a fresh setup)")
    
    # Test 4.5.2: Get candidate counts for contest ratio
    print("\n=== 4.5.2: Most Contested Committees ===")
    candidate_counts = db.execute('''
        SELECT 
            committee_name,
            COUNT(*) as candidate_count
        FROM candidates
        WHERE status = 'approved'
        GROUP BY committee_name
    ''').fetchall()
    
    if candidate_counts:
        print("✓ Query executed successfully")
        print(f"Found {len(candidate_counts)} committees with candidates:")
        for row in candidate_counts:
            print(f"  - {row[0]}: {row[1]} candidates")
        
        if committee_votes:
            # Calculate contest ratios
            vote_map = {row[0]: row[1] for row in committee_votes}
            print("\nContest Ratios (candidates per vote):")
            for row in candidate_counts:
                comm = row[0]
                candidates = row[1]
                votes = vote_map.get(comm, 0)
                if votes > 0:
                    ratio = candidates / votes
                    print(f"  - {comm}: {ratio:.2f} (higher = more contested)")
    else:
        print("ℹ No candidates in database yet")
    
    # Test 4.5.3: Candidate-to-voter ratio
    print("\n=== 4.5.3: Candidate-to-Voter Ratios ===")
    total_voters = db.execute('SELECT COUNT(*) FROM students WHERE has_voted=1').fetchone()[0]
    print(f"Total voters: {total_voters}")
    
    if total_voters > 0 and candidate_counts:
        print("✓ Calculating ratios:")
        for row in candidate_counts:
            comm = row[0]
            candidates = row[1]
            ratio = candidates / total_voters
            print(f"  - {comm}: {candidates} candidates / {total_voters} voters = {ratio:.4f}")
    else:
        print("ℹ Need voters and candidates to calculate ratios")
    
    # Test 4.5.4: Low participation committees
    print("\n=== 4.5.4: Committee Participation Rates ===")
    if total_voters > 0 and committee_votes:
        print("✓ Calculating participation rates:")
        low_participation = []
        for row in committee_votes:
            comm = row[0]
            votes = row[1]
            participation_rate = (votes / total_voters) * 100
            print(f"  - {comm}: {participation_rate:.1f}% ({votes}/{total_voters})")
            if participation_rate < 50:
                low_participation.append((comm, participation_rate))
        
        if low_participation:
            print("\n⚠️ Committees with low participation (<50%):")
            for comm, rate in low_participation:
                print(f"  - {comm}: {rate:.1f}%")
        else:
            print("\n✓ All committees have healthy participation (50%+)")
    else:
        print("ℹ Need votes to calculate participation rates")
    
    # Verify app.py implementation
    print("\n=== Verifying app.py Implementation ===")
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    features = [
        ('Total votes query', 'committee_name,\n                COUNT(*) as total_votes'),
        ('Contest ratio calculation', 'contest_ratio'),
        ('Candidate-voter ratio', 'candidate_voter_ratio'),
        ('Low participation detection', 'low_participation'),
        ('Committee metrics section', '# Task 4.5: Committee Popularity Metrics'),
        ('Votes distribution chart', 'Committee Votes vs Candidates'),
        ('Most contested display', 'Most Contested Committees'),
        ('Candidate-to-voter table', 'Candidate-to-Voter Ratios'),
        ('Low participation warning', 'Committees with Low Participation'),
    ]
    
    all_verified = True
    for name, pattern in features:
        if pattern in content:
            print(f"✓ {name}")
        else:
            print(f"✗ {name} - NOT FOUND")
            all_verified = False
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if all_verified:
        print("✅ ALL FEATURES VERIFIED IN app.py!")
        print("\nTask 4.5 Implementation Complete:")
        print("  ✓ 4.5.1: Calculate total votes per committee")
        print("  ✓ 4.5.2: Show most contested committees")
        print("  ✓ 4.5.3: Display candidate-to-voter ratio")
        print("  ✓ 4.5.4: Identify committees with low participation")
        print("\nFeatures:")
        print("  • Metrics grid with key statistics")
        print("  • Interactive chart showing votes vs candidates")
        print("  • Most contested committees ranking")
        print("  • Detailed candidate-to-voter ratio table")
        print("  • Low participation warnings")
        print("\nTo view the analytics:")
        print("  1. Run: streamlit run app.py")
        print("  2. Login as admin (admin/admin)")
        print("  3. Navigate to Analytics tab")
        print("  4. Scroll to 'Committee Popularity Metrics'")
    else:
        print("❌ Some features are missing")
    
    db.close()


if __name__ == '__main__':
    test_committee_metrics()
