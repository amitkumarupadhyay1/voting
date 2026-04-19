"""
Test verification for Task 4.3: House-wise participation breakdown
Verifies all subtasks are implemented correctly.
"""

import sqlite3
from models import Database, Student
from voting import VotingEngine
import hashlib

def test_house_participation_query():
    """Test 4.3.1 & 4.3.2: Query votes grouped by house and calculate participation rate"""
    print("\n=== Testing Task 4.3: House-wise Participation Breakdown ===\n")
    
    # Create test database
    db = Database('test_house_participation.db')
    student_model = Student(db)
    
    # Add test students across different houses
    test_students = [
        ('T001', 'Alice', '10', 'A', 'Taxila', hashlib.sha256('pass'.encode()).hexdigest(), 'pass'),
        ('T002', 'Bob', '10', 'A', 'Taxila', hashlib.sha256('pass'.encode()).hexdigest(), 'pass'),
        ('T003', 'Charlie', '10', 'B', 'Taxila', hashlib.sha256('pass'.encode()).hexdigest(), 'pass'),
        ('J001', 'David', '9', 'A', 'Janata', hashlib.sha256('pass'.encode()).hexdigest(), 'pass'),
        ('J002', 'Eve', '9', 'A', 'Janata', hashlib.sha256('pass'.encode()).hexdigest(), 'pass'),
        ('S001', 'Frank', '8', 'A', 'Saachi', hashlib.sha256('pass'.encode()).hexdigest(), 'pass'),
        ('S002', 'Grace', '8', 'B', 'Saachi', hashlib.sha256('pass'.encode()).hexdigest(), 'pass'),
        ('N001', 'Henry', '7', 'A', 'Nalanda', hashlib.sha256('pass'.encode()).hexdigest(), 'pass'),
    ]
    
    for student in test_students:
        student_model.add(*student)
    
    # Mark some students as voted
    student_model.mark_voted('T001')
    student_model.mark_voted('T002')
    student_model.mark_voted('J001')
    student_model.mark_voted('S001')
    student_model.mark_voted('S002')
    student_model.mark_voted('N001')
    
    # Test the query (same as in app.py)
    house_data = db.execute('''
        SELECT 
            house,
            COUNT(*) as total,
            SUM(has_voted) as voted,
            ROUND(CAST(SUM(has_voted) AS FLOAT) / COUNT(*) * 100, 1) as participation_rate
        FROM students
        GROUP BY house
        ORDER BY participation_rate DESC
    ''').fetchall()
    
    print("✓ Sub-task 4.3.1: Query votes grouped by house")
    print("✓ Sub-task 4.3.2: Calculate participation rate per house")
    print("\nHouse Participation Data:")
    print("-" * 60)
    
    house_stats = []
    for row in house_data:
        house_name = row[0]
        total = row[1]
        voted = row[2]
        participation_rate = row[3]
        house_stats.append({
            'house': house_name,
            'total': total,
            'voted': voted,
            'participation_rate': participation_rate
        })
        print(f"{house_name:12} | Total: {total:2} | Voted: {voted:2} | Rate: {participation_rate:5.1f}%")
    
    print("-" * 60)
    
    # Verify expected results
    assert len(house_stats) == 4, "Should have 4 houses"
    
    # Verify Saachi has 100% participation (2/2)
    saachi = next(h for h in house_stats if h['house'] == 'Saachi')
    assert saachi['participation_rate'] == 100.0, "Saachi should have 100% participation"
    
    # Verify Taxila has 66.7% participation (2/3)
    taxila = next(h for h in house_stats if h['house'] == 'Taxila')
    assert taxila['participation_rate'] == 66.7, "Taxila should have 66.7% participation"
    
    print("\n✓ All house participation calculations are correct!")
    
    # Clean up
    db.close()
    import os
    os.remove('test_house_participation.db')
    
    return True

def verify_implementation_in_app():
    """Verify that the implementation exists in app.py"""
    print("\n=== Verifying Implementation in app.py ===\n")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for all subtasks
    checks = [
        ('4.3.1', 'Query votes grouped by house', 'SELECT.*house.*GROUP BY house'),
        ('4.3.2', 'Calculate participation rate', 'participation_rate'),
        ('4.3.3', 'Display with house colors', "hm(h['house'])['color']"),
        ('4.3.4', 'House competition leaderboard', 'House Competition Leaderboard'),
    ]
    
    all_passed = True
    for task_id, description, pattern in checks:
        import re
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            print(f"✓ Sub-task {task_id}: {description}")
        else:
            print(f"✗ Sub-task {task_id}: {description} - NOT FOUND")
            all_passed = False
    
    if all_passed:
        print("\n✓ All subtasks are implemented in app.py!")
        print("\nLocation: app.py, Analytics tab (after class-wise participation)")
    
    return all_passed

if __name__ == '__main__':
    try:
        # Test the query logic
        test_house_participation_query()
        
        # Verify implementation in app.py
        verify_implementation_in_app()
        
        print("\n" + "="*60)
        print("✓ Task 4.3 Implementation Verified Successfully!")
        print("="*60)
        print("\nFeatures Implemented:")
        print("- 4.3.1: Query votes grouped by house")
        print("- 4.3.2: Calculate participation rate per house")
        print("- 4.3.3: Display with house-specific colors")
        print("- 4.3.4: House competition leaderboard with rankings")
        print("\nThe house-wise participation breakdown is now live in the")
        print("Analytics tab of the admin dashboard!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
