# Módulo 6 — Encerramento da etapa 4: revisão das telas e funcionalidades

Data: 13/11/2026. Escopo: código próprio do Módulo 6, sem dependências que exigem integração com outros grupos.

## Evidências automatizadas no GitHub

- PR #15: correções de permissões/cache de notificações, aprovado e integrado à `main`.
- PR #16: isolamento de falhas entre Chat e Notificações, aprovado e integrado.
- PR #17: testes de falha simultânea M1/M2, fallback e recuperação, aprovado e integrado.
- PR #18: revisão do fluxo de envio e disponibilidade do Chat geral, recuperação de Notificações, testes React, aprovado e integrado.
- PR #19: navegação responsiva no cabeçalho e regressões dos links Dashboard/Notificações/Chat, badges, tema e logout.
- Workflow de validação do PR #19: https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43517709400
  - Frontend: TypeScript/build e testes Vitest — **aprovados**.
  - Backend: lint e testes pytest — **aprovados**.
- Deploy dos três aplicativos Azure para o PR #18 (`main`) teve conclusão `success`:
  - portal: https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43501831312
  - BFF: https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43501831417
  - BFF-2: https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43501831670

## Áreas revisadas

| Área | Revisado no código e testes | Observações |
|---|---|---|
| Login e navegação | Sim | Rotas, cabeçalho, tema, logout, adaptação de menu a telas pequenas |
| Dashboard | Sim | Métricas, identificação de mocks, estados indisponíveis, troca de projeto e isolamento de falhas |
| Notificações | Sim | Feed, prioridade, filtros, contador, marcação de leitura, tentativa de reconexão |
| Chat geral | Sim | Histórico, envio, rascunho preservado no erro, estados offline, botão de recuperação |
| Conversas privadas | Revisão de código | Isoladas do estado offline do Chat geral; fluxo real depende de serviços/banco e usuários |
| Resiliência | Sim | Testes automáticos de circuit breaker, timeout, cache e queda de serviços |
| Segurança | Sim, testes de regressão | Acesso por projeto; não substitui auditoria completa |

## Limitações explicitadas

- O GitHub Actions comprova que código foi construído, testes passaram e a etapa de deploy terminou. Isso **não** garante que a URL do portal carregue para todo usuário ou que todos os fluxos com serviços externos funcionem ao vivo.
- Não foi possível abrir o site publicado para validar visualmente em navegador real ou capturar prints atuais de desktop e celular. Portanto **a homologação visual manual não foi executada**.
- Os testes de responsividade confirmam as classes CSS, não o layout renderizado em aparelhos reais.
- Chat privado, login por identidade real, Gemini e notificações reais dependem de configurações/dados/serviços que precisam ser validados em homologação com as equipes.
- Não foram manipulados segredos, Neon, contas de usuários ou APIs externas nesta revisão.

**Resultado:** revisão de código e testes automatizados da etapa 4 concluídos. Evidências de deploy automatizado aprovadas. A validação visual real e de integrações deve constar como pendência de homologação, não como teste já aprovado.
