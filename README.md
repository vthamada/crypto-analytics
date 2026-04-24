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
python scripts/verify_operational_readiness.py
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
- Camada aditiva de executabilidade com `executability_score`, `executability_band`, `interesting_signal` e `operable_signal`
- Metricas de book em notional e estimativa de slippage (`bid_notional_top_n`, `ask_notional_top_n`, `estimated_*_slippage_bps`, `fillable_notional_within_slippage_cap`)
- Perfil operacional por workspace com tamanho de ordem, liquidez notional minima e slippage maximo de entrada/saida
- `technical_signals`, `workspace_signal_projections` e `signal_outcomes`
- API capaz de operar sem scanner local via `opportunity_snapshots`
- `/api/opportunities` com ordenacao por score tecnico ou executabilidade e filtro `operable_only`
- Dashboard com leitura dual para payload legado/novo e explicabilidade operacional no card e no detalhe do sinal
- Worker dedicado como fluxo padrao de scan
- Politica de Telegram configuravel por workspace
- `trading_profile` por workspace e analytics operacionais
- Health check com `mode` (`scanner` ou `api_only`) e `scanner_state`
- Suite backend e E2E frontend ativas no repositorio

## Leitura recomendada

- Runtime e comportamento atual: [SYSTEM_STATE.md](SYSTEM_STATE.md)
- Prioridades e roadmap: [BACKLOG.md](BACKLOG.md)
- Proxima iteracao operacional: [docs/superpowers/plans/2026-04-18-post-release-operationalization-plan.md](docs/superpowers/plans/2026-04-18-post-release-operationalization-plan.md)
- Deploy: [DEPLOY.md](DEPLOY.md)
