"""
JB Academy Election Portal - Main Application
Refactored with class-based architecture for maintainability and trust
"""

import streamlit as st
import pandas as pd
from io import BytesIO

from models import Database, Student, Vote, Candidate, Election, AuditLog
from auth import Auth
from voting import VotingEngine
from utils import Utils

# ==================== PAGE CONFIG ====================
st.set_page_config(page_title='JB Academy Election Portal', layout='wide')

st.markdown('''
<style>
.stApp {background: #0f172a; color: white;}
header, footer {visibility: hidden;}
.stat-box {background: #1e3a8a; padding: 20px; border-radius: 10px; text-align: center;}
.vote-display {background: #1a3a52; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #10b981;}
</style>
''', unsafe_allow_html=True)

st.title('🗳️ JB Academy Election Portal')
st.markdown('*Secure • Transparent • Trustworthy*')

# ==================== INITIALIZE MODULES ====================
@st.cache_resource
def init_modules():
    """Initialize database and models"""
    db = Database('school_voting.db')
    auth = Auth(db)
    voting = VotingEngine(db)
    election = Election(db)
    audit = AuditLog(db)
    return db, auth, voting, election, audit

db, auth, voting, election, audit = init_modules()

# ==================== SESSION STATE ====================
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'review_votes' not in st.session_state:
    st.session_state.review_votes = False
if 'temp_votes' not in st.session_state:
    st.session_state.temp_votes = {}

# ==================== LOGIN PAGE ====================
if st.session_state.user_type is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader('🔐 Secure Login')

        login_id = st.text_input('Admission No / Admin ID', key='login_id')
        login_pass = st.text_input('Password', type='password', key='login_pass')

        if st.button('🔓 Login', use_container_width=True, type='primary'):
            if not login_id or not login_pass:
                st.error('❌ Please enter both ID and password')
            else:
                result = auth.validate_credentials(login_id, login_pass)

                if result['type'] == 'admin':
                    st.session_state.user_type = 'admin'
                    audit.log('ADMIN_LOGIN', login_id.lower())
                    st.rerun()
                elif result['type'] == 'student':
                    st.session_state.user_type = 'student'
                    st.session_state.user_data = result['data']
                    audit.log('STUDENT_LOGIN', result['data'][0])
                    st.rerun()
                else:
                    st.error('❌ Invalid credentials. Please check and try again.')
                    st.warning('If you forgot your password, contact the administrator.')

