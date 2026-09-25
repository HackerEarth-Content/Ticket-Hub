"""adds ticket validity

Revision ID: 257370246016
Revises: c8e1f9a02b4d
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '257370246016'
down_revision: Union[str, Sequence[str], None] = 'c8e1f9a02b4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tickets', sa.Column('ticket_validity', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tickets', 'ticket_validity')
