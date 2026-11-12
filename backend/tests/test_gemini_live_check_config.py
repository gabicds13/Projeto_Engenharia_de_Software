"""Verifica que o diagnóstico lê .env sem rede ou Neon, usando chave fictícia."""
from __future__ import annotations

from gemini_live_check import isolated_settings


def test_diagnostico_le_env_local_sem_conectar_ao_neon(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text(
        "NOTIFICATION_AI_API_KEY=chave-ficticia-testes\n"
        "DATABASE_URL=postgresql://exemplo-invalido/nao_conectar\n"
        "USE_NOTIFICATIONS_DB=true\n"
        "NOTIFICATION_AI_ENABLED=false\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NOTIFICATION_AI_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("USE_NOTIFICATIONS_DB", raising=False)
    settings = isolated_settings()

    assert settings.notification_ai_api_key == "chave-ficticia-testes"
    assert settings.notification_ai_enabled is True
    assert settings.notification_ai_model == "gemini-2.5-flash-lite"
    assert settings.use_notifications_db is False
    assert settings.use_chat_db is False
    assert settings.database_url is None
