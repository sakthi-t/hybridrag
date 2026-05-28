"""Add missing document/thread columns

Revision ID: 0b7d2f9e9a12
Revises: 533587efbb9e
Create Date: 2026-01-29 15:36:50.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0b7d2f9e9a12'
down_revision = '533587efbb9e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_by_user_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            'fk_documents_deleted_by_user_id_users',
            'users',
            ['deleted_by_user_id'],
            ['id']
        )

    with op.batch_alter_table('threads', schema=None) as batch_op:
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')))
        batch_op.add_column(sa.Column('deleted_by_user_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            'fk_threads_deleted_by_user_id_users',
            'users',
            ['deleted_by_user_id'],
            ['id']
        )


def downgrade():
    with op.batch_alter_table('threads', schema=None) as batch_op:
        batch_op.drop_constraint('fk_threads_deleted_by_user_id_users', type_='foreignkey')
        batch_op.drop_column('deleted_by_user_id')
        batch_op.drop_column('updated_at')

    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_constraint('fk_documents_deleted_by_user_id_users', type_='foreignkey')
        batch_op.drop_column('deleted_by_user_id')
