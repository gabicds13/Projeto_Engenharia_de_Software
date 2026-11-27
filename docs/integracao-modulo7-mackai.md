# Integração do Módulo 7 (MackAI) com Dashboard do Módulo 6

## Fonte dos dados
Contrato oficial publicado pelo grupo do Módulo 7: https://github.com/gabrielmarinhorosa/MackAi-Conversa/blob/main/docs/integracao-outros-modulos.md

- Aplicação do assistente: https://mackai-conversas.calmfield-d7c6c49f.brazilsouth.azurecontainerapps.io/
- Métricas: `GET /api/projects/{project_id}/metrics` (Bearer RS256 do Módulo 1).
- Resposta: `project_id`, `conversations`, `users`, `questions`, `answers_up`, `answers_down`, `answers_not_grounded`, `last_question_at`.
- A API soma a atividade dos usuários com acesso ao mesmo projeto, sem expor o conteúdo das conversas.

## Implementação
- A rota já existente `/api/bff/dashboard?project_id=...` inclui agora `mackai: {state, metrics}`.
- `state` pode ser `disabled`, `ok` ou `unavailable`.
- O Módulo 6 consulta o Módulo 7 somente **depois de validar o acesso ao projeto no próprio BFF**.
- Chamadas entre os backends enviam o Bearer de quem acessa, em cabeçalho Authorization; nunca em query string, frontend ou logs.
- As métricas do MackAI são buscadas paralelamente aos outros dados e erros do M7 não interrompem M1, M2, Chat ou Notificações.
- O portal apresenta 6 números reais quando disponíveis e um link para abrir o MackAI em outra aba, onde o usuário deverá autenticar-se no domínio do M7.
- A interface não exibe valores simulados de IA como se fossem reais.

## Configuração local ou no Azure
**Backend utilizado pelo frontend atual:** `software6-bff-2` (conforme workflow de build frontend).

```dotenv
MACKAI_METRICS_ENABLED=true
MACKAI_URL=https://mackai-conversas.calmfield-d7c6c49f.brazilsouth.azurecontainerapps.io
MACKAI_TIMEOUT_SECONDS=5
```

Nesta branch, a integração fica habilitada por padrão; uma variável `MACKAI_METRICS_ENABLED=false` explícita a desativa. Os testes automatizados desativam chamadas externas por padrão e usam transporte simulado nos testes de contrato. As configurações do Azure não são copiadas ao trocar de branch. A flag não altera `USE_MOCKS`, `USE_GITHUBSYNC_REAL` ou o modo do Chat/Notificações. Somente habilite em ambiente autorizado após confirmar a URL e o acesso ao projeto. O token não deve ser armazenado em variáveis de ambiente compartilhadas: o BFF repassa o token do login de cada usuário.

## Homologação do sistema real (pendente)
1. Fazer login no Módulo 6 com a conta real do Módulo 1.
2. Selecionar um projeto existente e autorizado no Módulo 1.
3. Acessar o MackAI com a mesma conta e registrar perguntas do projeto (apenas conteúdo autorizado).
4. No Azure do BFF utilizado pelo portal, habilitar `MACKAI_METRICS_ENABLED=true` e reiniciar.
5. No Dashboard, conferir o painel `MackAI — Módulo 7`; comparar os números com a resposta da API do M7.
6. Clicar em `Abrir assistente` para conferir se a navegação abre o serviço em nova aba, sem compartilhar token na URL.
7. Testar um projeto sem acesso e uma indisponibilidade do M7: não devem surgir números de outro projeto e outros cartões devem seguir funcionando.

**Limite da evidência:** testes automatizados com respostas fictícias do M7 confirmam o contrato e a resiliência. Não representam teste ponta a ponta com usuários, banco ou métricas reais em produção.

## Módulo 2 continua independente
A API de métricas MackAI não depende da sincronização GitHubSync do Módulo 2. O erro HTTP 403 do sync M2 deve ser tratado pelo grupo responsável, independentemente da integração M7.