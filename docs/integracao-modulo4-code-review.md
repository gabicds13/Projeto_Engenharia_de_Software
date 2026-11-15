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

A flag `CODE_REVIEW_ENABLED` começa em `false`.
O Módulo 2 precisa ter um repositório conectado ao projeto. O BFF não envia a senha M4 ao navegador.
O cliente exige HTTPS e não segue redirecionamentos.

## Pendências para a integração completa

- Frontend: seção de **revisões realizadas** no Dashboard, com estado indisponível e `history_limited` visível.
- Contrato M4: histórico paginado/filtrado por projeto ou PR e campo de estado de revisão, para que `Reviews pendentes` seja uma métrica confiável.
- Fluxo M4→M6 de notificações: depende de suporte do produtor no grupo M4.
- Teste ponta a ponta com conta real do M1, repositório do M2 e senha compartilhada exclusivamente por meio seguro do Azure.
- Não disparar `POST /api/analisar` ou `/comentar` automaticamente: são ações que geram análise ou publicações no GitHub, diferentes da leitura do histórico.

## Testes

`backend/tests/test_module4_code_review.py`: auth do BFF, acesso negado ao projeto, vínculo M2,
filtro seguro, Basic Auth, ausência de conteúdo privado e resposta 503.
Os testes usam apenas respostas simuladas; não confirmam acesso à API de produção.
