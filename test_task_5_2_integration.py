"""
Task 5.2 Integration Test: Verify optimization works with VotingEngine
"""

import sys
sys.path.insert(0, '.')

from models import Database
from voting import VotingEngine
import time

print("=" * 80)
print("TASK 5.2 INTEGRATION TEST")
print("=" * 80)

# Initialize
db = Database('school_voting.db')
engine = VotingEngine(db)

print("\n[1] TESTING VotingEngine.get_results()")
print("-" * 80)

# Test the get_results method which uses get_results_all internally
start = time.perf_counter()
results = engine.get_results()
end = time.perf_counter()

execution_time = (end - start) * 1000

print(f"✓ Method executed successfully")
print(f"  Execution time: {execution_time:.2f} ms")
print(f"  Committee types: {list(results.keys())}")

# Display sample results
for ctype in results:
    print(f"\n  {ctype} Committees:")
    for cname, data in list(results[ctype].items())[:2]:  # First 2 committees
        print(f"    - {cname}: {data['total_votes']} total votes, {len(data['candidates'])} candidates")
        if data['candidates']:
            winner = data['candidates'][0]
            print(f"      Winner: {winner['name']} ({winner['votes']} votes)")

# Performance test
print("\n[2] PERFORMANCE TEST")
print("-" * 80)

times = []
for i in range(10):
    start = time.perf_counter()
    engine.get_results()
    end = time.perf_counter()
    times.append((end - start) * 1000)

avg_time = sum(times) / len(times)
print(f"10 iterations average: {avg_time:.2f} ms")

if avg_time < 5.0:
    print("✓ Performance target met (< 5ms)")
else:
    print(f"⚠ Performance: {avg_time:.2f}ms")

print("\n" + "=" * 80)
print("INTEGRATION TEST COMPLETE")
print("=" * 80)

db.close()
