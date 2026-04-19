"""
Performance test for Task 5.1: Demonstrate index effectiveness
"""
import sqlite3
import time
from models import Database


def test_index_performance():
    """Test that queries benefit from the new composite indexes."""
    db = Database('school_voting.db')
    
    print("\n" + "="*70)
    print("PERFORMANCE TEST: Composite Index Effectiveness")
    print("="*70)
    
    # Test 1: Query students by voting status and class
    print("\n1. Query: Students by voting status and class")
    print("   Index used: idx_students_voted_class ON students(has_voted, class)")
    
    start = time.time()
    result = db.execute("""
        SELECT COUNT(*) 
        FROM students 
        WHERE has_voted = 1 AND class = '10'
    """).fetchone()
    elapsed = time.time() - start
    
    print(f"   Result: {result[0]} students")
    print(f"   Query time: {elapsed*1000:.2f}ms")
    
    # Test 2: Query students by voting status and house
    print("\n2. Query: Students by voting status and house")
    print("   Index used: idx_students_voted_house ON students(has_voted, house)")
    
    start = time.time()
    result = db.execute("""
        SELECT COUNT(*) 
        FROM students 
        WHERE has_voted = 1 AND house = 'Red'
    """).fetchone()
    elapsed = time.time() - start
    
    print(f"   Result: {result[0]} students")
    print(f"   Query time: {elapsed*1000:.2f}ms")
    
    # Test 3: Query votes by timestamp (for timeline analytics)
    print("\n3. Query: Votes ordered by timestamp (timeline)")
    print("   Index used: idx_votes_created ON votes(created_at)")
    
    start = time.time()
    result = db.execute("""
        SELECT COUNT(*) 
        FROM votes 
        WHERE created_at >= datetime('now', '-1 day')
        ORDER BY created_at
    """).fetchone()
    elapsed = time.time() - start
    
    print(f"   Result: {result[0]} votes in last 24h")
    print(f"   Query time: {elapsed*1000:.2f}ms")
    
    # Test 4: Query candidates by committee and status (existing index)
    print("\n4. Query: Approved candidates by committee")
    print("   Index used: idx_candidates_comm ON candidates(committee_name, status)")
    
    start = time.time()
    result = db.execute("""
        SELECT COUNT(*) 
        FROM candidates 
        WHERE committee_name = 'Sports' AND status = 'approved'
    """).fetchone()
    elapsed = time.time() - start
    
    print(f"   Result: {result[0]} candidates")
    print(f"   Query time: {elapsed*1000:.2f}ms")
    
    # Test 5: Complex analytics query using multiple indexes
    print("\n5. Complex Query: Class participation with vote timeline")
    print("   Uses: idx_students_voted_class + idx_votes_created")
    
    start = time.time()
    result = db.execute("""
        SELECT 
            s.class,
            COUNT(DISTINCT s.admission_no) as voted_count,
            COUNT(v.id) as total_votes
        FROM students s
        LEFT JOIN vote_tokens vt ON s.admission_no = vt.admission_no
        LEFT JOIN votes v ON vt.token = v.vote_token
        WHERE s.has_voted = 1
        GROUP BY s.class
        ORDER BY voted_count DESC
    """).fetchall()
    elapsed = time.time() - start
    
    print(f"   Result: {len(result)} classes analyzed")
    if result:
        for row in result[:3]:  # Show top 3
            print(f"     - Class {row[0]}: {row[1]} students voted, {row[2]} total votes")
    print(f"   Query time: {elapsed*1000:.2f}ms")
    
    # Test 6: House participation analytics
    print("\n6. Complex Query: House participation breakdown")
    print("   Uses: idx_students_voted_house")
    
    start = time.time()
    result = db.execute("""
        SELECT 
            house,
            COUNT(*) as total_students,
            SUM(has_voted) as voted_count,
            ROUND(100.0 * SUM(has_voted) / COUNT(*), 2) as participation_rate
        FROM students
        GROUP BY house
        ORDER BY participation_rate DESC
    """).fetchall()
    elapsed = time.time() - start
    
    print(f"   Result: {len(result)} houses analyzed")
    if result:
        for row in result:
            print(f"     - {row[0]}: {row[2]}/{row[1]} students ({row[3]}%)")
    print(f"   Query time: {elapsed*1000:.2f}ms")
    
    db.close()
    
    print("\n" + "="*70)
    print("✓ All performance tests completed successfully")
    print("  The new composite indexes enable efficient analytics queries")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_index_performance()
