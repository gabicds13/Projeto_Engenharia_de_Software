# AP2 — Roteiro de apresentação final do Módulo 6

**Formato sugerido:** 8 slides, com demonstração curta do portal.  
**Aviso:** roteiro interno da equipe; o professor especifica apresentação final e relatório, mas não foi encontrado limite formal de slides ou duração no enunciado fornecido. Adaptar às orientações da turma.

## Slide 1 — Identificação

- Projeto: *Assistente Inteligente de Projetos de Engenharia de Software*.
- Módulo 6 — Dashboard, Notificações e Comunicação.
- Engenharia de Software — Mackenzie, 2026/2.
- Integrantes: [PREENCHER NOMES REAIS].

**Fala:** “O nosso grupo desenvolveu o portal por onde o usuário acompanha métricas, recebe alertas priorizados e se comunica com os integrantes do projeto.”

## Slide 2 — Problema e objetivo

- Informações do projeto estão distribuídas em diferentes serviços.
- O portal precisa reunir indicadores, notificações e Chat.
- Falha de um módulo externo não deve derrubar o restante do portal.

**Fala:** “Além de disponibilizar as funções, nosso principal cuidado foi a resiliência.”

## Slide 3 — Arquitetura da solução

Mostrar diagrama: `Portal React -> BFF FastAPI -> Dashboard / Notificações / Chat`; clientes dos Módulos 1 e 2; fonte de IA opcional; banco quando habilitado.

- React + TypeScript + Vite (interface).
- Python + FastAPI (BFF e contratos).
- REST, WebSocket, SQLAlchemy/Alembic, GitHub Actions.
- Mocks em integrações ainda não validadas.

**Fala:** “O BFF isola a interface dos microsserviços e concentra o controle de acesso e as chamadas externas.”

## Slide 4 — Dashboard (demonstração)

**Mostrar captura real:** [PENDENTE — DASHBOARD].  
- Cards de commits, PRs, reviews e User Stories.
- Gráfico semanal.
- Troca de projeto.
- Dados simulados identificados.
- Estado degradado quando uma métrica falha.

**Não apresentar** valores fixos de MockGithubClient como se tivessem sido coletados em tempo real.

## Slide 5 — Central de Notificações e IA

**Mostrar captura real:** [PENDENTE — NOTIFICAÇÕES].  
- Filtros por prioridade, origem e leitura; contador; marcar como lida.
- Entrega em tempo real por WebSocket quando configurada.
- Classificador por regras: fallback operacional.
- Gemini opcional, prévia contextual e personalização por papel verificado.

**Fala:** “O modelo generativo é opcional; não apresentamos uma execução em produção como comprovada. Quando ele falha ou está desligado, as regras preservam a classificação.”

## Slide 6 — Chat geral e privado

**Mostrar captura real:** [PENDENTE — CHAT GERAL E PRIVADO].  
- Envio, histórico, leitura e menções.
- Convites e conversas privadas.
- Rascunho preservado em erro; recuperação e isolamento de falhas.
- Fronteira: Chat humano M6 não substitui o assistente RAG M7.

## Slide 7 — Testes, segurança e robustez

- **122 testes de backend aprovados** e **24 testes de frontend aprovados** (execução 43517866360).
- Ruff, TypeScript e build aprovados.
- Isolamento de cache por usuário/projeto, verificações de autenticação.
- Timeout, circuit breaker, cache stale, recuperação e degradação graciosa.
- Deploy por GitHub Actions com status de sucesso (frontend e dois backends, revisão `f99b08e`).

**Mostrar captura real:** [PENDENTE — WORKFLOW DO CI].  
**Fonte:** https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43517866360

## Slide 8 — Conclusão e limitações

**Concluído e testado:** portal, fluxos principais de Dashboard/Notificações/Chat, tratamento de falhas, testes automatizados, documentação.

**A confirmar fora do desenvolvimento isolado:** integração final com os demais grupos, homologação visual ao vivo, execução real de Gemini, avaliação de acurácia e ensaio integrado.

**Fala:** “O resultado é uma base funcional testada para o Módulo 6, com limites das integrações registrados com transparência.”

## Demonstração guiada (ordem sugerida)

1. Abrir o portal e entrar com conta **autorizada** (nunca mostrar senha ou JWT).
2. Abrir Dashboard e explicar projetos, métricas e rótulo de dados demonstrativos.
3. Abrir Notificações, selecionar prioridade e marcar uma notificação de teste como lida.
4. Abrir Chat geral e mostrar histórico; se possível, testar conversa com outra conta autorizada.
5. Abrir Conversas privadas e explicar convites.
6. Exibir o pipeline GitHub e o endpoint `/docs` do BFF.
7. Se alguma integração estiver indisponível, mostrar o aviso de fallback sem afirmar que o dado é real.

**Plano B:** prints reais capturados anteriormente, mais a execução de CI e este roteiro; vídeo apenas se a equipe o produzir.

## Cuidados para as falas

- Dizer “deploy automatizado aprovado”, não “100% de disponibilidade”.
- Dizer “IA integrada ao código, opcional e com fallback”, não “Gemini em produção validado”, sem evidência.
- Dizer “métrica simulada” onde o frontend indicar mock.
- Não inventar métricas de cobertura, precisão de IA, horas de desenvolvimento ou integração externa.

## Antes de apresentar

- [ ] Inserir nomes da equipe.
- [ ] Substituir placeholders por prints capturados da solução real.
- [ ] Confirmar URL publicada, login autorizado e conexão com os serviços necessários.
- [ ] Ajustar duração e formato conforme o professor.
- [ ] Registrar contribuições individuais e realizar a submissão individual solicitada.
