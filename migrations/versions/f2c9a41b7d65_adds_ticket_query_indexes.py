"""adds ticket query indexes

Revision ID: f2c9a41b7d65
Revises: e5b1c7a93d20
Create Date: 2026-11-24 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2c9a41b7d65"
down_revision: Union[str, Sequence[str], None] = "e5b1c7a93d20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # closed_at drives every TTR/MTTR/"resolved within X" query and had no index.
    op.create_index(op.f("ix_tickets_closed_at"), "tickets", ["closed_at"])
    # created_at range + the two columns nearly every dashboard query then filters on.
    op.create_index(
        "ix_tickets_created_status_actionable",
        "tickets",
        ["created_at", "canonical_status", "actionable"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_tickets_created_status_actionable", table_name="tickets")
    op.drop_index(op.f("ix_tickets_closed_at"), table_name="tickets")
