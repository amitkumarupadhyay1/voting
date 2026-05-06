import sqlite3
conn = sqlite3.connect('school_voting.db')

# Find the student from the screenshot
print("=== Looking for AAKARSH SINGH ===")
rows = conn.execute("SELECT * FROM students WHERE name LIKE '%AAKARSH%'").fetchall()
for r in rows:
    print(f"  {r}")

# Check what the query would return for a Class 9, Ajanta, Senior student
print("\n=== House candidates for Ajanta House, Senior group ===")
rows = conn.execute("""
    SELECT c.committee_name, c.scope_house, c.section_group, c.admission_no, s.name, s.class
    FROM candidates c
    LEFT JOIN students s ON LOWER(TRIM(c.admission_no)) = LOWER(TRIM(s.admission_no))
    WHERE c.committee_type='House' AND c.scope_house='Ajanta' AND c.section_group='Senior' AND c.status='approved'
""").fetchall()
print(f"Found {len(rows)} candidates")
for r in rows:
    print(f"  {r}")

# Check what section_group a class 9 student would get
# From voting.py: Junior if class in [6,7,8] else Senior
print("\n=== Class 9 student group: Senior (classes 9-12 are Senior) ===")

conn.close()
