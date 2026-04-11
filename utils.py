"""
JB Academy Election Portal - Utilities
Password generation, Excel import/export, results download.
"""

import random
import string
import pandas as pd
from io import BytesIO
from typing import List, Tuple, Dict
from datetime import datetime
from models import Database, Student


class Utils:

    # ── password helpers ───────────────────────────────────────────────────────

    @staticmethod
    def generate_password(length: int = 8) -> str:
        """
        Generate a memorable password: 4 letters + 4 digits.
        Avoids ambiguous chars (0/O, 1/l/I).
        """
        chars   = [c for c in string.ascii_uppercase if c not in 'OIL']
        digits  = [c for c in string.digits if c not in '01']
        letters = random.choices(chars, k=4)
        nums    = random.choices(digits, k=4)
        pwd     = letters + nums
        random.shuffle(pwd)
        return ''.join(pwd)

    @staticmethod
    def create_password_file(students: List[Tuple]) -> bytes:
        """Excel with student credentials — one sheet, sorted by class."""
        if not students:
            return b''
        data = []
        for s in students:
            data.append({
                'Admission No': s[0].upper(),
                'Name':         s[1],
                'Class':        s[2],
                'Section':      s[3],
                'House':        s[4],
                'Password':     s[6] if len(s) > 6 and s[6] else 'N/A',
                'Has Voted':    'Yes' if s[7] == 1 else 'No',
            })
        df = pd.DataFrame(data).sort_values(['Class', 'Name'])
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Student Passwords')
            ws = writer.sheets['Student Passwords']
            for col in ws.columns:
                ws.column_dimensions[col[0].column_letter].width = max(
                    len(str(col[0].value or '')), 14
                )
        return output.getvalue()

    # ── results download ───────────────────────────────────────────────────────

    @staticmethod
    def create_results_file(results: Dict, stats: Dict) -> bytes:
        """
        Multi-sheet Excel results file:
        - Sheet 1: Summary (winner per committee)
        - Sheet 2+: One sheet per committee with full breakdown
        - Final sheet: House participation stats
        """
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:

            # ── Summary sheet ──────────────────────────────────────────────
            summary_rows = []
            for ctype in ['School', 'House']:
                if ctype not in results:
                    continue
                for cname, data in sorted(results[ctype].items()):
                    cands = data['candidates']
                    if not cands:
                        continue
                    winner = cands[0]
                    tie_note = ' (TIE)' if winner.get('is_tied') else ''
                    summary_rows.append({
                        'Type':          ctype,
                        'Committee':     cname,
                        'Winner':        winner['name'] + tie_note,
                        'Winner Class':  winner['class'],
                        'Winner House':  winner['house'],
                        'Votes':         winner['votes'],
                        'Total Votes':   data['total_votes'],
                        'Vote %':        f"{winner['pct']}%",
                        'Candidates':    len(cands),
                    })
            if summary_rows:
                df_sum = pd.DataFrame(summary_rows)
                df_sum.to_excel(writer, index=False, sheet_name='Summary')
                _autofit(writer.sheets['Summary'], df_sum)

            # ── Per-committee sheets ───────────────────────────────────────
            for ctype in ['School', 'House']:
                if ctype not in results:
                    continue
                for cname, data in sorted(results[ctype].items()):
                    cands = data['candidates']
                    if not cands:
                        continue
                    rows = []
                    for rank, c in enumerate(cands, 1):
                        rows.append({
                            'Rank':      rank,
                            'Name':      c['name'],
                            'Class':     c['class'],
                            'House':     c['house'],
                            'Votes':     c['votes'],
                            'Vote %':    f"{c['pct']}%",
                            'Status':    ('🏆 WINNER' + (' (TIE)' if c.get('is_tied') else ''))
                                         if c['is_winner'] else '',
                        })
                    sheet_name = f"{ctype[:1]}-{cname}"[:31]  # Excel 31-char limit
                    df_c = pd.DataFrame(rows)
                    df_c.to_excel(writer, index=False, sheet_name=sheet_name)
                    _autofit(writer.sheets[sheet_name], df_c)

            # ── Participation sheet ────────────────────────────────────────
            part_rows = [{
                'Metric':  'Total Students',  'Value': stats['total_students']
            }, {
                'Metric':  'Voted',           'Value': stats['voted_students']
            }, {
                'Metric':  'Not Voted',       'Value': stats['not_voted']
            }, {
                'Metric':  'Turnout %',       'Value': f"{stats['participation_rate']:.1f}%"
            }, {
                'Metric':  'Total Votes Cast','Value': stats['total_votes']
            }]
            df_p = pd.DataFrame(part_rows)
            df_p.to_excel(writer, index=False, sheet_name='Participation')
            _autofit(writer.sheets['Participation'], df_p)

        return output.getvalue()

    @staticmethod
    def create_house_results_file(db: Database, results: Dict) -> bytes:
        """
        House-wise breakdown: one sheet per house showing all house committee results.
        """
        from models import Student as Sm
        houses = ['Taxila', 'Janata', 'Saachi', 'Nalanda']
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for house in houses:
                rows = []
                if 'House' in results:
                    for cname, data in sorted(results['House'].items()):
                        for c in data['candidates']:
                            if c['house'] == house or True:  # show all, filter by house scope
                                pass
                        # Get candidates scoped to this house
                        house_cands = db.execute('''
                            SELECT c.admission_no, s.name, s.class, s.house,
                                   COUNT(v.id) as vc
                            FROM candidates c
                            LEFT JOIN students s
                                ON LOWER(TRIM(c.admission_no))=LOWER(TRIM(s.admission_no))
                            LEFT JOIN votes v
                                ON LOWER(TRIM(v.candidate_adm))=LOWER(TRIM(c.admission_no))
                                AND v.committee_name=c.committee_name
                            WHERE c.committee_type="House" AND c.scope_house=?
                                AND c.committee_name=? AND c.status="approved"
                            GROUP BY c.admission_no ORDER BY vc DESC
                        ''', (house, cname)).fetchall()
                        if not house_cands:
                            continue
                        total = sum(r[4] for r in house_cands)
                        for rank, r in enumerate(house_cands, 1):
                            rows.append({
                                'Committee': cname,
                                'Rank':      rank,
                                'Name':      r[1] or r[0],
                                'Class':     r[2] or '?',
                                'Votes':     int(r[4]),
                                'Vote %':    f"{round(r[4]/total*100,1) if total else 0}%",
                            })
                if rows:
                    df = pd.DataFrame(rows)
                    df.to_excel(writer, index=False, sheet_name=house[:31])
                    _autofit(writer.sheets[house[:31]], df)
                else:
                    # Empty sheet placeholder
                    pd.DataFrame([{'Note': f'No house committee results for {house}'}]).to_excel(
                        writer, index=False, sheet_name=house[:31]
                    )
        return output.getvalue()

    # ── student import ─────────────────────────────────────────────────────────

    @staticmethod
    def validate_student_data(row: dict) -> Tuple[bool, str, dict]:
        valid_houses   = {'Taxila', 'Janata', 'Saachi', 'Nalanda'}
        valid_classes  = {'7', '8', '9', '10', '11', '12'}
        valid_sections = {'A', 'B', 'C', 'D', 'E'}
        try:
            admission_no = str(row.get('admission_no', '')).strip().lower().split('.')[0]
            name         = str(row.get('name', '')).strip()
            cls          = str(row.get('class', '')).strip().split('.')[0]
            section      = str(row.get('section', 'A')).strip().upper()
            house        = str(row.get('house', '')).strip().title()

            if not admission_no or len(admission_no) < 2:
                return False, "Invalid admission number", {}
            if not name or len(name) < 2:
                return False, "Invalid student name", {}
            if cls not in valid_classes:
                return False, f"Invalid class '{cls}' (must be 7–12)", {}
            if section not in valid_sections:
                return False, f"Invalid section '{section}' (A–E)", {}
            if house not in valid_houses:
                return False, f"Invalid house '{house}' (Taxila/Janata/Saachi/Nalanda)", {}

            return True, "", {
                'admission_no': admission_no,
                'name':         name,
                'class':        cls,
                'section':      section,
                'house':        house,
            }
        except Exception as e:
            return False, f"Parse error: {e}", {}

    @staticmethod
    def import_students_from_excel(df: pd.DataFrame,
                                   db: Database) -> Tuple[int, int, List[str]]:
        from auth import Auth
        imported, errors = 0, []
        student_model = Student(db)
        df.columns = [str(c).strip().lower() for c in df.columns]

        required = {'admission_no', 'name', 'class', 'section', 'house'}
        missing  = required - set(df.columns)
        if missing:
            return 0, len(df), [f"Missing columns: {', '.join(sorted(missing))}"]

        for idx, row in df.iterrows():
            valid, err, data = Utils.validate_student_data(row.to_dict())
            if not valid:
                errors.append(f"Row {idx+2}: {err}")
                continue
            if student_model.get(data['admission_no']):
                errors.append(f"Row {idx+2}: {data['admission_no']} already exists — skipped")
                continue
            pwd  = Utils.generate_password()
            if student_model.add(
                data['admission_no'], data['name'], data['class'],
                data['section'], data['house'],
                Auth.hash_password(pwd), pwd
            ):
                imported += 1
            else:
                errors.append(f"Row {idx+2}: DB error for {data['admission_no']}")

        return imported, len(errors), errors

    # ── misc ───────────────────────────────────────────────────────────────────

    @staticmethod
    def format_timestamp(ts: str) -> str:
        try:
            return datetime.fromisoformat(ts).strftime("%d-%m-%Y %H:%M:%S")
        except Exception:
            return ts or ''

    @staticmethod
    def get_vote_statistics(db: Database) -> dict:
        from models import Election
        stats = Election(db).get_statistics()
        rows  = db.execute(
            'SELECT committee_name,COUNT(*) FROM votes GROUP BY committee_name'
        ).fetchall()
        stats['votes_by_committee'] = {r[0]: r[1] for r in rows}
        return stats


def _autofit(ws, df: pd.DataFrame):
    """Auto-fit column widths in an openpyxl worksheet."""
    for col in ws.columns:
        max_len = max(
            (len(str(cell.value)) for cell in col if cell.value is not None),
            default=10
        )
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)
