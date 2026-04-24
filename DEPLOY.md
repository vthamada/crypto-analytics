# Guia de Deploy - Crypto Analytics

Este guia descreve o caminho recomendado de deploy para o estado atual do projeto:

- frontend em `Vercel`
- API em `Render` como `Web Service`
- scanner em `Render` como `Background Worker`
- banco em `Supabase`

Essa topologia e a mais alinhada ao repositorio hoje porque o fluxo padrao ja separa API e worker em `docker-compose.yml`.

Arquitetura alvo:

```text
┌──────────────┐      ┌──────────────────────┐      ┌──────────────┐
│    Vercel    │ ───► │ Render Web Service   │ ───► │   Supabase   │
│  frontend    │ HTTP │ FastAPI API-only     │  DB  │ PostgreSQL   │
│   Next.js    │  WS  │ /api + /ws           │      │              │
└──────────────┘      └──────────┬───────────┘      └──────────────┘
                                 │
                                 ▼
                       ┌──────────────────────┐
                       │ Render Worker        │
                       │ python -m app.worker │
                       └──────────┬───────────┘
                                  │
                                  ▼
                            ┌──────────┐
                            │ Telegram │
                            └──────────┘
```

## Antes de subir

Valide localmente antes do primeiro deploy:

### Backend

```bash
cd backend
python -m pytest tests -q
alembic heads
python scripts/verify_operational_readiness.py
```

### Frontend

```bash
cd frontend
npm run lint
npm run build
```

## Pre-requisitos

Crie contas em:

