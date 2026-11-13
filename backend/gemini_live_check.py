"""Diagnóstico isolado do Gemini real, para responsável autorizado pela API.

Executar apenas com credencial administrada por responsável elegível ao serviço.
Não acessa DATABASE_URL, não publica notificações, não modifica o Neon.
Usa somente um evento inventado. A chave pode vir de backend/.env ou do terminal; nunca é exibida nem salva.
"""
from __future__ import annotations

import asyncio

from app.core.config import Settings
from app.domain.schemas import Priority, Source
from app.notifications.classifier import classify_notification


def isolated_settings() -> Settings:
    """Lê apenas a configuração necessária para o teste.

    Settings usa as variáveis do terminal ou backend/.env (quando executado
    dentro de backend); as opções de banco são sobrescritas explicitamente.
    Este diagnóstico NÃO instancia sessões, clientes de banco ou o BFF.
    """
    return Settings(
        notification_ai_enabled=True,
        notification_ai_model="gemini-3.5-flash-lite",
        notification_ai_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        notification_ai_timeout_seconds=30,
        database_url=None,
        use_notifications_db=False,
        use_chat_db=False,
    )


async def main() -> int:
    settings = isolated_settings()
    if not settings.notification_ai_api_key:
        print("Teste real não executado: falta a credencial do responsável autorizado.")
        return 2

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
    if result.diagnostic:
        # Exibe apenas categoria ou código HTTP, nunca cabeçalhos ou chaves.
        print("Diagnóstico seguro:", result.diagnostic)
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
