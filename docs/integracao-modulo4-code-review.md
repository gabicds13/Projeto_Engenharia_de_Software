# Integração do Módulo 4 — Code Review com o Módulo 6

## API do grupo M4

- Serviço: `https://revisor-codigo-ia-gio-ach9dbg3g9ekazf3.chilecentral-01.azurewebsites.net`
- Histórico: `GET /api/historico`, protegido por HTTP Basic (`revisor` + senha).
- O histórico retorna **no máximo 20 revisões globais**; não aceita `project_id`.
- Uma revisão pode trazer `pr.url`, `criado_em`, `achados` e `arquitetura`.
- Revisões de arquivos avulsos não identificam um repositório/projeto.

## Implementação inicial no BFF M6

A rota `GET /api/bff/code-reviews?project_id=UUID` exige **JWT do Módulo 1**.
Ela valida o acesso ao projeto antes de consultar serviços externos e:

1. Consulta `GET /api/v1/repositories?project_id=...` no **Módulo 2**, usando o Bearer do usuário;
2. Busca o histórico global do **Módulo 4**, em chamada backend-to-backend com Basic Auth;
3. Entrega ao frontend somente revisões com `pr.url` de um repositório que o M2 confirma pertencer ao projeto e estar visível para o usuário;
4. Retorna metadados mínimos: ID, data, URL do PR, arquitetura, número de achados e contagem por gravidade. **Não** devolve o relatório inteiro, trechos de código nem texto da IA.

A resposta traz `history_limited: true` e `pending_reviews: null`.
Isto **não** representa o número total de revisões nem permite inferir PRs pendentes.
Se não houver repositórios visíveis, a API remota falhar ou a autenticação não estiver configurada,
o BFF responde `503` sem divulgar detalhes ou credenciais.

## Configuração somente no backend (Azure App Service / ambiente autorizado)

As variáveis abaixo pertencem ao BFF usado pelo portal (`software6-bff-2`).
**Não** adicione senha ao repositório, frontend, issue, print, chamada à API ou documento.

```dotenv
CODE_REVIEW_ENABLED=true
CODE_REVIEW_URL=https://revisor-codigo-ia-gio-ach9dbg3g9ekazf3.chilecentral-01.azurewebsites.net
CODE_REVIEW_USERNAME=revisor
CODE_REVIEW_PASSWORD=<segredo-configurado-no-Azure>
CODE_REVIEW_TIMEOUT_SECONDS=5
USE_GITHUBSYNC_REAL=true
GITHUB_URL=https://ai-platform-github-service-eduardo-frapb8fbbcd0bfdm.brazilsouth-01.azurewebsites.net
```

Nesta branch, `CODE_REVIEW_ENABLED` começa em `true`; `false` explícito ainda desativa a integração. Sem senha configurada, a consulta permanece indisponível, sem dados simulados. Para testar a branch localmente, mantenha a credencial autorizada já existente no `backend/.env` (não versionado). Para Docker Compose, forneça a variável `CODE_REVIEW_PASSWORD` no ambiente do Compose, sem registrá-la no repositório. As variáveis do Azure da main não são copiadas pelo Git.
O Módulo 2 precisa ter um repositório conectado ao projeto. O BFF não envia a senha M4 ao navegador.
O cliente exige HTTPS e não segue redirecionamentos.

## Pendências para a integração completa

- Frontend: **implementado** painel de revisões realizadas, com link para PR, achados por gravidade, limitação de 20 análises e estado indisponível independente.
- Contrato M4: histórico paginado/filtrado por projeto ou PR e campo de estado de revisão, para que `Reviews pendentes` seja uma métrica confiável.
- Fluxo M4→M6 de notificações: depende de suporte do produtor no grupo M4.
- Teste ponta a ponta com conta real do M1, repositório do M2 e senha compartilhada exclusivamente por meio seguro do Azure.
- Não disparar `POST /api/analisar` ou `/comentar` automaticamente: são ações que geram análise ou publicações no GitHub, diferentes da leitura do histórico.

## Testes

`frontend/src/features/dashboard/CodeReviewPanel.test.tsx`: apresentação dos achados, estado vazio, falha isolada e ausência de dados de outros projetos.


`backend/tests/test_module4_code_review.py`: auth do BFF, acesso negado ao projeto, vínculo M2,
filtro seguro, Basic Auth, ausência de conteúdo privado e resposta 503.
Os testes usam apenas respostas simuladas; não confirmam acesso à API de produção.


## Métricas agregadas para o dashboard (novembro de 2026)

O grupo M4 disponibilizou `GET /api/dashboard/metricas?project_id=UUID&dias=14`, sem
senha ou chave. O BFF expõe `GET /api/bff/code-reviews/metrics?project_id=UUID&dias=14`,
exige JWT, valida acesso ao projeto no M1 e sempre encaminha o UUID e período (1–90 dias).
Não encaminha credenciais ao M4 nem substitui falhas por mock. O escopo do projeto nunca é substituído por dados globais automaticamente.
Usa as configurações existentes `CODE_REVIEW_ENABLED`, `CODE_REVIEW_URL` e
`CODE_REVIEW_TIMEOUT_SECONDS`. O histórico de PRs continua usando Basic Auth e a validação
de repositórios no M2, independentemente das novas métricas.

O painel nativo do M6 mostra revisões realizadas, total de achados, críticos e altos,
distribuição por prioridade, categoria, arquitetura e evolução diária. O período inicial
é 14 dias; alterar a seleção de projeto ou período refaz a consulta. As métricas não
representam reviews pendentes.

O contrato fornecido pelo grupo informa `total_revisoes`, `total_achados`,
`por_prioridade`, `por_categoria`, `por_arquitetura` e `revisoes_por_dia`.
A implementação valida as distribuições como mapas de contagens e a evolução como uma
lista de datas e contagens. O contrato real do Azure foi consultado em 27/11/2026: a API retorna o campo project_id (UUID no escopo de projeto e null no global).


### Visão global explícita

O grupo M4 publicou contagens globais sem credenciais no mesmo endpoint, omitindo
`project_id`. O novo endpoint autenticado `GET /api/bff/code-reviews/metrics/global?dias=14`
faz essa consulta somente quando o usuário seleciona **Todos os projetos**.
O BFF exige `project_id: null` na resposta global e o UUID correspondente na resposta
de projeto; retorna apenas os campos numéricos agregados previstos no contrato.
O painel rotula a visão global separadamente. Nenhuma consulta de histórico ou outras
métricas muda de escopo. Em 27/11/2026 a API global retornou 6 revisões e 30 achados
no período de 14 dias; são valores dinâmicos, não fixtures incorporadas ao produto.


## Card de revisões realizadas

O card `reviews_completed` de `GET /api/bff/dashboard` substitui o antigo card sem fonte de reviews pendentes. Usa `total_revisoes` da API pública do M4 com UUID do projeto autorizado, sem credenciais ou mocks. Mostra o total informado pelo M4 (não promete uma janela de 14 dias, pois o serviço pode contar o histórico disponível); os gráficos possuem filtros e escopo independentes. Em falha, permanece indisponível ou sinaliza o último valor em cache como desatualizado. A indisponibilidade não altera os outros cards.
