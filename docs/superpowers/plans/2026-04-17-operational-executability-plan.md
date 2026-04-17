# Operational Executability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evoluir o produto de scanner heuristico para assistente operacional, introduzindo a camada de executabilidade sem quebrar o fluxo atual de coleta, ranking, persistencia, API e dashboard.

**Architecture:** A implementacao deve ser incremental e aditiva. Primeiro entram contratos e campos novos sem alterar o comportamento atual; depois entram liquidez em notional, slippage e executability score; na sequencia o frontend passa a explicar operabilidade e os workspaces ganham perfis operacionais; por ultimo entram reweighting por outcome e refatoracoes mais sensiveis do historico.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, worker Python async, Next.js App Router, TypeScript, Playwright, pytest.

---

## Scope And Release Strategy

Este plano esta dividido em releases pequenas para evitar breaking change:

1. **Release A - Contratos aditivos e observabilidade do motor**
2. **Release B - Liquidez em notional e slippage**
3. **Release C - Executability score e split interesting/operable**
4. **Release D - Frontend dual-read e explicabilidade operacional**
5. **Release E - Workspace trading profile, thresholds e alertas**
6. **Release F - Duracao util e taxonomia de movimento v2**
7. **Release G - Reweighting por outcome e analytics operacionais**
8. **Release H - Migracao estrutural do historico e separacao de camadas**

Releases `A` a `D` sao as mais valiosas e podem ser entregues sem reestruturar a persistencia profunda.

---

## File Map

### Backend - arquivos existentes mais provaveis de modificacao

- `backend/app/models/schemas.py`
- `backend/app/api/routes.py`
- `backend/app/services/scanner.py`
- `backend/app/services/shared_state.py`
- `backend/app/services/persistence.py`
- `backend/app/services/outcome_evaluator.py`
- `backend/app/filters/liquidity.py`
- `backend/app/filters/scoring.py`
- `backend/app/filters/movement.py`
- `backend/app/services/telegram.py`

### Backend - arquivos novos recomendados

- `backend/app/filters/executability.py`
- `backend/tests/test_executability.py`

### Frontend - arquivos existentes mais provaveis de modificacao

- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/components/opportunities-table.tsx`
- `frontend/src/components/signal-detail-modal.tsx`
- `frontend/src/app/history/page.tsx`
- `frontend/src/app/settings/page.tsx`
- `frontend/tests/e2e/app.spec.ts`

### Testes backend existentes para reaproveitar

- `backend/tests/test_filters.py`
- `backend/tests/test_scanner.py`
- `backend/tests/test_api_routes.py`
- `backend/tests/test_contract_integration.py`
- `backend/tests/test_persistence.py`
- `backend/tests/test_signal_outcomes.py`
- `backend/tests/test_runtime_persistence.py`

---

## Release A - Contratos Aditivos E Observabilidade Do Motor

Status: concluida em 2026-04-17.

### Task 1: Adicionar campos novos sem alterar o ranking atual

**Files:**
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/api/routes.py`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Test: `backend/tests/test_api_routes.py`
- Test: `backend/tests/test_contract_integration.py`

- [x] Adicionar ao `Opportunity` e `HistoryRecord` campos opcionais e aditivos:
  - `executability_score: float | None = None`
  - `executability_band: str | None = None`
  - `interesting_signal: bool | None = None`
  - `operable_signal: bool | None = None`
  - `bid_notional_top_n: float | None = None`
  - `ask_notional_top_n: float | None = None`
  - `total_notional_top_n: float | None = None`
  - `estimated_buy_slippage_bps: float | None = None`
  - `estimated_sell_slippage_bps: float | None = None`
  - `fillable_notional_within_slippage_cap: float | None = None`
  - `movement_persistence_score: float | None = None`
  - `score_version`, `executability_version`, `movement_version`, `profile_version`

- [x] Garantir que `routes.py` serialize esses campos sem exigir sua presenca em registros antigos.

- [x] Atualizar `frontend/src/lib/types.ts` para leitura dual, com todos os novos campos opcionais.

- [x] Atualizar `frontend/src/lib/api.ts` para nao falhar se o backend ainda nao enviar os novos campos.

