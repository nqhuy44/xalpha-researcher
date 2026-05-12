"""Add observability tables: debate_traces and llm_usage

Revision ID: 9f3a2e1d4c8b
Revises: f6518c075894
Create Date: 2026-05-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '9f3a2e1d4c8b'
down_revision: Union[str, Sequence[str], None] = '7324d0504b89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'debate_traces',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cached_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cost_usd', sa.Float(), nullable=True),
        sa.Column('total_latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_llm_calls', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('node_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='running'),
        sa.Column('verdict_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['verdict_id'], ['debate_verdicts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_debate_traces_ticker', 'debate_traces', ['ticker'])
    op.create_index('ix_debate_traces_started_at', 'debate_traces', ['started_at'])

    op.create_table(
        'llm_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('debate_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ticker', sa.String(length=20), nullable=True),
        sa.Column('node', sa.String(length=50), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('provider', sa.String(length=30), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cached_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='success'),
        sa.ForeignKeyConstraint(['debate_run_id'], ['debate_traces.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_llm_usage_ts', 'llm_usage', ['ts'])
    op.create_index('ix_llm_usage_ticker', 'llm_usage', ['ticker'])
    op.create_index('ix_llm_usage_debate_run_id', 'llm_usage', ['debate_run_id'])


def downgrade() -> None:
    op.drop_index('ix_llm_usage_debate_run_id', table_name='llm_usage')
    op.drop_index('ix_llm_usage_ticker', table_name='llm_usage')
    op.drop_index('ix_llm_usage_ts', table_name='llm_usage')
    op.drop_table('llm_usage')
    op.drop_index('ix_debate_traces_started_at', table_name='debate_traces')
    op.drop_index('ix_debate_traces_ticker', table_name='debate_traces')
    op.drop_table('debate_traces')
