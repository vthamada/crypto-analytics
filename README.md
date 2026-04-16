# Crypto Analytics

Monorepo de monitoramento de oportunidades em criptomoedas com backend FastAPI, worker dedicado de scan e frontend Next.js.

## Estrutura

- `backend/`: API, worker, persistencia, autenticacao e alertas
- `frontend/`: dashboard, historico, analytics e configuracoes
- `SPEC.md`: especificacao funcional e direcao de produto
- `ARCHITECTURE.md`: visao arquitetural de alto nivel
- `SYSTEM_STATE.md`: melhor retrato do runtime atual e do fluxo real de geracao de sinais
- `DEPLOY.md`: deploy e operacao
- `BACKLOG.md`: prioridades abertas

## Modos de operacao

- Desenvolvimento simples: `uvicorn app.main:app --reload` sobe a API com scanner local
- Fluxo padrao do repositorio: `docker-compose.yml` sobe `backend` em modo API-only e `worker` como produtor principal do scan

## Setup rapido

### 1. Configuracao

Use [.env.example](.env.example) como base para seu `.env` na raiz e [backend/.env.example](backend/.env.example) como referencia para o backend.

Campos importantes:
- `DATABASE_URL`
- `AUTH_SECRET_KEY` ou `ADMIN_TOKEN` como fallback legado
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_WS_URL`
- `SCANNER_ENABLED`
- `CORS_ALLOWED_ORIGINS`
- `SENTRY_DSN` e `LOG_AGGREGATION_URL` opcionais

### 2. Backend

```bash
cd backend
pip install .[dev]
uvicorn app.main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Stack separada via Docker Compose

```bash
docker compose up --build
```

## Comandos uteis

### Backend

```bash
cd backend
python -m pytest tests -q
python -m compileall app tests
```

### Frontend

```bash
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run e2e
```

## Estado atual

- Scanner global com projecao posterior por workspace
- `technical_score` neutro com `score_version`
- `technical_signals`, `workspace_signal_projections` e `signal_outcomes`
- API capaz de operar sem scanner local via `opportunity_snapshots`
- Worker dedicado como fluxo padrao de scan
- Politica de Telegram configuravel por workspace
- Health check com `mode` (`scanner` ou `api_only`) e `scanner_state`
- Suite backend e E2E frontend ativas no repositorio

## Leitura recomendada

- Runtime e comportamento atual: [SYSTEM_STATE.md](SYSTEM_STATE.md)
- Prioridades e roadmap: [BACKLOG.md](BACKLOG.md)
- Deploy: [DEPLOY.md](DEPLOY.md)