# ==================== ADMIN DASHBOARD ====================
elif st.session_state.user_type == 'admin':
    # Logout button
    col1, col2 = st.columns([8, 1])
    with col2:
        if st.button('🚪 Logout', type='secondary'):
            audit.log('ADMIN_LOGOUT')
            st.session_state.user_type = None
            st.session_state.user_data = None
            st.rerun()

    st.subheader('🛠️ Administrator Dashboard')

    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        'Import Students', 'Manage Students', 'Nominate Candidates',
        'Election Control', 'Results & Audit', 'Voting Records'
    ])

    # ==================== TAB 1: IMPORT STUDENTS ====================
    with tab1:
        st.write("📤 Import student data from Excel file")

        file = st.file_uploader('Upload student Excel', type=['xlsx'])
        if file:
            try:
                df = pd.read_excel(file, dtype=str)
                imported, errors, error_list = Utils.import_students_from_excel(df, db)

                if imported > 0:
                    st.success(f'✅ {imported} students imported successfully')
                    audit.log('IMPORT_STUDENTS', details=f'{imported} students imported')

                    if errors > 0:
                        with st.expander(f"⚠️ {errors} rows had errors"):
                            for error in error_list:
                                st.error(error, icon="❌")

                    # Download passwords
                    students = Student(db).get_all()
                    pwd_file = Utils.create_password_file(students)

                    st.download_button(
                        '📥 Download Student Password List',
                        data=pwd_file,
                        file_name=f'passwords_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        type='primary'
                    )
                else:
                    st.error(f"❌ No valid students imported. {errors} errors found.")
                    for error in error_list:
                        st.error(error, icon="❌")

            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")

    # ==================== TAB 2: MANAGE STUDENTS ====================
    with tab2:
        st.write("👥 View and manage all students")

        # Permanent download button
        st.markdown("### 📥 Download All Student Passwords")
        if st.button('📥 Download Password List', use_container_width=True, type='primary'):
            students = Student(db).get_all()
            pwd_file = Utils.create_password_file(students)
            st.download_button(
                '📥 Download Now',
                data=pwd_file,
                file_name=f'all_passwords_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                use_container_width=True,
                type='primary'
            )

        st.divider()

        # View students
        st.markdown("### 📋 All Students")

        col1, col2, col3 = st.columns(3)
        with col1:
            search = st.text_input('🔍 Search by Name/Admission').strip().lower()
        with col2:
            filter_class = st.selectbox('Filter by Class', ['All', '7', '8', '9', '10', '11', '12'])
        with col3:
            filter_house = st.selectbox('Filter by House', ['All', 'Taxila', 'Janata', 'Saachi', 'Nalanda'])

        # Get students
        all_students = Student(db).get_all()
        df_students = pd.DataFrame(all_students, columns=[
            'Admission No', 'Name', 'Class', 'Section', 'House',
            'Password Hash', 'Plain Password', 'Has Voted', 'Created At', 'Updated At'
        ])

        # Apply filters
        if search:
            df_students = df_students[
                (df_students['Name'].str.lower().str.contains(search)) |
                (df_students['Admission No'].str.lower().str.contains(search))
            ]

        if filter_class != 'All':
            df_students = df_students[df_students['Class'] == filter_class]

        if filter_house != 'All':
            df_students = df_students[df_students['House'] == filter_house]

        # Stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric('Total', len(df_students))
        with col2:
            voted = (df_students['Has Voted'] == 1).sum()
            st.metric('Voted', voted)
        with col3:
            st.metric('Not Voted', len(df_students) - voted)

        # Display
        st.dataframe(
            df_students[[
                'Admission No', 'Name', 'Class', 'Section', 'House',
                'Plain Password', 'Has Voted'
            ]],
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # CRUD Operations
        st.markdown("### ⚙️ Student Operations")

        crud_col1, crud_col2, crud_col3, crud_col4 = st.columns(4)

        # Add Student
        with crud_col1:
            if st.button('➕ Add Student', use_container_width=True):
                st.session_state.show_add_student = True

        # Edit Student
        with crud_col2:
            if st.button('✏️ Edit Student', use_container_width=True):
                st.session_state.show_edit_student = True

        # Reset Password
        with crud_col3:
            if st.button('🔑 Reset Password', use_container_width=True):
                st.session_state.show_reset_pwd = True

        # Delete Student
        with crud_col4:
            if st.button('🗑️ Delete Student', use_container_width=True):
                st.session_state.show_delete_student = True

        # Add Student Form
        if st.session_state.get('show_add_student'):
            st.markdown("#### ➕ Add New Student")
            col1, col2 = st.columns(2)

            with col1:
                new_adm = st.text_input('Admission Number', key='add_adm').strip().lower()
                new_name = st.text_input('Student Name', key='add_name')
                new_class = st.selectbox('Class', ['7', '8', '9', '10', '11', '12'], key='add_class')

            with col2:
                new_section = st.selectbox('Section', ['A', 'B', 'C'], key='add_section')
                new_house = st.selectbox('House', ['Taxila', 'Janata', 'Saachi', 'Nalanda'], key='add_house')

            if st.button('✅ Add Student', type='primary', use_container_width=True):
                pwd = Utils.generate_password()
                pwd_hash = Auth.hash_password(pwd)

                if Student(db).add(new_adm, new_name, new_class, new_section, new_house, pwd_hash, pwd):
                    st.success(f"✅ Student added! Password: **{pwd}**")
                    audit.log('ADD_STUDENT', 'admin', f'Added {new_name} ({new_adm})')
                    st.rerun()
                else:
                    st.error("❌ Error adding student")

        # Edit Student Form
        if st.session_state.get('show_edit_student'):
            st.markdown("#### ✏️ Edit Student")
            students_list = Student(db).get_all()
            edit_adm = st.selectbox(
                'Select Student',
                options=[s[0] for s in students_list],
                format_func=lambda x: f"{x} - {[s[1] for s in students_list if s[0] == x][0]}"
            )

            if edit_adm:
                student = Student(db).get(edit_adm)
                col1, col2 = st.columns(2)

                with col1:
                    edit_name = st.text_input('Name', value=student[1])
                    edit_class = st.selectbox('Class', ['7', '8', '9', '10', '11', '12'], index=['7', '8', '9', '10', '11', '12'].index(student[2]))

                with col2:
                    edit_section = st.selectbox('Section', ['A', 'B', 'C'], index=['A', 'B', 'C'].index(student[3]))
                    edit_house = st.selectbox('House', ['Taxila', 'Janata', 'Saachi', 'Nalanda'], index=['Taxila', 'Janata', 'Saachi', 'Nalanda'].index(student[4]))

                if st.button('💾 Save Changes', type='primary', use_container_width=True):
                    if Student(db).update(edit_adm, edit_name, edit_class, edit_section, edit_house):
                        st.success('✅ Student updated!')
                        audit.log('EDIT_STUDENT', 'admin', f'Edited {edit_name} ({edit_adm})')
                        st.rerun()
                    else:
                        st.error("❌ Error updating student")

        # Reset Password Form
        if st.session_state.get('show_reset_pwd'):
            st.markdown("#### 🔑 Reset Student Password")
            students_list = Student(db).get_all()
            reset_adm = st.selectbox(
                'Select Student',
                options=[s[0] for s in students_list],
                format_func=lambda x: f"{x} - {[s[1] for s in students_list if s[0] == x][0]}",
                key='reset_adm_select'
            )

            if st.button('🔄 Generate New Password', type='primary', use_container_width=True):
                new_pwd = Utils.generate_password()
                pwd_hash = Auth.hash_password(new_pwd)

                if Student(db).reset_password(reset_adm, pwd_hash, new_pwd):
                    st.success(f"✅ New password: **{new_pwd}**")
                    audit.log('RESET_PASSWORD', 'admin', f'Reset password for {reset_adm}')
                    st.rerun()
                else:
                    st.error("❌ Error resetting password")

        # Delete Student Form
        if st.session_state.get('show_delete_student'):
            st.markdown("#### 🗑️ Delete Student")
            students_list = Student(db).get_all()
            delete_adm = st.selectbox(
                'Select Student to Delete',
                options=[s[0] for s in students_list],
                format_func=lambda x: f"{x} - {[s[1] for s in students_list if s[0] == x][0]}",
                key='delete_adm_select'
            )

            if delete_adm:
                student = Student(db).get(delete_adm)
                st.warning(f"⚠️ Delete: **{student[1]}** (Adm: {delete_adm})")

                if student[7] == 1:  # has_voted
                    st.error("❌ Cannot delete - student has already voted")
                else:
                    if st.checkbox('I confirm deletion', key='confirm_delete'):
                        if st.button('🗑️ Delete', type='secondary', use_container_width=True):
                            if Student(db).delete(delete_adm):
                                st.success(f"✅ Deleted {student[1]}")
                                audit.log('DELETE_STUDENT', 'admin', f'Deleted {student[1]} ({delete_adm})')
                                st.rerun()

    # ==================== TAB 3: NOMINATE CANDIDATES ====================
    with tab3:
        st.write("👤 Nominate students as candidates")

        col1, col2 = st.columns(2)

        with col1:
            nom_adm = st.text_input('Candidate Admission Number').strip().lower()
            nom_type = st.selectbox('Committee Type', ['School', 'House'])

            if nom_type == 'School':
                nom_committee = st.selectbox('Committee', voting.SCHOOL_COMMITTEES)
                nom_class = st.selectbox('Voting Class', ['7', '8', '9', '10', '11', '12'])
                nom_house = None
                nom_group = None
            else:
                nom_committee = st.selectbox('Committee', voting.HOUSE_COMMITTEES)
                nom_house = st.selectbox('House', voting.HOUSES)
                nom_group = st.selectbox('Group', ['Junior (7-8)', 'Senior (9-12)'])
                nom_group = nom_group.split('(')[0].strip()
                nom_class = None

        with col2:
            st.write("")
            if nom_type == 'School':
                st.info(f"**Committee:** {nom_committee}\n**Class:** {nom_class}")
            else:
                st.info(f"**Committee:** {nom_committee}\n**House:** {nom_house}\n**Group:** {nom_group}")

        if st.button('✅ Nominate Candidate', use_container_width=True, type='primary'):
            candidate = Student(db).get(nom_adm)
            if not candidate:
                st.error(f"❌ Student {nom_adm} not found")
            else:
                if Candidate(db).add(nom_adm, nom_type, nom_committee, nom_class, nom_house, nom_group):
                    st.success(f'✅ {candidate[1]} nominated for {nom_committee}')
                    audit.log('NOMINATE_CANDIDATE', 'admin', f'{candidate[1]} for {nom_committee}')
                else:
                    st.error("❌ Error nominating candidate")

    # ==================== TAB 4: ELECTION CONTROL ====================
    with tab4:
        st.write("🎛️ Start, stop, and monitor election")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button('▶ START ELECTION', use_container_width=True, type='primary'):
                if election.start():
                    st.success('✅ Election is LIVE')
                    audit.log('START_ELECTION', 'admin')
                    st.rerun()

        with col2:
            if st.button('⏹ STOP ELECTION', use_container_width=True, type='secondary'):
                if election.stop():
                    st.warning('⏹ Election stopped')
                    audit.log('STOP_ELECTION', 'admin')
                    st.rerun()

        with col3:
            status = '🔴 LIVE' if election.is_live() else '⚫ STOPPED'
            st.metric('Status', status)

        st.divider()

        # Statistics
        st.markdown("### 📊 Real-time Statistics")
        stats = election.get_statistics()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric('Total Students', stats['total_students'])
        with col2:
            st.metric('Voted', stats['voted_students'])
        with col3:
            st.metric('Not Voted', stats['not_voted'])
        with col4:
            st.metric('Participation', f"{stats['participation_rate']:.1f}%")

    # ==================== TAB 5: RESULTS & AUDIT ====================
    with tab5:
        st.write("📊 Election results with audit information")

        result_sub_tabs = st.tabs(['Results', 'Statistics', 'Audit Log'])

        with result_sub_tabs[0]:
            if st.button('🔄 Refresh Results', use_container_width=True):
                st.rerun()

            results = db.execute('''
                SELECT
                    c.committee_name,
                    c.admission_no,
                    s.name,
                    s.class,
                    COUNT(v.id) as vote_count
                FROM candidates c
                LEFT JOIN students s ON LOWER(TRIM(c.admission_no)) = LOWER(TRIM(s.admission_no))
                LEFT JOIN votes v ON LOWER(TRIM(v.candidate_adm)) = LOWER(TRIM(c.admission_no))
                                  AND v.committee_name = c.committee_name
                GROUP BY c.id
                ORDER BY c.committee_name, vote_count DESC
            ''').fetchall()

            if results:
                current_committee = None
                for committee, adm, name, cls, vote_count in results:
                    if committee != current_committee:
                        current_committee = committee
                        st.markdown(f"### {committee}")

                    col1, col2, col3 = st.columns([3, 1, 2])
                    with col1:
                        st.write(f"**{name}** (Class {cls})")
                    with col2:
                        st.write(f"**{int(vote_count)}** votes")
                    with col3:
                        if results:
                            max_votes = max([r[4] for r in results if r[0] == committee])
                            if max_votes > 0:
                                pct = (vote_count / max_votes) * 100
                                st.progress(pct / 100, text=f"{pct:.0f}%")

                    st.divider()
            else:
                st.info("No results yet")

        with result_sub_tabs[1]:
            stats = election.get_statistics()
            st.metric('Total Students', stats['total_students'])
            st.metric('Participated', f"{stats['voted_students']} ({stats['participation_rate']:.1f}%)")
            st.metric('Total Votes Cast', stats['total_votes'])

            if stats['votes_by_committee']:
                st.markdown("### Votes by Committee")
                df_votes = pd.DataFrame(list(stats['votes_by_committee'].items()), columns=['Committee', 'Votes'])
                st.dataframe(df_votes, use_container_width=True, hide_index=True)

        with result_sub_tabs[2]:
            st.markdown("### 📋 Audit Trail")
            logs = audit.get_all()
            if logs:
                df_logs = pd.DataFrame(logs, columns=['ID', 'Action', 'User', 'Details', 'Timestamp'])
                df_logs['Timestamp'] = df_logs['Timestamp'].apply(Utils.format_timestamp)
                st.dataframe(df_logs, use_container_width=True, hide_index=True)
            else:
                st.info("No audit logs yet")

    # ==================== TAB 6: VOTING RECORDS ====================
    with tab6:
        st.write("🔍 Detailed voting records (who voted for whom)")

        votes = Vote(db).get_all_votes()

        if votes:
            df_votes = pd.DataFrame(votes, columns=['ID', 'Voter Adm', 'Candidate Adm', 'Committee', 'Timestamp'])

            # Add candidate and voter names
            voter_cache = {}
            candidate_cache = {}

            def get_voter_name(adm):
                if adm not in voter_cache:
                    student = Student(db).get(adm)
                    voter_cache[adm] = student[1] if student else 'Unknown'
                return voter_cache[adm]

            def get_candidate_name(adm):
                if adm not in candidate_cache:
                    student = Student(db).get(adm)
                    candidate_cache[adm] = student[1] if student else 'Unknown'
                return candidate_cache[adm]

            df_votes['Voter Name'] = df_votes['Voter Adm'].apply(get_voter_name)
            df_votes['Candidate Name'] = df_votes['Candidate Adm'].apply(get_candidate_name)
            df_votes['Timestamp'] = df_votes['Timestamp'].apply(Utils.format_timestamp)

            # Display
            st.dataframe(
                df_votes[['Voter Adm', 'Voter Name', 'Candidate Adm', 'Candidate Name', 'Committee', 'Timestamp']],
                use_container_width=True,
                hide_index=True
            )

            # Export option
            csv = df_votes.to_csv(index=False)
            st.download_button(
                '📥 Export Voting Records (CSV)',
                data=csv,
                file_name=f'voting_records_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv'
            )
        else:
            st.info("No votes recorded yet")

# ==================== STUDENT VOTING PAGE ====================
elif st.session_state.user_type == 'student':
    student = st.session_state.user_data
    student_obj = Student(db)

    # Refresh student data from DB
    fresh_student = student_obj.get(student[0])

    # Logout button
    col1, col2 = st.columns([8, 1])
    with col2:
        if st.button('🚪 Logout', type='secondary'):
            audit.log('STUDENT_LOGOUT', student[0])
            st.session_state.user_type = None
            st.session_state.user_data = None
            st.session_state.review_votes = False
            st.session_state.temp_votes = {}
            st.rerun()

    st.subheader(f'🎓 Welcome {fresh_student[1]}')
    st.markdown(f"**Class {fresh_student[2]}** | **{fresh_student[4]}** House")

    # Check if already voted
    if fresh_student[7] == 1:  # has_voted
        st.success('✅ You have already voted')
        st.info('📋 Here are your voting records:')

        # Display votes
        student_votes = voting.get_student_votes(fresh_student[0])

        if student_votes:
            for committee, vote_info in student_votes.items():
                with st.container():
                    st.markdown(f"""
                    <div class='vote-display'>
                        <b>{committee}</b><br>
                        ✓ {vote_info['candidate_name']} (Class {vote_info['candidate_class']})<br>
                        📅 {Utils.format_timestamp(vote_info['voted_at'])}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("No vote records found")

        if st.button('🚪 Logout', key='logout_after_vote'):
            audit.log('STUDENT_LOGOUT', student[0])
            st.session_state.user_type = None
            st.session_state.user_data = None
            st.rerun()

        st.stop()

    # Check election status
    if not election.is_live():
        st.warning('⏸️ Election is not currently live')
        st.stop()

    # ==================== VOTING INTERFACE ====================
    if not st.session_state.review_votes:
        vote_choices = st.session_state.temp_votes.copy()

        st.markdown('## 🏫 School Committees')
        school_candidates = db.execute('''
            SELECT * FROM candidates
            WHERE committee_type="School" AND scope_class=? AND admission_no IS NOT NULL
            GROUP BY committee_name
        ''', (fresh_student[2],)).fetchall()

        for committee in voting.SCHOOL_COMMITTEES:
            candidates = db.execute('''
                SELECT DISTINCT c.admission_no FROM candidates c
                WHERE c.committee_type="School" AND c.scope_class=?
                AND c.committee_name=?
            ''', (fresh_student[2], committee)).fetchall()

            if candidates:
                options = []
                mapping = {}

                for (cand_adm,) in candidates:
                    cand = student_obj.get(cand_adm)
                    if cand:
                        label = f"{cand[1]} | Class {cand[2]} | Sec {cand[3]}"
                        options.append(label)
                        mapping[label] = cand_adm

                if options:
                    default_idx = 0
                    if committee in vote_choices:
                        for i, opt in enumerate(options):
                            if mapping[opt] == vote_choices[committee]:
                                default_idx = i
                                break

                    choice = st.radio(f'{committee}', options, key=f's_{committee}', index=default_idx)
                    vote_choices[committee] = mapping[choice]

        st.markdown('## 🏠 House Committees')
        group = voting.get_eligible_house_committees(fresh_student[2])

        house_candidates = db.execute('''
            SELECT DISTINCT c.admission_no FROM candidates c
            WHERE c.committee_type="House" AND c.scope_house=?
            AND c.section_group=? AND c.admission_no IS NOT NULL
        ''', (fresh_student[4], group)).fetchall()

        for committee in voting.HOUSE_COMMITTEES:
            candidates = db.execute('''
                SELECT DISTINCT c.admission_no FROM candidates c
                WHERE c.committee_type="House" AND c.scope_house=?
                AND c.section_group=? AND c.committee_name=?
            ''', (fresh_student[4], group, committee)).fetchall()

            if candidates:
                options = []
                mapping = {}

                for (cand_adm,) in candidates:
                    cand = student_obj.get(cand_adm)
                    if cand:
                        label = f"{cand[1]} | Class {cand[2]} | Sec {cand[3]}"
                        options.append(label)
                        mapping[label] = cand_adm

                if options:
                    house_key = f'House-{committee}'
                    default_idx = 0
                    if house_key in vote_choices:
                        for i, opt in enumerate(options):
                            if mapping[opt] == vote_choices[house_key]:
                                default_idx = i
                                break

                    choice = st.radio(
                        f'{committee} ({fresh_student[4]})',
                        options,
                        key=f'h_{committee}',
                        index=default_idx
                    )
                    vote_choices[house_key] = mapping[choice]

        st.markdown("---")
        col1, col2 = st.columns([2, 1])

        with col1:
            if st.button('👁️ Review & Verify Votes', use_container_width=True, type='primary'):
                st.session_state.temp_votes = vote_choices
                st.session_state.review_votes = True
                st.rerun()

        with col2:
            if st.button('🚪 Exit Without Voting', use_container_width=True):
                audit.log('STUDENT_EXIT_NO_VOTE', student[0])
                st.session_state.user_type = None
                st.session_state.user_data = None
                st.session_state.review_votes = False
                st.session_state.temp_votes = {}
                st.rerun()

    # ==================== VERIFICATION SCREEN ====================
    else:
        st.markdown("## ✅ Verify Your Votes")
        st.info("🔒 **SECURE VOTING**: Review your selections carefully. Once submitted, votes CANNOT be changed.")

        vote_choices = st.session_state.temp_votes

        st.markdown("### Your Selections:")

        for committee, cand_adm in vote_choices.items():
            cand = student_obj.get(cand_adm)
            if cand:
                st.markdown(f"**{committee}:** {cand[1]} (Class {cand[2]}, Section {cand[3]})")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            if st.button('✅ CONFIRM & SUBMIT VOTES', use_container_width=True, type='primary'):
                # Final integrity check
                success, msg = voting.submit_votes(fresh_student[0], vote_choices)

                if success:
                    st.success('✅ Your vote has been securely recorded!')
                    st.balloons()
                    st.markdown("""
                    ### 🔒 Vote Confirmation
                    - **Voter ID**: Recorded
                    - **Timestamp**: Recorded
                    - **Integrity**: Verified
                    - **Status**: IMMUTABLE

                    Thank you for participating in a fair and transparent election.
                    """)

                    audit.log('VOTE_SUBMITTED', fresh_student[0], f'Submitted {len(vote_choices)} votes')

                    import time
                    time.sleep(3)

                    st.session_state.user_type = None
                    st.session_state.user_data = None
                    st.session_state.review_votes = False
                    st.session_state.temp_votes = {}
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

        with col2:
            if st.button('🔙 Back to Edit Votes', use_container_width=True):
                st.session_state.review_votes = False
                st.rerun()
