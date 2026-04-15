# Handoff

## Resumo

Projeto de monitoramento de oportunidades em criptomoedas com:
- `backend/`: FastAPI, scanner assincrono, persistencia SQLAlchemy e alertas Telegram.
- `frontend/`: Next.js App Router, dashboard em tempo real, historico e configuracoes.

Documentos principais ja existentes:
- `SPEC.md`: visao funcional e escopo do MVP.
- `DEPLOY.md`: fluxo de deploy e operacao.

## Arquitetura Atual

### Backend
- Entrada principal: `backend/app/main.py`
- Rotas REST: `backend/app/api/routes.py`
- WebSocket: `backend/app/api/websocket.py`
- Scanner: `backend/app/services/scanner.py`
- Persistencia: `backend/app/services/persistence.py`
- Integracoes com exchanges:
  - `backend/app/providers/novadax.py`
  - `backend/app/providers/mercado_bitcoin.py`
  - `backend/app/providers/binance.py`
- Filtros e score:
  - `backend/app/filters/*.py`

### Frontend
- Dashboard: `frontend/src/app/page.tsx`
- Historico e analytics: `frontend/src/app/history/page.tsx`
- Configuracoes: `frontend/src/app/settings/page.tsx`
- Cliente HTTP: `frontend/src/lib/api.ts`
- Cliente WebSocket: `frontend/src/lib/websocket.ts`
- Hook principal: `frontend/src/hooks/use-opportunities.ts`

## Estado Atual

### O que ja existe
- Coleta de dados de tres exchanges.
- Aplicacao de filtros de volatilidade, volume, liquidez e spread.
- Score de oportunidade.
- Persistencia de historico, auditoria e configuracao por workspace.
- Atualizacao em tempo real via WebSocket.
- Painel web funcional com modal de detalhe, historico, login administrativo e seletor de workspace.
- Fundacao multi-tenant com `users`, `workspaces`, `workspace_memberships` e `workspace_configs`.

### O que ainda nao esta maduro
- Onboarding completo de usuarios alem do admin bootstrapado por ambiente.
- Convite, recuperacao de conta e fluxo de sessao mais completo.
- Scanner dedicado por tenant; hoje o processo e global com filtragem por workspace na leitura.
- Observabilidade externa e operacao de producao mais refinadas.

## Riscos Tecnicos Relevantes

### 1. Multi-Tenant
- O scanner ainda e compartilhado entre workspaces.
- As oportunidades sao persistidas globalmente e projetadas por workspace na leitura.
- O modelo atual atende operacao interna, mas ainda nao equivale a um SaaS multi-tenant completo.

### 2. Runtime
- O estado atual de oportunidades ainda fica em memoria do processo.
- O worker e o scanner foram preparados para separacao, mas continuam no mesmo contexto de deploy por padrao.

### 3. Build e deploy
- SQLite continua sendo o default local; Postgres continua sendo a opcao recomendada para producao.

### 4. Qualidade
- A suite cobre backend, auth e rotas principais, mas ainda nao cobre cenarios mais profundos de workspace/membership.
- O frontend segue sem testes automatizados de interface.

## Validacao Ja Feita

- `python -m compileall backend/app backend/tests`: passou.
- `python -m pytest backend/tests -q -p no:cacheprovider`: `14 passed`.
- `npm --prefix frontend run lint`: passou.
- `npm --prefix frontend run build`: passou.

## Proximos Passos Recomendados

### Prioridade alta
1. Expandir gestao de usuarios alem do bootstrap admin.
2. Adicionar convite, recuperacao de senha e revogacao mais completa de sessao.
3. Decidir se o scanner vai permanecer global ou migrar para processamento por tenant.
4. Endurecer deploy de producao com Postgres e operacao externa de logs/monitoramento.

### Prioridade media
1. Cobrir workspaces e membership com testes adicionais.
2. Adicionar testes E2E do frontend para login, troca de workspace e configuracao isolada.
3. Refinar a documentacao operacional para o modo multi-tenant.

## Comandos Uteis

### Backend
```powershell
python -m compileall backend\app
python -m pytest backend\tests -q -p no:cacheprovider
```

### Frontend
```powershell
npm --prefix frontend install
npm --prefix frontend run lint
npm --prefix frontend run build
```

## Observacoes

- Existem warnings de permissao do ambiente ao rodar `git status` e tentativas de cache do `pytest`.
- O repositorio deixou de ser apenas single-admin, mas ainda deve ser tratado como plataforma interna em amadurecimento, nao como produto SaaS final.
