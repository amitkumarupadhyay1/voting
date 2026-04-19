"""
Test script for Task 4.2: Class-wise participation breakdown
"""
from models import Database

def test_class_participation():
    db = Database()
    
    # Sub-task 4.2.1 & 4.2.2: Query votes grouped by class and calculate participation rate
    class_data = db.execute('''
        SELECT 
            class,
            COUNT(*) as total,
            SUM(has_voted) as voted,
            ROUND(CAST(SUM(has_voted) AS FLOAT) / COUNT(*) * 100, 1) as participation_rate
        FROM students
        GROUP BY class
        ORDER BY class
    ''').fetchall()
    
    print("Class-wise Participation Data:")
    print("-" * 60)
    print(f"{'Class':<10} {'Total':<10} {'Voted':<10} {'Rate (%)':<10}")
    print("-" * 60)
    
    for row in class_data:
        print(f"{row[0]:<10} {row[1]:<10} {row[2]:<10} {row[3]:<10}")
    
    print("\n" + "=" * 60)
    
    # Convert to list of dicts
    class_stats = [
        {
            'class': row[0],
            'total': row[1],
            'voted': row[2],
            'participation_rate': row[3]
        }
        for row in class_data
    ]
    
    # Sub-task 4.2.4: Identify top 3 and bottom 3 classes
    sorted_by_rate = sorted(class_stats, key=lambda x: x['participation_rate'], reverse=True)
    
    print("\nTop 3 Performing Classes:")
    for i, cls in enumerate(sorted_by_rate[:3], 1):
        medal = ['🥇', '🥈', '🥉'][i-1]
        print(f"{medal} Class {cls['class']}: {cls['participation_rate']}% ({cls['voted']}/{cls['total']})")
    
    print("\nBottom 3 Performing Classes:")
    for cls in sorted_by_rate[-3:][::-1]:
        print(f"   Class {cls['class']}: {cls['participation_rate']}% ({cls['voted']}/{cls['total']})")
    
    print("\n✅ Test completed successfully!")
    return True

if __name__ == "__main__":
    test_class_participation()
