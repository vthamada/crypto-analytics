# Post-Release Operationalization Plan

Data: 2026-04-18

Objetivo: estabilizar e validar em ambiente real o que foi entregue ate a Release H, transformar a camada operacional em rotina confiavel de uso e abrir a proxima fase do produto sem perder auditabilidade.

---

## Semana 1

### 1. Executar e validar a migration `0007`

- Rodar `alembic upgrade head` no ambiente alvo.
- Validar as novas tabelas e colunas:
  - `raw_market_observations`
  - `opportunities.reweighting_version`
  - `opportunities.semantic_signal_key`
  - `opportunities.baseline_order_notional_brl`
  - `opportunities.movement_regime`
- Rodar o verificador:

```bash
cd backend
python scripts/verify_operational_readiness.py
```

- Critérios de aceite:
  - sem erro de schema
  - tabelas novas acessiveis
  - dados recentes aparecendo em `raw_market_observations`
  - cobertura minima dos novos campos operacionais nas oportunidades recentes

### 2. Validar comportamento real do `trading_profile`

- Testar pelo menos 2 perfis por workspace:
  - `conservador`
  - `intraday_liquido`
- Verificar se:
  - muda o conjunto de sinais `operable`
  - muda o score operacional final
  - muda o volume de alertas Telegram

### 3. Revisar deduplicacao semantica

- Medir se a nova chave semantica esta:
  - removendo spam de sinais repetidos
  - sem esconder mudancas legitimas de regime/movimento

---

## Semana 2

### 4. Ajuste fino de reweighting por outcome

- Avaliar buckets por:
  - `pair`
  - `exchange`
  - `movement_type`
  - `movement_regime`
- Revisar piso e teto do multiplicador (`0.90` a `1.15`) com dados reais.

### 5. Expandir analytics operacionais no frontend

- Exibir melhor:
  - distribuicao por `movement_regime`
  - score tecnico vs executabilidade
  - impacto do perfil operacional
  - volume de sinais `interesting` vs `operable`

### 6. Fechar runbook operacional

- Consolidar o fluxo:
  - deploy
  - migration
  - verificacao
  - rollback
  - smoke test

---

## Proxima Fase De Produto

Quando a camada operacional estiver estavel:

1. Paper trading
2. Confirmacao manual de execucao
3. Automacao parcial
4. Feature gates / planos

---

## Ordem Recomendada

1. migration `0007` + readiness check
2. validacao real de perfis/alertas
3. calibracao de reweighting
4. analytics operacionais mais completos
5. paper trading
