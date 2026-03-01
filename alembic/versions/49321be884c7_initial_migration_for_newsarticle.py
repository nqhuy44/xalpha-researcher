"""Initial migration for NewsArticle

Revision ID: 49321be884c7
Revises: 
Create Date: 2026-03-01 11:37:32.967605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49321be884c7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('news_articles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('author', sa.String(length=255), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('source_name', sa.String(length=100), nullable=False),
    sa.Column('domain', sa.String(length=50), nullable=False),
    sa.Column('language', sa.String(length=10), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_articles_content_hash'), 'news_articles', ['content_hash'], unique=True)
    op.create_index(op.f('ix_news_articles_domain'), 'news_articles', ['domain'], unique=False)
    op.create_index(op.f('ix_news_articles_ingested_at'), 'news_articles', ['ingested_at'], unique=False)
    op.create_index(op.f('ix_news_articles_published_at'), 'news_articles', ['published_at'], unique=False)
    op.create_index(op.f('ix_news_articles_source_name'), 'news_articles', ['source_name'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_news_articles_source_name'), table_name='news_articles')
    op.drop_index(op.f('ix_news_articles_published_at'), table_name='news_articles')
    op.drop_index(op.f('ix_news_articles_ingested_at'), table_name='news_articles')
    op.drop_index(op.f('ix_news_articles_domain'), table_name='news_articles')
    op.drop_index(op.f('ix_news_articles_content_hash'), table_name='news_articles')
    op.drop_table('news_articles')
    # ### end Alembic commands ###
