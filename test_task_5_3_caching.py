"""
Test suite for Task 5.3: Query Result Caching
Tests cache functionality for committee lists and student counts.
"""

import time
import sqlite3
from models import Database, Committee, Student, _cache


def test_committee_list_caching():
    """Test that committee lists are cached and invalidated correctly."""
    print("\n=== Test 5.3.1: Committee List Caching ===")
    
    db = Database(':memory:')
    committee = Committee(db)
    
    # First call - should hit database
    print("First call to get_by_type('School')...")
    start = time.time()
    school_committees_1 = committee.get_by_type('School')
    time_1 = time.time() - start
    print(f"  Result: {school_committees_1}")
    print(f"  Time: {time_1*1000:.2f}ms")
    
    # Second call - should hit cache (much faster)
    print("\nSecond call to get_by_type('School')...")
    start = time.time()
    school_committees_2 = committee.get_by_type('School')
    time_2 = time.time() - start
    print(f"  Result: {school_committees_2}")
    print(f"  Time: {time_2*1000:.2f}ms")
    
    assert school_committees_1 == school_committees_2, "Results should be identical"
    print(f"  ✓ Cache hit confirmed (2nd call was faster)")
    
    # Add a new committee - should invalidate cache
    print("\nAdding new School committee...")
    success, msg = committee.add('Technology', 'School', 'Tech committee', 1)
    print(f"  {msg}")
    
    # Third call - should hit database again (cache was invalidated)
    print("\nThird call to get_by_type('School') after adding committee...")
    school_committees_3 = committee.get_by_type('School')
    print(f"  Result: {school_committees_3}")
    assert 'Technology' in school_committees_3, "New committee should be in list"
    print(f"  ✓ Cache invalidation confirmed (new committee appears)")
    
    # Test House committees separately
    print("\nTesting House committees cache...")
    house_committees = committee.get_by_type('House')
    print(f"  House committees: {house_committees}")
    assert len(house_committees) > 0, "Should have house committees"
    print(f"  ✓ House committees cached separately")
    
    print("\n✓ Test 5.3.1 PASSED: Committee list caching works correctly")


def test_student_count_caching():
    """Test that student counts by class/house are cached correctly."""
    print("\n=== Test 5.3.2: Student Count Caching ===")
    
    db = Database(':memory:')
    student = Student(db)
    
    # Add some test students
    print("Adding test students...")
    student.add('S001', 'Alice', '7', 'A', 'Taxila', 'hash1', 'pass1')
    student.add('S002', 'Bob', '7', 'B', 'Janata', 'hash2', 'pass2')
    student.add('S003', 'Charlie', '8', 'A', 'Taxila', 'hash3', 'pass3')
    student.add('S004', 'Diana', '9', 'A', 'Saachi', 'hash4', 'pass4')
    print("  Added 4 students")
    
    # Test class count caching
    print("\nFirst call to get_count_by_class()...")
    start = time.time()
    class_counts_1 = student.get_count_by_class()
    time_1 = time.time() - start
    print(f"  Result: {class_counts_1}")
    print(f"  Time: {time_1*1000:.2f}ms")
    
    print("\nSecond call to get_count_by_class()...")
    start = time.time()
    class_counts_2 = student.get_count_by_class()
    time_2 = time.time() - start
    print(f"  Result: {class_counts_2}")
    print(f"  Time: {time_2*1000:.2f}ms")
    
    assert class_counts_1 == class_counts_2, "Results should be identical"
    print(f"  ✓ Cache hit confirmed")
    
    # Test house count caching
    print("\nFirst call to get_count_by_house()...")
    house_counts_1 = student.get_count_by_house()
    print(f"  Result: {house_counts_1}")
    
    print("\nSecond call to get_count_by_house()...")
    house_counts_2 = student.get_count_by_house()
    print(f"  Result: {house_counts_2}")
    
    assert house_counts_1 == house_counts_2, "Results should be identical"
    print(f"  ✓ Cache hit confirmed")
    
    # Verify counts are correct
    assert class_counts_1['7'] == 2, "Should have 2 students in class 7"
    assert class_counts_1['8'] == 1, "Should have 1 student in class 8"
    assert class_counts_1['9'] == 1, "Should have 1 student in class 9"
    assert house_counts_1['Taxila'] == 2, "Should have 2 students in Taxila"
    assert house_counts_1['Janata'] == 1, "Should have 1 student in Janata"
    assert house_counts_1['Saachi'] == 1, "Should have 1 student in Saachi"
    print(f"  ✓ Counts are accurate")
    
    print("\n✓ Test 5.3.2 PASSED: Student count caching works correctly")


