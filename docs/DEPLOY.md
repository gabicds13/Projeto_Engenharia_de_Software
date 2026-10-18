# Guia de deploy — como publicar sua própria cópia no Render

Este guia é para um colega de equipe pegar o código do `ms-dashboard` (portal + BFF do
Módulo 6) e publicar **a sua própria cópia** na nuvem, no Render, via Docker.

> Tempo estimado: ~20 minutos (a maior parte é esperar o build).
> Pré-requisitos: uma conta no GitHub e uma conta no Render (pode entrar com o GitHub).
> **Você NÃO precisa instalar Docker na sua máquina** — o Render constrói as imagens na nuvem.

---

## Visão geral

O projeto sobe **dois serviços** independentes, cada um com sua URL pública:

| Serviço | O que é | Exemplo de URL |
|---------|---------|----------------|
| `*-bff` | API (FastAPI) que agrega os dados | `https://SEU-bff.onrender.com` |
| `*-web` | Portal web (React/nginx) que o usuário abre | `https://SEU-web.onrender.com` |

O portal conversa com o BFF. Por isso, **cada um precisa conhecer a URL do outro** — é o
ponto que mais dá erro, então preste atenção na etapa 4.

> ⚠️ **Nomes de serviço no Render são únicos no mundo todo.** Você **não** pode usar
> `ms-dashboard-bff` e `ms-dashboard-web` (já são da Heloísa). Escolha nomes próprios, por
> exemplo `ms-dashboard-bff-gabi` e `ms-dashboard-web-gabi`.

---

## Etapa 1 — Copiar o código para o seu GitHub

Escolha **uma** das opções.

### Opção A — Fork (mais simples, mantém link com o original)
1. Abra o repositório da Heloísa no GitHub.
2. Clique em **Fork** (canto superior direito) e crie o fork na sua conta.

### Opção B — Cópia independente (sem vínculo com o original)
No seu computador, com o Git instalado:
```bash
git clone https://github.com/H3lois4/Engenharia_de_Software.git ms-dashboard
cd ms-dashboard
git remote remove origin
git remote add origin https://github.com/SEU-USUARIO/SEU-REPO.git
git push -u origin main
```
(Crie antes um repositório vazio em `github.com/SEU-USUARIO/SEU-REPO`.)

---

## Etapa 2 — Ajustar os nomes e as URLs no `render.yaml`

Abra o arquivo **`render.yaml`** na raiz do projeto e edite. Troque os nomes dos dois serviços
e as duas URLs cruzadas pelos **seus** nomes. Onde está `ms-dashboard-bff` e
`ms-dashboard-web`, use os seus (ex.: sufixo `-gabi`).

Trechos que você precisa alterar:

```yaml
services:
  - type: web
    name: ms-dashboard-bff-gabi          # << seu nome do BFF
    ...
    envVars:
      ...
      - key: CORS_ORIGINS
        value: https://ms-dashboard-web-gabi.onrender.com   # << URL do SEU portal

  - type: web
    name: ms-dashboard-web-gabi          # << seu nome do portal
    ...
    envVars:
      - key: VITE_API_BASE_URL
        value: https://ms-dashboard-bff-gabi.onrender.com   # << URL do SEU BFF
```

Regra de ouro:
- `CORS_ORIGINS` (no BFF) = a URL do **portal** (`-web`).
- `VITE_API_BASE_URL` (no portal) = a URL do **BFF** (`-bff`).

> As URLs seguem sempre o padrão `https://<nome-do-serviço>.onrender.com`. Como você já
> definiu os nomes acima, já sabe quais serão as URLs.

Salve, faça commit e envie:
```bash
git add render.yaml
git commit -m "chore: ajusta nomes e URLs do deploy para minha conta"
git push
```

---

## Etapa 3 — Criar o Blueprint no Render

1. Acesse https://render.com e faça login (pode ser com o GitHub).
2. **New ▸ Blueprint**.
3. Conecte e selecione o **seu** repositório. O Render lê o `render.yaml` e mostra os dois
   serviços com os nomes que você escolheu.
4. Confirme a criação (**Apply** / **Create**). O Render começa a construir as imagens Docker.

O primeiro build leva alguns minutos (o do portal é o mais demorado). Acompanhe em cada
serviço na aba **Logs**. Quando ficarem com o selo **Live** (verde), estão no ar.

---

## Etapa 4 — Conferir se o portal e o BFF se conversam

Esta é a etapa que evita o erro clássico de "login não entra". Como você já colocou as URLs
certas no `render.yaml` (etapa 2), deve funcionar de primeira. Confirme assim:

1. Abra a URL do seu **BFF** + `/health`, ex.: `https://ms-dashboard-bff-gabi.onrender.com/health`
   → deve mostrar `{"status":"ok"}`.
2. Abra a URL do seu **portal**, ex.: `https://ms-dashboard-web-gabi.onrender.com`.
3. Clique em **Entrar como Product Owner** → o Dashboard deve abrir.

> Se o portal abrir mas o login não entrar, quase sempre é a `VITE_API_BASE_URL` com a URL
> errada. Corrija no `render.yaml` (ou em **ms-dashboard-web-gabi ▸ Environment**) e faça
> **Manual Deploy ▸ Clear build cache & deploy** no portal — ele precisa ser **reconstruído**,
> porque essa URL é "assada" no JavaScript durante o build, não apenas lida na inicialização.

---

## Variáveis de ambiente (já vêm prontas no `render.yaml`)

| Variável (serviço) | Valor | Para que serve |
|--------------------|-------|----------------|
| `USE_MOCKS` (BFF) | `true` | Usa dados simulados enquanto os outros módulos não estão no ar |
| `ENABLE_DEV_LOGIN` (BFF) | `true` | Permite o login de demonstração (PO/PM/Dev) sem o Módulo 1 |
| `JWT_SECRET` (BFF) | gerado pelo Render | Segredo para validar o token |
| `CORS_ORIGINS` (BFF) | URL do portal | Libera o navegador a chamar o BFF |
| `VITE_API_BASE_URL` (portal) | URL do BFF | O portal sabe onde está a API (tempo de build) |

---

## Dúvidas rápidas (FAQ)

**O primeiro acesso está lento / parece travado.**
Normal no plano gratuito: o serviço "dorme" após inatividade e leva ~30-50s para acordar no
primeiro acesso. Abra o portal alguns minutos antes de apresentar.

**Preciso instalar Docker?**
Não. Só para testar localmente. Para o deploy, o Render constrói tudo na nuvem.

**Mudei uma variável e nada aconteceu.**
`VITE_API_BASE_URL` só tem efeito em um **novo build** do portal (Manual Deploy ▸ Clear build
cache & deploy). As variáveis do BFF valem com um simples restart.

**Como ligar os serviços reais dos outros grupos depois?**
No BFF, troque `USE_MOCKS=false` e preencha `NOTIFICATIONS_URL`, `CHAT_URL`, `BACKLOG_URL`,
`GITHUB_URL` com as URLs reais. Nenhuma mudança de código é necessária.

**Testar localmente antes (opcional, requer Docker):**
```bash
docker compose up --build
# portal: http://localhost:8080   | BFF: http://localhost:8006
```