- [Supabase](https://supabase.com)
- [Render](https://render.com)
- [Vercel](https://vercel.com)
- [GitHub](https://github.com)
- [Telegram](https://telegram.org)

Tenha o repositorio publicado no GitHub e a branch principal pronta para deploy.

## Passo 1 - Criar o banco no Supabase

1. Entre em [supabase.com](https://supabase.com) e crie um projeto novo.
2. Escolha uma senha forte para o banco e guarde.
3. Aguarde o provisionamento.
4. Em `Project Settings -> Database -> Connection string -> URI`, copie a string do pooler.
5. Use a variante assincrona trocando o prefixo para `postgresql+asyncpg://`.

Exemplo:

```text
postgresql+asyncpg://postgres.xxxxxxxxxxxx:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
```

Use a porta `6543` do pooler, nao a conexao direta `5432`, para evitar limites mais agressivos em planos pequenos.

Esse valor sera o `DATABASE_URL` usado pela API e pelo worker.

## Passo 2 - Criar o bot do Telegram

1. No Telegram, abra `@BotFather`.
2. Rode `/newbot`.
3. Guarde o token retornado.
4. Envie uma mensagem para o bot.
5. Abra:

```text
https://api.telegram.org/bot<SEU_TOKEN>/getUpdates
```

6. Copie o `chat.id`.

Valores a guardar:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Esses campos podem ser configurados globalmente por ambiente ou depois na UI por workspace.

## Passo 3 - Deploy da API no Render

Crie um `Web Service` no Render a partir do repositorio GitHub.

Configuracao recomendada:

| Campo | Valor |
|---|---|
| Service Type | `Web Service` |
| Runtime | `Python` |
| Root Directory | `backend` |
| Build Command | `pip install .` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| Health Check Path | `/api/health` |

Observacao:

- o projeto ja executa migracoes no startup via `init_db()`, entao o `Pre-Deploy Command` nao e obrigatorio
- no fluxo por `render.yaml`/Blueprint, manter sem `Pre-Deploy Command` evita incompatibilidades com configuracoes de plano

Variaveis de ambiente minimas da API:

| Variavel | Valor |
|---|---|
| `DATABASE_URL` | URL async do Supabase |
| `AUTH_SECRET_KEY` | segredo longo e aleatorio |
| `SCANNER_ENABLED` | `false` |
| `LOG_LEVEL` | `INFO` |
| `CORS_ALLOWED_ORIGINS` | ajuste depois que a URL da Vercel existir |

Variaveis opcionais:

| Variavel | Uso |
|---|---|
| `ADMIN_TOKEN` | fallback legado para auth |
| `ADMIN_USERNAME` | bootstrap inicial opcional |
| `ADMIN_PASSWORD` | bootstrap inicial opcional |
| `SENTRY_DSN` | observabilidade |
| `LOG_AGGREGATION_URL` | agregacao de logs |
| `LOG_AGGREGATION_TOKEN` | autenticacao do agregador |

Resultado esperado nos logs da API:

```text
Loaded workspace scan configuration
Scanner disabled (SCANNER_ENABLED=false) - running in API-only mode
```

Verificacao minima:

```text
https://seu-servico-api.onrender.com/api/health
```

Resposta esperada:

```json
{"status":"ok","mode":"api_only"}
```

## Passo 4 - Deploy do worker no Render

Crie um segundo servico no mesmo repositorio, agora como `Background Worker`.

Configuracao recomendada:

| Campo | Valor |
|---|---|
| Service Type | `Background Worker` |
| Runtime | `Python` |
| Root Directory | `backend` |
| Build Command | `pip install .` |
| Plan | `Starter` |
| Region | `Oregon` (`oregon`) |
| Start Command | `python -m app.worker` |

Observacao:

- assim como na API, o startup do worker tambem passa por `init_db()`, entao o `Pre-Deploy Command` nao e obrigatorio
- se providers como Binance retornarem `HTTP 451`, mover o worker para uma regiao menos restrita tende a ser a primeira acao. O `render.yaml` atual define `region: oregon` no worker.

Variaveis de ambiente minimas do worker:

| Variavel | Valor |
|---|---|
| `DATABASE_URL` | URL async do Supabase |
| `AUTH_SECRET_KEY` | mesmo valor da API |
| `SCANNER_ENABLED` | `true` |
| `LOG_LEVEL` | `INFO` |
| `SCAN_INTERVAL_SECONDS` | `30` |

Variaveis opcionais do worker:

| Variavel | Uso |
|---|---|
| `TELEGRAM_BOT_TOKEN` | fallback global para alertas |
| `TELEGRAM_CHAT_ID` | fallback global para alertas |
| `ADMIN_USERNAME` | bootstrap inicial opcional |
| `ADMIN_PASSWORD` | bootstrap inicial opcional |
| `SENTRY_DSN` | observabilidade |
| `LOG_AGGREGATION_URL` | agregacao de logs |
| `LOG_AGGREGATION_TOKEN` | autenticacao do agregador |

Resultado esperado nos logs do worker:

- inicializacao sem erro
- ciclos de scan completos
- gravacao de snapshots e sinais no banco

Exemplo de linha saudavel:

```text
scan_cycle_complete opportunities=... signals_saved=... projections_saved=...
```

## Passo 5 - Deploy do frontend na Vercel

Crie um projeto na Vercel a partir do mesmo repositorio.

Configuracao recomendada:

| Campo | Valor |
|---|---|
| Framework | `Next.js` |
| Root Directory | `frontend` |
| Build Command | `next build` |

Variaveis de ambiente da Vercel:

| Variavel | Valor |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://seu-servico-api.onrender.com/api` |
| `NEXT_PUBLIC_WS_URL` | `wss://seu-servico-api.onrender.com/ws` |

O frontend ja esta preparado para build de producao com `output: "standalone"`.

## Passo 6 - Ajustar CORS na API

Depois que a URL final da Vercel existir, atualize `CORS_ALLOWED_ORIGINS` no Render:

```env
CORS_ALLOWED_ORIGINS=https://seu-projeto.vercel.app,http://localhost:3000
```

Depois disso, faca redeploy da API.

## Resumo de variaveis

### API no Render

```env
DATABASE_URL=postgresql+asyncpg://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
AUTH_SECRET_KEY=gere-um-segredo-longo-e-aleatorio
SCANNER_ENABLED=false
LOG_LEVEL=INFO
CORS_ALLOWED_ORIGINS=https://seu-projeto.vercel.app,http://localhost:3000

# opcionais
ADMIN_TOKEN=
ADMIN_USERNAME=
ADMIN_PASSWORD=
SENTRY_DSN=
LOG_AGGREGATION_URL=
LOG_AGGREGATION_TOKEN=
```

### Worker no Render

```env
DATABASE_URL=postgresql+asyncpg://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
AUTH_SECRET_KEY=gere-um-segredo-longo-e-aleatorio
SCANNER_ENABLED=true
SCAN_INTERVAL_SECONDS=30
LOG_LEVEL=INFO

# opcionais
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ADMIN_USERNAME=
ADMIN_PASSWORD=
SENTRY_DSN=
LOG_AGGREGATION_URL=
LOG_AGGREGATION_TOKEN=
```

### Frontend na Vercel

```env
NEXT_PUBLIC_API_URL=https://seu-servico-api.onrender.com/api
NEXT_PUBLIC_WS_URL=wss://seu-servico-api.onrender.com/ws
```

## Checklist de smoke test

Depois do deploy, valide nesta ordem:

1. `GET /api/health` responde `ok` e `mode=api_only`.
2. O worker aparece ativo e sem crash loop no Render.
3. O dashboard abre na Vercel sem erro de CORS.
4. As oportunidades aparecem em ate `30-60s`.
5. O WebSocket conecta com `101 Switching Protocols`.
6. O frontend continua atualizando mesmo com API e worker separados.
7. O teste de Telegram entrega mensagem.
8. No Supabase, as tabelas recebem dados:

```sql
select count(*) from opportunities;
select count(*) from technical_signals;
select count(*) from signal_outcomes;
select count(*) from opportunity_snapshots;
select count(*) from raw_market_observations;
```

9. Rode o verificador operacional:

```bash
cd backend
python scripts/verify_operational_readiness.py
```

Resultado esperado:
- contagens nao nulas nas camadas novas
- campos operacionais populados nas oportunidades recentes
- sem erro de acesso ao schema `0007`

## Troubleshooting

### API sobe, mas o dashboard fica vazio

- confirme que o worker esta rodando
- confira se `DATABASE_URL` e identico na API e no worker
- cheque os logs do worker para falhas de provider ou de conexao com o banco

### Provider retorna `HTTP 451`

- confirme a regiao do worker no Render
- prefira `oregon` para reduzir risco de bloqueio regional de APIs como Binance
- depois de alterar a regiao, rode novo deploy do worker
- se o servico ja existir em outra regiao, pode ser necessario recriar o worker ou aplicar a alteracao pelo painel/CLI do Render

### Dashboard abre, mas nao atualiza em tempo real

- confirme `NEXT_PUBLIC_WS_URL` com `wss://`
- confirme que a API esta em `api_only`
- confirme que o worker escreve snapshots normalmente
- lembre que o frontend tem polling de fallback a cada `30s`, entao ausencia de update instantaneo nao significa necessariamente deploy quebrado

### `alembic upgrade head` falha no Render

- valide `DATABASE_URL`
- confirme prefixo `postgresql+asyncpg://`
- confirme acesso ao pooler do Supabase na porta `6543`

### Alertas duplicados no Telegram

- deixe apenas um worker ativo
- nao rode scanner na API e no worker ao mesmo tempo
- mantenha `SCANNER_ENABLED=false` na API

### Erro de CORS no frontend

- ajuste `CORS_ALLOWED_ORIGINS` na API
- faca redeploy da API depois da alteracao

## Operacao continua

- Render e Vercel vao redeployar a cada push na branch configurada
- alteracoes de schema devem continuar passando por `alembic upgrade head`
- a topologia recomendada continua sendo API-only + worker separado
