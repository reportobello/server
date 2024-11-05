import os
import sqlite3
from datetime import datetime
from secrets import token_urlsafe

from reportobello.domain.file import File
from reportobello.domain.report import Report
from reportobello.domain.template import Template
from reportobello.domain.user import User, UserId


def build_db(location: str = ":memory:") -> sqlite3.Connection:  # noqa: C901
    db = sqlite3.connect(location, check_same_thread=False)
    db.row_factory = sqlite3.Row

    user_version: int = db.execute("PRAGMA user_version").fetchone()[0]

    if user_version <= 0:
        db.executescript(
"""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key TEXT UNIQUE NULL,
    created_at TEXT NOT NULL DEFAULT '2024-10-28T00:00:00.000000+00:00',
    provider TEXT NOT NULL DEFAULT 'reportobello',
    provider_user_id TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    is_setting_up_account INT NOT NULL DEFAULT 0,
    email TEXT NULL
);
CREATE UNIQUE INDEX ux_users ON users(provider, provider_user_id);

CREATE TABLE templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    version INTEGER NOT NULL,
    template TEXT NOT NULL,
    FOREIGN KEY(owner_id) REFERENCES users(id)
);
CREATE UNIQUE INDEX ux_templates ON templates(owner_id, name, version);

CREATE TABLE env_vars (
    owner_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY(owner_id) REFERENCES users(id)
);
CREATE UNIQUE INDEX ux_env_vars ON env_vars(owner_id, key);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NULL,
    template_id INTEGER NOT NULL,
    requested_version INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NULL,
    error_msg TEXT NULL,
    data TEXT NOT NULL DEFAULT '',
    data_type TEXT NOT NULL DEFAULT 'json',
    expires_at TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(template_id) REFERENCES templates(id)
);

CREATE TABLE new_user_survey (
    owner_id INTEGER NOT NULL,
    submitted_at TEXT NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY(owner_id) REFERENCES users(id)
);

CREATE TABLE uploaded_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uploaded_at TEXT NOT NULL,
    uploaded_by_user_id INTEGER NOT NULL,
    template_name TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT NULL,
    FOREIGN KEY(uploaded_by_user_id) REFERENCES users(id)
    FOREIGN KEY(file_id) REFERENCES file_hashes(id)
);
CREATE UNIQUE INDEX ux_uploaded_files ON uploaded_files(uploaded_by_user_id, template_name, filename);

CREATE TABLE file_hashes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hash TEXT NOT NULL UNIQUE,
    size INT NOT NULL
);

PRAGMA user_version=1;
"""
        )

    if user_version <= 1:
        db.executescript(
"""
ALTER TABLE reports ADD COLUMN hash TEXT NOT NULL DEFAULT '';

PRAGMA user_version=2;
"""
        )

    db.commit()

    return db


db = build_db(os.getenv("REPORTOBELLO_DB", ":memory:"))


def create_random_api_key() -> str:
    return f"rpbl_{token_urlsafe(32)}"


def create_or_update_user(user: User) -> User:
    sql = """
INSERT INTO users (
    created_at,
    api_key,
    provider,
    provider_user_id,
    username,
    is_setting_up_account,
    email
)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT DO UPDATE SET
    is_setting_up_account=excluded.is_setting_up_account,
    email=excluded.email;
"""

    cursor = db.cursor()
    cursor.execute(
        sql,
        [
            user.created_at.isoformat(),
            user.api_key,
            user.provider,
            user.provider_user_id,
            user.username,
            int(user.is_setting_up_account),
            user.email,
        ],
    )
    db.commit()
    cursor.close()

    fresh_user = get_user_by_api_key(user.api_key)
    assert fresh_user

    return fresh_user


def get_user_by_api_key(api_key: str) -> User | None:
    sql = "SELECT * FROM users WHERE api_key=?"

    cursor = db.cursor()
    row = cursor.execute(sql, [api_key]).fetchone()
    cursor.close()

    if row is None:
        return None

    return user_row_to_user(row)


def get_user_by_user_id(user_id: UserId) -> User | None:
    sql = "SELECT * FROM users WHERE id=?"

    cursor = db.cursor()
    row = cursor.execute(sql, [user_id]).fetchone()
    cursor.close()

    if row is None:
        return None

    return user_row_to_user(row)


def get_user_by_provider_id(*, provider: str, provider_user_id: str) -> User | None:
    sql = "SELECT * FROM users WHERE provider=? AND provider_user_id=? LIMIT 1"

    cursor = db.cursor()
    row = cursor.execute(sql, [provider, provider_user_id]).fetchone()
    cursor.close()

    if row is None:
        return None

    return user_row_to_user(row)


def user_row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        api_key=row["api_key"],
        created_at=datetime.fromisoformat(row["created_at"]),
        provider=row["provider"],
        provider_user_id=row["provider_user_id"],
        username=row["username"],
        is_setting_up_account=bool(row["is_setting_up_account"]),
        email=row["email"],
    )


