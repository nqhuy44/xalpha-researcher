"""Add cost_basis to portfolio

Revision ID: 7324d0504b89
Revises: 3772edb1c125
Create Date: 2026-03-13 15:57:41.830866

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7324d0504b89'
down_revision: Union[str, Sequence[str], None] = '3772edb1c125'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns if they don't exist
    op.execute('ALTER TABLE portfolio_positions ADD COLUMN IF NOT EXISTS cost_basis BIGINT DEFAULT 0')
    op.execute('ALTER TABLE portfolio_suggestions ADD COLUMN IF NOT EXISTS suggested_cost BIGINT DEFAULT 0')
    
    # Remove redundant columns
    op.execute('ALTER TABLE portfolio_positions DROP COLUMN IF EXISTS avg_price')
    op.execute('ALTER TABLE portfolio_suggestions DROP COLUMN IF EXISTS suggested_price')
    
    # Data migration: Ensure cost_basis is populated for CASH if it was just added
    op.execute("UPDATE portfolio_positions SET cost_basis = shares WHERE symbol = 'CASH' AND cost_basis = 0")
    # For stocks, we assume avg_price was used to populate cost_basis in a previous step or by the user. 
    # Since we are dropping avg_price here, this is the last chance.


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('portfolio_suggestions', 'suggested_cost')
    op.drop_column('portfolio_positions', 'cost_basis')
