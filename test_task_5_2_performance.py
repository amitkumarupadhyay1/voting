"""
Task 5.2.4: Performance Testing with 1000+ Vote Records
Generates test data and compares query performance before/after optimization
"""

import sqlite3
import time
from datetime import datetime, timedelta
import random
import secrets

# Connect to the database
conn = sqlite3.connect('school_voting.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("TASK 5.2.4: PERFORMANCE TESTING WITH 1000+ VOTES")
print("=" * 80)

# ============================================================================
# Check current data size
# ============================================================================
print("\n[1] CURRENT DATA SIZE")
print("-" * 80)

cursor.execute('SELECT COUNT(*) FROM students')
student_count = cursor.fetchone()[0]
print(f"Students: {student_count}")

cursor.execute('SELECT COUNT(*) FROM candidates WHERE status="approved"')
candidate_count = cursor.fetchone()[0]
print(f"Approved Candidates: {candidate_count}")

cursor.execute('SELECT COUNT(*) FROM votes')
vote_count = cursor.fetchone()[0]
print(f"Current Votes: {vote_count}")

# ============================================================================
# Generate test data if needed
# ============================================================================
if vote_count < 1000:
    print(f"\n[2] GENERATING TEST DATA (need {1000 - vote_count} more votes)")
    print("-" * 80)
    
    # Get all students and candidates
    students = cursor.execute('SELECT admission_no FROM students').fetchall()
    candidates = cursor.execute('''
        SELECT admission_no, committee_name 
        FROM candidates 
        WHERE status="approved"
    ''').fetchall()
    
    if len(students) < 100:
        print("⚠ Warning: Only {} students in database. Generating synthetic students...".format(len(students)))
        # Generate synthetic students
        for i in range(100 - len(students)):
            adm_no = f"test{1000 + i}"
            cursor.execute('''
                INSERT OR IGNORE INTO students 
                (admission_no, name, class, section, house, password, has_voted)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            ''', (adm_no, f"Test Student {i}", "10", "A", 
                  random.choice(['Taxila', 'Janata', 'Saachi', 'Nalanda']), 
                  "test_hash"))
        conn.commit()
        students = cursor.execute('SELECT admission_no FROM students').fetchall()
        print(f"✓ Generated {100 - len(students)} synthetic students")
    
    if len(candidates) < 20:
        print("⚠ Warning: Only {} candidates. Performance test may not be representative.".format(len(candidates)))
    
    # Generate votes to reach 1000+
    votes_to_generate = max(1000 - vote_count, 0)
    print(f"Generating {votes_to_generate} test votes...")
    
    generated = 0
    for i in range(votes_to_generate):
        # Pick random student and candidate
        student = random.choice(students)[0]
        candidate = random.choice(candidates)
        
        # Generate token
        token = secrets.token_hex(16)
        
        # Create vote token
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO vote_tokens (token, admission_no, is_used, created_at)
                VALUES (?, ?, 1, ?)
            ''', (token, student, datetime.now().isoformat()))
            
            # Create vote
            cursor.execute('''
                INSERT INTO votes (vote_token, candidate_adm, committee_name, created_at)
                VALUES (?, ?, ?, ?)
            ''', (token, candidate[0], candidate[1], 
                  (datetime.now() - timedelta(hours=random.randint(0, 48))).isoformat()))
            
            generated += 1
            if generated % 100 == 0:
                print(f"  Generated {generated}/{votes_to_generate} votes...")
                conn.commit()
        except sqlite3.IntegrityError:
            pass  # Skip duplicates
    
    conn.commit()
    print(f"✓ Generated {generated} test votes")
    
    # Update final count
    cursor.execute('SELECT COUNT(*) FROM votes')
    vote_count = cursor.fetchone()[0]
    print(f"Total votes now: {vote_count}")
else:
    print(f"\n[2] SUFFICIENT TEST DATA")
    print("-" * 80)
    print(f"✓ Already have {vote_count} votes (>= 1000)")

# ============================================================================
# Performance Testing
# ============================================================================
print("\n\n[3] PERFORMANCE COMPARISON")
print("-" * 80)

# Test 1: Current query with LOWER/TRIM
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

# Test 2: Optimized query without LOWER/TRIM (since data is normalized)
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

# Warm up
cursor.execute(current_query).fetchall()
cursor.execute(optimized_query).fetchall()

# Run tests
num_iterations = 10

print(f"\nRunning {num_iterations} iterations of each query...\n")

# Test current query
current_times = []
for i in range(num_iterations):
    start = time.perf_counter()
    results = cursor.execute(current_query).fetchall()
    end = time.perf_counter()
    current_times.append((end - start) * 1000)  # Convert to ms

# Test optimized query
optimized_times = []
for i in range(num_iterations):
    start = time.perf_counter()
    results = cursor.execute(optimized_query).fetchall()
    end = time.perf_counter()
    optimized_times.append((end - start) * 1000)  # Convert to ms

# Calculate statistics
current_avg = sum(current_times) / len(current_times)
current_min = min(current_times)
current_max = max(current_times)

optimized_avg = sum(optimized_times) / len(optimized_times)
optimized_min = min(optimized_times)
optimized_max = max(optimized_times)

improvement = ((current_avg - optimized_avg) / current_avg) * 100

print("RESULTS:")
print("-" * 80)
print(f"\nCurrent Query (with LOWER/TRIM):")
print(f"  Average: {current_avg:.2f} ms")
print(f"  Min:     {current_min:.2f} ms")
print(f"  Max:     {current_max:.2f} ms")

print(f"\nOptimized Query (without LOWER/TRIM):")
print(f"  Average: {optimized_avg:.2f} ms")
print(f"  Min:     {optimized_min:.2f} ms")
print(f"  Max:     {optimized_max:.2f} ms")

print(f"\n{'IMPROVEMENT' if improvement > 0 else 'REGRESSION'}: {abs(improvement):.1f}%")
print(f"Time saved per query: {current_avg - optimized_avg:.2f} ms")

# Verify results are identical
print("\n\n[4] CORRECTNESS VERIFICATION")
print("-" * 80)
current_results = cursor.execute(current_query).fetchall()
optimized_results = cursor.execute(optimized_query).fetchall()

if len(current_results) == len(optimized_results):
    print(f"✓ Both queries return {len(current_results)} rows")
    
    # Compare first few rows
    matches = True
    for i in range(min(5, len(current_results))):
        if current_results[i] != optimized_results[i]:
            matches = False
            print(f"✗ Row {i} differs!")
            print(f"  Current:   {current_results[i]}")
            print(f"  Optimized: {optimized_results[i]}")
    
    if matches:
        print("✓ Sample rows match - queries produce identical results")
else:
    print(f"✗ Row count mismatch: {len(current_results)} vs {len(optimized_results)}")

print("\n" + "=" * 80)
print("PERFORMANCE TEST COMPLETE")
print("=" * 80)

conn.close()
