# 🔔 ms-notifications — Central de Notificações Inteligente

> **Módulo 6 — Dashboard, Central de Notificações e Comunicação**
> Plataforma de Assistente Inteligente de Projetos de Engenharia de Software, Code Review e Curadoria Técnica
> Universidade Presbiteriana Mackenzie · Projeto de Engenharia de Software com Microsserviços · 2026-2 · Prof. Dr. Rodrigo Juliani

![status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow)
![python](https://img.shields.io/badge/python-3.12-blue)
![fastapi](https://img.shields.io/badge/FastAPI-0.11x-009688)
![ci](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF)
![license](https://img.shields.io/badge/license-MIT-green)

<!-- Substitua os badges estáticos pelos dinâmicos depois do primeiro pipeline:
![CI](https://github.com/<org>/ms-notifications/actions/workflows/ci.yml/badge.svg) -->

---

## 📑 Sumário

1. [Contexto da plataforma](#-contexto-da-plataforma)
2. [O Módulo 6 e a divisão em microsserviços](#-o-módulo-6-e-a-divisão-em-microsserviços)
3. [Visão do produto](#-visão-do-produto)
4. [Personas e o que cada uma recebe](#-personas-e-o-que-cada-uma-recebe)
5. [Escopo](#-escopo)
6. [Funcionalidades](#-funcionalidades)
7. [Inteligência Artificial: priorização de notificações](#-inteligência-artificial-priorização-de-notificações)
8. [Arquitetura](#-arquitetura)
9. [Contratos de integração com os demais módulos](#-contratos-de-integração-com-os-demais-módulos)
10. [API](#-api)
11. [Modelo de dados](#-modelo-de-dados)
12. [Robustez e tolerância a falhas](#-robustez-e-tolerância-a-falhas)
13. [Segurança](#-segurança)
14. [Stack tecnológica](#-stack-tecnológica)
15. [Como executar](#-como-executar)
16. [Variáveis de ambiente](#-variáveis-de-ambiente)
17. [Estrutura do repositório](#-estrutura-do-repositório)
18. [Qualidade e testes](#-qualidade-e-testes)
19. [CI/CD](#-cicd)
20. [Backlog e User Stories](#-backlog-e-user-stories)
21. [Definition of Ready e Definition of Done](#-definition-of-ready-e-definition-of-done)
22. [Roadmap e entregas](#-roadmap-e-entregas)
23. [Processo de trabalho](#-processo-de-trabalho)
24. [Como este repositório atende aos critérios de avaliação](#-como-este-repositório-atende-aos-critérios-de-avaliação)
25. [Equipe](#-equipe)
26. [Licença](#-licença)

---

## 🌐 Contexto da plataforma

A turma está construindo, em conjunto, um **Assistente Inteligente de Engenharia de Software**: uma plataforma que centraliza os artefatos do projeto (requisitos, User Stories, arquitetura e código no GitHub), faz revisões automatizadas de código e arquitetura e atua como um agente curador que sugere artigos, bibliotecas e ferramentas relevantes para o que a equipe está desenvolvendo.

Cada grupo implementa um módulo, e todos os módulos se comunicam para formar um sistema único. Uma falha em um ou mais microsserviços **não pode** tornar a plataforma inteira indisponível.

| # | Módulo | Relação com este serviço |
|---|--------|--------------------------|
| 1 | Autenticação, Gestão de Projetos e Backlog | Fornece identidade (JWT), papéis RBAC e membros dos projetos |
| 2 | Integração e Sincronização com GitHub | Produz eventos de commits, PRs e gargalos detectados |
| 3 | Ingestão e Organização de Artefatos | Produz eventos de novos artefatos e versões |
| 4 | Code Review Automatizado e Análise Arquitetural | Produz eventos de revisões concluídas e problemas críticos |
| 5 | Agente de Curadoria e Tendências Tecnológicas | Produz recomendações de conteúdo e alertas de segurança |
| **6** | **Dashboard, Notificações e Comunicação** | **Este módulo** |
| 7 | Assistente RAG e Consulta Conversacional | Pode notificar respostas assíncronas longas (opcional) |
| 8 | Relatórios | Produz eventos de relatórios gerados |

---

## 🧩 O Módulo 6 e a divisão em microsserviços

O Módulo 6 foi dividido em três microsserviços independentes, um por integrante, cada um com seu próprio repositório, banco de dados e pipeline:

| Repositório | Responsabilidade | Responsável |
|-------------|------------------|-------------|
| `ms-dashboard` | Portal web central (frontend) e BFF que agrega as métricas dos demais módulos | `<Integrante 2>` |
| **`ms-notifications`** | **Recebe eventos de toda a plataforma, prioriza com IA e entrega alertas em tempo real** | **`<Seu nome>` (PO)** |
| `ms-chat` | Chat interativo em tempo real entre membros da equipe | `<Integrante 3>` |

Os três serviços compartilham o mesmo contrato de autenticação (JWT emitido pelo Módulo 1) e o mesmo barramento de eventos da turma. O `ms-dashboard` é o principal consumidor deste serviço: ele exibe o sino de notificações, o feed e os toasts em tempo real.

---

## 🎯 Visão do produto

**Para** Product Owners, Scrum Masters e desenvolvedores que usam a plataforma,
**que** são bombardeados por eventos de GitHub, code review, curadoria e relatórios,
**o** `ms-notifications` **é** uma central de alertas inteligente
**que** entrega a informação certa, para a pessoa certa, no momento certo,
**diferente de** um feed cronológico que trata todo evento como igualmente importante,
**nosso serviço** usa IA para priorizar, agrupar e filtrar o ruído com base no papel, no contexto e no comportamento de cada usuário.

### Problema

Cada módulo da plataforma gera eventos. Sem um ponto central, o usuário recebe dezenas de avisos desconexos e passa a ignorar todos, inclusive o alerta de vulnerabilidade crítica que realmente importava (a chamada *fadiga de alertas*).

### Objetivos do produto

1. Ser o **único ponto de entrada** de alertas para todos os módulos da plataforma.
2. Entregar alertas relevantes em **tempo real** (sem recarregar a página).
3. **Reduzir o ruído** por meio de priorização por IA, agrupamento e preferências do usuário.
4. Continuar funcionando, de forma degradada, **mesmo quando a IA ou outros módulos estiverem fora do ar**.

### Métricas de sucesso (KPIs)

| Métrica | Meta para AP2 | Como medir |
|---------|---------------|------------|
| Latência evento → tela (p95) | < 2 s | Timestamp do evento vs. entrega no WebSocket |
| Disponibilidade do serviço | ≥ 99% no período de avaliação | `/health/ready` monitorado |
| Taxa de leitura de notificações P1/P2 | ≥ 70% | `read_at` preenchido / total |
| Redução de volume por agrupamento | ≥ 30% | Eventos recebidos vs. notificações criadas |
| Feedback "irrelevante" | < 15% | Endpoint de feedback |
| Módulos integrados | ≥ 4 de 6 produtores | Tipos de evento distintos recebidos em produção |

---

## 👥 Personas e o que cada uma recebe

As personas são as definidas na especificação do projeto. A priorização por IA usa o papel RBAC de cada uma como principal sinal de relevância.

| Evento | Product Owner | PM / Scrum Master | Desenvolvedor(a) |
|--------|:-------------:|:-----------------:|:----------------:|
| Vulnerabilidade crítica encontrada em PR (Mód. 4) | Alta | Alta | **Crítica** (se autor) |
| Code review concluído no meu PR (Mód. 4) | — | Baixa | **Alta** |
| Gargalo de desenvolvimento detectado (Mód. 2) | Média | **Alta** | Baixa |
| PR aberto aguardando revisão há mais de 48 h (Mód. 2) | — | **Alta** | Média |
| Novo artefato de requisitos enviado (Mód. 3) | **Alta** | Média | Baixa |
| Relatório de qualidade/arquitetura gerado (Mód. 8) | **Alta** | Média | — |
| Atualização de segurança da stack do projeto (Mód. 5) | Média | Média | **Alta** |
| Artigo/ferramenta recomendada (Mód. 5) | Baixa | Baixa | Média (digest) |
| Adicionado a um projeto / papel alterado (Mód. 1) | Alta | Alta | Alta |
| Menção em conversa (`ms-chat`) | Alta | Alta | Alta |

> Esta matriz é o **ponto de partida das regras determinísticas**. A IA ajusta o score a partir dela (veja a seção de IA).

---

## 📦 Escopo

### Dentro do escopo

- Recepção de eventos de todos os módulos via barramento de mensagens **e** via endpoint HTTP (para grupos que não usarem o barramento).
- Criação, persistência e entrega de notificações por usuário.
- Entrega em tempo real via WebSocket.
- Priorização automática por IA com fallback por regras.
- Agrupamento, deduplicação e digest de notificações de baixa prioridade.
- Preferências por usuário (tipos silenciados, horário de silêncio, nível mínimo).
- Feedback do usuário ("útil" / "irrelevante") alimentando a priorização.
- Métricas agregadas para o `ms-dashboard`.

### Fora do escopo (nesta versão)

- Envio por e-mail, SMS ou push mobile (possível evolução).
- Interface visual: fica a cargo do `ms-dashboard`.
- Chat entre usuários: fica a cargo do `ms-chat` (este serviço apenas notifica menções).
- Geração de eventos de negócio: cada módulo é dono dos seus próprios eventos.

---

## ✨ Funcionalidades

- **Ingestão multi-fonte**: consome eventos padronizados de todos os módulos.
- **Tempo real**: notificações chegam ao navegador em menos de 2 segundos.
- **Priorização inteligente**: cada notificação recebe um score de 0 a 100 e um nível de prioridade (P1 a P4).
- **Resumo por IA**: eventos técnicos longos viram uma frase curta e acionável.
- **Anti-ruído**: agrupamento ("5 novos commits em `feature/login`"), deduplicação e digest diário para P4.
- **Preferências**: o usuário silencia tipos de evento, define horário de silêncio e nível mínimo.
- **Ações**: marcar como lida, marcar todas, dispensar, adiar (snooze) e dar feedback.
- **Contador de não lidas** para o sino do dashboard.
- **Métricas** de volume, taxa de leitura e distribuição por prioridade.

---

## 🤖 Inteligência Artificial: priorização de notificações

> Aplicação sugerida de IA na especificação: *análise de relevância e priorização automática de alertas e notificações com base no perfil e urgência do usuário.*

### Níveis de prioridade

| Nível | Score | Comportamento na interface |
|-------|-------|----------------------------|
| **P1 — Crítica** | 85–100 | Toast persistente + destaque no sino, ignora horário de silêncio |
| **P2 — Alta** | 60–84 | Toast temporário + sino |
| **P3 — Média** | 30–59 | Apenas no feed e contador |
| **P4 — Baixa** | 0–29 | Agrupada no digest diário |

### Pipeline de priorização

```
Evento → [1] Regras determinísticas → [2] Ajuste contextual por IA → [3] Ajuste por feedback → Score final
```

1. **Regras determinísticas (sempre executam)**
   Score base = peso do tipo de evento × peso do papel RBAC do destinatário (matriz da seção de personas), mais bônus quando o usuário é diretamente envolvido (autor do PR, responsável pela User Story, mencionado).

2. **Ajuste contextual por LLM (quando disponível)**
   O LLM recebe o evento, o papel do usuário e um resumo do seu contexto (stack do projeto, arquivos que alterou recentemente, histórico de interação) e devolve em JSON:
   ```json
   {
     "score_adjustment": 12,
     "summary": "Seu PR #42 tem 1 vulnerabilidade de SQL Injection em auth/repository.py",
     "reason": "Usuário é autor do PR e o problema é de segurança",
     "group_key": "pr-42-review"
   }
   ```
   O ajuste é limitado a ±20 pontos para que a IA refine, e não substitua, as regras auditáveis.

3. **Ajuste por feedback (aprendizado leve)**
   Se o usuário marca repetidamente um tipo de evento como "irrelevante", o peso desse tipo para ele diminui. Se ele sempre abre um tipo rapidamente, o peso aumenta.

### Decisões de projeto da IA

- **Regras primeiro, IA depois**: garante que o sistema funcione sem IA e torna a priorização explicável.
- **Saída estruturada (JSON validado com Pydantic)**: respostas fora do schema são descartadas e o score base é mantido.
- **Timeout curto (3 s)**: a IA não pode atrasar um alerta crítico. Se estourar, o evento segue com o score das regras e a flag `ai_enriched=false`.
- **Cache** por combinação de tipo de evento + papel + contexto, para reduzir custo e latência.
- **Provedor configurável** via `LLM_PROVIDER` e `LLM_MODEL`, sem acoplar o código a um fornecedor específico.
- **Privacidade**: somente os campos necessários são enviados ao LLM; nunca tokens, senhas ou conteúdo integral de código.
- **Transparência**: o campo `reason` fica disponível na API para a interface mostrar "por que estou vendo isso?".

---

## 🏗️ Arquitetura

### Visão de contexto

```mermaid
flowchart LR
    subgraph EXT[Outros módulos da plataforma]
        M1[Mód. 1<br/>Auth & Backlog]
        M2[Mód. 2<br/>GitHub]
        M3[Mód. 3<br/>Artefatos]
        M4[Mód. 4<br/>Code Review]
        M5[Mód. 5<br/>Curadoria]
        M8[Mód. 8<br/>Relatórios]
        CHAT[ms-chat]
    end

    BUS[(Event Bus<br/>da turma)]
    GW[API Gateway]

    M2 & M3 & M4 & M5 & M8 & CHAT -->|publicam eventos| BUS
    M2 & M3 & M4 & M5 & M8 -.->|alternativa HTTP| GW

    subgraph NH[ms-notifications]
        CONS[Consumer de eventos]
        ING[POST /api/v1/events]
        PIPE[Pipeline<br/>validação · dedup · agrupamento]
        AI[Priorizador<br/>regras + LLM]
        DB[(PostgreSQL)]
        RD[(Redis<br/>pub/sub · cache)]
        WS[WebSocket Gateway]
        API[REST API]
    end

    BUS --> CONS --> PIPE
    GW --> ING --> PIPE
    PIPE --> AI --> DB
    AI --> RD --> WS
    DB --> API

    WS -->|tempo real| DASH[ms-dashboard<br/>Portal Web]
    API --> DASH
    M1 -.->|JWKS + perfil/papéis| NH
    AI -.->|com timeout e fallback| LLM[Provedor LLM]
```

### Fluxo de uma notificação (com degradação graciosa)

```mermaid
sequenceDiagram
    participant M4 as Mód. 4 (Code Review)
    participant BUS as Event Bus
    participant NH as ms-notifications
    participant LLM as Provedor LLM
    participant DB as PostgreSQL
    participant WS as WebSocket
    participant UI as ms-dashboard

    M4->>BUS: review.completed (PR #42, 1 crítico)
    BUS->>NH: entrega evento
    NH->>NH: valida schema, verifica idempotência (event.id)
    NH->>NH: calcula score base (regras)
    NH->>LLM: ajuste contextual (timeout 3s)
    alt LLM responde
        LLM-->>NH: score_adjustment + summary
    else LLM falha ou demora
        NH->>NH: mantém score base (ai_enriched=false)
    end
    NH->>DB: persiste notificação
    NH->>WS: publica no canal do usuário
    WS-->>UI: toast P1 + contador atualizado
    NH-->>BUS: ack (sucesso) ou envia para DLQ
```

### Estilo arquitetural

- **Microsserviço independente** com banco próprio (*database per service*).
- **Comunicação assíncrona orientada a eventos** como caminho principal, com **HTTP síncrono** como alternativa de integração.
- **Arquitetura em camadas** internamente: `api` → `services` → `domain` → `repositories`.
- **Stateless** na camada HTTP/WebSocket: o fan-out entre instâncias é feito via Redis pub/sub, permitindo escalar horizontalmente.

As decisões arquiteturais relevantes são registradas como ADRs em [`docs/adr/`](docs/adr/).

---

## 🔌 Contratos de integração com os demais módulos

> ⚠️ **Os contratos abaixo são uma proposta do grupo do Módulo 6** e devem ser validados com os demais grupos. Assim que acordados, a versão oficial fica em [`docs/events/asyncapi.yaml`](docs/events/asyncapi.yaml) e qualquer mudança exige nova versão do schema.

### Envelope padrão de evento

Todo evento enviado para este serviço, pelo barramento ou por HTTP, deve seguir este envelope (inspirado no padrão CloudEvents):

```json
{
  "id": "0f8c2a5e-7b1d-4e3a-9c61-2d4f8a1b9e77",
  "type": "review.completed",
  "source": "module-4/code-review",
  "time": "2026-10-11T14:32:05Z",
  "schema_version": "1.0",
  "project_id": "proj-123",
  "actor_id": "user-456",
  "target": {
    "user_ids": ["user-789"],
    "roles": ["DEV", "SCRUM_MASTER"]
  },
  "severity_hint": "critical",
  "link": "/projects/proj-123/reviews/42",
  "data": {
    "pull_request": 42,
    "critical_issues": 1,
    "summary": "SQL Injection em auth/repository.py"
  }
}
```

| Campo | Obrigatório | Descrição |
|-------|:-----------:|-----------|
| `id` | ✅ | UUID único; usado para idempotência |
| `type` | ✅ | Tipo do evento no formato `dominio.acao` |
| `source` | ✅ | Módulo de origem |
| `time` | ✅ | ISO 8601 em UTC |
| `schema_version` | ✅ | Versão do envelope |
| `project_id` | ✅ | Projeto ao qual o evento pertence |
| `target` | ✅ | Usuários e/ou papéis destinatários (ao menos um dos dois) |
| `severity_hint` | ❌ | `info`, `low`, `medium`, `high`, `critical` — sugestão do produtor |
| `link` | ❌ | Rota da interface para onde o clique leva |
| `data` | ❌ | Payload específico do tipo de evento |

### Eventos consumidos

| Módulo de origem | `type` | Quando é emitido |
|------------------|--------|------------------|
| 1 — Auth & Backlog | `project.member.added` | Usuário adicionado a um projeto |
| 1 — Auth & Backlog | `project.role.changed` | Papel RBAC do usuário alterado |
| 1 — Auth & Backlog | `backlog.story.assigned` | User Story atribuída a um usuário |
| 2 — GitHub | `github.pull_request.opened` | Novo PR aberto |
| 2 — GitHub | `github.pull_request.stale` | PR sem revisão há mais de X horas |
| 2 — GitHub | `github.bottleneck.detected` | IA do Mód. 2 detecta gargalo no fluxo |
| 3 — Artefatos | `artifact.uploaded` | Novo documento enviado |
| 3 — Artefatos | `artifact.version.created` | Nova versão de um artefato |
| 4 — Code Review | `review.completed` | Revisão automática concluída |
| 4 — Code Review | `review.critical_issue.found` | Problema de segurança/arquitetura crítico |
| 5 — Curadoria | `curation.item.recommended` | Novo conteúdo recomendado |
| 5 — Curadoria | `curation.security_advisory` | Atualização de segurança na stack do projeto |
| 7 — RAG | `assistant.answer.ready` | Resposta assíncrona pronta (opcional) |
| 8 — Relatórios | `report.generated` | Relatório gerado e disponível |
| 6 — ms-chat | `chat.mention.created` | Usuário mencionado em conversa |

### Eventos publicados

| `type` | Consumidor principal | Uso |
|--------|---------------------|-----|
| `notification.created` | `ms-dashboard` | Métricas de volume |
| `notification.read` | `ms-dashboard`, Mód. 8 | Engajamento da equipe nos relatórios |

### Dependências síncronas

| Serviço | Endpoint | Uso | Se estiver fora do ar |
|---------|----------|-----|-----------------------|
| Mód. 1 | `GET /.well-known/jwks.json` | Validar JWT | Usa chaves em cache (TTL 24 h) |
| Mód. 1 | `GET /api/v1/projects/{id}/members` | Resolver papéis em destinatários | Usa cache de membros; eventos com `user_ids` explícitos seguem normalmente |

---

## 📡 API

Documentação interativa gerada automaticamente em `/docs` (Swagger UI) e `/redoc`. A especificação OpenAPI é exportada para [`docs/openapi.json`](docs/openapi.json) no CI.

### REST

Todas as rotas exigem `Authorization: Bearer <JWT emitido pelo Módulo 1>`, exceto as de health.

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/api/v1/notifications` | Lista notificações do usuário. Filtros: `status`, `priority`, `project_id`, `cursor`, `limit` |
| `GET` | `/api/v1/notifications/unread-count` | Contador de não lidas (por prioridade) |
| `GET` | `/api/v1/notifications/{id}` | Detalhe, incluindo `reason` da IA |
| `PATCH` | `/api/v1/notifications/{id}` | Atualiza estado: `read`, `dismissed`, `snoozed_until` |
| `POST` | `/api/v1/notifications/read-all` | Marca todas como lidas (opcionalmente por projeto) |
| `POST` | `/api/v1/notifications/{id}/feedback` | Feedback `useful` ou `irrelevant` |
| `GET` | `/api/v1/preferences` | Preferências do usuário |
| `PUT` | `/api/v1/preferences` | Atualiza preferências |
| `POST` | `/api/v1/events` | Ingestão de eventos via HTTP (token de serviço) |
| `GET` | `/api/v1/metrics/summary` | Métricas agregadas para o dashboard (PO e SM) |
| `GET` | `/health/live` | Liveness: o processo está de pé |
| `GET` | `/health/ready` | Readiness: banco, Redis e broker acessíveis |
| `GET` | `/metrics` | Métricas Prometheus |

Exemplo de resposta de `GET /api/v1/notifications`:

```json
{
  "items": [
    {
      "id": "ntf-001",
      "type": "review.critical_issue.found",
      "title": "Vulnerabilidade crítica no PR #42",
      "summary": "Seu PR #42 tem 1 vulnerabilidade de SQL Injection em auth/repository.py",
      "priority": "P1",
      "score": 94,
      "reason": "Você é o autor do PR e o problema é de segurança",
      "ai_enriched": true,
      "project_id": "proj-123",
      "link": "/projects/proj-123/reviews/42",
      "group_count": 1,
      "created_at": "2026-10-11T14:32:06Z",
      "read_at": null
    }
  ],
  "next_cursor": "eyJpZCI6Im50Zi0wMDEifQ=="
}
```

### WebSocket

```
wss://<host>/ws/notifications?token=<JWT>
```

Mensagens enviadas pelo servidor:

```json
{ "event": "notification.new",     "data": { "...notificação..." } }
{ "event": "notification.updated", "data": { "id": "ntf-001", "read_at": "..." } }
{ "event": "unread_count",         "data": { "total": 7, "P1": 1, "P2": 2, "P3": 4 } }
{ "event": "ping" }
```

O cliente deve responder `{"event":"pong"}` e reconectar com *backoff* exponencial em caso de queda. Ao reconectar, deve chamar `GET /notifications?cursor=` para recuperar o que perdeu.

---

## 🗄️ Modelo de dados

```mermaid
erDiagram
    NOTIFICATION {
        uuid id PK
        uuid event_id UK
        string user_id
        string project_id
        string type
        string title
        text summary
        int score
        string priority
        text reason
        bool ai_enriched
        string group_key
        int group_count
        string link
        timestamp created_at
        timestamp read_at
        timestamp dismissed_at
        timestamp snoozed_until
    }
    PREFERENCE {
        string user_id PK
        string min_priority
        jsonb muted_types
        time quiet_start
        time quiet_end
        bool digest_enabled
    }
    FEEDBACK {
        uuid id PK
        uuid notification_id FK
        string user_id
        string value
        timestamp created_at
    }
    PROCESSED_EVENT {
        uuid event_id PK
        string source
        timestamp processed_at
    }
    NOTIFICATION ||--o{ FEEDBACK : recebe
```

As migrations são versionadas com Alembic em [`migrations/`](migrations/).

---

## 🛡️ Robustez e tolerância a falhas

A especificação exige que a falha de um microsserviço **não** torne a plataforma indisponível. Este serviço trata isso em duas direções: não cair quando os outros caem, e não derrubar os outros quando ele cai.

### Quando outros componentes falham

| Falha | Comportamento do ms-notifications |
|-------|-----------------------------------|
| Provedor LLM fora do ar ou lento | Circuit breaker abre após 5 falhas; notificações seguem com score das regras (`ai_enriched=false`) |
| Módulo 1 fora do ar | Valida JWT com chaves JWKS em cache; resolve papéis com cache de membros |
| Um módulo produtor fora do ar | Nenhum impacto: apenas deixa de receber eventos daquele módulo |
| Broker de eventos fora do ar | Endpoint HTTP `/api/v1/events` continua aceitando eventos; consumer reconecta com backoff |
| Redis fora do ar | Notificações continuam sendo persistidas; clientes recebem via polling da REST API até o Redis voltar |

### Quando este serviço falha

| Falha | Impacto na plataforma |
|-------|----------------------|
| ms-notifications fora do ar | O `ms-dashboard` esconde o sino e exibe "notificações indisponíveis"; nenhum outro módulo é afetado, pois os produtores apenas publicam no broker e os eventos ficam enfileirados até o serviço voltar |

### Padrões aplicados

- **Idempotência**: `event_id` único em `PROCESSED_EVENT`; reentregas não geram duplicatas.
- **Retry com backoff exponencial e jitter** (biblioteca `tenacity`) em chamadas externas.
- **Circuit breaker** no cliente LLM e no cliente do Módulo 1.
- **Dead Letter Queue (DLQ)**: eventos inválidos ou que falham 3 vezes vão para a DLQ para análise, sem travar a fila.
- **Timeouts explícitos** em todas as chamadas de rede.
- **Health checks** separados (`live` e `ready`) para o orquestrador reiniciar ou retirar a instância do balanceamento.
- **Graceful shutdown**: termina de processar mensagens em andamento antes de encerrar.
- **Rate limiting** na ingestão HTTP para impedir que um produtor com bug sobrecarregue o serviço.

---

## 🔐 Segurança

- **Autenticação** via JWT emitido pelo Módulo 1, validado localmente com JWKS.
- **Autorização**: o usuário só acessa as próprias notificações; `/metrics/summary` exige papel `PO` ou `SCRUM_MASTER` no projeto (princípio do menor privilégio).
- **Tokens de serviço** separados para a ingestão HTTP, com escopo apenas `events:write`.
- **Validação de entrada** com Pydantic em todos os endpoints e mensagens.
- **Sem segredos no repositório**: variáveis de ambiente e GitHub Secrets; `.env` no `.gitignore`.
- **Minimização de dados enviados ao LLM** (nunca código completo, tokens ou dados pessoais desnecessários).
- **Análise de dependências** com Dependabot e `pip-audit` no CI.

---

## 🧰 Stack tecnológica

| Camada | Tecnologia | Motivo |
|--------|-----------|--------|
| Linguagem | Python 3.12 | Ecossistema forte de IA e familiaridade da equipe |
| Framework web | FastAPI | Assíncrono, WebSocket nativo, OpenAPI automático |
| Validação | Pydantic v2 | Schemas de eventos e respostas do LLM |
| Banco de dados | PostgreSQL 16 | Relacional, JSONB para payloads |
| ORM e migrations | SQLAlchemy 2 + Alembic | Padrão de mercado |
| Cache e fan-out | Redis 7 | Pub/sub entre instâncias, cache de IA e rate limit |
| Mensageria | RabbitMQ 3.13 *(a confirmar com a turma)* | Filas duráveis, DLQ nativa |
| Resiliência | tenacity, pybreaker | Retry e circuit breaker |
| IA | Provedor LLM configurável | Evita acoplamento a fornecedor |
| Testes | pytest, pytest-asyncio, httpx, testcontainers | Unitários, integração e contrato |
| Qualidade | ruff, mypy, pre-commit | Lint, formatação e tipagem |
| Observabilidade | logs JSON estruturados, Prometheus | Rastreio e métricas |
| Contêineres | Docker, Docker Compose | Ambiente idêntico em dev e produção |
| CI/CD | GitHub Actions | Integrado ao GitHub da turma |

---

## 🚀 Como executar

### Pré-requisitos

- Docker e Docker Compose
- Python 3.12+ (apenas para desenvolvimento fora do contêiner)
- Git

### Subindo com Docker (recomendado)

```bash
git clone https://github.com/<org>/ms-notifications.git
cd ms-notifications
cp .env.example .env          # ajuste os valores se necessário
docker compose up -d --build  # sobe API, PostgreSQL, Redis e RabbitMQ
docker compose exec api alembic upgrade head
```

Acesse:

- API: http://localhost:8006
- Swagger: http://localhost:8006/docs
- RabbitMQ (painel): http://localhost:15672

### Desenvolvimento local

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
docker compose up -d db redis broker
alembic upgrade head
uvicorn app.main:app --reload --port 8006
```

### Enviando um evento de teste

```bash
curl -X POST http://localhost:8006/api/v1/events \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d @docs/events/examples/review.completed.json
```

### Atalhos (Makefile)

| Comando | Ação |
|---------|------|
| `make up` | Sobe todo o ambiente |
| `make test` | Roda todos os testes com cobertura |
| `make lint` | ruff + mypy |
| `make seed` | Popula o banco com notificações de exemplo |
| `make simulate` | Publica eventos simulados de todos os módulos (útil para demo quando outros grupos não estão no ar) |

---

## ⚙️ Variáveis de ambiente

| Variável | Exemplo | Descrição |
|----------|---------|-----------|
| `APP_ENV` | `development` | `development`, `staging` ou `production` |
| `PORT` | `8006` | Porta HTTP |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@db:5432/notifications` | Conexão PostgreSQL |
| `REDIS_URL` | `redis://redis:6379/0` | Conexão Redis |
| `BROKER_URL` | `amqp://guest:guest@broker:5672/` | Conexão com o barramento |
| `BROKER_EXCHANGE` | `platform.events` | Exchange compartilhada da turma |
| `AUTH_JWKS_URL` | `https://<modulo1>/.well-known/jwks.json` | Chaves públicas do Módulo 1 |
| `AUTH_MEMBERS_URL` | `https://<modulo1>/api/v1/projects` | Consulta de membros e papéis |
| `SERVICE_TOKENS` | `mod2:xxx,mod4:yyy` | Tokens aceitos na ingestão HTTP |
| `LLM_PROVIDER` | `anthropic` | Provedor de IA |
| `LLM_MODEL` | `<modelo>` | Modelo utilizado |
| `LLM_API_KEY` | — | Chave da API (nunca commitar) |
| `LLM_TIMEOUT_SECONDS` | `3` | Timeout da priorização por IA |
| `AI_ENABLED` | `true` | Liga/desliga a camada de IA |
| `CORS_ORIGINS` | `https://<dashboard>` | Origens permitidas |
| `LOG_LEVEL` | `INFO` | Nível de log |

---

## 📁 Estrutura do repositório

```
ms-notifications/
├── app/
│   ├── main.py                  # Criação da app FastAPI e ciclo de vida
│   ├── api/
│   │   ├── notifications.py     # Rotas REST de notificações
│   │   ├── preferences.py
│   │   ├── events.py            # Ingestão HTTP
│   │   ├── metrics.py
│   │   ├── websocket.py
│   │   └── health.py
│   ├── core/                    # Configuração, segurança, logging
│   ├── domain/                  # Entidades, schemas Pydantic, envelope de evento
│   ├── services/                # Regras de negócio: criação, agrupamento, entrega
│   ├── ai/
│   │   ├── prioritizer.py       # Orquestra regras + LLM + feedback
│   │   ├── rules.py             # Matriz de pesos por tipo e papel
│   │   ├── llm_client.py        # Cliente com timeout e circuit breaker
│   │   └── prompts/
│   ├── integrations/
│   │   ├── consumer.py          # Consumer do barramento
│   │   ├── auth_client.py       # Cliente do Módulo 1
│   │   └── dlq.py
│   └── repositories/
├── migrations/                  # Alembic
├── tests/
│   ├── unit/
│   ├── integration/
│   └── contract/                # Valida exemplos de eventos contra o schema
├── docs/
│   ├── adr/                     # Architecture Decision Records
│   ├── events/
│   │   ├── asyncapi.yaml
│   │   └── examples/            # Um JSON por tipo de evento
│   └── openapi.json
├── scripts/
│   └── simulate_events.py
├── .github/
│   ├── workflows/ci.yml
│   ├── workflows/cd.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── .env.example
└── README.md
```

---

## ✅ Qualidade e testes

| Tipo | Ferramenta | O que cobre | Meta |
|------|-----------|-------------|------|
| Unitário | pytest | Regras de priorização, agrupamento, parsing da resposta do LLM | ≥ 80% em `app/ai` e `app/services` |
| Integração | pytest + testcontainers | Banco, Redis, broker e WebSocket reais | Fluxos principais |
| Contrato | pytest + JSON Schema | Todos os exemplos em `docs/events/examples` | 100% dos tipos de evento |
| Resiliência | pytest | LLM fora do ar, Módulo 1 fora do ar, evento duplicado | Cenários da tabela de robustez |
| Carga (opcional) | Locust | Throughput de ingestão e conexões WebSocket | 100 eventos/s |

**Cobertura mínima global exigida no CI: 70%.**

```bash
make test           # todos os testes
pytest tests/unit   # apenas unitários
pytest --cov=app --cov-report=html
```

---

## 🔄 CI/CD

Pipeline em GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)):

```
push / pull_request
   │
   ├─ 1. Lint e formatação (ruff)
   ├─ 2. Tipagem (mypy)
   ├─ 3. Testes unitários e de contrato
   ├─ 4. Testes de integração (serviços em contêiner)
   ├─ 5. Cobertura ≥ 70%
   ├─ 6. Auditoria de dependências (pip-audit)
   └─ 7. Build da imagem Docker
            │
            └─ (somente na main) 8. Publica imagem → 9. Deploy → 10. Smoke test em /health/ready
```

Regras da branch `main`:

- Push direto bloqueado.
- PR exige pipeline verde e ao menos **1 aprovação** de outro integrante.
- Squash merge com mensagem no padrão Conventional Commits.

---

## 📋 Backlog e User Stories

O backlog vivo está no **GitHub Projects** do grupo: `<link do quadro>`. Esta seção resume os épicos e as histórias priorizadas pelo PO.

### Épicos

| ID | Épico | Valor para o negócio |
|----|-------|----------------------|
| E1 | Recepção de eventos | Torna o serviço o ponto único de alertas da plataforma |
| E2 | Entrega em tempo real | Usuário reage rápido a problemas críticos |
| E3 | Priorização por IA | Reduz fadiga de alertas; diferencial do módulo |
| E4 | Preferências e anti-ruído | Usuário controla o que recebe |
| E5 | Robustez e observabilidade | Atende ao critério de robustez da avaliação |
| E6 | Métricas para o dashboard | PO e SM acompanham engajamento da equipe |

### User Stories

| ID | Épico | História | MoSCoW | Pts | Sprint |
|----|-------|----------|:------:|:---:|:------:|
| NTF-01 | E1 | Como **módulo produtor**, quero enviar eventos via HTTP para que meus usuários sejam notificados mesmo sem usar o barramento | Must | 3 | 1 |
| NTF-02 | E1 | Como **módulo produtor**, quero publicar eventos no barramento para que a entrega seja assíncrona e desacoplada | Must | 5 | 2 |
| NTF-03 | E1 | Como **sistema**, quero ignorar eventos duplicados para que o usuário não receba o mesmo alerta duas vezes | Must | 2 | 2 |
| NTF-04 | E2 | Como **desenvolvedor**, quero ver minhas notificações em uma lista paginada para acompanhar o que aconteceu | Must | 3 | 1 |
| NTF-05 | E2 | Como **desenvolvedor**, quero receber notificações em tempo real para agir sem recarregar a página | Must | 5 | 2 |
| NTF-06 | E2 | Como **usuário**, quero marcar notificações como lidas (uma ou todas) para manter meu feed organizado | Must | 2 | 1 |
| NTF-07 | E3 | Como **usuário**, quero que cada notificação tenha uma prioridade calculada pelo meu papel para ver primeiro o que importa | Must | 3 | 2 |
| NTF-08 | E3 | Como **desenvolvedor**, quero que a IA resuma e ajuste a prioridade conforme meu contexto para não perder tempo com alertas genéricos | Must | 8 | 3 |
| NTF-09 | E3 | Como **usuário**, quero saber por que recebi uma notificação para confiar na priorização | Should | 2 | 3 |
| NTF-10 | E3 | Como **usuário**, quero marcar uma notificação como irrelevante para que o sistema aprenda minhas preferências | Should | 5 | 3 |
| NTF-11 | E4 | Como **PM/Scrum Master**, quero que eventos repetidos sejam agrupados para não receber 20 alertas de commits | Should | 5 | 3 |
| NTF-12 | E4 | Como **usuário**, quero silenciar tipos de evento e definir horário de silêncio para trabalhar com foco | Should | 3 | 3 |
| NTF-13 | E4 | Como **desenvolvedor**, quero receber recomendações de baixa prioridade em um digest diário | Could | 3 | 4 |
| NTF-14 | E5 | Como **equipe de operação**, quero que o serviço continue notificando mesmo com a IA fora do ar | Must | 3 | 2 |
| NTF-15 | E5 | Como **equipe de operação**, quero health checks e métricas para monitorar o serviço em produção | Must | 2 | 2 |
| NTF-16 | E5 | Como **equipe de operação**, quero que eventos inválidos vão para uma DLQ sem travar a fila | Should | 3 | 3 |
| NTF-17 | E6 | Como **Product Owner**, quero ver métricas de leitura e volume por prioridade para avaliar o engajamento da equipe | Should | 3 | 3 |
| NTF-18 | E4 | Como **usuário**, quero adiar uma notificação para ser lembrado depois | Could | 2 | 4 |
| NTF-19 | — | Envio por e-mail | Won't (nesta versão) | — | — |

### Critérios de aceite (exemplos)

**NTF-05 — Notificações em tempo real**

```gherkin
Funcionalidade: Entrega em tempo real

  Cenário: Usuário conectado recebe notificação
    Dado que estou autenticado e conectado ao WebSocket
    Quando um evento "review.completed" destinado a mim é recebido pelo serviço
    Então recebo a mensagem "notification.new" em menos de 2 segundos
    E o contador de não lidas é atualizado

  Cenário: Usuário reconecta após queda
    Dado que minha conexão caiu e 3 notificações foram criadas nesse intervalo
    Quando eu reconecto e consulto a lista a partir do último cursor
    Então recebo as 3 notificações perdidas, sem duplicatas
```

**NTF-08 — Priorização contextual por IA**

```gherkin
Funcionalidade: Priorização por IA

  Cenário: Autor do PR recebe problema de segurança como crítico
    Dado que sou "DEV" e autor do PR #42
    Quando chega o evento "review.critical_issue.found" do PR #42
    Então a notificação tem prioridade "P1"
    E possui um resumo de no máximo 140 caracteres
    E o campo "reason" explica a priorização

  Cenário: IA indisponível
    Dado que o provedor LLM não responde em 3 segundos
    Quando chega qualquer evento válido
    Então a notificação é criada com o score das regras
    E o campo "ai_enriched" é "false"
    E a entrega não sofre atraso adicional
```

**NTF-11 — Agrupamento**

```gherkin
Funcionalidade: Agrupamento anti-ruído

  Cenário: Vários eventos do mesmo PR
    Dado que recebo 5 eventos do tipo "github.pull_request.updated" do PR #42 em 10 minutos
    Então vejo apenas 1 notificação com "group_count" igual a 5
```

---

## 📐 Definition of Ready e Definition of Done

### Definition of Ready (a história pode entrar na sprint quando…)

- [ ] Está escrita no formato "Como… quero… para…".
- [ ] Tem critérios de aceite verificáveis.
- [ ] Está estimada pela equipe.
- [ ] Dependências de outros módulos (contratos de eventos) estão identificadas e, se necessário, acordadas.
- [ ] Cabe em uma sprint.

### Definition of Done (a história está pronta quando…)

- [ ] Código revisado e aprovado em PR por outro integrante.
- [ ] Pipeline de CI verde (lint, tipagem, testes, cobertura).
- [ ] Testes cobrindo os critérios de aceite.
- [ ] Endpoints documentados no OpenAPI; eventos novos documentados no AsyncAPI.
- [ ] Sem segredos no código.
- [ ] Implantado no ambiente de produção e validado pelo PO.
- [ ] Card movido para "Concluído" no quadro Kanban.

---

## 🗺️ Roadmap e entregas

Planejamento em sprints de duas semanas alinhado ao cronograma da disciplina:

| Sprint | Período | Meta da sprint | Entregas da disciplina |
|--------|---------|----------------|------------------------|
| 1 | 21/09 – 04/10 | Repositório, esqueleto do serviço, ingestão HTTP e listagem | **P5** (27/09) · **AP1** (02/10) |
| 2 | 05/10 – 18/10 | MVP: barramento, WebSocket, prioridade por regras, deploy | **P6** MVP (11/10) · **P7** deploy (18/10) |
| 3 | 19/10 – 01/11 | IA contextual, agrupamento, preferências, DLQ, métricas | **P8** CI/CD (25/10) · **P9** arquitetura (01/11) |
| 4 | 02/11 – 13/11 | Digest, snooze, testes de integração com a turma, polimento | **P10** código completo (08/11) · **AP2** + relatório (13/11) |

### Acompanhamento das entregas

- [x] P0 — Grupos, temas e ambiente colaborativo
- [x] P1 — Cronograma
- [x] P2 — Perfis de usuários
- [x] P3 — User Stories e backlog
- [x] P4 — Planejamento Scrum e Kanban
- [ ] P5 — GitHub e primeiro commit
- [ ] AP1 — Apresentação parcial / MVP
- [ ] P6 — MVP
- [ ] P7 — Primeiro deploy em ambiente funcional
- [ ] P8 — Pipeline CI/CD
- [ ] P9 — Arquitetura da solução
- [ ] P10 — Commit do código completo e organizado
- [ ] AP2 — Apresentação final e relatório

<!-- Ajuste as caixas conforme o andamento real do grupo -->

---

## 🔁 Processo de trabalho

### Scrum no grupo

| Cerimônia | Frequência | Duração | Objetivo |
|-----------|-----------|---------|----------|
| Sprint Planning | Início de cada sprint | 1 h | Selecionar histórias e definir meta |
| Daily (assíncrona) | Dias úteis | — | Atualização no canal do grupo: o que fiz, o que farei, impedimentos |
| Sync de integração | Semanal | 30 min | Alinhar contratos com os grupos dos outros módulos |
| Sprint Review | Fim de cada sprint | 30 min | Demonstrar o incremento ao PO |
| Retrospectiva | Fim de cada sprint | 30 min | Melhorar o processo |

### Kanban

Colunas do quadro: `Backlog` → `Pronto (DoR)` → `Em andamento` → `Em revisão (PR)` → `Validação PO` → `Concluído`.

### Fluxo de branches (GitHub Flow)

```
main  ←── PR ── feature/NTF-05-websocket
      ←── PR ── fix/NTF-03-idempotencia
      ←── PR ── docs/asyncapi-v1
```

- Branches nomeadas com o ID da história: `feature/NTF-XX-descricao-curta`.
- Commits no padrão **Conventional Commits**:
  ```
  feat(ws): entrega notificações em tempo real (NTF-05)
  fix(ingest): evita duplicatas por event_id (NTF-03)
  docs(readme): adiciona contrato de eventos
  test(ai): cobre fallback quando LLM está indisponível
  ```
- Todo PR referencia a issue (`Closes #12`) e segue o template em `.github/PULL_REQUEST_TEMPLATE.md`.

---

## 🏆 Como este repositório atende aos critérios de avaliação

| Critério | Peso | Como é atendido |
|----------|:----:|-----------------|
| Funcionamento | 0 / 1 | Deploy em produção com smoke test automático em `/health/ready` |
| Integração com os demais grupos | 0,5 / 1 | Contrato de eventos publicado, ingestão via barramento **e** HTTP, simulador para testes antes da integração real |
| Funcionalidade | 5 | Escopo técnico (hub de alertas em tempo real) e aplicação de IA (priorização por perfil e urgência) completos |
| Qualidade | 2 | Lint, tipagem, testes com cobertura mínima, code review obrigatório, arquitetura em camadas, ADRs |
| Robustez | 2 | Fallback de IA, circuit breaker, retry, idempotência, DLQ, health checks, degradação graciosa |
| Conceitos do curso | 1 | Microsserviços, mensageria, Scrum, Kanban, CI/CD, User Stories, DoR/DoD, RBAC, least privilege |
| Participação individual | — | Histórico de commits, PRs e issues atribuídos a cada integrante |

> Lembrete: Funcionamento e Integração **multiplicam** a nota. Integração com os outros grupos é prioridade desde a Sprint 1.

---

## 👤 Equipe

| Integrante | Papel no Scrum | Microsserviço | GitHub |
|------------|----------------|---------------|--------|
| `<Seu nome>` | Product Owner + Dev | `ms-notifications` | `@<usuario>` |
| `<Integrante 2>` | Scrum Master + Dev | `ms-dashboard` | `@<usuario>` |
| `<Integrante 3>` | Dev | `ms-chat` | `@<usuario>` |

### Repositórios relacionados

- Módulo 6: [`ms-dashboard`](https://github.com/<org>/ms-dashboard) · [`ms-chat`](https://github.com/<org>/ms-chat)
- Demais módulos da turma: `<links a preencher>`

---

## 📄 Licença

Distribuído sob a licença MIT. Veja [`LICENSE`](LICENSE).

Projeto acadêmico desenvolvido na disciplina de Engenharia de Software da Universidade Presbiteriana Mackenzie, 2026-2.
