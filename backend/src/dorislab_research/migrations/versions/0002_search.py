"""Monotonic changes for the desktop's rebuildable search projection."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE search")
    op.execute("INSERT INTO settings VALUES ('search_generation',lower(hex(randomblob(16))))")
    op.execute("""CREATE TABLE search_changes (
        sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE)""")
    op.execute("CREATE TABLE search_files (id TEXT PRIMARY KEY, stamp TEXT, text TEXT)")
    op.execute("INSERT INTO search_changes(id) SELECT id FROM entries")
    for event, name in (("INSERT", "new"), ("UPDATE", "new"), ("DELETE", "old")):
        op.execute(f"""CREATE TRIGGER search_{event.lower()} AFTER {event} ON entries BEGIN
            DELETE FROM search_changes WHERE id={name}.id;
            INSERT INTO search_changes(id) VALUES ({name}.id);
        END""")


def downgrade() -> None:
    raise RuntimeError("研究数据库不自动降级")
