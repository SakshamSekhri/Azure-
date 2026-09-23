"""Canonical skills, question hashing, multi-attempt tracking, and AI Gateway telemetry

Revision ID: 001_hardening
Revises: 
Create Date: 2026-09-22 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_hardening'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. Skills table updates
    with op.batch_alter_table('skills', schema=None) as batch_op:
        batch_op.add_column(sa.Column('canonical_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('aliases', sa.JSON(), nullable=True))
        batch_op.create_index('ix_skills_canonical_id', ['canonical_id'], unique=False)

    # 2. Assessment questions table updates
    with op.batch_alter_table('assessment_questions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('canonical_skill_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('question_hash', sa.String(length=64), nullable=True))
        batch_op.create_index('ix_assessment_questions_canonical_skill_id', ['canonical_skill_id'], unique=False)
        batch_op.create_index('ix_assessment_questions_question_hash', ['question_hash'], unique=False)

    # 3. Assessment attempts table updates
    with op.batch_alter_table('assessment_attempts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('attempt_number', sa.Integer(), server_default='1', nullable=False))
        batch_op.add_column(sa.Column('duration_seconds', sa.Integer(), nullable=True))

    # 4. AI operations table updates
    with op.batch_alter_table('ai_operations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('model', sa.String(length=100), server_default='gpt-5-mini', nullable=True))
        batch_op.add_column(sa.Column('prompt_version', sa.String(length=50), server_default='v1.0', nullable=True))
        batch_op.add_column(sa.Column('input_tokens', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('output_tokens', sa.Integer(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('cache_hit', sa.Boolean(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('estimated_cost', sa.Float(), server_default='0.0', nullable=False))


def downgrade():
    with op.batch_alter_table('ai_operations', schema=None) as batch_op:
        batch_op.drop_column('estimated_cost')
        batch_op.drop_column('cache_hit')
        batch_op.drop_column('output_tokens')
        batch_op.drop_column('input_tokens')
        batch_op.drop_column('prompt_version')
        batch_op.drop_column('model')

    with op.batch_alter_table('assessment_attempts', schema=None) as batch_op:
        batch_op.drop_column('duration_seconds')
        batch_op.drop_column('attempt_number')

    with op.batch_alter_table('assessment_questions', schema=None) as batch_op:
        batch_op.drop_index('ix_assessment_questions_question_hash')
        batch_op.drop_index('ix_assessment_questions_canonical_skill_id')
        batch_op.drop_column('question_hash')
        batch_op.drop_column('canonical_skill_id')

    with op.batch_alter_table('skills', schema=None) as batch_op:
        batch_op.drop_index('ix_skills_canonical_id')
        batch_op.drop_column('aliases')
        batch_op.drop_column('canonical_id')
