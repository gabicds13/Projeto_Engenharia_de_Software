"""Smoke test ponta a ponta: BFF M6 -> API real pública M5 -> JSON para painel.

Executar com CURADORIA_ENABLED=true e URL real, fora da suíte de testes unitários.
Não precisa de nenhuma credencial do grupo M5. Não grava dados no M5.
"""
from __future__ import annotations

import asyncio

import httpx

from app.core.config import get_settings
from app.core.security import Role, issue_dev_token
from app.main import create_app


async def main() -> None:
    settings = get_settings()
    if not settings.curadoria_enabled:
        raise RuntimeError("Ative CURADORIA_ENABLED=true para o smoke live.")

    app = create_app()
    token = issue_dev_token(Role.DEV, settings)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://bff.test") as client:
        response = await client.get(
            "/api/bff/curadoria/em-alta",
            headers={"Authorization": f"Bearer {token}"},
            timeout=settings.curadoria_timeout_seconds + 5,
        )

    print(f"BFF /api/bff/curadoria/em-alta -> HTTP {response.status_code}")
    if response.status_code != 200:
        body = response.json()
        raise RuntimeError(
            f"Conexao real indisponivel: {body.get('error', {}).get('code', 'unknown')}"
        )

    result = response.json()
    if result.get("source") != "module-5" or result.get("scope") != "global":
        raise RuntimeError("Resposta nao segue o contrato do M6.")
    articles = result.get("articles")
    if not isinstance(articles, list):
        raise RuntimeError("Lista de artigos fora do contrato.")
    if len(articles) > 6:
        raise RuntimeError("Quantidade de artigos maior que o solicitado.")

    if not articles:
        print("AVISO: integracao HTTP validada, mas feed vazio no M5; painel mostrara estado sem artigos.")
        return

    print(f"SUCESSO: {len(articles)} artigos reais recebidos pelo BFF do M6.")
    print("Exemplos de artigos disponiveis ao painel:")
    for item in articles[:3]:
        print(f"- {item['title']} ({item['source']})")


if __name__ == "__main__":
    asyncio.run(main())
