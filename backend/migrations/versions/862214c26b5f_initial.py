"""initial

Revision ID: 862214c26b5f
Revises:
Create Date: 2026-05-26 21:46:05.662428
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "862214c26b5f"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop all FK constraints
    fks = op.get_bind().execute(sa.text("""
        SELECT conname, conrelid::regclass AS tbl
        FROM pg_constraint WHERE contype = 'f'
    """)).mappings().all()
    for row in fks:
        op.execute(sa.text(f'ALTER TABLE {row["tbl"]} DROP CONSTRAINT IF EXISTS "{row["conname"]}"'))

    # Convert all VARCHAR(36) → UUID
    _to_uuid("users", "id")
    _to_uuid("documents", "id")
    _to_uuid("documents", "owner_user_id")
    _to_uuid("documents", "deleted_by_user_id")
    _to_uuid("threads", "id")
    _to_uuid("threads", "user_id")
    _to_uuid("threads", "document_id")
    op.execute("ALTER TABLE threads ALTER COLUMN document_id DROP NOT NULL")
    _to_uuid("threads", "deleted_by_user_id")
    _to_uuid("messages", "id")
    _to_uuid("messages", "thread_id")
    _to_uuid("message_evaluations", "id")
    _to_uuid("message_evaluations", "message_id")
    _to_uuid("ingestion_jobs", "id")
    _to_uuid("ingestion_jobs", "document_id")
    _to_uuid("activity_logs", "id")
    _to_uuid("activity_logs", "actor_user_id")

    # Recreate FKs
    op.create_foreign_key(None, "documents", "users", ["owner_user_id"], ["id"])
    op.create_foreign_key(None, "documents", "users", ["deleted_by_user_id"], ["id"])
    op.create_foreign_key(None, "threads", "users", ["user_id"], ["id"])
    op.create_foreign_key(None, "threads", "documents", ["document_id"], ["id"])
    op.create_foreign_key(None, "threads", "users", ["deleted_by_user_id"], ["id"])
    op.create_foreign_key(None, "messages", "threads", ["thread_id"], ["id"])
    op.create_foreign_key(None, "message_evaluations", "messages", ["message_id"], ["id"])
    op.create_foreign_key(None, "ingestion_jobs", "documents", ["document_id"], ["id"])
    op.create_foreign_key(None, "activity_logs", "users", ["actor_user_id"], ["id"])

    # Users: add clerk_user_id (nullable first), drop password_hash/github_id
    op.add_column("users", sa.Column("clerk_user_id", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_users_clerk_user_id"), "users", ["clerk_user_id"], unique=True)
    op.execute("UPDATE users SET clerk_user_id = 'legacy-' || id::text WHERE clerk_user_id IS NULL")
    op.alter_column("users", "clerk_user_id", nullable=False)
    op.drop_index(op.f("ix_users_github_id"), table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "github_id")

    # Create upload_batches
    op.create_table(
        "upload_batches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("total_files", sa.Integer(), nullable=False),
        sa.Column("total_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=True),
        sa.Column("recommended_retrieval_type", sa.String(length=20), nullable=True),
        sa.Column("user_confirmed_type", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Documents: new columns
    op.add_column("documents", sa.Column("file_type", sa.String(length=20), nullable=True))
    op.add_column("documents", sa.Column("retrieval_type", sa.String(length=20), nullable=True))
    op.execute("UPDATE documents SET file_type = 'pdf' WHERE file_type IS NULL")
    op.execute("UPDATE documents SET retrieval_type = 'vector' WHERE retrieval_type IS NULL")
    op.alter_column("documents", "file_type", nullable=False, server_default=sa.text("'pdf'"))
    op.alter_column("documents", "retrieval_type", nullable=False, server_default=sa.text("'vector'"))
    op.add_column("documents", sa.Column("upload_batch_id", sa.UUID(), nullable=True))
    op.create_foreign_key(None, "documents", "upload_batches", ["upload_batch_id"], ["id"])

    # Ingestion jobs: new columns
    op.add_column("ingestion_jobs", sa.Column("celery_task_id", sa.String(length=255), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("chunk_count", sa.Integer(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("chunks_rejected", sa.Integer(), nullable=True))

    # Message evaluations: new columns
    op.add_column("message_evaluations", sa.Column("retrieval_type", sa.String(length=20), nullable=True))
    op.add_column("message_evaluations", sa.Column("latency_ms", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("message_evaluations", "latency_ms")
    op.drop_column("message_evaluations", "retrieval_type")
    op.drop_column("ingestion_jobs", "chunks_rejected")
    op.drop_column("ingestion_jobs", "chunk_count")
    op.drop_column("ingestion_jobs", "celery_task_id")
    op.drop_constraint(None, "documents", type_="foreignkey")
    op.drop_column("documents", "upload_batch_id")
    op.alter_column("documents", "retrieval_type", nullable=True, server_default=None)
    op.alter_column("documents", "file_type", nullable=True, server_default=None)
    op.drop_column("documents", "retrieval_type")
    op.drop_column("documents", "file_type")
    op.drop_table("upload_batches")
    op.add_column("users", sa.Column("github_id", sa.VARCHAR(length=255), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.VARCHAR(length=255), nullable=True))
    op.drop_index(op.f("ix_users_clerk_user_id"), table_name="users")
    op.create_index(op.f("ix_users_github_id"), "users", ["github_id"], unique=True)
    op.drop_column("users", "clerk_user_id")


def _to_uuid(table: str, col: str):
    op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE UUID USING {col}::uuid"))
    op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {col} SET NOT NULL"))