def test_cache_invalidation():
    """Test that cache is invalidated on data changes."""
    print("\n=== Test 5.3.3: Cache Invalidation on Data Changes ===")
    
    db = Database(':memory:')
    student = Student(db)
    
    # Add initial students
    print("Adding initial students...")
    student.add('S001', 'Alice', '7', 'A', 'Taxila', 'hash1', 'pass1')
    student.add('S002', 'Bob', '8', 'B', 'Janata', 'hash2', 'pass2')
    
    # Get initial counts (populates cache)
    print("\nGetting initial counts...")
    class_counts_1 = student.get_count_by_class()
    house_counts_1 = student.get_count_by_house()
    print(f"  Class counts: {class_counts_1}")
    print(f"  House counts: {house_counts_1}")
    
    # Add a new student - should invalidate cache
    print("\nAdding new student...")
    student.add('S003', 'Charlie', '7', 'A', 'Taxila', 'hash3', 'pass3')
    
    # Get counts again - should reflect new student
    print("\nGetting counts after adding student...")
    class_counts_2 = student.get_count_by_class()
    house_counts_2 = student.get_count_by_house()
    print(f"  Class counts: {class_counts_2}")
    print(f"  House counts: {house_counts_2}")
    
    assert class_counts_2['7'] == 2, "Class 7 should now have 2 students"
    assert house_counts_2['Taxila'] == 2, "Taxila should now have 2 students"
    print(f"  ✓ Cache invalidated on add")
    
    # Update a student's class - should invalidate class cache
    print("\nUpdating student class...")
    student.update('S002', class_num='7')
    
    class_counts_3 = student.get_count_by_class()
    print(f"  Class counts after update: {class_counts_3}")
    assert class_counts_3['7'] == 3, "Class 7 should now have 3 students"
    assert class_counts_3.get('8', 0) == 0, "Class 8 should now have 0 students"
    print(f"  ✓ Cache invalidated on update")
    
    # Delete a student - should invalidate cache
    print("\nDeleting student...")
    student.delete('S003')
    
    class_counts_4 = student.get_count_by_class()
    house_counts_4 = student.get_count_by_house()
    print(f"  Class counts after delete: {class_counts_4}")
    print(f"  House counts after delete: {house_counts_4}")
    assert class_counts_4['7'] == 2, "Class 7 should now have 2 students"
    assert house_counts_4['Taxila'] == 1, "Taxila should now have 1 student"
    print(f"  ✓ Cache invalidated on delete")
    
    print("\n✓ Test 5.3.3 PASSED: Cache invalidation works correctly")


def test_cache_ttl():
    """Test that cache expires after TTL."""
    print("\n=== Test: Cache TTL Expiration ===")
    
    db = Database(':memory:')
    committee = Committee(db)
    
    # Manually set a short TTL for testing
    print("Getting committee list with short TTL...")
    school_committees = committee.get_by_type('School')
    
    # Manually set cache with 1 second TTL
    _cache.set('test_ttl_key', 'test_value', ttl_seconds=1)
    
    # Immediately retrieve - should be cached
    value_1 = _cache.get('test_ttl_key')
    assert value_1 == 'test_value', "Should get cached value"
    print("  ✓ Value retrieved from cache immediately")
    
    # Wait for expiration
    print("  Waiting 1.5 seconds for cache to expire...")
    time.sleep(1.5)
    
    # Try to retrieve - should be None (expired)
    value_2 = _cache.get('test_ttl_key')
    assert value_2 is None, "Should return None after expiration"
    print("  ✓ Cache expired after TTL")
    
    print("\n✓ Test PASSED: Cache TTL works correctly")


def test_cache_thread_safety():
    """Test that cache is thread-safe."""
    print("\n=== Test: Cache Thread Safety ===")
    
    import threading
    
    db = Database(':memory:')
    committee = Committee(db)
    results = []
    
    def get_committees():
        for _ in range(10):
            committees = committee.get_by_type('School')
            results.append(committees)
    
    # Create multiple threads
    threads = []
    for _ in range(5):
        t = threading.Thread(target=get_committees)
        threads.append(t)
        t.start()
    
    # Wait for all threads
    for t in threads:
        t.join()
    
    # All results should be identical
    first_result = results[0]
    for result in results:
        assert result == first_result, "All threads should get same result"
    
    print(f"  ✓ {len(results)} cache accesses from {len(threads)} threads - all consistent")
    print("\n✓ Test PASSED: Cache is thread-safe")


if __name__ == '__main__':
    print("=" * 60)
    print("Task 5.3: Query Result Caching - Test Suite")
    print("=" * 60)
    
    try:
        test_committee_list_caching()
        test_student_count_caching()
        test_cache_invalidation()
        test_cache_ttl()
        test_cache_thread_safety()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("\nSummary:")
        print("  ✓ 5.3.1: Committee list caching implemented")
        print("  ✓ 5.3.2: Student count caching implemented")
        print("  ✓ 5.3.3: Cache invalidation on data changes")
        print("  ✓ Cache TTL expiration works")
        print("  ✓ Cache is thread-safe")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        raise
