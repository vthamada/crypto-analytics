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
- Contrato compartilhado: `backend/app/services/shared_state.py`
- Integracoes com exchanges:
  - `backend/app/providers/novadax.py`
  - `backend/app/providers/mercado_bitcoin.py`
  - `backend/app/providers/binance.py`
- Filtros e score:
  - `backend/app/filters/*.py`
- Worker dedicado: `backend/app/worker.py`

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
- Score de oportunidade com `technical_score` neutro (pesos fixos) e `workspace_score` derivado por tenant.
- `score_version` para versionamento do motor de score.
- Dual-write de `technical_signals` com identidade semantica por sinal.
- `workspace_signal_projections` materializado por ciclo de scan.
- `signal_outcomes` com campos para avaliacao temporal e job de avaliacao executado no loop de scan.
- Repeticao persistida em banco com decay automatico.
- Persistencia de historico, auditoria e configuracao por workspace.
- Atualizacao em tempo real via WebSocket.
- Painel web funcional com modal de detalhe, historico, login administrativo e seletor de workspace.
- Dashboard consome payload agregado em `/api/dashboard`; historico usa `/api/history/summary` e analytics operacional sob demanda para reduzir egress.
- Scanner em modo default faz descoberta ampla de pares BRL quando nao ha watchlist manual em `enabled_pairs`.
- Oportunidades agora incluem margem operacional e classificacao `trade`, `hold`, `observe` ou `avoid`.
- Fundacao multi-tenant com `users`, `workspaces`, `workspace_memberships` e `workspace_configs`.
- Worker dedicado com mesmo contrato de scan que o processo principal.
- API capaz de operar sem scanner local, lendo snapshots do banco (modo `api_only`).
- API em `api_only` agora repropaga snapshots persistidos para clientes WebSocket conectados, mesmo com o scan rodando apenas no worker.
- Politica de Telegram configuravel por workspace (threshold, tipos, cooldown).
- Suite de 63 testes no backend incluindo contratos de API, auth, filtros, scanner, persistencia, workspace, WebSocket em `api_only` e outcome evaluator.

### O que ainda nao esta maduro
- Operacao de producao com API-only + worker separado em provedores gerenciados ainda precisa de fechamento mais padronizado.
- Feature gates por plano e integracao com Stripe.
- Autoregistro aberto sem convite.
- Observabilidade externa e operacao de producao mais refinadas.
- Medicao objetiva de egress por rota/tela ainda precisa de telemetria em producao.

## Modelo de Dados P2

### Tabelas novas (migracao 0006)
| Tabela | Finalidade |
|---|---|
| `scanner_runtime_state` | Singleton com estado do ultimo ciclo (inicio, duracao, erro, sucesso) |
| `opportunity_snapshots` | Snapshot atual das oportunidades para modo API-only |
| `technical_signals` | Identidade semantica do sinal com componentes de score e contexto cross-exchange |
| `workspace_signal_projections` | Projecao materializada por workspace (score, visibilidade, elegibilidade de alerta) |
| `signal_outcomes` | Tracking de resultado temporal (entry_price, precos em 5m/15m/1h/4h) |
| `repetition_counts` | Contagem de repeticao persistida com decay por inatividade |

### Colunas adicionadas em `opportunities`
- `technical_score` (Float) — score neutro com pesos fixos
- `score_version` (String) — versao do motor ("v1")
- `technical_signal_id` (String) — referencia ao sinal tecnico

## Riscos Tecnicos Relevantes

### 1. Multi-Tenant
- O scanner ainda e compartilhado entre workspaces (unico processo, configuracao mesclada).
- As oportunidades sao persistidas globalmente com `technical_score` neutro e projetadas por workspace na leitura.
- O modelo atual atende operacao interna, mas ainda nao equivale a um SaaS multi-tenant completo.

### 2. Runtime
- O estado corrente ja pode ser lido do banco (snapshots + runtime state), e a API em `api_only` repropaga snapshots para o WebSocket observando `scanner_runtime_state`; ainda assim, isso depende de polling em banco e nao de um barramento distribuido dedicado.
- O worker tem paridade funcional com `main.py` e ja e o modo padrao de deploy no `docker-compose.yml`.
- O job de avaliacao de `signal_outcomes` existe, mas ainda falta janela historica suficiente para calibracao de score por outcome.

### 3. Build e deploy
- SQLite continua sendo o default local; Postgres continua sendo a opcao recomendada para producao.
- O `docker-compose.yml` separa API e worker em servicos distintos, mas ainda nao ha barramento de broadcast entre processos para o WebSocket.

### 4. Qualidade
- 63 testes passando: rotas, auth, filtros, scanner, persistencia, WebSocket, tenancy, contratos P2 e outcome evaluator.
- O frontend segue com suite Playwright para fluxos criticos mas sem cobertura dos novos campos tecnicos.

## Validacao Ja Feita

- `python -m compileall backend/app backend/tests`: passou.
- `python -m pytest backend/tests -q`: `63 passed`.
- `npm --prefix frontend run lint`: passou.
- `npm --prefix frontend run build`: passou.

## Proximos Passos Recomendados

### Prioridade alta (P2 residual + P3 fundacao)
1. Endurecer o deploy de producao com Postgres, HTTPS, rotacao de segredos e monitoramento externo.
2. Preparar feature gates por plano e integracao Stripe.
3. Substituir o polling em banco do rebroadcast `api_only` por um barramento distribuido se houver necessidade de multiplas replicas.

### Prioridade media (P3)
1. Feature gates por plano (middleware `organization.plan`).
2. Integracao Stripe para cobranca.
3. Autoregistro aberto com Free tier e verificacao de email.
4. Deploy de producao endurecido (Postgres, HTTPS, rotacao de segredos).

### Prioridade futura (P4)
1. Paper trading com simulacao de entradas e saidas.
2. Execucao manual confirmada via Telegram + API Binance.
3. Motor de execucao automatica com gestao de risco.

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

- O `score` no modelo `Opportunity` e workspace-dependente (recalculado por `project_workspace_opportunity`). O `technical_score` e neutro e fixo.
- O `technical_signal_id` atual e um UUID gerado no dual-write de `technical_signals`, nao um hash deterministico dos componentes.
- O outcome evaluator ja preenche `price_after_5m`, `price_after_15m`, `price_after_1h` e `price_after_4h` para sinais pendentes.
