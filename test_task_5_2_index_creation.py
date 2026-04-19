"""
Task 5.2: Verify indexes are created automatically on database initialization
"""

import sqlite3
import os
import sys
sys.path.insert(0, '.')

# Create a test database
test_db = 'test_indexes_5_2.db'

# Remove if exists
if os.path.exists(test_db):
    os.remove(test_db)

print("=" * 80)
print("TASK 5.2: INDEX AUTO-CREATION TEST")
print("=" * 80)

print(f"\n[1] Creating fresh database: {test_db}")
print("-" * 80)

# Import Database class (this will create schema with indexes)
from models import Database

db = Database(test_db)

print("✓ Database initialized")

# Check if our new indexes exist
print("\n[2] VERIFYING NEW INDEXES")
print("-" * 80)

cursor = db.execute('''
    SELECT name, tbl_name, sql 
    FROM sqlite_master 
    WHERE type='index' AND name IN ('idx_candidates_adm', 'idx_votes_candidate_comm')
    ORDER BY name
''')

indexes = cursor.fetchall()

if len(indexes) == 2:
    print(f"✓ Found {len(indexes)} new indexes")
    for idx in indexes:
        print(f"\n  Index: {idx[0]}")
        print(f"  Table: {idx[1]}")
        print(f"  SQL: {idx[2]}")
else:
    print(f"✗ Expected 2 indexes, found {len(indexes)}")
    for idx in indexes:
        print(f"  - {idx[0]}")

# Verify all expected indexes
print("\n[3] COMPLETE INDEX LIST")
print("-" * 80)

cursor = db.execute('''
    SELECT name, tbl_name 
    FROM sqlite_master 
    WHERE type='index' AND sql IS NOT NULL
    ORDER BY tbl_name, name
''')

all_indexes = cursor.fetchall()
print(f"Total indexes: {len(all_indexes)}")

expected_indexes = [
    'idx_candidates_adm',
    'idx_candidates_comm',
    'idx_login_attempts',
    'idx_students_voted',
    'idx_students_voted_class',
    'idx_students_voted_house',
    'idx_votes_candidate_comm',
    'idx_votes_committee',
    'idx_votes_created',
    'idx_votes_token',
]

found_indexes = [idx[0] for idx in all_indexes]

print("\nExpected indexes:")
for exp_idx in expected_indexes:
    if exp_idx in found_indexes:
        print(f"  ✓ {exp_idx}")
    else:
        print(f"  ✗ {exp_idx} MISSING")

# Cleanup
db.close()
os.remove(test_db)

print("\n" + "=" * 80)
print("INDEX AUTO-CREATION TEST COMPLETE")
print("=" * 80)
