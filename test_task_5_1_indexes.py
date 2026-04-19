"""
Test for Task 5.1: Verify composite indexes are created correctly
"""
import sqlite3
import os
import tempfile
from models import Database


def test_composite_indexes_exist():
    """Verify all required composite indexes are created in the database."""
    # Create a temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        test_db_path = tmp.name
    
    try:
        # Initialize database (this should create all indexes)
        db = Database(test_db_path)
        
        # Connect directly to check indexes
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        
        # Query all indexes
        cursor.execute("""
            SELECT name, tbl_name, sql 
            FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
            ORDER BY name
        """)
        
        indexes = cursor.fetchall()
        index_dict = {row[0]: (row[1], row[2]) for row in indexes}
        
        print("\n=== All Indexes Found ===")
        for name, (table, sql) in sorted(index_dict.items()):
            print(f"{name:30} -> {table:15} | {sql}")
        
        # Verify required indexes exist
        required_indexes = {
            'idx_votes_committee': 'votes',
            'idx_votes_token': 'votes',
            'idx_candidates_comm': 'candidates',
            'idx_students_voted': 'students',
            'idx_login_attempts': 'login_attempts',
            # New indexes from Task 5.1
            'idx_students_voted_class': 'students',
            'idx_students_voted_house': 'students',
            'idx_votes_created': 'votes',
        }
        
        print("\n=== Verification Results ===")
        all_passed = True
        for idx_name, expected_table in required_indexes.items():
            if idx_name in index_dict:
                actual_table = index_dict[idx_name][0]
                if actual_table == expected_table:
                    print(f"✓ {idx_name:30} exists on {expected_table}")
                else:
                    print(f"✗ {idx_name:30} exists but on wrong table: {actual_table} (expected {expected_table})")
                    all_passed = False
            else:
                print(f"✗ {idx_name:30} MISSING")
                all_passed = False
        
        # Verify specific composite index structures
        print("\n=== Composite Index Structure Verification ===")
        
        # Check idx_students_voted_class
        if 'idx_students_voted_class' in index_dict:
            sql = index_dict['idx_students_voted_class'][1]
            if 'has_voted' in sql and 'class' in sql:
                print(f"✓ idx_students_voted_class has correct columns (has_voted, class)")
            else:
                print(f"✗ idx_students_voted_class has incorrect structure: {sql}")
                all_passed = False
        
        # Check idx_students_voted_house
        if 'idx_students_voted_house' in index_dict:
            sql = index_dict['idx_students_voted_house'][1]
            if 'has_voted' in sql and 'house' in sql:
                print(f"✓ idx_students_voted_house has correct columns (has_voted, house)")
            else:
                print(f"✗ idx_students_voted_house has incorrect structure: {sql}")
                all_passed = False
        
        # Check idx_votes_created
        if 'idx_votes_created' in index_dict:
            sql = index_dict['idx_votes_created'][1]
            if 'created_at' in sql:
                print(f"✓ idx_votes_created has correct column (created_at)")
            else:
                print(f"✗ idx_votes_created has incorrect structure: {sql}")
                all_passed = False
        
        # Check idx_candidates_comm (existing, should have committee_name and status)
        if 'idx_candidates_comm' in index_dict:
            sql = index_dict['idx_candidates_comm'][1]
            if 'committee_name' in sql and 'status' in sql:
                print(f"✓ idx_candidates_comm has correct columns (committee_name, status)")
            else:
                print(f"✗ idx_candidates_comm has incorrect structure: {sql}")
                all_passed = False
        
        conn.close()
        db.close()
        
        print("\n" + "="*60)
        if all_passed:
            print("✓ ALL TESTS PASSED - All required indexes exist with correct structure")
        else:
            print("✗ SOME TESTS FAILED - Check output above")
        print("="*60)
        
        assert all_passed, "Not all required indexes exist or have correct structure"
        
    finally:
        # Clean up temporary database
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)


if __name__ == '__main__':
    test_composite_indexes_exist()
    print("\n✓ Task 5.1 verification complete!")