- [x] Cobrir o contrato com testes:
  - resposta de oportunidades continua valida sem os novos campos
  - resposta passa a aceitar os novos campos quando presentes

- [x] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_api_routes.py backend\tests\test_contract_integration.py -v`
  - Run: `npm --prefix frontend run build`

**Commit suggestion:** `feat: add additive executability fields to API contracts`

### Task 2: Versionar o motor de forma explicita

**Files:**
- Modify: `backend/app/services/shared_state.py`
- Modify: `backend/app/services/persistence.py`
- Modify: `backend/app/models/schemas.py`
- Test: `backend/tests/test_persistence.py`

- [x] Padronizar constantes de versao:
  - `SCORE_VERSION`
  - `EXECUTABILITY_VERSION`
  - `MOVEMENT_VERSION`
  - `PROFILE_VERSION`

- [x] Persistir as versoes nos registros novos de oportunidade/historico/projecao.

- [x] Garantir fallback seguro para registros legados sem versao.

- [x] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_persistence.py backend\tests\test_runtime_persistence.py -v`

**Commit suggestion:** `feat: persist signal engine versions`

---

## Release B - Liquidez Em Notional E Slippage

Status: concluida em 2026-04-17.

### Task 3: Introduzir liquidez em notional

**Files:**
- Modify: `backend/app/filters/liquidity.py`
- Modify: `backend/app/services/scanner.py`
- Modify: `backend/app/models/schemas.py`
- Test: `backend/tests/test_filters.py`
- Test: `backend/tests/test_scanner.py`

- [x] Manter `calculate_liquidity()` para compatibilidade.

- [x] Adicionar novas funcoes em `filters/liquidity.py`:
  - `calculate_notional_depth(order_book, side, levels=10)`
  - `calculate_total_notional_depth(order_book, levels=10)`
  - `calculate_depth_ratio_by_distance(order_book, bps_window=50, levels=10)`

- [x] Popular os novos campos no scanner sem mexer ainda no `score`.

- [x] Atualizar os testes de filtro para diferenciar:
  - moeda barata com muita quantidade e baixo notional
  - moeda cara com menor quantidade e alto notional

- [x] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_filters.py backend\tests\test_scanner.py -v`

**Commit suggestion:** `feat: add notional liquidity metrics`

### Task 4: Introduzir slippage estimado por tamanho de ordem

**Files:**
- Create: `backend/app/filters/executability.py`
- Modify: `backend/app/services/scanner.py`
- Modify: `backend/app/models/schemas.py`
- Create: `backend/tests/test_executability.py`
- Test: `backend/tests/test_scanner.py`

- [x] Criar `filters/executability.py` com funcoes:
  - `estimate_slippage_bps(order_book, side, order_notional_brl, levels=10)`
  - `estimate_fillable_notional(order_book, max_slippage_bps, side, levels=10)`
  - `classify_exit_risk(...)`

- [x] Definir um tamanho de ordem padrao inicial no scanner:
  - `1000 BRL` como baseline global para MVP
  - ainda sem perfil de workspace na primeira iteracao

- [x] Popular no `Opportunity`:
  - `estimated_buy_slippage_bps`
  - `estimated_sell_slippage_bps`
  - `fillable_notional_within_slippage_cap`

- [x] Cobrir testes de book raso, book profundo e book assimetrico.

- [x] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_executability.py backend\tests\test_scanner.py -v`

**Commit suggestion:** `feat: estimate order-book slippage`

---

## Release C - Executability Score E Split Interesting/Operable

Status: concluida em 2026-04-17.

### Task 5: Calcular executability score sem substituir o score tecnico

**Files:**
- Modify: `backend/app/filters/scoring.py`
- Modify: `backend/app/filters/executability.py`
- Modify: `backend/app/services/scanner.py`
- Modify: `backend/app/models/schemas.py`
- Test: `backend/tests/test_executability.py`
- Test: `backend/tests/test_scanner.py`

- [x] Criar funcao nova:
  - `calculate_executability_score(...)`

- [x] Componentes iniciais recomendados:
  - `notional_depth_score`
  - `buy_slippage_score`
  - `sell_slippage_score`
  - `spread_score`
  - `quote_volume_score`
  - `exit_risk_penalty`

- [x] Manter `score` atual como ranking tecnico/base.

