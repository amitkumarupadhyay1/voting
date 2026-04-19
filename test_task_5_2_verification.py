"""
Task 5.2 Verification: Ensure optimized query works correctly
Tests the updated get_results_all() method in production code
"""

import sys
sys.path.insert(0, '.')

from models import Database, Vote
import time

print("=" * 80)
print("TASK 5.2 VERIFICATION: Optimized get_results_all()")
print("=" * 80)

# Initialize database
db = Database('school_voting.db')
vote_model = Vote(db)

print("\n[1] TESTING OPTIMIZED METHOD")
print("-" * 80)

# Test the method
start = time.perf_counter()
results = vote_model.get_results_all()
end = time.perf_counter()

execution_time = (end - start) * 1000  # Convert to ms

print(f"✓ Method executed successfully")
print(f"  Execution time: {execution_time:.2f} ms")
print(f"  Results returned: {len(results)} rows")

# Display sample results
if len(results) > 0:
    print("\n[2] SAMPLE RESULTS")
    print("-" * 80)
    print("First 5 results:")
    for i, row in enumerate(results[:5]):
        committee_type, committee_name, scope_house, section_group, adm_no, name, cls, house, vote_count = row
        print(f"  {i+1}. {committee_name} ({committee_type}): {name or adm_no} - {vote_count} votes")

# Verify indexes exist
print("\n[3] INDEX VERIFICATION")
print("-" * 80)

cursor = db.execute('''
    SELECT name FROM sqlite_master 
    WHERE type='index' AND name IN ('idx_candidates_adm', 'idx_votes_candidate_comm')
''')
indexes = [row[0] for row in cursor.fetchall()]

if 'idx_candidates_adm' in indexes:
    print("✓ idx_candidates_adm exists")
else:
    print("✗ idx_candidates_adm missing")

if 'idx_votes_candidate_comm' in indexes:
    print("✓ idx_votes_candidate_comm exists")
else:
    print("✗ idx_votes_candidate_comm missing")

# Query plan verification
print("\n[4] QUERY PLAN VERIFICATION")
print("-" * 80)

query = '''
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

plan = db.execute(f'EXPLAIN QUERY PLAN {query}').fetchall()
print("Query plan:")
for row in plan:
    print(f"  {row[3]}")

# Check if indexes are being used
plan_text = ' '.join([str(row[3]) for row in plan])
if 'idx_candidates_comm' in plan_text or 'idx_votes_candidate_comm' in plan_text:
    print("\n✓ Indexes are being utilized")
else:
    print("\n⚠ Warning: Indexes may not be fully utilized")

# Performance benchmark
print("\n[5] PERFORMANCE BENCHMARK")
print("-" * 80)

times = []
for i in range(20):
    start = time.perf_counter()
    vote_model.get_results_all()
    end = time.perf_counter()
    times.append((end - start) * 1000)

avg_time = sum(times) / len(times)
min_time = min(times)
max_time = max(times)

print(f"20 iterations:")
print(f"  Average: {avg_time:.2f} ms")
print(f"  Min:     {min_time:.2f} ms")
print(f"  Max:     {max_time:.2f} ms")

if avg_time < 5.0:
    print(f"\n✓ EXCELLENT: Query executes in under 5ms (target met)")
elif avg_time < 10.0:
    print(f"\n✓ GOOD: Query executes in under 10ms")
else:
    print(f"\n⚠ Query takes {avg_time:.2f}ms - may need further optimization")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)

db.close()
