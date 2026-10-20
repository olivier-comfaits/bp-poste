"""Accès MySQL (MariaDB) avec repli SQLite si le serveur n'est pas joignable."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

try:
    import pymysql
    from pymysql.cursors import DictCursor
    HAS_PYMYSQL = True
except ImportError:
    pymysql = None
    DictCursor = None
    HAS_PYMYSQL = False

ROOT = Path(__file__).resolve().parent
SCHEMA_SQL = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
SEED_SQL = (ROOT / "sql" / "seed.sql").read_text(encoding="utf-8")
# Sur Windows, /tmp n'existe pas. On écrit dans le dossier du projet.
_default_sqlite = ROOT / "data" / "laposte_bp.sqlite"
SQLITE_PATH = Path(os.environ.get("SQLITE_PATH", str(_default_sqlite)))

MYSQL_CFG = {
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DATABASE", "laposte_bp"),
    "charset": "utf8mb4",
    "autocommit": True,
}
if HAS_PYMYSQL:
    MYSQL_CFG["cursorclass"] = DictCursor

ENGINE = {"name": None}  # "mysql" | "sqlite"


def _mysql_connect(with_db: bool = True):
    cfg = dict(MYSQL_CFG)
    if not with_db:
        cfg.pop("database", None)
    return pymysql.connect(**cfg)


def _sqlite_connect():
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _mysql_to_sqlite(sql: str) -> str:
    sql = sql.replace("ENGINE=InnoDB", "")
    sql = sql.replace("INT AUTO_INCREMENT PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")
    sql = sql.replace("AUTO_INCREMENT", "AUTOINCREMENT")
    sql = sql.replace("TINYINT", "INTEGER")
    sql = sql.replace("DECIMAL(12,2)", "REAL")
    sql = sql.replace("DECIMAL(8,2)", "REAL")
    sql = sql.replace("DECIMAL(5,2)", "REAL")
    sql = sql.replace("LONGTEXT", "TEXT")
    sql = sql.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "TEXT DEFAULT CURRENT_TIMESTAMP")
    sql = sql.replace("ENUM('bas','median','haut')", "TEXT")
    sql = sql.replace("CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci", "")
    sql = sql.replace("UNIQUE KEY uq_hypo ", "UNIQUE ")
    sql = sql.replace("UNIQUE KEY uq_scen ", "UNIQUE ")
    # drop MySQL-only preamble
    lines = []
    for line in sql.splitlines():
        u = line.strip().upper()
        if u.startswith("CREATE DATABASE") or u.startswith("USE ") or u.startswith("SET FOREIGN"):
            continue
        if " COMMENT '" in line:
            tail_comma = line.rstrip().endswith(",")
            line = line.split(" COMMENT '", 1)[0].rstrip()
            if tail_comma and not line.endswith(","):
                line += ","
        lines.append(line)
    return "\n".join(lines)


def _split_statements(sql: str) -> list[str]:
    stmts, buf = [], []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        buf.append(line)
        if line.strip().endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";")
            if stmt:
                stmts.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        stmts.append(tail)
    return stmts


def _table_count_mysql(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
        return int(cur.fetchone()["n"])


def init_mysql() -> bool:
    if not HAS_PYMYSQL:
        return False
    try:
        root = _mysql_connect(with_db=False)
    except Exception:
        return False
    try:
        with root.cursor() as cur:
            cur.execute(
                "CREATE DATABASE IF NOT EXISTS laposte_bp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            try:
                cur.execute("CREATE USER IF NOT EXISTS 'bpuser'@'localhost' IDENTIFIED BY 'bppass'")
                cur.execute("GRANT ALL ON laposte_bp.* TO 'bpuser'@'localhost'")
            except Exception:
                pass
        root.close()
        conn = _mysql_connect(with_db=True)
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = cur.fetchall()
        if not tables:
            for stmt in _split_statements(SCHEMA_SQL):
                if stmt.upper().startswith("CREATE DATABASE") or stmt.upper().startswith("USE "):
                    continue
                if stmt.upper().startswith("SET "):
                    continue
                with conn.cursor() as cur:
                    cur.execute(stmt)
        conn.close()
        conn = _mysql_connect(with_db=True)
        if _table_count_mysql(conn, "projets") == 0:
            for stmt in _split_statements(SEED_SQL):
                if stmt.upper().startswith("USE "):
                    continue
                with conn.cursor() as cur:
                    cur.execute(stmt)
        conn.close()
        ENGINE["name"] = "mysql"
        return True
    except Exception as exc:
        print("MySQL init failed:", exc)
        return False


def _ensure_versions_table(conn):
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS versions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              projet_id INTEGER NOT NULL,
              source TEXT NOT NULL DEFAULT 'user',
              label TEXT,
              snapshot_json TEXT NOT NULL,
              created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Exception:
        pass


def init_sqlite():
    first = not SQLITE_PATH.exists()
    conn = _sqlite_connect()
    _ensure_versions_table(conn)
    def run_script(sql: str):
        for stmt in _split_statements(sql):
            conn.execute(stmt)
            conn.commit()
    if first:
        run_script(_mysql_to_sqlite(SCHEMA_SQL))
        run_script(_mysql_to_sqlite(SEED_SQL))
    else:
        try:
            n = conn.execute("SELECT COUNT(*) FROM projets").fetchone()[0]
        except Exception:
            n = 0
        # Recharge les exemples si la base est vide ou incomplète
        if n < 8:
            conn.close()
            SQLITE_PATH.unlink(missing_ok=True)
            conn = _sqlite_connect()
            run_script(_mysql_to_sqlite(SCHEMA_SQL))
            run_script(_mysql_to_sqlite(SEED_SQL))
    conn.close()
    ENGINE["name"] = "sqlite"


def init_db():
    if not init_mysql():
        init_sqlite()
    return ENGINE["name"]


class Connection:
    def __init__(self):
        if ENGINE["name"] == "mysql":
            self._conn = _mysql_connect(with_db=True)
            self.kind = "mysql"
        else:
            self._conn = _sqlite_connect()
            self.kind = "sqlite"

    def _adapt(self, sql: str) -> str:
        if self.kind != "sqlite":
            return sql
        sql = sql.replace("%s", "?")
        sql = sql.replace(
            "ORDER BY FIELD(type_scenario,'bas','median','haut')",
            "ORDER BY CASE type_scenario WHEN 'bas' THEN 1 WHEN 'median' THEN 2 ELSE 3 END",
        )
        return sql

    def query(self, sql: str, params=None):
        params = params or ()
        sql = self._adapt(sql)
        if self.kind == "mysql":
            with self._conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        cur = self._conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    def execute(self, sql: str, params=None):
        params = params or ()
        sql = self._adapt(sql)
        if self.kind == "mysql":
            with self._conn.cursor() as cur:
                cur.execute(sql, params)
                return cur.lastrowid
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return cur.lastrowid

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def q(sql: str, params=None):
    with Connection() as c:
        return c.query(sql, params)


def x(sql: str, params=None):
    with Connection() as c:
        return c.execute(sql, params)