def check_template_exists_for_user(user_id: UserId, template_name: str) -> bool:
    cursor = db.cursor()
    row = cursor.execute(
        """
        SELECT EXISTS(
            SELECT id FROM templates WHERE owner_id=? AND name=?
        );
        """,
        [user_id, template_name],
    ).fetchone()
    cursor.close()

    return bool(row[0])


def get_all_template_versions_for_user(user_id: UserId, template_name: str) -> list[Template]:
    cursor = db.cursor()
    rows = cursor.execute(
        """
        SELECT version, template
        FROM templates
        WHERE owner_id=? AND name=?;
        """,
        [user_id, template_name],
    ).fetchall()
    cursor.close()

    return [
        Template(name=template_name, template=row["template"], version=row["version"])
        for row in rows
    ]


def get_template_for_user(user_id: UserId, template_name: str, version: int = -1) -> Template | None:
    # TODO: make specialized version of this so we aren't overfetching
    templates = get_all_template_versions_for_user(user_id, template_name)

    if not templates:
        return None

    if version == -1:
        return templates[-1]

    try:
        return templates[version - 1]

    except IndexError:
        return None


def get_all_templates_for_user(user_id: UserId) -> list[Template]:
    cursor = db.cursor()
    rows = cursor.execute(
        """
        SELECT name, MAX(version) AS version, template
        FROM templates
        WHERE owner_id=?
        GROUP BY name;
        """,
        [user_id],
    ).fetchall()
    cursor.close()

    return [
        Template(name=row["name"], template=row["template"], version=row["version"])
        for row in rows
    ]


def save_template_for_user(user_id: UserId, template: Template) -> None:
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO templates (owner_id, name, version, template)
        VALUES (?, ?, ?, ?);
        """,
        [user_id, template.name, template.version, template.template],
    )
    db.commit()
    cursor.close()


def create_or_update_template_for_user(user_id: UserId, *, name: str, content: str) -> Template:
    old_template = get_template_for_user(user_id, name)

    version = 1 if old_template is None else old_template.version + 1

    template = Template(name=name, template=content, version=version)

    save_template_for_user(user_id, template)

    return template


def save_recent_report_build_for_user(user_id: UserId, report: Report) -> None:
    # This is a hack and I don't like it. Basically if the version is negative it is a preview
    # report, meaning it is probably used by the editor and should be ignored. The versioning system
    # is not very standardized, so once I figure out a better solution this will have to do.
    if report.actual_version == -1:
        return

    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO reports (
            template_id,
            filename,
            requested_version,
            started_at,
            finished_at,
            expires_at,
            error_msg,
            data,
            data_type,
            hash
        ) VALUES (
            (SELECT id FROM templates WHERE owner_id=? AND name=? AND version=? LIMIT 1),
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        );
        """,
        [
            user_id,
            report.template_name,
            report.actual_version,
            report.filename,
            report.requested_version,
            report.started_at.isoformat(),
            report.finished_at.isoformat(),
            report.expires_at.isoformat(),
            report.error_message,
            report.data,
            report.data_type,
            report.hash,
        ],
    )
    db.commit()
    cursor.close()


def get_recent_report_builds_for_user(user_id: UserId, template_name: str, before: datetime | None = None, limit: int = 20) -> list[Report] | None:
    if not check_template_exists_for_user(user_id, template_name):
        return None

    if before is not None:
        query = "started_at<?"
        args = [before.isoformat()]
    else:
        query = "?"
        args = [True]

    cursor = db.cursor()
    rows = cursor.execute(
        f"""
        SELECT
            filename,
            requested_version,
            t.version,
            t.name,
            started_at,
            finished_at,
            expires_at,
            error_msg,
            data,
            data_type,
            hash
        FROM reports r
        JOIN templates t ON t.id = r.template_id
        WHERE t.owner_id=? AND t.name=? AND {query}
        ORDER BY r.finished_at DESC
        LIMIT {limit};
        """,
        [user_id, template_name, *args],
    ).fetchall()
    cursor.close()

    return [report_row_to_report(row) for row in rows]


def get_cached_report_by_hash(user_id: UserId, template_name: str, template_version: int, hash: str) -> Report | None:
    cursor = db.cursor()
    rows = cursor.execute(
        f"""
        SELECT
            filename,
            requested_version,
            t.version,
            t.name,
            started_at,
            finished_at,
            expires_at,
            error_msg,
            data,
            data_type,
            hash
        FROM reports r
        JOIN templates t ON t.id = r.template_id
        WHERE t.owner_id=? AND t.name=? AND t.version=? AND r.hash=? AND r.filename IS NOT NULL
        ORDER BY r.finished_at DESC
        LIMIT 1;
        """,
        [user_id, template_name, template_version, hash],
    ).fetchall()
    cursor.close()

    if not rows:
        return None

    row = rows[0]

    return report_row_to_report(row)


