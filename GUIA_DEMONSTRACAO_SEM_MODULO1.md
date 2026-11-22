# Módulo 6 com backend real e Módulo 1 temporariamente offline

A branch `demo/capturas-sem-modulo1` deixa apenas **login e projetos do Módulo 1**
em modo de desenvolvimento. O frontend React faz solicitações REST e WebSocket
para o **FastAPI real** do projeto. O banco PostgreSQL local permanece ligado.

## Iniciar

Na raiz do projeto, com Docker Desktop aberto:

```bash
git switch demo/capturas-sem-modulo1
git pull origin demo/capturas-sem-modulo1
docker compose -f docker-compose.yml -f docker-compose.modulo1-offline.yml up --build db bff
```

Em outro terminal:

```bash
cd frontend
npm ci
npm run dev:demo
```

Abra http://localhost:5173 e clique em **Entrar com backend local**.
O BFF está em http://localhost:8006 e o Swagger em http://localhost:8006/docs.
Sem iniciar o BFF, o botão de entrada não funciona.

## Quais partes são reais?

- Frontend: React original do projeto.
- Backend: BFF FastAPI real; os endpoints e WebSockets continuam ativos.
- Chat, conversas privadas e notificações: backend e banco PostgreSQL reais, com dados locais.
- Módulo 1: somente login e projetos são substituídos por JWT e projetos de desenvolvimento.
- Backlog do Módulo 1 e métricas do Módulo 2: dados simulados pela configuração local USE_MOCKS=true.
- Módulo 4/Módulo 7: recursos podem permanecer indisponíveis sem autenticação e configuração reais.

**Não é uma homologação de integração com M1, M2, M4 ou M7.**
É uma demonstração do frontend ligado ao backend local real.
Todos os prints devem ser descritos como **ambiente local de desenvolvimento**
quando mostrarem dados substitutos.

Segurança: a flag de fallback é ignorada em produção, os JWT de desenvolvimento
só são aceitos em development, e o modo de tela local só aparece em localhost.
A branch `main` e as publicações do Azure não são alteradas.

## Prints

Registre a entrada local, Dashboard, filtros de notificações, chat geral e
conversas privadas. Um print de http://localhost:8006/docs documenta a API
que está respondendo. Não inclua tokens, cabeçalhos Authorization ou segredos.
