"""Adiciona resumo e agrupamento opcionais às notificações.

Revision ID: b8f4d2a19c60
Revises: 7b30b1fe41a7

Os campos são opcionais para manter notificações anteriores compatíveis.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8f4d2a19c60"
down_revision: str | Sequence[str] | None = "7b30b1fe41a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("summary", sa.Text(), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("group_key", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("notifications", "group_key")
    op.drop_column("notifications", "summary")
