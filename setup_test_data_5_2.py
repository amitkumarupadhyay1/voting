"""
Setup test data for Task 5.2 performance testing
"""

import sqlite3
from datetime import datetime

conn = sqlite3.connect('school_voting.db')
cursor = conn.cursor()

print("Setting up test data for Task 5.2...")

# Get students
students = cursor.execute('SELECT admission_no, class, house FROM students LIMIT 20').fetchall()
print(f"Found {len(students)} students")

if len(students) == 0:
    print("No students found. Cannot create test data.")
    conn.close()
    exit(1)

# Get committees
committees = cursor.execute('SELECT name, committee_type FROM committees').fetchall()
print(f"Found {len(committees)} committees")

if len(committees) == 0:
    print("No committees found. Creating default committees...")
    default_committees = [
        ('Sports', 'School'),
        ('Literary', 'School'),
        ('Cultural', 'School'),
        ('Discipline', 'School'),
    ]
    for name, ctype in default_committees:
        cursor.execute('''
            INSERT OR IGNORE INTO committees (name, committee_type, created_at)
            VALUES (?, ?, ?)
        ''', (name, ctype, datetime.now().isoformat()))
    conn.commit()
    committees = cursor.execute('SELECT name, committee_type FROM committees').fetchall()
    print(f"Created {len(committees)} committees")

# Create candidates (nominate students for committees)
print("\nCreating test candidates...")
created = 0
for i, student in enumerate(students[:15]):  # Use first 15 students as candidates
    adm_no = student[0]
    student_class = student[1]
    student_house = student[2]
    
    # Nominate for 2-3 committees
    for committee in committees[:3]:
        comm_name = committee[0]
        comm_type = committee[1]
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO candidates 
                (admission_no, committee_type, committee_name, scope_class, scope_house, 
                 section_group, manifesto, status, nominated_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (adm_no, comm_type, comm_name, student_class, student_house,
                  None, f"Test manifesto for {comm_name}", "approved", "admin",
                  datetime.now().isoformat()))
            created += 1
        except Exception as e:
            print(f"Error creating candidate: {e}")

conn.commit()
print(f"✓ Created {created} candidate nominations")

# Verify
cursor.execute('SELECT COUNT(*) FROM candidates WHERE status="approved"')
approved_count = cursor.fetchone()[0]
print(f"✓ Total approved candidates: {approved_count}")

conn.close()
print("\nTest data setup complete!")
