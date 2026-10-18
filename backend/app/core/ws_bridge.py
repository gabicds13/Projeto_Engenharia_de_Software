"""Ponte de WebSocket: encaminha um stream do upstream (ou mock) ao cliente.

Isola o ponto de extensão para, no futuro, trocar o mock por um proxy real para
ms-notifications/ms-chat sem tocar nas rotas.
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Callable

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("bff.ws")


async def pump(
    websocket: WebSocket,
    source_factory: Callable[[], AsyncIterator[dict]],
) -> None:
    """Aceita a conexão e repassa cada mensagem do source ao cliente.

    Também drena mensagens recebidas do cliente (ex.: pong) para detectar quedas.
    Qualquer falha do upstream encerra a conexão de forma limpa — o cliente
    reconecta com backoff (lógica do front-end).
    """
    await websocket.accept()
    source = source_factory()

    async def forward() -> None:
        async for message in source:
            await websocket.send_json(message)

    async def drain() -> None:
        while True:
            await websocket.receive_text()  # ignora conteúdo; serve p/ detectar close

    forward_task = asyncio.create_task(forward())
    drain_task = asyncio.create_task(drain())
    try:
        done, pending = await asyncio.wait(
            {forward_task, drain_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.warning("ws bridge encerrada: %s", exc)
    finally:
        aclose = getattr(source, "aclose", None)
        if aclose is not None:
            try:
                await aclose()
            except Exception:  # noqa: BLE001
                pass
