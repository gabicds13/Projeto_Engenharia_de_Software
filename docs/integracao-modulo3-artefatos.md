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
# Opcional: apenas após confirmar que ambos são o mesmo projeto lógico.
# Formato: ID_PROJETO_M1=ID_PROJETO_M3
MODULE3_PROJECT_MAP=f092329c-0747-4b88-92f0-c3036786ce91=3
```

## Projetos com identificadores diferentes

O Módulo 1 usa UUIDs, enquanto o Módulo 3 pode usar IDs numéricos.
A configuração `MODULE3_PROJECT_MAP` permite que o backend faça a correspondência
de forma explícita, sem alterar os IDs externos nem desativar autorização.

O exemplo acima foi fornecido na verificação de 27/11/2026 e serve apenas
para demonstrar o vínculo pretendido entre o projeto M1 e o projeto
`Projeto Teste26112026` (M3, ID 3). **Confirme que pertencem ao mesmo projeto**
antes de ativar o vínculo em produção. Para outros projetos:
`MODULE3_PROJECT_MAP=uuid-m1=3,outro-uuid-m1=4`.

O frontend recebe o ID do M1 para navegar pelas rotas internas, e o backend
traduz para o M3 somente depois de verificar acesso ao projeto no M1.
Nenhuma associação é criada automaticamente por coincidência de nomes.
A listagem do M3 permanece somente leitura e não transfere credenciais do M1.

No PowerShell local, configure a variável **antes de iniciar** o Uvicorn:
```powershell
$env:MODULE3_PROJECT_MAP="f092329c-0747-4b88-92f0-c3036786ce91=3"
```

Se a associação estiver correta mas não houver documentos, compare os nomes,
IDs e resposta do endpoint `/api/bff/module3/projects`. As métricas do Dashboard
marcadas com `data_origin: mock` continuam simuladas e não são alteradas
por esta integração.

## Condições antes do merge

1. Confirmar se o upstream responde em `/health`, `/projects/` e `/docs`.
2. **Confirmar o formato JSON real**: listas de projetos/artefatos/versões e
   como o ID de análise fica ligado à versão. Não supor uma análise existente
   quando só há um ID de versão; não executar POST.
3. Confirmar que cada associação `MODULE3_PROJECT_MAP` representa o mesmo
   projeto lógico e está autorizada, sem expor outros projetos do M3.
4. Testar visualmente a aba em conta autorizada.
5. Verificar CI (pytest, Vitest, build) e revisar código antes de mesclar.
6. Não incluir prints simulados como prova de integração real.

**Estado:** código de integração pronto para CI, mas o Azure do M3 não respondeu
durante a verificação externa; a validação com dados de produção segue pendente.