- [x] Preencher:
  - `executability_score`
  - `executability_band`

- [x] Documentar na API a diferenca entre:
  - `score`
  - `technical_score`
  - `executability_score`

- [x] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_executability.py backend\tests\test_scanner.py backend\tests\test_contract_integration.py -v`

**Commit suggestion:** `feat: add executability scoring`

### Task 6: Separar sinais interessantes de sinais operaveis

**Files:**
- Modify: `backend/app/services/scanner.py`
- Modify: `backend/app/api/routes.py`
- Modify: `frontend/src/lib/types.ts`
- Test: `backend/tests/test_scanner.py`
- Test: `backend/tests/test_api_routes.py`

- [x] Definir heuristica inicial:
  - `interesting_signal = score >= 40`
  - `operable_signal = executability_score >= 60 and estimated_sell_slippage_bps <= cap and spread_pct <= cap`

- [x] Persistir/serializar esses flags.

- [x] Garantir fallback em registros antigos:
  - se os campos nao existirem, o frontend continua tratando tudo como interessante

- [x] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_scanner.py backend\tests\test_api_routes.py -v`

**Commit suggestion:** `feat: split interesting and operable signals`

### Task 7: Adaptar o ranking do backend sem quebrar a projecao por workspace

**Files:**
- Modify: `backend/app/api/routes.py`
- Modify: `backend/app/services/persistence.py`
- Test: `backend/tests/test_api_routes.py`
- Test: `backend/tests/test_workspace_tenancy.py`

- [x] Atualizar `project_workspace_opportunity()` para:
  - manter o `score` atual recalculado por workspace
  - nao sobrescrever `executability_score`
  - permitir futura personalizacao por perfil

- [x] Preparar query params futuros:
  - `sort=score`
  - `sort=executability`
  - `filter=operable`

- [x] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_api_routes.py backend\tests\test_workspace_tenancy.py -v`

**Commit suggestion:** `feat: support workspace projection with executability`

---

## Release D - Frontend Dual-Read E Explicabilidade Operacional

Status: concluida em 2026-04-17.

### Task 8: Tornar o frontend compativel com payload antigo e novo

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/hooks/use-opportunities.ts`
- Test: `frontend/tests/e2e/app.spec.ts`

- [x] Garantir leitura segura dos novos campos opcionais.

- [x] Preservar ordenacao atual por `score` quando `executability_score` ainda nao existir.

- [x] Adicionar testes e2e para ambos cenarios:
  - payload antigo
  - payload com executability

- [x] Verificacao:
  - Run: `npm --prefix frontend run build`
  - Run: `npm --prefix frontend run test`

**Commit suggestion:** `feat: support dual-read opportunities payload`

### Task 9: Melhorar a tabela de oportunidades para explicar operabilidade

**Files:**
- Modify: `frontend/src/components/opportunities-table.tsx`
- Modify: `frontend/src/components/signal-detail-modal.tsx`
- Modify: `frontend/src/app/page.tsx`
- Test: `frontend/tests/e2e/app.spec.ts`

- [x] Incluir badges e labels:
  - `Operavel`
  - `Interessante`
  - `Saida dificil`
  - `Slippage alto`
  - `Liquidez OK`

- [x] Incluir alternancia de ranking:
  - `Score tecnico`
  - `Operabilidade`

- [x] No detalhe do sinal, exibir:
  - liquidez BRL no top N
  - slippage estimado compra/venda
  - faixa de operabilidade

- [x] Garantir boa leitura no mobile.

- [x] Verificacao:
  - Run: `npm --prefix frontend run build`
  - Run: `npm --prefix frontend run test`

**Commit suggestion:** `feat: explain operability in opportunities UI`

---

## Release E - Workspace Trading Profile, Thresholds E Alertas

### Task 10: Introduzir trading profile por workspace

**Files:**
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/services/persistence.py`
- Modify: `backend/app/api/routes.py`
- Modify: `frontend/src/app/settings/page.tsx`
- Test: `backend/tests/test_api_routes.py`
- Test: `backend/tests/test_persistence.py`

- [ ] Adicionar em `AppConfig` ou configuracao derivada:
  - `trading_profile: Literal["conservador", "intraday_liquido", "agressivo", "scalp"]`
  - `order_notional_brl`
  - `max_entry_slippage_bps`
  - `max_exit_slippage_bps`
  - `min_quote_volume_brl`

- [ ] Implementar defaults seguros por perfil.

- [ ] Expor e salvar no endpoint de configuracao.

- [ ] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_api_routes.py backend\tests\test_persistence.py -v`
  - Run: `npm --prefix frontend run build`

