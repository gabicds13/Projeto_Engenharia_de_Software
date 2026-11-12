"""adiciona membros aos canais de chat

Revision ID: 5e5782f4f11c
Revises: 50076219acd9
Create Date: 2026-11-11 13:43:07.003183
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5e5782f4f11c"
down_revision: str | Sequence[str] | None = "50076219acd9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_channel_members",
        sa.Column("channel_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["chat_channels.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("channel_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("chat_channel_members")