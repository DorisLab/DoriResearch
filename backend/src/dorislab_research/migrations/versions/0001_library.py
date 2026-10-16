"""Initial editable research library; no migration of retired publication packages."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE entries (
        id TEXT PRIMARY KEY, kind TEXT NOT NULL, revision INTEGER NOT NULL,
        title TEXT NOT NULL, summary TEXT NOT NULL, body TEXT NOT NULL,
        directory TEXT NOT NULL UNIQUE, origin TEXT NOT NULL, data_nature TEXT NOT NULL,
        references_json TEXT NOT NULL, config_json TEXT NOT NULL,
        created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
        archived_at INTEGER, deleted_at INTEGER
    )""")
    op.execute("""CREATE TABLE revisions (
        id TEXT NOT NULL, revision INTEGER NOT NULL, content TEXT NOT NULL,
        PRIMARY KEY (id, revision), FOREIGN KEY(id) REFERENCES entries(id)
    )""")
    op.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    op.execute("""CREATE TABLE jobs (
        id TEXT PRIMARY KEY, strategy TEXT NOT NULL, revision INTEGER NOT NULL,
        status TEXT NOT NULL, parameters TEXT NOT NULL, result TEXT,
        error TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
    )""")
    op.execute("CREATE INDEX entries_recent ON entries(kind, updated_at DESC)")
    op.execute("CREATE VIRTUAL TABLE search USING fts5(id UNINDEXED, title, summary, body)")


def downgrade() -> None:
    raise RuntimeError("研究数据库不自动降级；请恢复同一备份的工程与数据库")
