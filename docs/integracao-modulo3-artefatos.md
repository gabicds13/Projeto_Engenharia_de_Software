# Integração Módulo 3 → Módulo 6 (leitura)

Branch: `feat/integracao-modulo3-artefatos`.

## Funcionalidade

O portal React mostra **Artefatos** no menu principal e Módulo 3 em **Outros módulos**.
Por meio do BFF FastAPI, oferece:
- lista de projetos do Módulo 3 filtrada pelos projetos autorizados no M1;
- listagem de artefatos, busca por nome e filtro de tipo (PDF/MARKDOWN/PNG/JPEG);
- versões de cada artefato;
- análises **já existentes** (resumo, classificação, justificativa, evidências,
  confiança, arquitetura e metadados), quando o Módulo 3 disponibiliza seu ID na versão;
- download autenticado pelo BFF (limite de 20 MiB).

**Não enviamos POST** ao Módulo 3; nenhuma análise de IA nova é solicitada.
Também não expomos o JWT do usuário ao M3. O frontend conversa somente com o BFF,
portanto não precisamos solicitar configuração de CORS no Módulo 3.

## Endpoints internos

Todos exigem JWT M6 válido e validação de acesso ao projeto no M1.

| Método | Endpoint BFF |
|---|---|
| GET | `/api/bff/module3/projects` |
| GET | `/api/bff/module3/projects/{project_id}` |
| GET | `/api/bff/module3/projects/{project_id}/artifacts?search=...&artifact_type=PDF` |
| GET | `/api/bff/module3/projects/{project_id}/artifacts/{artifact_id}/versions` |
| GET | `/api/bff/module3/projects/{project_id}/artifacts/{artifact_id}/analyses/{analysis_id}` |
| GET | `/api/bff/module3/projects/{project_id}/artifacts/{artifact_id}/download` |

Configuração no BFF:
```bash
MODULE3_ENABLED=true
MODULE3_URL=https://modulo3-fhgjdpa6d5bbfvff.canadacentral-01.azurewebsites.net
MODULE3_TIMEOUT_SECONDS=8
```

## Condições antes do merge

1. Confirmar se o upstream responde em `/health`, `/projects/` e `/docs`.
2. **Confirmar o formato JSON real**: listas de projetos/artefatos/versões e
   como o ID de análise fica ligado à versão. Não supor uma análise existente
   quando só há um ID de versão; não executar POST.
3. Confirmar se os IDs de projeto do M1/M6 são os mesmos que o M3 usa.
   O BFF não associa dados entre IDs diferentes sem vínculo confiável.
4. Testar visualmente a aba em conta autorizada.
5. Verificar CI (pytest, Vitest, build) e revisar código antes de mesclar.
6. Não incluir prints simulados como prova de integração real.

**Estado:** código de integração pronto para CI, mas o Azure do M3 não respondeu
durante a verificação externa; a validação com dados de produção segue pendente.
