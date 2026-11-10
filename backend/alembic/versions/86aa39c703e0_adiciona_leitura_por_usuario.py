"""adiciona leitura por usuario

Revision ID: 86aa39c703e0
Revises: ef6ebf76a959
Create Date: 2026-11-10 10:47:26.202724

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "86aa39c703e0"
down_revision: Union[str, Sequence[str], None] = "ef6ebf76a959"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "notification_reads",
        sa.Column(
            "notification_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "read_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "notification_id",
            "user_id",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("notification_reads")