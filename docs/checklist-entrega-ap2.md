# AP2 — Checklist de entrega final do Módulo 6

**Marco informado pelo professor:** 13/11/2026 · **Entrega individual exigida pelo enunciado.**  
Este checklist distingue **material preparado**, **resultado automatizado comprovado**, **dependência externa** e **ação pessoal pendente**.

## 1. Materiais da entrega

| Item | Situação | Local |
|---|---|---|
| Código completo e organizado | Presente na `main` | [GitHub](https://github.com/gabicds13/Projeto_Engenharia_de_Software) |
| Relatório técnico do Módulo 6 | Rascunho completo; conferir autores e participação antes de submeter | [Relatório](relatorio-final-modulo6.md) |
| Roteiro de slides e apresentação | Preparado; converter em slides e adicionar prints reais | [Roteiro AP2](roteiro-apresentacao-ap2.md) |
| Evidências de PRs, testes e deploy | Documentadas | [Evidências](evidencias-entrega-ap2.md) |
| Documentação técnica / README | Revisada para o estado atual | [README](../README.md) |
| Arquitetura e API | Código, diagrama e Swagger/OpenAPI do FastAPI | [Visão geral](visao-geral-modulo6.md) / `/docs` do BFF |
| Demonstração real do portal | **A confirmar**: pipeline success não é teste visual | Acessar URL do Azure e registrar prints |
| Vídeo de demonstração (plano B) | **Não fornecido / não comprovado** | Produzir somente se necessário |
| Ensaio integrado com demais grupos | **Não comprovado** | Depende das equipes |
| Evidência de YouTrack atualizado | **Não comprovada** | Inserir link/prints do board |
| Registro da participação de cada aluno | **A preencher individualmente** | Seção 11 do relatório / histórico GitHub |
| Submissão individual | **A realizar por cada aluno** | Sistema oficial indicado pelo professor |

## 2. Sequência de conferência antes de enviar

- [ ] Abrir o site publicado e verificar login/autorização sem compartilhar credenciais.
- [ ] No Dashboard, confirmar seleção de projeto, cards/gráfico, etiquetas `Dados de demonstração` quando aplicáveis e estado indisponível.
- [ ] Em Notificações, conferir feed, contadores, prioridades, filtros, leitura e tentativa de reconexão.
- [ ] No Chat, verificar envio/histórico, menções, Chat privado e convite/aceite quando os serviços/banco estiverem habilitados.
- [ ] Conferir as mesmas telas em janela estreita (celular ou modo responsivo) e em tema claro/escuro.
- [ ] Capturar pelo menos 4 prints reais: Dashboard, Notificações, Chat geral, tela de conversa privada; adicionar imagem dos testes/pipeline e da documentação Swagger.
- [ ] Não usar conta alheia, credenciais em prints ou notificações de projetos reais que exponham dados privados.
- [ ] Preencher nomes dos integrantes, responsabilidades reais e links de commits/PRs/YouTrack.
- [ ] Adaptar o relatório às regras de formatação/submissão adotadas pelo professor; incluir prints e referências.
- [ ] Montar os slides seguindo o roteiro; ensaiar a demonstração e preparar plano B.
- [ ] Confirmar os workflows de deploy de `main` e a disponibilidade do portal sem extrapolar o que os logs provam.
- [ ] Enviar a entrega individualmente (como exige o PDF do professor).

## 3. Atenção a itens planejados que não devem ser anunciados como prontos sem evidências

- Integração efetiva com todos os módulos, e especialmente encaixe do assistente RAG M7.
- Recepção real de eventos dos grupos externos no hub de notificações.
- Métrica de reviews pendentes em fonte HTTP real (cliente de Backlog não a fornece).
- Tela de preferências individuais de notificações, medição de acurácia da IA em dataset rotulado, ensaio de caos real em produção.
- Uso efetivo do Gemini com resposta `classified_by=llm` comprovada em ambiente autorizado.
- Homologação manual das telas no navegador em diferentes tamanhos.

É válido apresentar as interfaces/contratos implementados e os testes simulados; isso não equivale a afirmar integração ponta a ponta.

## 4. Materiais mínimos a anexar ou referenciar (se o professor não exigir formato diferente)

1. Relatório final individual ou relatório da equipe com seção individual preenchida.
2. Link do repositório e commit/PRs que representam a versão entregue.
3. Evidências do CI/CD e dos testes de robustez e segurança.
4. Prints reais do portal e do Swagger (não disponíveis automaticamente nesta documentação).
5. Apresentação final / vídeo de apoio conforme orientação recebida.
6. Link ou prints do backlog/YouTrack, se solicitado pelo professor.

**Observação:** o PDF do enunciado explicita AP2 como *apresentação final da solução funcional + relatório*, com entregas individuais. Este checklist acrescenta evidências úteis, mas não as transforma em requisitos formais não escritos.

## 5. Links importantes

- Repositório: https://github.com/gabicds13/Projeto_Engenharia_de_Software
- PR revisão final: https://github.com/gabicds13/Projeto_Engenharia_de_Software/pull/19
- Pipeline de validação (122 backend, 24 frontend): https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43517866360
- Deploy frontend da versão de revisão final: https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43517885743
- Deploy BFF: https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43517885862
- Deploy BFF-2: https://github.com/gabicds13/Projeto_Engenharia_de_Software/actions/runs/43517886327
