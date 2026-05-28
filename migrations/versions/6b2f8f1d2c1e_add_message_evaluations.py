"""Add message_evaluations table

Revision ID: 6b2f8f1d2c1e
Revises: 533587efbb9e
Create Date: 2026-01-30 13:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6b2f8f1d2c1e'
down_revision = '533587efbb9e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'message_evaluations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('message_id', sa.String(length=36), nullable=False),
        sa.Column('faithfulness_score', sa.Float(), nullable=False),
        sa.Column('citation_precision_score', sa.Float(), nullable=False),
        sa.Column('groundedness_score', sa.Float(), nullable=False),
        sa.Column('rationale_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('message_evaluations', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_message_evaluations_message_id'), ['message_id'], unique=False)


def downgrade():
    with op.batch_alter_table('message_evaluations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_message_evaluations_message_id'))

    op.drop_table('message_evaluations')
