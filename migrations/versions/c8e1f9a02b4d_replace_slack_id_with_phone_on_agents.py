"""replace slack_id with phone on frontline agents

Revision ID: c8e1f9a02b4d
Revises: a3d857f0ee05
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8e1f9a02b4d'
down_revision: Union[str, Sequence[str], None] = 'a3d857f0ee05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('frontline_agents', sa.Column('phone', sa.String(), nullable=True))
    op.drop_column('frontline_agents', 'slack_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('frontline_agents', sa.Column('slack_id', sa.String(), nullable=True))
    op.drop_column('frontline_agents', 'phone')
