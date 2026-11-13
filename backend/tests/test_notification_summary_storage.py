"""Valida migração aditiva e persistência dos metadados estruturados sem Neon."""
from __future__ import annotations

from datetime import UTC, datetime
from importlib import util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.orm import Session

from app.models.notification import NotificationModel
from app.clients.database_notifications_client import _to_notification


def test_migration_adiciona_colunas_sem_apagar_registros():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        # Simula uma tabela existente, antes da migração.
        conn.execute(sa.text("CREATE TABLE notifications (id VARCHAR(36) PRIMARY KEY)"))
        conn.execute(sa.text("INSERT INTO notifications (id) VALUES ('old-1')"))
        ctx = MigrationContext.configure(conn)
        script = (
            Path(__file__).resolve().parents[1]
            / "alembic/versions/b8f4d2a19c60_adiciona_resumo_e_agrupamento_de_notificacoes.py"
        )
        spec = util.spec_from_file_location("test_notification_migration", script)
        assert spec is not None and spec.loader is not None
        module = util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.op = Operations(ctx)
        module.upgrade()

        names = {column["name"] for column in sa.inspect(conn).get_columns("notifications")}
        assert {"summary", "group_key"}.issubset(names)
        old = conn.execute(
            sa.text("SELECT id, summary, group_key FROM notifications WHERE id='old-1'")
        ).one()
        assert tuple(old) == ("old-1", None, None)


def test_modelo_armazena_e_retorna_resumo_e_agrupamento():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    NotificationModel.__table__.create(bind=engine)
    with Session(engine) as session:
        session.add(
            NotificationModel(
                id="new-1",
                event_id="event-1",
                scope="project",
                project_id="project-1",
                target_user_id=None,
                source="github",
                type="commit.pushed",
                priority="medium",
                relevance_score=0.77,
                reason="Mudança importante.",
                classified_by="llm",
                summary="Atualização do repositório.",
                group_key="github-commit",
                title="Novo commit",
                body="Alterações enviadas",
                link=None,
                created_at=datetime.now(UTC),
                read_at=None,
            )
        )
        session.commit()
        row = session.get(NotificationModel, "new-1")
        assert row is not None
        converted = _to_notification(row)
        assert converted.summary == "Atualização do repositório."
        assert converted.group_key == "github-commit"

        # Notificações anteriores continuam compatíveis sem esses valores.
        row.summary = None
        row.group_key = None
        session.commit()
        old = _to_notification(row)
        assert old.summary is None
        assert old.group_key is None
