# Crypto Analytics

Monorepo de monitoramento de oportunidades em criptomoedas com backend FastAPI e frontend Next.js.

## Estrutura

- `backend/`: scanner, API, persistencia e alertas
- `frontend/`: dashboard, historico e configuracoes
- `SPEC.md`: escopo funcional
- `ARCHITECTURE.md`: visao tecnica
- `DEPLOY.md`: deploy e operacao
- `BACKLOG.md`: prioridades abertas

## Setup Rapido

### 1. Configuracao

Use [`.env.example`](</c:/Users/vtham/OneDrive/Área de Trabalho/crypto-analytics/.env.example>) como base para seu `.env`.

Campos importantes:
- `ADMIN_TOKEN`
- `DATABASE_URL`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_WS_URL`
- `SENTRY_DSN` (opcional)

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

## Comandos Uteis

### Backend

```bash
python -m pytest backend/tests -q -p no:cacheprovider
python -m compileall backend/app
```

### Frontend

```bash
npm --prefix frontend run lint
npm --prefix frontend run build
```

## Estado Atual

- Configuracao administrativa protegida por token.
- Scanner com reconfiguracao em runtime.
- Cooldown de alertas Telegram.
- Analytics filtrados por periodo.
- CI inicial em `.github/workflows/ci.yml`.
- Suite inicial de testes do backend adicionada.
- Health check enriquecido com metricas de scanner e providers.
- Integracao opcional com Sentry no backend.

## Proximos Passos

Os itens restantes estao em [BACKLOG.md](</c:/Users/vtham/OneDrive/Área de Trabalho/crypto-analytics/BACKLOG.md>), com foco em:
- ampliar cobertura de testes
- endurecer autenticacao/autorizacao
- melhorar observabilidade
- evoluir analytics e regras de negocio
