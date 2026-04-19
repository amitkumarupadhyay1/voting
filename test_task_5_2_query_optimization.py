"""
Task 5.2: Query Optimization Analysis and Testing
Tests the get_results_all() query optimization with query plan analysis
"""

import sqlite3
import time
from datetime import datetime
import random

# Connect to the database
conn = sqlite3.connect('school_voting.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("TASK 5.2: QUERY OPTIMIZATION ANALYSIS")
print("=" * 80)

# ============================================================================
# SUBTASK 5.2.1: Review current query
# ============================================================================
print("\n[5.2.1] CURRENT QUERY REVIEW")
print("-" * 80)

current_query = '''
SELECT
    c.committee_type,
    c.committee_name,
    c.scope_house,
    c.section_group,
    c.admission_no,
    s.name,
    s.class,
    s.house,
    COUNT(v.id) AS vote_count
FROM candidates c
LEFT JOIN students s
    ON LOWER(TRIM(c.admission_no)) = LOWER(TRIM(s.admission_no))
LEFT JOIN votes v
    ON LOWER(TRIM(v.candidate_adm)) = LOWER(TRIM(c.admission_no))
    AND v.committee_name = c.committee_name
WHERE c.status = "approved"
GROUP BY c.committee_name, c.admission_no
ORDER BY c.committee_type, c.committee_name, vote_count DESC
'''

print("Current Query:")
print(current_query)

# ============================================================================
# SUBTASK 5.2.2: Query plan analysis
# ============================================================================
print("\n[5.2.2] QUERY PLAN ANALYSIS - CURRENT QUERY")
print("-" * 80)

print("\nEXPLAIN QUERY PLAN for CURRENT query:")
plan = cursor.execute(f'EXPLAIN QUERY PLAN {current_query}').fetchall()
for row in plan:
    print(f"  {row[0]}: {row[1]}: {row[2]}: {row[3]}")

# Check existing indexes
print("\n\nEXISTING INDEXES:")
indexes = cursor.execute('''
    SELECT name, tbl_name, sql 
    FROM sqlite_master 
    WHERE type='index' AND sql IS NOT NULL
    ORDER BY tbl_name, name
''').fetchall()
for idx in indexes:
    print(f"  {idx[0]} on {idx[1]}")
    print(f"    {idx[2]}")

# ============================================================================
# SUBTASK 5.2.3: Identify optimization opportunities
# ============================================================================
print("\n\n[5.2.3] OPTIMIZATION OPPORTUNITIES")
print("-" * 80)

print("""
ISSUES IDENTIFIED:
1. LOWER(TRIM()) functions prevent index usage on admission_no columns
2. No index on candidates.admission_no for direct lookups
3. No index on votes.candidate_adm for JOIN optimization
4. Function calls in JOIN conditions force full table scans

PROPOSED OPTIMIZATIONS:
1. Add index on candidates(admission_no) - normalized lowercase
2. Add index on votes(candidate_adm, committee_name) - composite for JOIN
3. Remove LOWER/TRIM from JOIN if data is already normalized
4. Alternative: Normalize admission_no data at insert time
""")

# Check if admission_no data is already normalized
print("\n\nDATA NORMALIZATION CHECK:")
print("Checking if admission_no values contain uppercase or whitespace...")

# Check candidates
cursor.execute('''
    SELECT COUNT(*) as total,
           SUM(CASE WHEN admission_no != LOWER(TRIM(admission_no)) THEN 1 ELSE 0 END) as needs_norm
    FROM candidates
''')
cand_check = cursor.fetchone()
print(f"  Candidates: {cand_check[1]}/{cand_check[0]} need normalization")

# Check students
cursor.execute('''
    SELECT COUNT(*) as total,
           SUM(CASE WHEN admission_no != LOWER(TRIM(admission_no)) THEN 1 ELSE 0 END) as needs_norm
    FROM students
''')
stud_check = cursor.fetchone()
print(f"  Students: {stud_check[1]}/{stud_check[0]} need normalization")

# Check votes
cursor.execute('''
    SELECT COUNT(*) as total,
           SUM(CASE WHEN candidate_adm != LOWER(TRIM(candidate_adm)) THEN 1 ELSE 0 END) as needs_norm
    FROM votes
''')
vote_check = cursor.fetchone()
print(f"  Votes: {vote_check[1]}/{vote_check[0]} need normalization")

# Determine if we can remove LOWER/TRIM
can_remove_functions = (cand_check[1] == 0 and stud_check[1] == 0 and vote_check[1] == 0)

if can_remove_functions:
    print("\n✓ Data is already normalized - LOWER/TRIM can be safely removed!")
    optimized_query = '''
SELECT
    c.committee_type,
    c.committee_name,
    c.scope_house,
    c.section_group,
    c.admission_no,
    s.name,
    s.class,
    s.house,
    COUNT(v.id) AS vote_count
FROM candidates c
LEFT JOIN students s ON c.admission_no = s.admission_no
LEFT JOIN votes v ON v.candidate_adm = c.admission_no
    AND v.committee_name = c.committee_name
WHERE c.status = "approved"
GROUP BY c.committee_name, c.admission_no
ORDER BY c.committee_type, c.committee_name, vote_count DESC
'''
else:
    print("\n⚠ Data needs normalization - keeping LOWER/TRIM for now")
    print("  Recommendation: Normalize data at insert time in future")
    optimized_query = current_query

print("\n\nOPTIMIZED QUERY:")
print(optimized_query)

# ============================================================================
# Create optimized indexes
# ============================================================================
print("\n\nCREATING OPTIMIZED INDEXES:")
print("-" * 80)

# Index for candidates.admission_no
try:
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_candidates_adm ON candidates(admission_no)')
    print("✓ Created idx_candidates_adm ON candidates(admission_no)")
except Exception as e:
    print(f"✗ Error creating idx_candidates_adm: {e}")

# Composite index for votes JOIN
try:
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_votes_candidate_comm ON votes(candidate_adm, committee_name)')
    print("✓ Created idx_votes_candidate_comm ON votes(candidate_adm, committee_name)")
except Exception as e:
    print(f"✗ Error creating idx_votes_candidate_comm: {e}")

conn.commit()

# Show query plan with new indexes
print("\n\nEXPLAIN QUERY PLAN for OPTIMIZED query (with new indexes):")
plan = cursor.execute(f'EXPLAIN QUERY PLAN {optimized_query}').fetchall()
for row in plan:
    print(f"  {row[0]}: {row[1]}: {row[2]}: {row[3]}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)

conn.close()
