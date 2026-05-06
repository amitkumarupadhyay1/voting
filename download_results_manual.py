"""
Manual script to download election results as Excel files
This bypasses the Streamlit UI and generates files directly
"""
import pandas as pd
from datetime import datetime
from models import Database
from voting import VotingEngine
from utils import Utils

print("=" * 60)
print("JB ACADEMY ELECTION - RESULTS DOWNLOAD")
print("=" * 60)

# Initialize
db = Database('school_voting.db')
voting = VotingEngine(db)

# Fetch results
print("\n📊 Fetching election results...")
results = voting.get_results()

if not results:
    print("❌ No results found. Make sure votes have been cast.")
    exit(1)

print(f"✅ Results fetched successfully")
print(f"   - School committees: {len(results.get('School', {}))}")
print(f"   - House committees: {len(results.get('House', {}))}")

# Generate timestamp for filenames
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Download School Results
print("\n📥 Generating School Results (Class-Wise)...")
try:
    if "School" in results and results["School"]:
        school_file = Utils.create_school_results_class_wise(results["School"])
        filename = f'school_results_classwise_{timestamp}.xlsx'
        with open(filename, 'wb') as f:
            f.write(school_file)
        print(f"✅ School results saved: {filename}")
        print(f"   File size: {len(school_file):,} bytes")
        print(f"   Features: Title rows, Admission No, Section, Enhanced formatting")
    else:
        print("⚠️  No School committee results to download")
except Exception as e:
    print(f"❌ Error generating school results: {e}")

# Download House Results
print("\n📥 Generating House Results...")
try:
    if results:
        house_file = Utils.create_house_results_file(db, results)
        filename = f'house_results_{timestamp}.xlsx'
        with open(filename, 'wb') as f:
            f.write(house_file)
        print(f"✅ House results saved: {filename}")
        print(f"   File size: {len(house_file):,} bytes")
        print(f"   Features: Title rows, Admission No, Section, Winner highlighting")
    else:
        print("⚠️  No results to download")
except Exception as e:
    print(f"❌ Error generating house results: {e}")

# Generate comprehensive results file
print("\n📥 Generating Comprehensive Results...")
try:
    stats = voting._election.get_statistics()
    comprehensive_file = Utils.create_results_file(results, stats)
    filename = f'comprehensive_results_{timestamp}.xlsx'
    with open(filename, 'wb') as f:
        f.write(comprehensive_file)
    print(f"✅ Comprehensive results saved: {filename}")
    print(f"   File size: {len(comprehensive_file):,} bytes")
except Exception as e:
    print(f"❌ Error generating comprehensive results: {e}")

print("\n" + "=" * 60)
print("✅ DOWNLOAD COMPLETE")
print("=" * 60)
print("\nAll files have been saved to the current directory.")
print("You can now open them in Excel or any spreadsheet application.")
print("\n📋 What's New:")
print("  • Admission Number column added")
print("  • Section column added")
print("  • Winners highlighted in GOLD")
print("  • Title rows for each sheet")
print("  • Professional formatting and styling")
