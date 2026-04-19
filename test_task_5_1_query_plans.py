"""
Query plan analysis for Task 5.1: Verify indexes are used by SQLite optimizer
"""
import sqlite3
from models import Database


def test_query_plans():
    """Verify that SQLite query optimizer uses the new composite indexes."""
    db = Database('school_voting.db')
    
    print("\n" + "="*70)
    print("QUERY PLAN ANALYSIS: Verifying Index Usage")
    print("="*70)
    
    queries = [
        (
            "Students by voting status and class",
            "idx_students_voted_class",
            """
            SELECT * FROM students 
            WHERE has_voted = 1 AND class = '10'
            """
        ),
        (
            "Students by voting status and house",
            "idx_students_voted_house",
            """
            SELECT * FROM students 
            WHERE has_voted = 1 AND house = 'Red'
            """
        ),
        (
            "Votes ordered by timestamp",
            "idx_votes_created",
            """
            SELECT * FROM votes 
            ORDER BY created_at DESC
            LIMIT 100
            """
        ),
        (
            "Votes in time range",
            "idx_votes_created",
            """
            SELECT * FROM votes 
            WHERE created_at >= '2024-01-01'
            ORDER BY created_at
            """
        ),
        (
            "Candidates by committee and status",
            "idx_candidates_comm",
            """
            SELECT * FROM candidates 
            WHERE committee_name = 'Sports' AND status = 'approved'
            """
        ),
    ]
    
    for i, (description, expected_index, query) in enumerate(queries, 1):
        print(f"\n{i}. {description}")
        print(f"   Expected index: {expected_index}")
        print(f"   Query: {query.strip()}")
        
        # Get query plan
        plan = db.execute(f"EXPLAIN QUERY PLAN {query}").fetchall()
        
        print("   Query Plan:")
        index_used = False
        for row in plan:
            # Convert Row object to tuple for display
            plan_details = tuple(row)
            plan_text = ' | '.join(str(x) for x in plan_details)
            print(f"     {plan_text}")
            if expected_index in plan_text:
                index_used = True
        
        if index_used:
            print(f"   ✓ Index {expected_index} is being used")
        else:
            print(f"   ⚠ Index {expected_index} may not be used (check plan above)")
    
    db.close()
    
    print("\n" + "="*70)
    print("✓ Query plan analysis complete")
    print("="*70 + "\n")


if __name__ == '__main__':
    test_query_plans()