**Commit suggestion:** `feat: add workspace trading profiles`

### Task 11: Aplicar thresholds por perfil ao scanner e aos alertas

**Files:**
- Modify: `backend/app/services/scanner.py`
- Modify: `backend/app/services/persistence.py`
- Modify: `backend/app/services/telegram.py`
- Test: `backend/tests/test_scanner.py`

- [ ] Usar `order_notional_brl` do perfil no calculo de slippage.

- [ ] Usar limites por perfil para `operable_signal`.

- [ ] Atualizar regras de alerta para aceitar:
  - apenas operaveis
  - operaveis por faixa de score
  - operaveis apenas de exchanges/pairs selecionados

- [ ] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_scanner.py backend\tests\test_persistence.py -v`

**Commit suggestion:** `feat: apply workspace profile thresholds to signals and alerts`

---

## Release F - Duracao Util E Taxonomia V2

### Task 12: Popular `duration_minutes` e `movement_persistence_score`

**Files:**
- Modify: `backend/app/services/shared_state.py`
- Modify: `backend/app/services/scanner.py`
- Modify: `backend/app/models/schemas.py`
- Test: `backend/tests/test_runtime_persistence.py`
- Test: `backend/tests/test_scanner.py`

- [ ] Derivar duracao a partir de repeticao em ciclos consecutivos e estabilidade minima.

- [ ] Persistir `movement_persistence_score`.

- [ ] Penalizar `operable_signal` quando a duracao util for muito curta.

- [ ] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_runtime_persistence.py backend\tests\test_scanner.py -v`

**Commit suggestion:** `feat: model useful movement duration`

### Task 13: Refinar taxonomia de movimentos

**Files:**
- Modify: `backend/app/filters/movement.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `frontend/src/components/opportunities-table.tsx`
- Test: `backend/tests/test_filters.py`

- [ ] Introduzir `movement_class_v2` ou `movement_regime` sem remover `movement_type`.

- [ ] Mapeamento inicial sugerido:
  - `trend_continuation`
  - `breakout_clean`
  - `breakout_exhaustion`
  - `mean_reversion_candidate`
  - `illiquid_spike`

- [ ] Continuar exibindo labels legadas enquanto o frontend nao migrar totalmente.

- [ ] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_filters.py backend\tests\test_scanner.py -v`
  - Run: `npm --prefix frontend run build`

**Commit suggestion:** `feat: add movement taxonomy v2`

---

## Release G - Reweighting Por Outcome E Analytics Operacionais

### Task 14: Criar agregados operacionais por bucket

**Files:**
- Modify: `backend/app/services/persistence.py`
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/test_persistence.py`
- Test: `backend/tests/test_signal_outcomes.py`

- [ ] Criar consultas agregadas por:
  - faixa de `score`
  - faixa de `executability_score`
  - exchange
  - par
  - tipo de movimento
  - perfil

- [ ] Expor endpoint interno ou administrativo para analytics de calibracao.

- [ ] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_persistence.py backend\tests\test_signal_outcomes.py -v`

**Commit suggestion:** `feat: add operational analytics aggregates`

### Task 15: Aplicar reweighting conservador por outcome

**Files:**
- Modify: `backend/app/services/persistence.py`
- Modify: `backend/app/services/scanner.py`
- Modify: `backend/app/models/schemas.py`
- Test: `backend/tests/test_signal_outcomes.py`
- Test: `backend/tests/test_scanner.py`

- [ ] Substituir `historical_confidence` por uma calibracao mais explicita, ou manter o nome mas recalcular com base em buckets reais.

- [ ] Limitar o multiplicador final para evitar dominancia excessiva:
  - piso sugerido: `0.90`
  - teto sugerido: `1.15`

- [ ] Persistir `reweighting_version`.

