import json
import os
import sys
from datetime import datetime

import pandas as pd

# Add current directory to path to import local modules
sys.path.append(os.getcwd())

import voting
from models import Config, Database
from utils import Utils


def test_excel_validation():
    db = Database()
    config = Config(db)

    excel_path = "sample_students.xlsx"
    if not os.path.exists(excel_path):
        print(f"File {excel_path} not found.")
        return

    try:
        df = pd.read_excel(excel_path, dtype=str)
        print(f"Total rows in Excel: {len(df)}")

        # Initialize default lists in DB if not present
        valid_houses = config.get_houses()
        valid_classes = config.get_classes()
        valid_sections = config.get_sections()

        print(f"Initial Config Valid Houses: {valid_houses}")
        print(f"Initial Config Valid Classes: {valid_classes}")
        print(f"Initial Config Valid Sections: {valid_sections}")

        # Update Config with any missing values found in Excel to simulate what the user would do
        excel_houses = set(df["house"].dropna().unique())
        excel_classes = set(df["class"].dropna().unique())
        excel_sections = set(df["section"].dropna().unique())

        # Title case houses for matching
        excel_houses = {str(h).strip().title() for h in excel_houses}

        print(f"Excel Houses: {excel_houses}")
        print(f"Excel Classes: {excel_classes}")
        print(f"Excel Sections: {excel_sections}")

        # Merge Excel values into Config
        new_houses = sorted(list(set(valid_houses) | excel_houses))
        new_classes = sorted(
            list(set(valid_classes) | excel_classes),
            key=lambda x: int(x) if x.isdigit() else 999,
        )
        new_sections = sorted(list(set(valid_sections) | excel_sections))

        config.set_houses(new_houses)
        config.set_classes(new_classes)
        config.set_sections(new_sections)

        print("\n--- After updating config with Excel values ---")
        updated_houses = config.get_houses()
        updated_classes = config.get_classes()
        updated_sections = config.get_sections()
        print(f"Updated Valid Houses: {updated_houses}")
        print(f"Updated Valid Classes: {updated_classes}")
        print(f"Updated Valid Sections: {updated_sections}")

        valid_count = 0
        errors = []

        for index, row in df.iterrows():
            # Convert row to dict
            row_dict = row.to_dict()

            # Utils.validate_student_data(row: dict, db: Database) -> Tuple[bool, str, dict]
            is_valid, error_msg, cleaned_data = Utils.validate_student_data(
                row_dict, db
            )
            if not is_valid:
                errors.append(f"Row {index+2}: {error_msg}")
            else:
                valid_count += 1

        print(f"Valid students after config update: {valid_count}")
        if errors:
            print(f"First 10 errors:")
            for e in errors[:10]:
                print(e)

        if valid_count == len(df):
            print("\nSUCCESS: All students pass validation with updated configuration!")
        else:
            print(f"\nFAILURE: {len(errors)} students still fail validation.")

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Error: {e}")


if __name__ == "__main__":
    test_excel_validation()
