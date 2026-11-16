# Integração Módulo 5 — Curadoria Inteligente no Dashboard M6

## Contratos confirmados no repositório do M5

- API: `https://agente-tendencias-tecnologicas-fyd3bzerc9a2cqcu.chilecentral-01.azurewebsites.net`
- `GET /feed`: feed de artigos; aceita `categoria` e `repositorio`.
- `GET /em-alta?limite=6`: tendências classificadas por recência/relevância, sem `project_id`.
- `POST /consultas`: exige Bearer do Módulo 1 e **salva conversa do usuário**, portanto não é chamado automaticamente pelo Dashboard.
- `GET /projetos/{project_id}/recomendacoes`: recomendações vinculadas ao projeto e protegidas por Bearer M1; podem ser integradas em etapa posterior, com teste E2E e autorização por projeto.

O código do M5 em `app/main.py` registra essas rotas. `/em-alta` devolve `artigos`, `total`, `categorias`, `atualizado_em` e informações da classificação; não é uma métrica de tráfego/views nem uma recomendação personalizada por projeto.

## O que foi implementado no M6

- `GET /api/bff/curadoria/em-alta`: exige JWT do BFF, consulta o M5 exclusivamente pelo backend e oferece só título, URL HTTPS, fonte, categoria e data.
- `CuradoriaPanel` no Dashboard: lista de artigos e links externos; exibe estado indisponível sem bloquear M1/M2/M7 ou o restante da tela.
- O feed é explicitamente rotulado como **global**, não associado ao projeto selecionado.
- Não cria notificações automáticas por artigo e não dispara consultas persistentes.
- Testes simulados no backend e frontend, sem credenciais ou chamadas externas.

## Configuração de ambiente do BFF (Azure)

```dotenv
CURADORIA_ENABLED=true
CURADORIA_URL=https://agente-tendencias-tecnologicas-fyd3bzerc9a2cqcu.chilecentral-01.azurewebsites.net
CURADORIA_TIMEOUT_SECONDS=5
```

A flag começa em `false`, de modo que a implantação não afete o portal antes do teste real.
O acesso ao feed de tendências não exige senha própria do M5.

## Antes de mesclar

1. Verificar CI do Pull Request e revisar o painel em dispositivos diferentes.
2. Configurar a flag no ambiente de teste e validar retorno real de `/em-alta`.
3. Testar casos de M5 offline e sem artigos.
4. Se o grupo quiser recomendações por projeto, integrar separadamente com JWT M1 e teste de permissão.

Não há neste PR alteração na integração Módulo 4 nem no seu PR em rascunho.
