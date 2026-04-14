# Guia de Deploy — Crypto Analytics

Este guia cobre o deploy completo do sistema em produção usando serviços gerenciados (gratuitos ou de baixo custo). Tempo estimado: **30–45 minutos** na primeira vez.

Arquitetura alvo:

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Vercel     │ ───► │   Railway    │ ───► │   Supabase   │
│ (frontend)   │ HTTP │  (backend)   │  DB  │ (PostgreSQL) │
│  Next.js     │  WS  │  FastAPI     │      │              │
└──────────────┘      └──────┬───────┘      └──────────────┘
                             │
                             ▼
                       ┌──────────┐
                       │ Telegram │
                       │   Bot    │
                       └──────────┘
```

---

## Pré-requisitos

Crie contas nos seguintes serviços (todos têm plano gratuito):

- [Supabase](https://supabase.com) — banco PostgreSQL gerenciado
- [Railway](https://railway.app) — hospedagem do backend (alternativas: [Render](https://render.com) ou [Fly.io](https://fly.io))
- [Vercel](https://vercel.com) — hospedagem do frontend
- [GitHub](https://github.com) — hospedagem do código (os deploys puxam do Git)
- [Telegram](https://telegram.org) — para criar o bot de alertas

Tenha instalado localmente:

- `git`
- Conta GitHub com o repositório `crypto-analytics` enviado (`git push origin main`)

---

## Passo 1 — Criar o banco de dados (Supabase)

1. Entre em [supabase.com](https://supabase.com) → **New Project**
2. Preencha:
   - **Name**: `crypto-analytics`
   - **Database Password**: gere uma senha forte (**guarde — você vai precisar**)
   - **Region**: `South America (São Paulo)` (mais próximo das exchanges BR)
   - **Plan**: Free
3. Aguarde ~2 minutos até o banco provisionar
4. Vá em **Project Settings → Database → Connection string → URI**
5. Copie a string e **substitua** `[YOUR-PASSWORD]` pela senha real:

```
postgresql://postgres.xxxxxxxxxxxx:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
```

6. Troque o prefixo para `postgresql+asyncpg://` (necessário para o SQLAlchemy async):

```
postgresql+asyncpg://postgres.xxxxxxxxxxxx:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
```

Guarde essa URL — ela é o valor de `DATABASE_URL` do backend.

> **Observação**: as tabelas são criadas automaticamente na primeira inicialização via `init_db()` em [backend/app/models/database.py](backend/app/models/database.py). Nenhum passo manual de migração.

---

## Passo 2 — Criar o bot do Telegram

1. Abra o Telegram e busque **@BotFather**
2. Envie `/newbot` e siga as instruções (escolha nome e username)
3. Copie o **token** retornado (formato `123456789:AAH...`)
4. Envie qualquer mensagem para o seu novo bot (ex: `/start`)
5. Abra no navegador:
   ```
   https://api.telegram.org/bot<SEU_TOKEN>/getUpdates
   ```
6. Procure o campo `chat.id` na resposta JSON — esse é o seu `TELEGRAM_CHAT_ID`

Guarde os dois valores:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

> Dica: se quiser receber em grupo, adicione o bot ao grupo, envie uma mensagem no grupo e o `chat.id` do grupo aparecerá no mesmo endpoint (será negativo, ex: `-1001234567890`).

---

## Passo 3 — Deploy do backend (Railway)

