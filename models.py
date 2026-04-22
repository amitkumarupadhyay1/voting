"""
JB Academy Election Portal - Database Models
Thread-safe, WAL-mode SQLite with full election integrity.
"""

import json
import secrets
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

# ══════════════════════════════════════════════════════════════════════════════
#  CACHE MANAGER
# ══════════════════════════════════════════════════════════════════════════════


class CacheManager:
    """
    Thread-safe in-memory cache with TTL (Time To Live).
    Used for caching frequently accessed data that rarely changes.
    """

    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}  # {key: (value, expiry_time)}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if it exists and hasn't expired."""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                else:
                    # Expired, remove it
                    del self._cache[key]
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set a cached value with TTL (default 5 minutes)."""
        with self._lock:
            expiry = time.time() + ttl_seconds
            self._cache[key] = (value, expiry)

    def invalidate(self, key: str = None):
        """Invalidate a specific key or all cache if key is None."""
        with self._lock:
            if key is None:
                self._cache.clear()
            elif key in self._cache:
                del self._cache[key]

    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys that start with the given pattern."""
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
            for key in keys_to_delete:
                del self._cache[key]


# Global cache instance
_cache = CacheManager()


class Database:
    """
    Thread-safe SQLite wrapper.
    - WAL journal mode for concurrent reads + serialised writes
    - One connection per thread via threading.local()
    - A module-level write lock serialises all INSERT/UPDATE/DELETE
    """

    _write_lock = threading.Lock()  # one writer at a time across all threads
    _local = threading.local()  # per-thread connection cache

    def __init__(self, db_file: str = "school_voting.db"):
        self.db_file = db_file
        # Run schema setup on the calling thread's connection
        conn = self._conn()
        self._initialize_schema(conn)
        self._migrate_schema(conn)

    # ── connection management ──────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        """Return (or create) a per-thread connection."""
        if not getattr(self._local, "conn", None):
            conn = sqlite3.connect(self.db_file, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA cache_size=10000")
            conn.execute("PRAGMA busy_timeout=5000")  # wait up to 5 s on lock
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return self._local.conn

    # ── public query helpers ───────────────────────────────────────────────────

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a read query (no lock needed for WAL reads)."""
        return self._conn().execute(query, params)

    def write(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single write statement with the global write lock."""
        with self._write_lock:
            cur = self._conn().execute(query, params)
            self._conn().commit()
            return cur

    def write_many(self, statements: List[Tuple[str, tuple]]) -> bool:
        """
        Execute multiple write statements atomically.
        statements: [(sql, params), ...]
        Returns True on success, False on failure (auto-rollback).
        """
        with self._write_lock:
            conn = self._conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                for sql, params in statements:
                    conn.execute(sql, params)
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"[DB] write_many rollback: {e}")
                return False

    # kept for backward compat with old call sites
    def commit(self):
        self._conn().commit()

    def close(self):
        if getattr(self._local, "conn", None):
            self._local.conn.close()
            self._local.conn = None

    # ── schema ─────────────────────────────────────────────────────────────────

    def _initialize_schema(self, conn: sqlite3.Connection):
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            admission_no      TEXT PRIMARY KEY,
            name              TEXT NOT NULL,
            class             TEXT NOT NULL,
            section           TEXT NOT NULL,
            house             TEXT NOT NULL,
            password          TEXT NOT NULL,
            generated_password TEXT,
            has_voted         INTEGER DEFAULT 0,
            created_at        TEXT,
            updated_at        TEXT
        );

        CREATE TABLE IF NOT EXISTS committees (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            committee_type TEXT NOT NULL CHECK(committee_type IN ("School","House")),
            description    TEXT DEFAULT "",
            max_winners    INTEGER DEFAULT 1,
            created_at     TEXT,
            UNIQUE(name, committee_type)
        );

        CREATE TABLE IF NOT EXISTS candidates (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            admission_no   TEXT NOT NULL,
            committee_type TEXT NOT NULL,
            committee_name TEXT NOT NULL,
            scope_class    TEXT,
            scope_house    TEXT,
            section_group  TEXT,
            manifesto      TEXT,
            status         TEXT DEFAULT "approved",
            nominated_by   TEXT DEFAULT "admin",
            created_at     TEXT,
            UNIQUE(admission_no, committee_name)
        );

        CREATE TABLE IF NOT EXISTS vote_tokens (
            token        TEXT PRIMARY KEY,
            admission_no TEXT NOT NULL UNIQUE,
            is_used      INTEGER DEFAULT 0,
            created_at   TEXT,
            FOREIGN KEY (admission_no) REFERENCES students(admission_no)
        );

        CREATE TABLE IF NOT EXISTS votes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            vote_token     TEXT NOT NULL,
            candidate_adm  TEXT NOT NULL,
            committee_name TEXT NOT NULL,
            created_at     TEXT NOT NULL,
            FOREIGN KEY (candidate_adm) REFERENCES students(admission_no),
            FOREIGN KEY (vote_token)    REFERENCES vote_tokens(token)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            action     TEXT NOT NULL,
            user_adm   TEXT,
            details    TEXT,
            ip_address TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            key        TEXT PRIMARY KEY,
            value      TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS election_backups (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            filename   TEXT NOT NULL,
            total_votes INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            user_id    TEXT NOT NULL,
            attempted_at TEXT NOT NULL,
            success    INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_votes_committee   ON votes(committee_name);
        CREATE INDEX IF NOT EXISTS idx_votes_token       ON votes(vote_token);
        CREATE INDEX IF NOT EXISTS idx_candidates_comm   ON candidates(committee_name, status);
        CREATE INDEX IF NOT EXISTS idx_students_voted    ON students(has_voted);
        CREATE INDEX IF NOT EXISTS idx_login_attempts    ON login_attempts(user_id, attempted_at);
        CREATE INDEX IF NOT EXISTS idx_students_voted_class ON students(has_voted, class);
        CREATE INDEX IF NOT EXISTS idx_students_voted_house ON students(has_voted, house);
        CREATE INDEX IF NOT EXISTS idx_votes_created     ON votes(created_at);
        CREATE INDEX IF NOT EXISTS idx_candidates_adm    ON candidates(admission_no);
        CREATE INDEX IF NOT EXISTS idx_votes_candidate_comm ON votes(candidate_adm, committee_name);
        """)
        conn.commit()

    def _migrate_schema(self, conn: sqlite3.Connection):
        """Non-destructive migrations for existing databases."""
        migrations = [
            ("students", "generated_password", "TEXT"),
            ("students", "created_at", "TEXT"),
            ("students", "updated_at", "TEXT"),
            ("candidates", "created_at", "TEXT"),
            ("candidates", "manifesto", "TEXT"),
            ("candidates", "status", "TEXT DEFAULT 'approved'"),
            ("candidates", "nominated_by", "TEXT DEFAULT 'admin'"),
            ("committees", "description", "TEXT DEFAULT ''"),
            ("committees", "max_winners", "INTEGER DEFAULT 1"),
            ("audit_log", "ip_address", "TEXT"),
            ("settings", "updated_at", "TEXT"),
        ]
        for table, col, col_type in migrations:
            try:
                conn.execute(f"SELECT {col} FROM {table} LIMIT 1")
            except sqlite3.OperationalError:
                try:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass

        # Warn about truly old schema
        try:
            conn.execute("SELECT voter_adm FROM votes LIMIT 1")
            print("WARNING: Old schema detected — delete school_voting.db and restart.")
        except sqlite3.OperationalError:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  MODELS
# ══════════════════════════════════════════════════════════════════════════════


class Student:
    def __init__(self, db: Database):
        self.db = db

    def add(
        self,
        admission_no: str,
        name: str,
        class_num: str,
        section: str,
        house: str,
        password_hash: str,
        password_plain: str,
    ) -> bool:
        now = datetime.now().isoformat()
        result = self.db.write_many(
            [
                (
                    """INSERT OR REPLACE INTO students
                (admission_no,name,class,section,house,password,
                 generated_password,has_voted,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,0,?,?)""",
                    (
                        admission_no,
                        name,
                        class_num,
                        section,
                        house,
                        password_hash,
                        password_plain,
                        now,
                        now,
                    ),
                )
            ]
        )
        if result:
            # Invalidate student count caches
            _cache.invalidate("student_count_by_class")
            _cache.invalidate("student_count_by_house")
        return result

    def get(self, admission_no: str) -> Optional[Tuple]:
        adm = str(admission_no).strip().lower().split(".")[0]
        row = self.db.execute(
            "SELECT * FROM students WHERE LOWER(TRIM(admission_no))=?", (adm,)
        ).fetchone()
        return tuple(row) if row else None

    def get_all(self) -> List[Tuple]:
        return [
            tuple(r)
            for r in self.db.execute(
                "SELECT * FROM students ORDER BY admission_no"
            ).fetchall()
        ]

    def update(
        self,
        admission_no: str,
        name: str = None,
        class_num: str = None,
        section: str = None,
        house: str = None,
    ) -> bool:
        updates, params = [], []
        if name:
            updates.append("name=?")
            params.append(name)
        if class_num:
            updates.append("class=?")
            params.append(class_num)
        if section:
            updates.append("section=?")
            params.append(section)
        if house:
            updates.append("house=?")
            params.append(house)
        if not updates:
            return False
        updates.append("updated_at=?")
        params.extend([datetime.now().isoformat(), admission_no])
        result = self.db.write_many(
            [
                (
                    f'UPDATE students SET {", ".join(updates)} WHERE admission_no=?',
                    tuple(params),
                )
            ]
        )
        if result and (class_num or house):
            # Invalidate caches if class or house changed
            if class_num:
                _cache.invalidate("student_count_by_class")
            if house:
                _cache.invalidate("student_count_by_house")
        return result

    def delete(self, admission_no: str) -> bool:
        student = self.get(admission_no)
        if not student or student[7] == 1:
            return False
        result = self.db.write_many(
            [
                (
                    "DELETE FROM candidates WHERE LOWER(TRIM(admission_no))=?",
                    (admission_no.lower(),),
                ),
                ("DELETE FROM students WHERE admission_no=?", (admission_no,)),
            ]
        )
        if result:
            # Invalidate student count caches
            _cache.invalidate("student_count_by_class")
            _cache.invalidate("student_count_by_house")
        return result

    def reset_password(
        self, admission_no: str, password_hash: str, password_plain: str
    ) -> bool:
        return self.db.write_many(
            [
                (
                    """UPDATE students SET password=?,generated_password=?,updated_at=?
                WHERE admission_no=?""",
                    (
                        password_hash,
                        password_plain,
                        datetime.now().isoformat(),
                        admission_no,
                    ),
                )
            ]
        )

    def mark_voted(self, admission_no: str) -> bool:
        return self.db.write_many(
            [
                (
                    "UPDATE students SET has_voted=1,updated_at=? WHERE admission_no=?",
                    (datetime.now().isoformat(), admission_no),
                )
            ]
        )

    def get_pending_voters(self) -> List[Tuple]:
        """Students who haven't voted yet — for download."""
        return [
            tuple(r)
            for r in self.db.execute(
                "SELECT admission_no,name,class,section,house FROM students WHERE has_voted=0 ORDER BY class,name"
            ).fetchall()
        ]

    def get_count_by_class(self) -> Dict[str, int]:
        """Get student count grouped by class (cached)."""
        cache_key = "student_count_by_class"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        rows = self.db.execute(
            "SELECT class, COUNT(*) FROM students GROUP BY class ORDER BY class"
        ).fetchall()
        result = {row[0]: row[1] for row in rows}
        _cache.set(cache_key, result, ttl_seconds=300)  # 5 minutes
        return result

    def get_count_by_house(self) -> Dict[str, int]:
        """Get student count grouped by house (cached)."""
        cache_key = "student_count_by_house"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        rows = self.db.execute(
            "SELECT house, COUNT(*) FROM students GROUP BY house ORDER BY house"
        ).fetchall()
        result = {row[0]: row[1] for row in rows}
        _cache.set(cache_key, result, ttl_seconds=300)  # 5 minutes
        return result


class VoteToken:
    def __init__(self, db: Database):
        self.db = db

    def generate_token(self, admission_no: str) -> Optional[str]:
        token = secrets.token_hex(32)
        ok = self.db.write_many(
            [
                (
                    "INSERT INTO vote_tokens (token,admission_no,created_at) VALUES (?,?,?)",
                    (token, admission_no, datetime.now().isoformat()),
                )
            ]
        )
        return token if ok else None

    def get_unused(self, admission_no: str) -> Optional[str]:
        row = self.db.execute(
            "SELECT token FROM vote_tokens WHERE admission_no=? AND is_used=0",
            (admission_no,),
        ).fetchone()
        return row[0] if row else None

    def mark_used(self, token: str) -> bool:
        return self.db.write_many(
            [("UPDATE vote_tokens SET is_used=1 WHERE token=?", (token,))]
        )


class Vote:
    def __init__(self, db: Database):
        self.db = db

    def cast_all(
        self, vote_token: str, admission_no: str, votes_dict: Dict[str, str]
    ) -> Tuple[bool, str]:
        """
        Fully atomic vote submission.
        1. Re-check has_voted inside the write lock (prevents race condition)
        2. Insert all vote rows
        3. Mark token used
        4. Mark student as voted
        All in one BEGIN IMMEDIATE transaction.
        """
        now = datetime.now().isoformat()
        stmts = []

        for committee_name, candidate_adm in votes_dict.items():
            stmts.append(
                (
                    "INSERT INTO votes (vote_token,candidate_adm,committee_name,created_at) VALUES (?,?,?,?)",
                    (vote_token, candidate_adm, committee_name, now),
                )
            )
        stmts.append(("UPDATE vote_tokens SET is_used=1 WHERE token=?", (vote_token,)))
        stmts.append(
            (
                "UPDATE students SET has_voted=1,updated_at=? WHERE admission_no=?",
                (now, admission_no),
            )
        )

        # We need to check has_voted inside the lock — do it manually
        with Database._write_lock:
            conn = self.db._conn()
            try:
                conn.execute("BEGIN IMMEDIATE")
                # Double-check inside the transaction
                row = conn.execute(
                    "SELECT has_voted FROM students WHERE admission_no=?",
                    (admission_no,),
                ).fetchone()
                if not row or row[0] == 1:
                    conn.rollback()
                    return False, "Already voted (concurrent submission detected)"
                for sql, params in stmts:
                    conn.execute(sql, params)
                conn.commit()
                return True, "OK"
            except Exception as e:
                conn.rollback()
                print(f"[Vote] cast_all error: {e}")
                return False, str(e)

    def get_student_votes(self, voter_adm: str) -> List[Tuple]:
        row = self.db.execute(
            "SELECT token FROM vote_tokens WHERE admission_no=? AND is_used=1",
            (voter_adm,),
        ).fetchone()
        if not row:
            return []
        return [
            tuple(r)
            for r in self.db.execute(
                "SELECT committee_name,candidate_adm,created_at FROM votes WHERE vote_token=? ORDER BY created_at",
                (row[0],),
            ).fetchall()
        ]

    def get_all_votes(self) -> List[Tuple]:
        return [
            tuple(r)
            for r in self.db.execute(
                "SELECT id,candidate_adm,committee_name,created_at FROM votes ORDER BY created_at DESC"
            ).fetchall()
        ]

    def delete_vote(self, vote_id: int) -> bool:
        return self.db.write_many([("DELETE FROM votes WHERE id=?", (vote_id,))])

    def record_tie_break(
        self, committee_name: str, winner_adm: str, reason: str, admin_id: str = "admin"
    ) -> bool:
        """Log a manual tie-break decision in the audit log."""

        return self.db.write_many(
            [
                (
                    "INSERT INTO audit_log (action,user_adm,details,created_at) VALUES (?,?,?,?)",
                    (
                        "TIE_BREAK",
                        admin_id,
                        f"Committee={committee_name} Winner={winner_adm} Reason={reason}",
                        datetime.now().isoformat(),
                    ),
                )
            ]
        )

    def get_results_all(self) -> List[Tuple]:
        """
        Single query: all committee results with candidate names, class, house, section.
        Uses LOWER/TRIM to handle case-insensitive admission_no matching.
        """
        return [tuple(r) for r in self.db.execute("""
            SELECT
                c.committee_type,
                c.committee_name,
                c.scope_house,
                c.section_group,
                c.admission_no,
                s.name,
                s.class,
                s.section,
                s.house,
                COUNT(v.id) AS vote_count
            FROM candidates c
            LEFT JOIN students s ON LOWER(TRIM(c.admission_no)) = LOWER(TRIM(s.admission_no))
            LEFT JOIN votes v ON LOWER(TRIM(v.candidate_adm)) = LOWER(TRIM(c.admission_no))
                AND v.committee_name = c.committee_name
            WHERE c.status = "approved"
            GROUP BY c.committee_name, c.admission_no
            ORDER BY c.committee_type, c.committee_name, vote_count DESC
        """).fetchall()]


class Candidate:
    def __init__(self, db: Database):
        self.db = db

    def add(
        self,
        admission_no: str,
        committee_type: str,
        committee_name: str,
        scope_class: str = None,
        scope_house: str = None,
        section_group: str = None,
        manifesto: str = None,
        status: str = "approved",
        nominated_by: str = "admin",
    ) -> Tuple[bool, str]:
        adm = admission_no.strip().lower()
        existing = self.db.execute(
            "SELECT id FROM candidates WHERE LOWER(TRIM(admission_no))=? AND committee_name=?",
            (adm, committee_name),
        ).fetchone()
        if existing:
            return False, "Student is already nominated for this committee"
        ok = self.db.write_many(
            [
                (
                    """INSERT INTO candidates
               (admission_no,committee_type,committee_name,scope_class,
                scope_house,section_group,manifesto,status,nominated_by,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (
                        adm,
                        committee_type,
                        committee_name,
                        scope_class,
                        scope_house,
                        section_group,
                        manifesto or "",
                        status,
                        nominated_by,
                        datetime.now().isoformat(),
                    ),
                )
            ]
        )
        return (True, "Nominated successfully") if ok else (False, "Database error")

    def approve(self, candidate_id: int) -> bool:
        return self.db.write_many(
            [("UPDATE candidates SET status='approved' WHERE id=?", (candidate_id,))]
        )

    def reject(self, candidate_id: int) -> bool:
        return self.db.write_many(
            [("UPDATE candidates SET status='rejected' WHERE id=?", (candidate_id,))]
        )

    def remove(self, candidate_id: int) -> bool:
        return self.db.write_many(
            [("DELETE FROM candidates WHERE id=?", (candidate_id,))]
        )

    def withdraw(self, admission_no: str, committee_name: str) -> Tuple[bool, str]:
        """Student withdraws their own nomination (only when election is in SETUP phase)."""
        row = self.db.execute(
            "SELECT id,status FROM candidates WHERE LOWER(TRIM(admission_no))=? AND committee_name=?",
            (admission_no.strip().lower(), committee_name),
        ).fetchone()
        if not row:
            return False, "Nomination not found"
        ok = self.db.write_many([("DELETE FROM candidates WHERE id=?", (row[0],))])
        return (True, "Nomination withdrawn") if ok else (False, "Database error")

    def bulk_add(
        self, rows: List[Dict], progress_callback=None
    ) -> Tuple[int, List[str]]:
        """
        Bulk-nominate from a list of dicts.
        Each dict: {admission_no, committee_type, committee_name,
                    scope_class, scope_house, section_group, manifesto}
        Returns (imported_count, error_messages).
        """
        imported, errors = 0, []
        now = datetime.now().isoformat()
        total = len(rows)
        for i, r in enumerate(rows, 1):
            if progress_callback:
                progress_callback(i, total)
            adm = str(r.get("admission_no", "")).strip().lower()
            ctype = str(r.get("committee_type", "")).strip()
            cname = str(r.get("committee_name", "")).strip()
            if not adm or not ctype or not cname:
                errors.append(
                    f"Row {i}: missing admission_no / committee_type / committee_name"
                )
                continue
            existing = self.db.execute(
                "SELECT id FROM candidates WHERE LOWER(TRIM(admission_no))=? AND committee_name=?",
                (adm, cname),
            ).fetchone()
            if existing:
                errors.append(f"Row {i}: {adm} already nominated for {cname} — skipped")
                continue
            ok = self.db.write_many(
                [
                    (
                        """INSERT INTO candidates
                   (admission_no,committee_type,committee_name,scope_class,
                    scope_house,section_group,manifesto,status,nominated_by,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (
                            adm,
                            ctype,
                            cname,
                            r.get("scope_class"),
                            r.get("scope_house"),
                            r.get("section_group"),
                            r.get("manifesto", ""),
                            "approved",
                            "admin",
                            now,
                        ),
                    )
                ]
            )
            if ok:
                imported += 1
            else:
                errors.append(f"Row {i}: DB error for {adm}")
        return imported, errors

    def get_all(self) -> List[Tuple]:
        return [
            tuple(r)
            for r in self.db.execute(
                "SELECT * FROM candidates ORDER BY committee_name"
            ).fetchall()
        ]

    def get_all_with_names(self) -> List[Tuple]:
        return [tuple(r) for r in self.db.execute("""
            SELECT c.id,c.admission_no,s.name,c.committee_type,
                   c.committee_name,c.scope_class,c.scope_house,
                   c.section_group,c.manifesto,c.status,c.nominated_by,c.created_at
            FROM candidates c
            LEFT JOIN students s ON LOWER(TRIM(c.admission_no))=LOWER(TRIM(s.admission_no))
            ORDER BY c.status,c.committee_name,s.name
        """).fetchall()]

    def get_pending(self) -> List[Tuple]:
        return [tuple(r) for r in self.db.execute("""
            SELECT c.id,c.admission_no,s.name,c.committee_type,
                   c.committee_name,c.scope_class,c.scope_house,
                   c.section_group,c.manifesto,c.status,c.nominated_by,c.created_at
            FROM candidates c
            LEFT JOIN students s ON LOWER(TRIM(c.admission_no))=LOWER(TRIM(s.admission_no))
            WHERE c.status="pending" ORDER BY c.created_at
        """).fetchall()]


class Committee:
    DEFAULT_SCHOOL = [
        "Sports",
        "Literary",
        "Eco",
        "Cultural",
        "Maintenance",
        "Discipline",
    ]
    DEFAULT_HOUSE = ["Sports", "CCA", "Discipline"]

    def __init__(self, db: Database):
        self.db = db
        self._seed_defaults()

    def _seed_defaults(self):
        count = self.db.execute("SELECT COUNT(*) FROM committees").fetchone()[0]
        if count == 0:
            stmts = []
            for name in self.DEFAULT_SCHOOL:
                stmts.append(
                    (
                        "INSERT OR IGNORE INTO committees (name,committee_type,created_at) VALUES (?,?,?)",
                        (name, "School", datetime.now().isoformat()),
                    )
                )
            for name in self.DEFAULT_HOUSE:
                stmts.append(
                    (
                        "INSERT OR IGNORE INTO committees (name,committee_type,created_at) VALUES (?,?,?)",
                        (name, "House", datetime.now().isoformat()),
                    )
                )
            self.db.write_many(stmts)
            # Invalidate committee caches after seeding
            _cache.invalidate("committee_list_School")
            _cache.invalidate("committee_list_House")

    def get_all(self) -> List[Tuple]:
        return [
            tuple(r)
            for r in self.db.execute(
                "SELECT * FROM committees ORDER BY committee_type,name"
            ).fetchall()
        ]

    def get_by_type(self, committee_type: str) -> List[str]:
        """Get committee names by type (cached)."""
        cache_key = f"committee_list_{committee_type}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        result = [
            r[0]
            for r in self.db.execute(
                "SELECT name FROM committees WHERE committee_type=? ORDER BY name",
                (committee_type,),
            ).fetchall()
        ]
        _cache.set(cache_key, result, ttl_seconds=600)  # 10 minutes (rarely changes)
        return result

    def get_max_winners(self, committee_name: str) -> int:
        """Return max_winners for a committee (default 1)."""
        row = self.db.execute(
            "SELECT max_winners FROM committees WHERE name=?", (committee_name,)
        ).fetchone()
        return int(row[0]) if row and row[0] else 1

    def get_meta_map(self) -> Dict[str, Dict]:
        """Return {name: {type, description, max_winners}} for all committees — one query."""
        rows = self.db.execute(
            "SELECT name, committee_type, description, max_winners FROM committees"
        ).fetchall()
        return {
            r[0]: {
                "type": r[1],
                "description": r[2] or "",
                "max_winners": int(r[3] or 1),
            }
            for r in rows
        }

    def add(
        self,
        name: str,
        committee_type: str,
        description: str = "",
        max_winners: int = 1,
    ) -> Tuple[bool, str]:
        name = name.strip()
        if not name:
            return False, "Committee name cannot be empty"
        if max_winners < 1:
            max_winners = 1
        ok = self.db.write_many(
            [
                (
                    "INSERT INTO committees (name,committee_type,description,max_winners,created_at) VALUES (?,?,?,?,?)",
                    (
                        name,
                        committee_type,
                        description.strip(),
                        max_winners,
                        datetime.now().isoformat(),
                    ),
                )
            ]
        )
        if ok:
            # Invalidate committee list cache for this type
            _cache.invalidate(f"committee_list_{committee_type}")
            return True, "Committee added"
        return False, "Committee already exists or database error"

    def delete(self, committee_id: int) -> Tuple[bool, str]:
        row = self.db.execute(
            "SELECT name, committee_type FROM committees WHERE id=?", (committee_id,)
        ).fetchone()
        if not row:
            return False, "Committee not found"
        name = row[0]
        committee_type = row[1]
        in_use = self.db.execute(
            "SELECT COUNT(*) FROM candidates WHERE committee_name=?", (name,)
        ).fetchone()[0]
        if in_use > 0:
            return (
                False,
                f"Cannot delete — {in_use} candidate(s) nominated under this committee",
            )
        self.db.write_many([("DELETE FROM committees WHERE id=?", (committee_id,))])
        # Invalidate committee list cache for this type
        _cache.invalidate(f"committee_list_{committee_type}")
        return True, "Committee deleted"


class Election:
    """
    Phase state machine:
      SETUP  — nominations open, voting blocked
      LIVE   — voting open, nominations locked
      CLOSED — voting stopped, results public
    Transitions: SETUP→LIVE→CLOSED  (reset returns to SETUP)
    """

    PHASE_SETUP = "setup"
    PHASE_LIVE = "live"
    PHASE_CLOSED = "closed"

    def __init__(self, db: Database):
        self.db = db
        # Migrate old binary flag to phase
        self._migrate_phase()

    def _migrate_phase(self):
        """One-time migration: convert old election_live flag to phase."""
        phase_row = self.db.execute(
            "SELECT value FROM settings WHERE key='election_phase'"
        ).fetchone()
        if phase_row:
            return  # already migrated
        old_row = self.db.execute(
            "SELECT value FROM settings WHERE key='election_live'"
        ).fetchone()
        phase = self.PHASE_LIVE if (old_row and old_row[0] == "1") else self.PHASE_SETUP
        self.db.write_many(
            [
                (
                    "INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,?)",
                    ("election_phase", phase, datetime.now().isoformat()),
                )
            ]
        )

    def _set_phase(self, phase: str):
        self.db.write_many(
            [
                (
                    "INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,?)",
                    ("election_phase", phase, datetime.now().isoformat()),
                )
            ]
        )

    def get_phase(self) -> str:
        row = self.db.execute(
            "SELECT value FROM settings WHERE key='election_phase'"
        ).fetchone()
        return row[0] if row else self.PHASE_SETUP

    # Convenience booleans used throughout the app
    def is_setup(self) -> bool:
        return self.get_phase() == self.PHASE_SETUP

    def is_live(self) -> bool:
        return self.get_phase() == self.PHASE_LIVE

    def is_closed(self) -> bool:
        return self.get_phase() == self.PHASE_CLOSED

    def go_live(self) -> Tuple[bool, str]:
        """SETUP → LIVE. Auto-rejects all pending nominations."""
        if not self.is_setup():
            return False, "Can only go live from Setup phase."
        approved = self.db.execute(
            'SELECT COUNT(*) FROM candidates WHERE status="approved"'
        ).fetchone()[0]
        if approved == 0:
            return False, "Cannot go live — no approved candidates exist."
        # Auto-reject lingering pending nominations
        self.db.write_many(
            [('UPDATE candidates SET status="rejected" WHERE status="pending"', ())]
        )
        self._set_phase(self.PHASE_LIVE)
        return True, "Election is now LIVE. Pending nominations auto-rejected."

    def close(self) -> Tuple[bool, str]:
        """LIVE → CLOSED."""
        if not self.is_live():
            return False, "Election is not currently live."
        self._set_phase(self.PHASE_CLOSED)
        return True, "Election closed. Results are now public."

    def reset(self) -> Tuple[bool, str]:
        """Any phase → SETUP. Clears votes. Caller must backup first."""
        now = datetime.now().isoformat()
        total_votes = self.db.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
        ok = self.db.write_many(
            [
                (
                    "INSERT INTO audit_log (action,user_adm,details,created_at) VALUES (?,?,?,?)",
                    (
                        "ELECTION_RESET",
                        "admin",
                        f"Reset from phase={self.get_phase()}. {total_votes} votes cleared.",
                        now,
                    ),
                ),
                ("DELETE FROM votes", ()),
                ("DELETE FROM vote_tokens", ()),
                ("UPDATE students SET has_voted=0", ()),
                (
                    "INSERT OR REPLACE INTO settings(key,value,updated_at) VALUES(?,?,?)",
                    ("election_phase", self.PHASE_SETUP, now),
                ),
            ]
        )
        return (
            (True, f"Reset complete. {total_votes} votes cleared.")
            if ok
            else (False, "Reset failed — check logs.")
        )

    def get_statistics(self) -> Dict:
        total = self.db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        voted = self.db.execute(
            "SELECT COUNT(*) FROM students WHERE has_voted=1"
        ).fetchone()[0]
        t_votes = self.db.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
        return {
            "total_students": total,
            "voted_students": voted,
            "not_voted": total - voted,
            "total_votes": t_votes,
            "participation_rate": (voted / total * 100) if total > 0 else 0,
            "phase": self.get_phase(),
        }


class AuditLog:
    def __init__(self, db: Database):
        self.db = db

    def log(
        self, action: str, user_adm: str = None, details: str = None, ip: str = None
    ):
        self.db.write_many(
            [
                (
                    "INSERT INTO audit_log (action,user_adm,details,ip_address,created_at) VALUES (?,?,?,?,?)",
                    (action, user_adm, details, ip, datetime.now().isoformat()),
                )
            ]
        )

    def get_all(self) -> List[Tuple]:
        return [
            tuple(r)
            for r in self.db.execute(
                "SELECT * FROM audit_log ORDER BY created_at DESC"
            ).fetchall()
        ]

    def get_by_user(self, user_adm: str) -> List[Tuple]:
        return [
            tuple(r)
            for r in self.db.execute(
                "SELECT * FROM audit_log WHERE user_adm=? ORDER BY created_at DESC",
                (user_adm,),
            ).fetchall()
        ]


class Config:
    """Manager for configurable lists like Houses, Classes, and Sections."""

    DEFAULTS = {
        "houses": ["Ajanta", "Sanchi", "Taxila", "Nalanda"],
        "classes": ["6", "7", "8", "9", "10", "11", "12"],
        "sections": ["A", "B", "C", "D", "E"],
    }

    def __init__(self, db: Database):
        self.db = db

    def _get(self, key: str, default: Any) -> Any:
        cache_key = f"config_{key}"
        cached = _cache.get(cache_key)
        if cached is not None:
            return cached

        row = self.db.execute(
            "SELECT value FROM settings WHERE key=?",
            (f"conf_{key}",),
        ).fetchone()
        if row:
            try:
                val = json.loads(row[0])
                _cache.set(cache_key, val)
                return val
            except Exception:
                pass

        # Save default if not exists
        self._set(key, default)
        return default

    def _set(self, key: str, value: Any):
        self.db.write_many(
            [
                (
                    "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                    (f"conf_{key}", json.dumps(value), datetime.now().isoformat()),
                )
            ]
        )
        _cache.invalidate(f"config_{key}")

    def get_houses(self) -> List[str]:
        return self._get("houses", self.DEFAULTS["houses"])

    def set_houses(self, houses: List[str]):
        self._set(
            "houses",
            sorted(list(set(str(h).strip().title() for h in houses if str(h).strip()))),
        )

    def get_classes(self) -> List[str]:
        return self._get("classes", self.DEFAULTS["classes"])

    def set_classes(self, classes: List[str]):
        # Store classes as strings, sorted numerically
        def _sort_key(c):
            try:
                return int(c)
            except Exception:
                return 999

        data = sorted(
            list(set(str(c).strip() for c in classes if str(c).strip())), key=_sort_key
        )
        self._set("classes", data)

    def get_sections(self) -> List[str]:
        return self._get("sections", self.DEFAULTS["sections"])

    def set_sections(self, sections: List[str]):
        self._set(
            "sections",
            sorted(
                list(set(str(s).strip().upper() for s in sections if str(s).strip()))
            ),
        )
    def get_house_meta(self) -> Dict[str, Dict]:
        return self._get("house_meta", {})

    def set_house_meta(self, meta: Dict[str, Dict]):
        self._set("house_meta", meta)