- [ ] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_signal_outcomes.py backend\tests\test_scanner.py -v`

**Commit suggestion:** `feat: reweight ranking using signal outcomes`

---

## Release H - Migracao Estrutural Do Historico

### Task 16: Preparar escrita dual para camadas separadas

**Files:**
- Modify: `backend/app/models/database.py`
- Modify: `backend/app/services/shared_state.py`
- Modify: `backend/app/services/persistence.py`
- Test: `backend/tests/test_runtime_persistence.py`
- Test: `backend/tests/test_persistence.py`

- [ ] Introduzir camadas mais explicitas:
  - `raw_market_observations`
  - `technical_signals`
  - `workspace_signal_projections`
  - `signal_outcomes`

- [ ] Habilitar dual-write durante fase de transicao.

- [ ] Nao desligar leituras antigas nesta release.

- [ ] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_runtime_persistence.py backend\tests\test_persistence.py -v`

**Commit suggestion:** `feat: add dual-write for separated signal lifecycle tables`

### Task 17: Revisar retencao, deduplicacao e leitura do historico

**Files:**
- Modify: `backend/app/services/persistence.py`
- Modify: `backend/app/api/routes.py`
- Modify: `frontend/src/app/history/page.tsx`
- Test: `backend/tests/test_persistence.py`

- [ ] Mudar deduplicacao para semantica de sinal, nao apenas janela fixa de 5 minutos.

- [ ] Definir retencao por camada:
  - feed operacional curto
  - historico analitico medio prazo
  - agregados longo prazo

- [ ] Migrar a tela de historico para a nova leitura quando os dados estiverem estaveis.

- [ ] Verificacao:
  - Run: `.\.venv\Scripts\python.exe -m pytest backend\tests\test_persistence.py -v`
  - Run: `npm --prefix frontend run build`

**Commit suggestion:** `feat: update history retention and semantic deduplication`

---

## Verification Matrix

### Backend smoke suite por release

- `.\.venv\Scripts\python.exe -m pytest backend\tests\test_filters.py -v`
- `.\.venv\Scripts\python.exe -m pytest backend\tests\test_scanner.py -v`
- `.\.venv\Scripts\python.exe -m pytest backend\tests\test_api_routes.py -v`
- `.\.venv\Scripts\python.exe -m pytest backend\tests\test_persistence.py -v`
- `.\.venv\Scripts\python.exe -m pytest backend\tests\test_signal_outcomes.py -v`

### Frontend verification

- `npm --prefix frontend run build`
- `npm --prefix frontend run test`

### Manual product checks after Releases C, D and E

- Login no frontend publicado
- Dashboard carrega sem erro com payload antigo
- Dashboard carrega sem erro com payload novo
- Ordenacao por score tecnico continua igual
- Ordenacao por operabilidade destaca sinais diferentes do score puro
- Configuracao de perfil muda thresholds e alertas

---

## Deployment Sequence

### Deploy 1

- Backend Release A
- Frontend dual-read basico
- Objetivo: preparar contrato sem alterar comportamento

### Deploy 2

- Backend Release B + C
- Objetivo: produzir campos reais de executabilidade

### Deploy 3

- Frontend Release D
- Objetivo: exibir operabilidade e razoes do sinal

### Deploy 4

- Backend/Frontend Release E
- Objetivo: personalizacao por workspace

### Deploy 5

- Backend Release F + G
- Objetivo: melhorar qualidade do ranking

### Deploy 6

- Backend/Frontend Release H
- Objetivo: consolidar modelo de historico e analytics

---

## Fastest Value Path

Se houver pressa e for preciso cortar escopo, executar apenas:

1. Release A
2. Release B
3. Release C
4. Release D

Esse recorte ja entrega:

- liquidez em notional
- slippage estimado
- executability score
- split entre interessante e operavel
- dashboard explicando operabilidade

Sem precisar tocar ainda na migracao estrutural mais sensivel do historico.

---

## Handoff Notes

- Nao substituir o `score` atual na primeira fase.
- Nao quebrar `Opportunity`, `HistoryRecord` ou a serializacao atual.
- Nao acoplar o calculo de slippage ao `Workspace Trading Profile` antes de existir fallback global.
- Nao iniciar a separacao estrutural de persistencia antes de Releases `A` a `E` estabilizarem.
- Toda nova metrica deve entrar com versao explicita para auditoria.