1. Entre em [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo**
2. Selecione o repositório `crypto-analytics`
3. Na tela de configuração do serviço:
   - **Root Directory**: `backend`
   - **Build**: detecta `Dockerfile` automaticamente (não precisa alterar)
4. Vá em **Variables** e adicione:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | URL do Supabase do Passo 1 |
| `TELEGRAM_BOT_TOKEN` | token do Passo 2 |
| `TELEGRAM_CHAT_ID` | chat id do Passo 2 |
| `SCAN_INTERVAL_SECONDS` | `30` |
| `LOG_LEVEL` | `INFO` |
| `PORT` | `8000` |

5. Em **Settings → Networking** clique em **Generate Domain** — anote a URL gerada (ex: `crypto-analytics-production.up.railway.app`)
6. Em **Settings → Deploy** confirme o **Start Command**:

```
uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
```

> **⚠️ CRÍTICO — mantenha `--workers 1`.** O scan loop roda em background via `asyncio.create_task` no lifespan da FastAPI. Com mais de um worker, cada réplica roda um scanner independente, gerando **alertas duplicados** no Telegram e **requisições redundantes** às APIs das exchanges (risco de rate-limit 429). Se precisar escalar, extraia o scanner para um worker separado (ver seção *Evolução futura*).

7. Aguarde o primeiro deploy (~3 min). Em **Deployments → View Logs** confirme:

```
INFO:     Application startup complete.
app.main: Scanner started
```

### Verificação do backend

Abra no navegador (troque pelo seu domínio Railway):

```
https://seu-dominio.up.railway.app/api/health
```

Deve responder:

```json
{"status": "ok"}
```

---

## Passo 4 — Deploy do frontend (Vercel)

1. Entre em [vercel.com](https://vercel.com) → **Add New → Project**
2. Importe o repositório `crypto-analytics`
3. Configure:
   - **Framework Preset**: Next.js (detecta automático)
   - **Root Directory**: `frontend`
   - **Build Command**: deixe padrão (`next build`)
4. Em **Environment Variables** adicione:

| Variável | Valor |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://seu-dominio.up.railway.app/api` |
| `NEXT_PUBLIC_WS_URL` | `wss://seu-dominio.up.railway.app/ws` |

> **Atenção**: em produção use `https` e `wss` (com SSL). O Railway provê HTTPS por padrão no domínio gerado.

5. Clique em **Deploy**. Aguarde ~2 min
6. A Vercel gera um domínio tipo `crypto-analytics.vercel.app`

### Verificação do frontend

1. Acesse `https://seu-projeto.vercel.app`
2. Abra o DevTools → **Network** → **WS** e confirme a conexão `wss://.../ws` com status **101 Switching Protocols**
3. Após o primeiro ciclo de scan (~30s), as oportunidades devem aparecer na tabela

---

## Passo 5 — Atualizar o CORS do backend

Por padrão o CORS do backend aceita `*` (qualquer origem). Para produção, restrinja em [backend/app/main.py](backend/app/main.py):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://seu-projeto.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Faça commit → push → o Railway redeploya sozinho.

---

## Variáveis de ambiente — resumo

### Backend (Railway)

```env
DATABASE_URL=postgresql+asyncpg://postgres.xxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
TELEGRAM_BOT_TOKEN=123456:AAH...
TELEGRAM_CHAT_ID=987654321
SCAN_INTERVAL_SECONDS=30
LOG_LEVEL=INFO
PORT=8000

# Opcionais (rotas públicas das exchanges não exigem):
NOVADAX_API_KEY=
NOVADAX_API_SECRET=
MB_API_KEY=
MB_API_SECRET=
BINANCE_API_KEY=
BINANCE_API_SECRET=
```

### Frontend (Vercel)

```env
NEXT_PUBLIC_API_URL=https://seu-backend.up.railway.app/api
NEXT_PUBLIC_WS_URL=wss://seu-backend.up.railway.app/ws
```

---

## Troubleshooting

### Frontend carrega mas tabela vazia / "Failed to fetch"

- Confira `NEXT_PUBLIC_API_URL` na Vercel (precisa `https`, não `http`)
- Abra DevTools → Console — se aparecer `CORS blocked`, volte ao Passo 5
- Teste o endpoint direto: `curl https://seu-backend.up.railway.app/api/health`

### WebSocket não conecta (status ficando "Connecting...")

- URL precisa ser `wss://` (com SSL) em produção, não `ws://`
- Railway suporta WebSockets nativamente, não precisa configuração extra
- Se persistir, confira os logs do Railway — erros de upgrade aparecem ali

### Alertas duplicados no Telegram

- Você tem mais de 1 worker rodando. Em **Railway → Settings → Deploy** force `--workers 1`
- Verifique também se há mais de uma réplica do serviço em **Settings → Replicas** (deve ser 1)

### `asyncpg.exceptions.InvalidPasswordError` nos logs

- Senha do Supabase está errada ou contém caracteres especiais não-URL-encodados
- Re-gere a senha sem `@ : / #` ou use `urllib.parse.quote_plus` antes de colar

### Scanner não inicia / nenhuma oportunidade após minutos

- Confira logs — procure `Scanner started`
- Teste uma exchange manualmente: `curl https://seu-backend.up.railway.app/api/opportunities`
- Exchanges podem estar temporariamente indisponíveis (veja [status.novadax.com](https://status.novadax.com) etc)

### "application exited with status 1" logo na inicialização

- Quase sempre é `DATABASE_URL` inválida — valide se o prefixo é `postgresql+asyncpg://`
- Se apontar pro Supabase, use o **Connection Pooler** (porta `6543`), não a conexão direta (`5432`) — planos gratuitos limitam conexões diretas

---

## Atualizações futuras

Ambos os serviços fazem **deploy automático** em cada `git push origin main`:

```bash
git add .
git commit -m "feat: nova funcionalidade"
git push origin main
```

- Railway: rebuilda o Dockerfile e redeploya (~2 min)
- Vercel: rebuilda o Next.js e redeploya (~1 min)

Para rollback, use a UI de cada plataforma — ambos mantêm histórico de deploys.

---

## Custos estimados

| Serviço | Plano | Custo mensal | Limites relevantes |
|---|---|---|---|
| **Supabase** | Free | R$ 0 | 500 MB DB, 2 GB transfer |
| **Railway** | Hobby | ~R$ 25 (US$ 5) | 500h execução, 8 GB RAM |
| **Vercel** | Hobby | R$ 0 | 100 GB bandwidth |
| **Telegram** | — | R$ 0 | ilimitado |
| **Total** | | **~R$ 25/mês** | |

Quando precisar escalar (tráfego alto, mais exchanges, histórico longo):

| Serviço | Plano | Custo mensal |
|---|---|---|
| Supabase Pro | | ~R$ 125 (US$ 25) |
| Railway Pro | | ~R$ 100 (US$ 20) |
| Vercel Pro | | ~R$ 100 (US$ 20) |
| **Total** | | **~R$ 325/mês** |

---

## Evolução futura

Quando o sistema crescer, considere estes próximos passos:

### 1. Separar scanner em worker dedicado

Hoje o scanner roda no mesmo processo do FastAPI. Para escalar horizontalmente a API sem duplicar o scanner:

- Criar `backend/app/worker.py` que só roda o `scan_loop`
- Railway: criar segundo serviço apontando pro mesmo repo com start command diferente
- Scanner grava no DB, API lê do DB — WebSocket usa Redis pub/sub pra broadcast cross-process

### 2. Migrações com Alembic

Hoje `init_db()` cria tabelas se não existirem, mas não versiona mudanças de schema. Quando for alterar tabelas em produção:

```bash
cd backend
alembic init alembic
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 3. Observabilidade

- [Sentry](https://sentry.io) — erros em produção (adicionar `sentry-sdk[fastapi]`)
- [Logtail](https://logtail.com) — agregador de logs estruturados
- [UptimeRobot](https://uptimerobot.com) — ping no `/api/health` a cada 5 min, grátis

### 4. CI/CD

- GitHub Actions rodando `pytest` e `tsc --noEmit` antes de aceitar PRs
- Deploy pra staging em branch `develop`, produção em `main`

---

## Checklist final

Antes de considerar o deploy concluído, valide:

- [ ] `https://seu-backend.up.railway.app/api/health` retorna `{"status":"ok"}`
- [ ] `https://seu-projeto.vercel.app` carrega o dashboard
- [ ] Oportunidades aparecem na tabela após ~30s
- [ ] WebSocket conecta (status "Connected" na UI ou no Network → WS)
- [ ] Alerta de teste chega no Telegram
- [ ] `SELECT count(*) FROM opportunities;` no Supabase SQL Editor retorna > 0 após alguns minutos
- [ ] CORS restrito ao domínio da Vercel (não `*`)
- [ ] `--workers 1` confirmado no start command do Railway
