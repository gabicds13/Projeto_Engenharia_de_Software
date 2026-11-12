"""Diagnóstico isolado do Gemini real, para responsável autorizado pela API.

Executar apenas com credencial administrada por responsável elegível ao serviço.
Não acessa DATABASE_URL, não publica notificações, não modifica o Neon.
Usa somente um evento inventado. A chave nunca é exibida nem salva.
"""
from __future__ import annotations

import asyncio
import os

from app.core.config import Settings
from app.domain.schemas import Priority, Source
from app.notifications.classifier import classify_notification


async def main() -> int:
    api_key = os.environ.get("NOTIFICATION_AI_API_KEY", "").strip()
    if not api_key:
        print("Teste real não executado: falta a credencial do responsável autorizado.")
        return 2

    # Ignora o .env para impedir o uso acidental do Neon ou da configuração local.
    settings = Settings(
        _env_file=None,
        notification_ai_enabled=True,
        notification_ai_api_key=api_key,
        notification_ai_model="gemini-2.5-flash-lite",
        notification_ai_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        notification_ai_timeout_seconds=30,
        database_url=None,
        use_notifications_db=False,
        use_chat_db=False,
    )

    # Teste inofensivo: não contém dados reais do curso ou dos usuários.
    result = await classify_notification(
        source=Source.GITHUB,
        event_type="pull_request.opened",
        title="Exemplo fictício: revisão de código pendente",
        body="Um pull request imaginário alterou testes e aguarda revisão.",
        incoming_priority=Priority.MEDIUM,
        settings=settings,
        stack=("Python", "FastAPI"),
        changed_files=("tests/exemplo_ficticio.py",),
    )

    print("Fonte da classificação:", result.classified_by)
    print("Prioridade:", result.priority.value)
    print("Relevância:", result.relevance_score)
    print("Resumo:", result.summary)
    print("Motivo:", result.reason)
    print("Agrupamento:", result.group_key)

    if result.classified_by != "llm":
        print(
            "Não foi possível confirmar resposta real do Gemini: "
            "o backend aplicou o fallback por regras. "
            "O responsável deve verificar conta, cota, modelo e conectividade."
        )
        return 1

    print("Teste real confirmado. Nenhum registro foi enviado ao Neon.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
