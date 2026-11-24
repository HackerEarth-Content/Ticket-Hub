"""adds metric snapshots table

Revision ID: e5b1c7a93d20
Revises: 257370246016
Create Date: 2026-11-24 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e5b1c7a93d20"
down_revision: Union[str, Sequence[str], None] = "257370246016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "metric_snapshots",
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "computed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("period"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("metric_snapshots")
