# Evidências técnicas — AP2 / Módulo 6

**Data de verificação:** 13/11/2026.  
**Versão-base do desenvolvimento:** commit `f99b08ea2659250e9e43f608d59ffd7b24dd351d` na `main` antes da documentação AP2.

## 1. Rastreabilidade no GitHub

| PR | Assunto | Evidência |
|---|---|---|
| [#11](https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/11) | Entrega do Chat e Central de Notificações | Incorporado na `main` |
| [#12](https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/12) | IA e personalização de notificações | Incorporado na `main` |
| [#13](https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/13) | Resiliência do Dashboard com falhas do Módulo 1 | Incorporado |
| [#14](https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/14) | Etiquetas de dados simulados | Incorporado |
| [#15](https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/15) | Segurança, permissões e cache | Incorporado |
| [#16](https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/16) | Isolamento de falhas Chat/Notificações | Incorporado |
| [#17](https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/17) | Testes de falhas, circuit breaker e recuperação | Incorporado |
| [#18](https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/18) | Correções de fluxos de Chat/Notificações | Incorporado |
| [#19](https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/19) | Menu responsivo e testes de navegação | Incorporado |

## 2. Execução confirmada de testes

**GitHub Actions — [Validate modulo6 features #43517866360](https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43517866360)**:

- Backend Python 3.12: `pytest tests -v` — **122 passed**, **3 warnings**; lint Ruff aprovado.
- Frontend: build com TypeScript, testes Vitest — **24 passed** em **8 arquivos**.
- Não informar 100% de cobertura: esse percentual não foi medido nessas evidências.
- Não afirmar aprovação de todos os testes em Python 3.14 apenas a partir do CI de validação em Python 3.12.

## 3. Deploy da revisão final do frontend (GitHub Actions)

Para o commit `f99b08e`:

| Workflow | Resultado observado | Link |
|---|---|---|
| React / `software6-web` | **success** | [Execução 43517885743](https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43517885743) |
| BFF / `software6-bff` | **success** | [Execução 43517885862](https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43517885862) |
| BFF2 / `software6-bff-2` | **success** | [Execução 43517886327](https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43517886327) |

Esses resultados indicam conclusão do processo de build/deploy, **não** confirmam healthcheck acessível, login ou fluxo de ponta a ponta pelo navegador.

## 4. Arquivos técnicos relevantes

- `frontend/src/features/dashboard/DashboardPage.tsx` — Dashboard; `backend/app/dashboard/aggregator.py` — agregação.
- `frontend/src/features/notifications/NotificationsPage.tsx` e `NotificationsContext.tsx` — feed, filtros, contagem e WebSocket.
- `frontend/src/features/chat/ChatPage.tsx`, `DirectChatPanel.tsx` — Chat geral e privado.
- `backend/app/notifications/classifier.py` — classificação por regras/Gemini opcional.
- `backend/app/notifications/personalization.py` — relevância por perfil.
- `backend/app/core/resilience.py` — fallback, breaker, timeout e cache.
- `backend/app/core/security.py` — autenticação e autorização.
- `backend/app/api/integrations.py` — contrato de publicação para outros módulos.
- `backend/app/main.py` — aplicação FastAPI, rotas e OpenAPI.
- `backend/tests/`, `frontend/src/**/*.test.tsx` — testes.
- `docs/validacao-etapa4.md` — evidências específicas da etapa 4.

## 5. Lacunas evidenciais / anexos manuais

| Evidência | Situação |
|---|---|
| Captura do Dashboard real no Azure | **PENDENTE: anexar print** |
| Captura de Notificações reais ou demonstrativas identificadas | **PENDENTE: anexar print** |
| Captura de Chat geral e privado | **PENDENTE: anexar print** |
| Captura do Swagger/OpenAPI | **PENDENTE: anexar print** |
| Capturas de layout mobile e dark mode | **PENDENTE: anexar print** |
| Teste manual de login/logout e troca de projeto | **PENDENTE: registrar resultado** |
| Mensagens/eventos reais entre usuários e grupos | **NÃO COMPROVADO** |
| Teste de Gemini real com resposta classificada pelo modelo | **NÃO COMPROVADO** |
| Acurácia da IA com dataset validado | **NÃO ENCONTRADA** |
| Ensaio integrado de todos os grupos | **NÃO COMPROVADO** |
| YouTrack atualizado / responsáveis | **PENDENTE: link ou captura** |
| Revisão por outros integrantes / aprovações de PR | **PENDENTE: conferir se aplicável** |

Não criar prints sintéticos passando por produção. Dados de demonstração devem permanecer rotulados.

## 6. Correspondência com avaliação do enunciado

- **Funcionamento:** build/testes e deploy automatizados aprovados; prova visual de funcionamento ainda pendente.
- **Integração:** clientes e contratos existentes, mas ligação completa entre todos os grupos não comprovada.
- **Funcionalidade:** Dashboard, Notificações e Chat codificados e testados, com limitações documentadas.
- **Qualidade:** lint, tipagem, testes e separação de responsabilidades.
- **Robustez:** testes de isolamento e falhas; sem evidência de ensaio real de caos no Azure.
- **Conceitos:** microsserviços, REST, WebSocket, IA com fallback, controle de acesso, Scrum, versionamento, CI/CD.
- **Participação individual:** cada aluno deve demonstrá-la com commits, PRs e contribuições reais.

**Fonte primária:** *Projeto de Engenharia de Software com Microsserviços 2026-2*, páginas 4 e 5 (entregas e critérios). 
