# Integração GitHubSync (Módulo 2) → Dashboard (Módulo 6)

## Contratos
API pública M2: https://ai-platform-github-service-eduardo-frapb8fbbcd0bfdm.brazilsouth-01.azurewebsites.net
Documentação: https://github.com/EduardoFdeM/ai-platform-github-service/blob/main/docs/integration-guide.md

O BFF consulta estas rotas com o Bearer real do usuário emitido pelo Módulo 1:
- GET /api/v1/repositories?project_id=UUID: repositórios visíveis no projeto.
- GET /api/v1/metrics/dashboard?repository_id=ID&days=7: total_commits e prs_open.
- GET /api/v1/commits?repository_id=ID&since=ISO&page=N: eventos reais para série semanal.
- GET /api/v1/pull-requests?repository_id=ID&page=N: PRs para série semanal.

## Configuração, sem alterar outros módulos
Em App Service (ambiente de testes autorizado), definir:

```dotenv
USE_MOCKS=true
USE_GITHUBSYNC_REAL=true
GITHUB_URL=https://ai-platform-github-service-eduardo-frapb8fbbcd0bfdm.brazilsouth-01.azurewebsites.net
```

Nesta branch a API publicada e USE_GITHUBSYNC_REAL=true são os padrões. Sessões reais do M1 consultam M2 mesmo com USE_MOCKS=true; para sessão de demonstração, USE_GITHUBSYNC_REAL=false permite mock. A flag independe do modo mock de Notificações, Chat e Backlog. O prazo total de cada consulta M2 é configurável em GITHUBSYNC_TIMEOUT_SECONDS (20 por padrão). Não habilitar em produção sem validar a conta, os projetos e os contratos. Não colocar tokens, PATs, senhas, URLs de banco ou chaves em arquivos versionados. Chamadas BFF→M2 não dependem de CORS.

## O que aparece
- Commits na semana: soma de total_commits de cada repositório do projeto (últimos 7 dias, janela móvel).
- PRs abertos: soma de prs_open atuais de cada repositório.
- Gráfico: cinco semanas ISO; soma de commits agrupados por authored_at e PRs agrupadas por opened_at.
- User Stories permanecem no Módulo 1; o card de revisões realizadas usa o total real por projeto do Módulo 4.

O M2 restringe repositórios visíveis segundo o usuário autenticado, podendo mostrar apenas os vinculados ao proprietário. Um projeto sem repositórios acessíveis aparece como indisponível, não como zero. Para não mostrar métricas parciais, o cliente aceita no máximo 10 repositórios e 10 páginas por repositório; exceder o limite deixa o gráfico indisponível.

O Dashboard isola caches por identidade do usuário e projeto; respostas atrasadas, fonte ausente ou autenticação rejeitada não devem virar métricas de outro usuário.

## Validação real ainda pendente
1. Entrar com uma conta real do Módulo 1, sem divulgar Bearer.
2. Vincular repositório do projeto no M2 e sincronizar (é necessário ter dados indexados).
3. Habilitar USE_GITHUBSYNC_REAL e GITHUB_URL em um BFF de testes, reiniciando somente esse ambiente.
4. Abrir o Dashboard do M6, selecionar o mesmo projeto e comparar commits/PRs com os dados do M2.
5. Confirmar ausência de etiqueta de mock nos cards reais e isolamento entre usuários/projetos.
6. Confirmar que dados inexistentes ou serviços offline aparecem como indisponíveis e não derrubam Notificações/Chat.

**Não confundir métricas com notificações.** M2 publica eventos para nossa Central por uma integração separada, descrita em https://github.com/EduardoFdeM/ai-platform-github-service/blob/main/docs/module6-notifications.md.

**Status:** integração de código e testes de contrato. Homologação ponta a ponta com dados reais ainda não verificada.