def report_row_to_report(row: sqlite3.Row) -> Report:
    return Report(
        filename=row["filename"],
        requested_version=row["requested_version"],
        actual_version=row["version"],
        template_name=row["name"],
        started_at=datetime.fromisoformat(row["started_at"]),
        finished_at=datetime.fromisoformat(row["finished_at"]),
        expires_at=datetime.fromisoformat(row["expires_at"]),
        error_message=row["error_msg"],
        data=row["data"],
        data_type=row["data_type"],
        hash=row["hash"],
    )


def get_env_vars_for_user(user_id: UserId) -> dict[str, str]:
    cursor = db.cursor()
    rows = cursor.execute("SELECT key, value FROM env_vars WHERE owner_id=?", [user_id]).fetchall()
    cursor.close()

    return dict(tuple(row) for row in rows)


def update_env_vars_for_user(user_id: UserId, env_vars: dict[str, str]) -> None:
    cursor = db.cursor()
    cursor.executemany(
        """
        INSERT INTO env_vars (owner_id, key, value)
        VALUES (?, ?, ?)
        ON CONFLICT DO UPDATE SET value=excluded.value;
        """,
        [(user_id, k, v) for k, v in env_vars.items()],
    )
    db.commit()
    cursor.close()


def delete_env_vars_for_user(user_id: UserId, keys: list[str]) -> None:
    cursor = db.cursor()
    cursor.executemany("DELETE FROM env_vars WHERE owner_id=? AND key=?", [(user_id, k) for k in keys])
    db.commit()
    cursor.close()


def delete_template_for_user(user_id: UserId, name: str) -> None:
    cursor = db.cursor()
    cursor.execute("DELETE FROM templates WHERE owner_id=? AND name=?;", [user_id, name])
    db.commit()
    cursor.close()


def save_file_metadata(*, user_id: UserId, template_name: str, file: File) -> None:
    sql = "INSERT OR IGNORE INTO file_hashes (hash, size) VALUES (?, ?);"

    cursor = db.cursor()
    cursor.execute(sql, [file.hash, file.size])
    db.commit()
    cursor.close()

    sql = "SELECT id FROM file_hashes WHERE hash=?;"

    cursor = db.cursor()
    file_id = cursor.execute(sql, [file.hash]).fetchone()[0]
    cursor.close()

    sql = """
INSERT INTO uploaded_files (
    uploaded_by_user_id,
    template_name,
    file_id,
    filename,
    content_type,
    uploaded_at
) VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT DO UPDATE SET content_type=excluded.content_type, uploaded_at=excluded.uploaded_at;
"""

    cursor = db.cursor()
    cursor.execute(sql, [user_id, template_name, file_id, file.filename, file.content_type, file.uploaded_at.isoformat()])
    db.commit()
    cursor.close()


def row_to_file(row: sqlite3.Row) -> File:
    return File(
        filename=row["filename"],
        hash=row["hash"],
        size=row["size"],
        content_type=row["content_type"],
        uploaded_at=datetime.fromisoformat(row["uploaded_at"]),
    )


def get_files_for_template(user_id: UserId, template_name: str) -> list[File]:
    sql = """
SELECT uf.filename, uf.content_type, uf.uploaded_at, fh.hash, fh.size
FROM uploaded_files uf
JOIN templates t ON t.name = uf.template_name
JOIN file_hashes fh ON fh.id = uf.file_id
WHERE (
    uf.template_name=?
    AND uf.uploaded_by_user_id=?
    AND t.id=(SELECT id FROM templates WHERE owner_id=? AND name=? LIMIT 1)
);
"""

    cursor = db.cursor()
    rows = cursor.execute(sql, [template_name, user_id, user_id, template_name]).fetchall()
    cursor.close()

    return [row_to_file(row) for row in rows]


def get_file_for_template(user_id: UserId, template_name: str, filename: str) -> File | None:
    sql = """
SELECT uf.*, fh.hash, fh.size
FROM uploaded_files uf
JOIN templates t ON t.name=uf.template_name
JOIN file_hashes fh ON fh.id=uf.file_id
WHERE (
    t.name=?
    AND t.owner_id=uf.uploaded_by_user_id
    AND t.owner_id=?
    AND uf.filename=?
)
LIMIT 1;
"""

    cursor = db.cursor()
    rows = cursor.execute(sql, [template_name, user_id, filename]).fetchall()
    cursor.close()

    return None if not rows else row_to_file(rows[0])


def delete_file_for_template(user_id: UserId, template_name: str, filename: str) -> None:
    sql = """
DELETE FROM uploaded_files
WHERE id IN (
    SELECT uf.id
    FROM uploaded_files uf
    JOIN templates t ON t.name=uf.template_name
    WHERE (
        t.name=?
        AND t.owner_id=uf.uploaded_by_user_id
        AND t.owner_id=?
        AND uf.filename=?
    )
);
"""

    cursor = db.cursor()
    cursor.execute(sql, [template_name, user_id, filename])
    db.commit()
    cursor.close()
