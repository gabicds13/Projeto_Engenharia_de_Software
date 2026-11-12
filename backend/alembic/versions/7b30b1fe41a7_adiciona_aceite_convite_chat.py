"""Adiciona aceite do convite para conversas privadas.

Revision ID: 7b30b1fe41a7
Revises: 5e5782f4f11c
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b30b1fe41a7"
down_revision: str | Sequence[str] | None = "5e5782f4f11c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_channel_members",
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Conversas existentes continuam acessíveis após a migração.
    op.execute(
        "UPDATE chat_channel_members SET accepted_at = joined_at"
    )


def downgrade() -> None:
    op.drop_column("chat_channel_members", "accepted_at")
