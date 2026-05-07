# Backlog

Ultima revisao: 2026-05-07

Legenda: `[x]` concluido · `[ ]` pendente · `[~]` parcialmente feito

---

## Decisoes tomadas

| Decisao | Escolha |
|---|---|
| Registro de usuarios | Autoregistro por convite (beta) → autoregistro aberto + Free tier (SaaS publico) |
| Scanner | Global com recalculo por workspace na leitura — 1 scan serve todos sem multiplicar chamadas as exchanges |
| Trading | Sequencial: Monitoramento → Paper trading → Manual confirmado → Automatico |
| Exchange prioritaria | **Mercado Bitcoin + NovaDAX** como nucleo BRL inicial; Binance fica provider complementar, opcional e desativado por padrao |
| Unidade de cobranca (SaaS) | `Organization` — e a conta que paga; `Workspace` e subdivisao operacional dentro dela |
| Modelo de planos | Free / Pro / Trading / Enterprise (ver tabela em P3) |

---

## Arquitetura alvo

```
Organization  ← unidade de cobranca (tem plano, Stripe customer)
  ├── Plan: free | pro | trading | enterprise
  ├── Members: usuario A (owner), usuario B (admin), ...
  ├── Workspace "Scalping"
  │     └── Config: thresholds proprios, pares, pesos de score, Telegram
  └── Workspace "Swing Trade"
        └── Config: thresholds diferentes
```

---

## Concluido (historico)

### Plano de executabilidade operacional
- [x] Refinamento final 2026-05 - fase do movimento, faixa operacional reaproveitavel, ranking comparativo por ciclo, outcomes 24h/enriquecidos e feedback manual de sinais
- [x] Release I parcial - scanner em dois estagios com triagem leve, temperatura/cooldown em memoria, telemetria agregada em health, dashboard consumindo payload resumido, detalhe sob demanda e catalogo observavel por provider
- [x] Auditoria P0 do funil de sinais - eventos compactos por ciclo/par, resumo persistente do scanner e endpoint de diagnostico de sinal perdido
- [x] UI inicial de auditoria operacional - busca de sinal perdido na tela de configuracoes com timeline do funil e resumo por ciclo
- [x] Refinamento de escopo BRL 2026-05 - Binance desativada por padrao, Mercado Bitcoin/NovaDAX como nucleo, catalogo com providers desativados isolados e ativacao manual por workspace
- [x] Especificacao BRL 2026-05 - margem operacional, classificacao `trade/hold/observe/avoid`, descoberta ampla BRL, resumo de historico e reducao de egress do dashboard/analytics
- [x] Release E â€” trading profile por workspace, thresholds operacionais e filtros de alerta
- [x] Release F â€” `duration_minutes`, `movement_persistence_score` e taxonomia `movement_regime`
- [x] Release G â€” reweighting conservador por outcome e analytics operacionais por bucket
- [x] Release H â€” dual-write com `raw_market_observations` e deduplicacao semantica do historico

### Seguranca e acesso
- [x] Proteger `/api/config` com autenticacao e autorizacao
- [x] Impedir leitura de segredos no frontend e no endpoint de configuracao
- [x] Restringir CORS no backend para dominios confiaveis
- [x] Senha admin com hash (PBKDF2-SHA256), token assinado com `token_version`
- [x] Revocacao automatica de tokens ao trocar senha

### Qualidade e estabilidade
- [x] Testes unitarios para filtros e score
- [x] Testes de integracao para rotas principais do backend
- [x] Mocks/fakes para providers de exchange nos testes
- [x] Tratar erros e rate limit nos providers
- [x] Deduplicacao de oportunidades no banco (janela de 5 min por par+exchange)
- [x] Logs estruturados do scanner e dos providers

### Funcionalidades
- [x] Comparacao cross-exchange e deteccao de arbitragem simples
- [x] Score com calibracao baseada em historico (`historical_confidence`)
- [x] Analytics filtrados pelo mesmo periodo do historico
- [x] Filtros avancados no dashboard e historico

### Multi-tenant (base)
- [x] Tabelas `users`, `workspaces`, `workspace_memberships`, `workspace_configs`
- [x] Login com credenciais, access token assinado e refresh token
- [x] Seletor de workspace no frontend
- [x] Configuracao administrativa e auditoria isoladas por workspace

### Infra e operacao
- [x] Migracoes com Alembic (3 migrations: baseline, admin_auth, workspace)
- [x] Pipeline CI no GitHub Actions (lint, build, testes)
- [x] Health check expandido com metricas de scanner e providers
- [x] Integracao opcional com Sentry via `SENTRY_DSN`
- [x] `.env.example` completo na raiz
- [x] `ARCHITECTURE.md`, `HANDOFF.md`, `CHANGELOG.md`, `DEPLOY.md`
- [x] Fonte Inter no frontend, dark mode, traducoes PT-BR
- [x] Grafico horizontal corrigido para dark mode
- [x] Cooldown configuravel para alertas Telegram

---

## P0 — Bloqueia o uso com duas ou mais pessoas

- [x] **Criar usuarios pelo admin** — endpoint `POST /api/users` (admin cria contas com usuario+senha temporaria) e tela "Usuarios" no frontend para listar, criar e desativar contas. Sem isso o pai nao tem conta propria.

- [x] **Refresh token** — sessao atual expira em 8h sem renovacao silenciosa. Implementar refresh token de 30 dias: o access token (8h) e renovado automaticamente enquanto o refresh token for valido. Usuario so ve tela de login apos 30 dias de inatividade.

- [x] **Redefinicao de senha** — se alguem esquecer a senha o unico caminho e alterar as vars de ambiente e reiniciar o servidor. Fluxo de reset gerado pelo admin agora emite credencial temporaria e obriga troca no primeiro login.

---

## P1 — Bloqueia crescimento para mais usuarios

- [x] **Autoregistro por convite**
  Admin gera link com codigo unico e prazo de validade (ex: 7 dias, uso unico).
  Usuario abre o link, preenche email + senha — conta criada sem admin precisar estar online.
  Fundacao para autoregistro aberto do SaaS: so troca o guard de "codigo valido" por "email verificado".

- [x] **Entidade Organization (fundacao do SaaS)**
  Criar `Organization` como unidade de cobranca acima dos workspaces atuais.
  `User` pertence a uma `Organization`; `Workspace` e subdivisao dela.
  Campos: `plan`, `stripe_customer_id`, `subscription_status`, `trial_ends_at`.
  Implementar agora evita refatoracao maior quando o SaaS for lancado.

- [x] **Pares dinamicos por exchange** — catalogo e UI usam descoberta via `get_available_pairs()` com cache no backend de 1h. Novos workspaces recebem selecao inicial derivada do catalogo, e o scanner cruza `enabled_pairs` com a disponibilidade real por exchange antes de consultar os providers:
  ```
  BTC/BRL   [NovaDAX ✓] [Mercado BTC ✓] [Binance ✓]
  PEPE/BRL  [NovaDAX ✗] [Mercado BTC ✗] [Binance ✓]
  ```
  Endpoint `GET /api/pairs/available`. Resolve o problema de pares renomeados (ex: MATIC→POL).

- [x] **Mobile responsivo** — tabela do dashboard tem 10 colunas, quebra em celular. Implementada visao em cards para telas pequenas (`sm:`) mantendo a tabela completa no desktop.

- [x] **Onboarding de novos usuarios** — quando uma pessoa entra pela primeira vez nao ha nenhuma orientacao. Implementada checklist inicial no dashboard com conclusao persistida por usuario.

- [x] **Scanner hot-reload de configuracao** — mudar exchanges/pares habilitados na UI agora sinaliza wake-up imediato do scanner sem reiniciar o servidor.

- [x] **Teste de Telegram na UI** — botao "Enviar mensagem de teste" nas Configuracoes dispara uma mensagem real para o bot configurado, usando os valores digitados ou as credenciais persistidas do workspace.

- [x] **Validacao de API keys das exchanges** — apos salvar chaves de API, o sistema valida acesso real e mostra status por exchange: ausente, valida, invalida, sem permissao de trade ou erro.

---

## P2 — Qualidade, confiabilidade e robustez do motor

- [~] **Politica de retencao do historico** — existe configuracao e funcao de limpeza (`HISTORY_RETENTION_DAYS`, `HISTORY_RETENTION_CHECK_MINUTES`), mas a execucao periodica precisa ser validada no fluxo real do worker/API e expandida para todas as camadas historicas antes de ser considerada concluida.

- [x] **Testes E2E do frontend** — Playwright cobre login administrativo, troca de workspace com configuracao isolada, dashboard em tempo real e falha de historico com feedback visual.

- [x] **Testes de workspace e membership no backend** — cobertura agora valida isolamento de config por tenant, membership por workspace e projecao de score recalculada por workspace.

- [x] **Tratamento de erros no frontend** — app ganhou `error.tsx`, `global-error.tsx`, toaster global para falhas de API/WebSocket/runtime e estados inline de erro no dashboard e historico.

### Backlog tecnico derivado do plano de refatoracao

- [x] **Congelar contratos operacionais atuais**
  Adicionar testes de integracao cobrindo os contratos observados hoje em `/api/dashboard/stats`, `/api/opportunities`, `/api/history`, `/api/analytics`, `/api/health` e `/ws`, incluindo carga inicial do dashboard, filtro de workspace no historico e recebimento de `opportunities_update` no WebSocket.
  *Sem isso, o desacoplamento do scanner vira regressao dificil de detectar.*

- [x] **Criar contrato compartilhado do estado corrente entre worker e API**
  Extrair `scan_once()` / `scan_loop()` para servico reutilizavel e criar base para a API operar sem scanner local obrigatorio.
  Entregas minimas:
  - `scanner_runtime_state` para ultimo ciclo, falha, duracao e ultimo sucesso
  - `current_opportunity_snapshots` ou store equivalente para o snapshot atual das oportunidades
  - fallback temporario da API para manter compatibilidade enquanto o contrato amadurece

- [x] **Desacoplar scanner da API sem quebrar dashboard e tempo real**
  Tornar o worker o produtor principal do scan, mantendo a API como camada de leitura, autenticacao, configuracao e streaming.
  Criterio de aceite:
  - API sobe sem rodar scanner interno
  - dashboard continua funcional
  - WebSocket continua entregando atualizacoes com base no estado compartilhado

- [x] **Neutralizar o score tecnico e versionar o motor**
  Introduzir `technical_score` e `score_version`, removendo a dependencia atual de `weights=configs[0].weights` no motor global.
  `workspace_score` continua existindo como derivacao posterior por workspace.
  *Nao criar UI de configuracao global do motor nesta fase; pesos tecnicos devem ser controlados por release/versionamento.*

- [x] **Dar identidade semantica ao sinal tecnico**
  Criar `technical_signals` e iniciar dual-write com a tabela `opportunities`, registrando `technical_signal_id`, `technical_score`, componentes do score, `score_version`, fator historico e contexto cross-exchange.
  *Pre-requisito para explicabilidade mais forte e qualquer outcome tracking futuro.*

- [x] **Estabilizar a semantica de repeticao fora da memoria efemera**
  Parar de depender apenas de `_repetition_counts` em memoria do processo. A repeticao deve vir de janela recente persistida ou cache compartilhado para o score ser reproduzivel entre reinicios.

- [x] **Materializar projecoes por workspace quando houver ganho real**
  Criar `workspace_signal_projections` para auditoria, analytics de produto e explicabilidade por workspace quando isso passar a ser requisito operacional claro.
  Campos minimos: `workspace_id`, `technical_signal_id`, `workspace_score`, `visible`, `alert_eligible`, `projection_reason`, `created_at`.

- [x] **Criar outcome tracking apenas depois da identidade do sinal ficar estavel**
  Criar `signal_outcomes` e jobs de avaliacao temporal somente depois que `technical_signal_id` estiver confiavel.
  *Nao antecipar esta fase antes da nova semantica de sinal existir de forma duravel.*

- [x] **Tornar a politica de Telegram configuravel por workspace**
  Evoluir do corte fixo `score >= 60` para threshold configuravel, tipos de alerta, cooldown por politica e auditoria de alteracoes.

- [x] **Evoluir observabilidade antes de adotar barramento distribuido**
  Separar health de API e worker, medir oportunidades projetadas por workspace, alertas enviados/suprimidos e decidir Redis/NATS/event bus apenas quando houver evidencia concreta de necessidade de multiplas instancias ou gargalo do contrato compartilhado.

### Nao priorizar antes da base acima

- [ ] **`raw_market_events` como fundacao obrigatoria**
  So considerar depois de medir throughput real, custo, valor analitico e politica de TTL/compactacao.

- [ ] **`execution_score` / slippage / depth como P0**
  So avancar depois que outcome tracking existir; antes disso a camada ainda e hipotese de produto.

---

## P3 — Plataforma SaaS e multi-tenant madura

- [ ] **Feature gates por plano**
  Middleware que verifica `organization.plan` antes de servir cada feature.
  Retorna `402 Payment Required` com mensagem clara quando limite e atingido.
  Ex: workspace adicional bloqueado no Free; Telegram bloqueado no Free; paper trading so no Trading+.

- [ ] **Stripe integration (cobranca)**
  Tres eventos criticos a reagir:
  - `checkout.session.completed` → ativa o plano
  - `invoice.payment_failed` → aviso, bloqueia apos grace period
  - `customer.subscription.deleted` → downgrade para Free
  Self-service billing portal (Stripe fornece pagina pronta — so redirecionar).

- [ ] **Planos e limites**
  | | Free | Pro (~R$49/mes) | Trading (~R$149/mes) | Enterprise (~R$499/mes) |
  |---|---|---|---|---|
  | Pares | 3 | Ilimitado | Ilimitado | Ilimitado |
  | Exchanges | 1 | 3 | 3 | 3 |
  | Telegram | Nao | Sim | Sim | Sim |
  | Historico | 7 dias | 90 dias | 180 dias | 1 ano |
  | Paper trading | Nao | Nao | Sim | Sim |
  | Execucao manual | Nao | Nao | Sim | Sim |
  | Execucao automatica | Nao | Nao | Nao | Sim |
  | Membros por org | 1 | 2 | 3 | 10 |
  | Trial gratuito | 14 dias | — | — | — |

- [ ] **Autoregistro aberto com Free tier**
  Remover guard de convite, adicionar verificacao de email.
  Free tier com limites automaticamente aplicados.
  Stripe Checkout para upgrade de plano.

- [x] **Modelo de permissoes por workspace**
  Rotas e UI agora usam a membership do workspace ativo, em vez do papel global do usuario.
  Roles `owner`, `admin`, `member`:
  - `member`: visualiza dashboard e historico
  - `admin`: configura thresholds, pares, Telegram e auditoria
  - `owner`: + gerencia membros e convites do workspace

- [x] **Scanner dedicado por worker**
  `backend/app/worker.py` agora integra o contrato compartilhado completo: `scanner_runtime_state`, `opportunity_snapshots`, `technical_signals`, `workspace_signal_projections`, `signal_outcomes`, repeticao persistente e threshold Telegram configuravel. A API pode servir dashboard e WebSocket sem scanner local, lendo do estado compartilhado.
  Obrigatorio antes de ter dezenas de tenants ativos.

- [x] **Notificacoes por workspace**
  O dispatch agora projeta oportunidades por workspace e envia alertas usando o bot/chat configurado naquele workspace, sem depender do token/chat mesclado global.

- [x] **Isolamento do tempo real e leituras publicas**
  Leituras operacionais agora exigem sessao autenticada, e o WebSocket autentica a conexao e publica somente para o workspace ativo.

- [x] **Auditoria no frontend**
  Pagina de configuracoes exibe auditoria recente do workspace ativo para administradores.

- [ ] **Deploy de producao endurecido**
  Postgres como padrao, rotacao de segredos, HTTPS obrigatorio, `cors_allowed_origins` configurado,
  health check conectado a monitoramento externo.

---

## P4 — Fundacao para trading (Binance prioritaria)

> Implementar apos o produto de monitoramento estar validado com usuarios reais e receita recorrente estabelecida. Cada fase valida a anterior antes de arriscar capital real.

- [ ] **Governanca de historico para trading**
  Definir e implementar politica por camada antes de usar historico para decisoes automatizadas:
  - `raw_market_observations`: retencao curta/media, usada para auditoria tecnica e debug
  - `opportunities`: feed operacional legado com retencao controlada
  - `technical_signals`: sinais versionados mantidos por mais tempo para calibracao
  - `workspace_signal_projections`: trilha de como cada workspace viu o sinal
  - `signal_outcomes`: base de aprendizado e avaliacao de edge
  - futuros `decisions` e `executions`: obrigatorios antes de paper trading avancado, manual confirmado ou automatico
  Criterio de aceite: rotina ativa de pruning/compactacao por camada, queries do historico rapidas e agregados de calibracao preservados.

- [ ] **Metadados de trading por par (Binance)**
  Enriquecer cache de pares com: tamanho minimo de ordem, precisao de preco (step size), status de trading.
  Pre-requisito para qualquer execucao sem erros da exchange.

- [ ] **Busca de saldo por exchange**
  Quando API keys estao configuradas, exibir saldo disponivel.
  Pre-requisito para calcular tamanho de posicao.

- [ ] **Paper trading — Fase 1 do trading**
  Simula entradas e saidas com base nos sinais detectados, sem dinheiro real.
  Entidade `SimulatedTrade`: par, exchange, preco de entrada, preco de saida, resultado %.
  Dashboard de performance: win rate, retorno medio, drawdown maximo.
  Deve consumir sinais/outcomes versionados e registrar uma decisao simulada antes de criar a posicao simulada.
  Validacao obrigatoria antes de colocar capital real. Disponivel no plano Trading.

- [ ] **Execucao manual confirmada — Fase 2 do trading**
  Sinal detectado → alerta Telegram com botao "Executar".
  Usuario confirma → ordem executada via API privada da Binance.
  Log imutavel de todas as ordens.
  Exige entidade de decisao e entidade de execucao separadas do historico de sinais.
  Disponivel no plano Trading.

- [ ] **Gestao de posicoes**
  Entidade `Position`: par, exchange, preco de entrada, quantidade, stop-loss, target, status.
  Historico de posicoes fechadas com resultado em BRL e percentual.

- [ ] **Gestao de risco (obrigatoria antes do automatico)**
  Regras por workspace:
  - Exposicao maxima por exchange (ex: max 30% do capital na Binance)
  - Exposicao maxima por par (ex: max 10% em DOGE)
  - Stop global diario (ex: parar se perda > 2% no dia)
  - Tamanho de posicao por faixa de score (score 80+ = 2x tamanho padrao)

- [ ] **Motor de execucao automatica — Fase 3 do trading**
  Pipeline: sinal → verificacao de risco → calculo de tamanho → ordem → monitoramento → saida.
  Circuit breaker: parar se perda acumulada > limite configurado.
  Nunca deve operar diretamente a partir de `opportunities`; deve consumir sinal versionado, perfil do workspace, decisao auditada, regras de risco e estado de posicao.
  Disponivel no plano Enterprise.

- [ ] **Portfolio e P&L**
  Visao consolidada de posicoes abertas e trades fechados.
  Resultado em BRL e percentual por exchange e por par.

---

## Proximos passos (ordem de implementacao)

1. ~~**P2 residual** — Job de avaliacao de `signal_outcomes`~~ ✅ Concluido
  *`outcome_evaluator.py` preenche `price_after_5m/15m/1h/4h` e `outcome_pct` a cada ciclo de scan.*

2. ~~**P2 residual** — Separar API e worker no `docker-compose.yml`~~ ✅ Concluido
  *`SCANNER_ENABLED=false` no backend, worker como servico separado. `docker-compose.yml` atualizado.*

3. **P3** — Feature gates por plano + Stripe
  *Liga monetizacao em cima da arquitetura de Organization ja implantada*

4. **P3** — Autoregistro aberto com Free tier
  *Abre a entrada self-service do produto sem depender de convite manual para o plano inicial*

5. **P3** — Deploy de producao endurecido
  *Fecha os requisitos operacionais minimos antes de tratar o ambiente como producao real*

6. **P4** — Paper trading → execucao manual → automatica (nao pula fases)

---

## Roadmap incremental de robustez dos sinais

Executar somente depois da base P2/P3 estar estavel e com dados reais suficientes para calibracao.

- [ ] **Nivel 1 — Indicadores tecnicos classicos**
  Adicionar RSI, Bollinger Bands, EMA crossover, MACD e OBV ao motor tecnico versionado. Cada mudanca entra com novo `score_version`, sem liberar ajuste arbitrario de pesos por UI nesta fase.

- [ ] **Nivel 2 — Confirmacao multi-timeframe**
  Cruzar 5m com timeframes maiores e exigir confluencia minima antes de publicar ou alertar um sinal com score alto.

- [ ] **Nivel 3 — Mean reversion com z-score**
  Criar leitura de desvio da media para pares em range, reduzindo falso positivo de continuidade quando o mercado esta lateral.

- [ ] **Nivel 4 — Filtro de regime com ADX**
  Detectar se o mercado esta lateral ou tendencial para alternar regras de momentum e reversao no motor tecnico.

- [ ] **Nivel 5 — Modelo supervisionado com outcomes**
  Treinar modelo apenas depois de 4-8 semanas de `signal_outcomes` confiaveis, usando features tecnicas e rotulo de outcome para refinar o ranking final.

---

## Backlog tecnico de evolucao operacional (2026-04-17)

Objetivo: evoluir o produto de `scanner heuristico de atencao` para `assistente operacional util`, preservando a base atual de coleta, filtros minimos, score tecnico inicial, persistencia e outcomes, e adicionando uma camada explicita de executabilidade.

### Progresso de execucao do plano operacional

- [x] **Release A** — contratos aditivos, leitura dual, campos opcionais de executabilidade e versionamento explicito do motor.
- [x] **Release B** — liquidez em notional, estimativa de slippage por tamanho de ordem e `fillable_notional_within_slippage_cap`.
- [x] **Release C** — `executability_score`, `executability_band`, split entre `interesting_signal` e `operable_signal`, alem de ordenacao e filtro operacional na API.
- [x] **Release D** — explicabilidade operacional, dual-read seguro e consumo visual da nova camada no frontend.
- [x] **Release E** — perfil operacional por workspace, thresholds de executabilidade, alertas operaveis e UI de configuracao correspondente.
- [ ] **Release F+** — duracao util, taxonomia refinada, reweighting por outcome e evolucao estrutural do historico.

### Bloco 1 - Evolucao da logica de sinais

| Nome da iniciativa | Problema que resolve | Descricao da implementacao | Impacto esperado | Dependencias | Complexidade estimada | Prioridade | Criterios de aceite | Risco de implementacao | Observacoes tecnicas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Liquidez em notional por lado do book | `liquidity_units` distorce ativos baratos e caros e nao representa capacidade financeira real de entrada/saida | Substituir a metrica atual por `bid_notional_top_n`, `ask_notional_top_n`, `total_notional_top_n` e `depth_ratio_by_distance` usando `preco * quantidade` no top N do order book; manter `liquidity_units` apenas para compatibilidade/transicao | Melhora imediata na filtragem de moedas ruins e reduz falso positivo em ativos baratos com book raso | Dados atuais de order book; ajuste em `filters/liquidity.py`, `scanner.py`, schemas e API | Media | P0 | Nova metrica aparece no payload da oportunidade; ranking muda em cenarios onde quantidade era alta mas notional era baixo; testes cobrem moedas baratas vs caras | Medio | Pode ser introduzido sem breaking change se os novos campos forem aditivos e o score antigo seguir funcionando durante transicao |
| Slippage estimado por tamanho de ordem | O sistema nao sabe se o book aguenta uma ordem real sem deterioracao relevante de preco | Calcular `estimated_buy_slippage_bps` e `estimated_sell_slippage_bps` simulando consumo progressivo do book para tamanhos de ordem configuraveis em BRL (`250`, `1000`, `5000`, por perfil); expor tambem `fillable_notional_within_slippage_cap` | Separa sinal bonito de sinal realmente executavel e reduz risco de ficar preso | Liquidez em notional; definicao de tamanhos padrao por workspace/perfil | Media | P0 | API retorna slippage estimado por sinal; sinais com spread baixo mas slippage alto deixam de rankear no topo; testes reproduzem books rasos e profundos | Medio/Alto | O modelo inicial pode usar book estatico com tolerancia documentada; nao precisa modelar latencia nem impacto dinamico na primeira fase |
| Score de executabilidade | O score atual mede interesse tecnico, nao operabilidade real | Criar `executability_score` separado do `technical_score`, combinando notional depth, slippage, spread, assimetria bid/ask, volume e facilidade de saida; expor tambem `executability_band` (`poor`, `fair`, `good`, `strong`) | Passa a rankear pelo que o operador consegue executar, nao so pelo que chama atencao | Liquidez em notional e slippage estimado | Media | P0 | Toda oportunidade passa a ter `technical_score` e `executability_score`; frontend consegue ordenar por ambos; documentacao explica diferenca entre os dois | Medio | Recomendado manter o score tecnico intacto e adicionar o novo score em paralelo para evitar quebrar comparabilidade historica |
| Split entre `interesting_signal` e `operable_signal` | Hoje tudo aparece como oportunidade no mesmo plano, misturando curiosidade de mercado e oportunidade real | Adicionar classificacao booleana/enum separando `interesting_signal` e `operable_signal`, com regras iniciais baseadas em executability score, spread maximo efetivo, slippage cap e volume minimo por perfil | Reduz ruido no dashboard e no Telegram e economiza tempo do operador | Score de executabilidade; ajustes de API e UI | Baixa/Media | P0 | Dashboard e alertas conseguem filtrar/exibir separadamente sinais interessantes e sinais operaveis; testes de contrato da API cobrem os novos campos | Baixo | Pode nascer como classificacao derivada sem schema novo permanente; depois pode virar entidade mais explicita se fizer sentido |
| Duracao util do movimento | O sistema detecta o movimento, mas nao mede se ele tem janela operacional suficiente | Preencher `duration_minutes` com uma heuristica real baseada em persistencia do movimento, repeticao em ciclos consecutivos, estabilidade do spread e manutencao de liquidez por uma janela curta; complementar com `movement_persistence_score` | Ajuda a distinguir impulso morto de oportunidade com continuidade minima | Dados de ciclos atuais; `shared_state.py`; outcome pipeline | Media | P1 | `duration_minutes` deixa de ser `0` na maioria dos sinais validos; sinais com continuidade curta sao penalizados; testes cobrem persistencia em ciclos consecutivos | Medio | Pode ser iniciado sem mudar schema se reaproveitar `duration_minutes`; o refinamento posterior pode exigir tabela agregada por janela |
| Refinamento da taxonomia de movimentos | `strong_range/spike/weak/trap` ainda e util, mas generico demais para decisao operacional | Expandir a taxonomia para categorias mais operacionais, como `trend_continuation`, `breakout_clean`, `breakout_exhaustion`, `mean_reversion_candidate`, `illiquid_spike`, preservando mapeamento backward-compatible para as labels atuais | Melhora leitura rapida e qualidade dos filtros por tipo de movimento | Duracao util; ajustes em `filters/movement.py` e frontend | Media | P1 | Taxonomia nova existe no backend com mapeamento para categorias legadas; frontend consegue exibir nova label sem quebrar historico | Medio | Recomenda-se manter campo legado `movement_type` e adicionar `movement_regime` ou `movement_class_v2` para migracao gradual |
| Reweighting por outcome | `historical_confidence` atual e fraco e usa pouco do resultado real dos sinais | Criar recalibracao por desempenho historico de buckets de score, tipo de movimento, exchange, par e perfil, usando `signal_outcomes` confiaveis para ajustar o ranking final com limites conservadores | Melhora progressiva da qualidade do ranking e aproxima o motor de evidencia real | Outcome pipeline confiavel; agregacoes historicas; schema para versao do motor | Media/Alta | P1 | Ranking mostra impacto do reweighting sem causar oscilacoes extremas; ha relatorio de calibracao por bucket; testes garantem limites min/max do multiplicador | Alto | Deve entrar com versionamento explicito (`ranking_version`, `reweighting_version`) para auditoria e rollback |

### Bloco 2 - Persistencia, historico e analytics

| Nome da iniciativa | Problema que resolve | Descricao da implementacao | Impacto esperado | Dependencias | Complexidade estimada | Prioridade | Criterios de aceite | Risco de implementacao | Observacoes tecnicas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Separacao entre evento bruto, sinal, projecao e outcome | O modelo atual funciona, mas ainda mistura camadas de observacao e decisao, o que limita analytics e experimentacao | Introduzir camadas mais explicitas: `raw_market_observations`, `technical_signals`, `workspace_signal_projections`, `signal_outcomes`, com chaves de correlacao e timestamps de ciclo; manter escrita dual temporaria com o modelo atual | Facilita auditoria, reprocessamento, comparacao de motores e experimentacao futura | Revisao de schema; migracao incremental; adaptacoes em persistence/shared_state | Alta | P1 | Cada camada passa a ter responsabilidade clara; e possivel rastrear um sinal desde o book observado ate o outcome; jobs e API continuam funcionando durante migracao | Alto | Migracao sensivel; ideal usar dual-write, backfill e feature flag antes de desligar leituras antigas |
| Historico orientado a analytics operacionais | O historico atual serve ao feed, mas ainda e fraco para responder “o que realmente funciona?” | Criar visoes ou tabelas agregadas por bucket de score, faixa de slippage, exchange, par, movimento e perfil, com metricas de win rate, mediana de outcome e degradacao de executabilidade | Permite avaliar edge de verdade e sustenta calibracao do ranking | Outcomes estaveis; separacao de camadas ou visoes derivadas | Media | P1 | Dashboard interno/endpoint de analytics responde queries por bucket sem consultas pesadas nas tabelas operacionais | Medio | Pode começar com materialized views ou jobs periodicos, sem reestruturar tudo de uma vez |
| Auditoria de versao do motor de sinais | Sem versao explicita, fica dificil comparar score antigo vs novo e explicar regressao/melhoria | Persistir `score_version`, `executability_version`, `movement_version`, `profile_version` e parametros relevantes junto de cada sinal/projecao | Viabiliza experimentacao segura e comparacao entre iteracoes do motor | Ajustes de schema e pontos de persistencia | Baixa/Media | P0 | Todo sinal novo grava versoes do motor; API exibe esses campos quando solicitado; comparacoes historicas tornam-se possiveis | Baixo | Entrega valor cedo e reduz risco de evolucao silenciosa do ranking |
| Politica de retencao e compactacao do historico | O volume de registros tende a crescer e pode pesar sem governanca clara | Definir retencao por camada: feed operacional curto, sinais/outcomes medio prazo, agregados longo prazo; implementar rotinas de pruning/compactacao e documentar limites | Controla custo e performance sem perder capacidade analitica | Separacao de camadas; revisao de queries do historico | Media | P1 | Existe politica explicita de retencao; jobs removem ou agregam dados antigos sem degradar telas principais | Medio | A deduplicacao atual ajuda o feed, mas nao substitui uma politica clara de retencao por tipo de dado |
| Deduplificacao orientada a semantica do sinal | A deduplicacao atual por 5 minutos pode tanto reduzir ruido quanto esconder evolucao real do sinal | Revisar a deduplicacao para considerar mudancas materiais de score, slippage, spread e regime do movimento antes de suprimir uma nova linha | Mantem historico mais util para analytics sem virar spam de registros | Liquidez/slippage/score novos; revisao de persistence | Media | P1 | Dois sinais proximos no tempo so sao deduplicados se forem semanticamente equivalentes; testes cobrem casos de score igual vs score materialmente diferente | Medio | Mudanca sensivel porque altera densidade do historico; ideal ativar por feature flag e medir impacto |

### Bloco 3 - Personalizacao e experiencia operacional

| Nome da iniciativa | Problema que resolve | Descricao da implementacao | Impacto esperado | Dependencias | Complexidade estimada | Prioridade | Criterios de aceite | Risco de implementacao | Observacoes tecnicas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Workspace Trading Profile | O sistema ainda e generico demais e nao reflete o “olho” operacional do usuario final | Criar perfis por workspace como `conservador`, `intraday liquido`, `agressivo`, `scalp`, com parametros de tamanho de ordem, slippage maximo, spread tolerado, volume minimo, preferencia por duracao e sensibilidade a spike | Alinha o motor ao uso real do operador e reduz ruido de ativos ruins | Score de executabilidade; schema de configuracao; UI de settings | Media | P1 | Cada workspace consegue selecionar perfil; ranking e alertas mudam conforme o perfil; API retorna perfil ativo nas oportunidades projetadas | Medio | Prioridade elevada por diretriz de produto; deve ser P1, nao P2 |
| Thresholds por perfil operacional | Thresholds fixos atuais servem como base, mas nao como representacao do operador real | Derivar thresholds minimos e pesos de executabilidade a partir do trading profile, mantendo defaults seguros e override manual limitado | Melhora aderencia sem transformar a UI em painel de ajuste arbitrario | Workspace Trading Profile; score de executabilidade | Media | P1 | Alterar o perfil muda os thresholds efetivos do workspace; configuracao continua auditavel e previsivel | Medio | Melhor usar presets com poucos overrides do que liberar pesos totalmente livres logo de inicio |
| Alertas orientados a operabilidade | Alertas atuais podem disparar sinais interessantes, mas nao necessariamente executaveis | Adicionar filtros de alerta por `operable_signal`, banda de executabilidade, par favorito, exchange e tamanho de ordem suportado | Aumenta utilidade do Telegram e reduz fadiga de notificacao | Split interesting/operable; profile; ajustes de config UI | Baixa/Media | P1 | Usuario consegue receber apenas sinais operaveis dentro do seu perfil; mensagem do alerta explica por que o sinal foi enviado | Baixo | Alto valor perceptivel com pouco risco, desde que a camada de executabilidade esteja minimamente pronta |
| Dashboard com explicabilidade operacional | O frontend atual ainda mostra score e filtros, mas nao deixa claro “por que isso vale atencao” ou “por que nao e operavel” | Mostrar badges e razoes de operabilidade: `liquidez BRL`, `slippage estimado`, `saida dificil`, `duracao curta`, `operavel para R$ X`; incluir alternancia entre “interessantes” e “operaveis” | Reduz tempo perdido lendo ativo ruim e melhora confianca do operador | Score de executabilidade; API com campos novos; ajustes em `opportunities-table.tsx` | Media | P1 | No dashboard mobile/desktop o usuario consegue entender rapidamente por que um sinal e ou nao operavel; testes e2e cobrem a nova UX | Baixo/Medio | Gera valor rapido quando combinado com P0; nao depende da separacao completa do historico |

### Bloco 4 - Melhorias estruturais de suporte

| Nome da iniciativa | Problema que resolve | Descricao da implementacao | Impacto esperado | Dependencias | Complexidade estimada | Prioridade | Criterios de aceite | Risco de implementacao | Observacoes tecnicas |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Evolucao de schema e contratos de API sem quebra | As mudancas de score e executabilidade vao ampliar bastante o payload das oportunidades | Adicionar campos novos de forma aditiva em schemas, rotas e clientes (`technical_score`, `executability_score`, `operable_signal`, `slippage`, `notional_depth`, versoes do motor), preservando os campos atuais durante uma fase de transicao | Permite entregar valor sem quebrar frontend, worker ou historico existente | Iniciativas P0 de logica de sinais | Media | P0 | Frontend atual continua funcionando; novos consumidores podem usar os campos novos; testes de contrato e build passam | Baixo | Principal item para garantir migracao incremental sem breaking change |
| Pipeline incremental de migracao e backfill | Parte das mudancas exige reclassificacao ou preenchimento historico parcial | Criar migracoes DB em etapas, backfill para campos derivados quando possivel e feature flags para alternar leitura do modelo antigo para o novo | Reduz risco de deploy e viabiliza rollback | Evolucao de schema; possivel dual-write | Media/Alta | P1 | Migracoes podem ser aplicadas sem downtime perceptivel; rollback e documentado; ambiente de staging valida o fluxo | Alto | Item-chave para as iniciativas de persistencia; vale preparar antes das migracoes mais sensiveis |
| Adaptacao do ranking backend com compatibilidade | O backend hoje projeta score por workspace, mas nao contempla a camada nova de operabilidade | Atualizar o pipeline de `project_workspace_opportunity` e ranking para suportar multiplos scores, perfis e regras de visibilidade sem alterar semanticamente o score tecnico original | Garante consistencia entre scanner, API e dashboard | Score de executabilidade; profile; API aditiva | Media | P0 | O backend passa a expor ordenacao por score tecnico e por operabilidade; respostas seguem consistentes entre endpoints | Medio | Melhor tratar o ranking como composicao de camadas, nao substituir o score tecnico existente |
| Adaptacao do frontend para leitura dual | O frontend precisara conviver por um tempo com payload antigo e novo | Atualizar `types.ts`, `api.ts` e componentes para suportar fallback quando campos novos nao existirem, com feature flags visuais quando necessario | Permite rollout gradual sem travar deploy conjunto backend/frontend | Evolucao de schema/API | Baixa/Media | P0 | Frontend renderiza com e sem os novos campos; nenhuma tela principal quebra durante rollout | Baixo | Essencial para manter deploy incremental entre Render e Vercel |
| Suite de verificacao e benchmark do motor | Sem testes especificos, o ranking pode piorar silenciosamente a cada ajuste | Adicionar fixtures de books/klines, testes de ranking e snapshots de cenarios operacionais, alem de um benchmark comparando score tecnico vs executabilidade | Aumenta seguranca para iterar na camada nova | Campos e calculos novos; infraestrutura de teste existente | Media | P0 | Existe suite automatizada cobrindo books rasos/profundos, sinais operaveis/nao operaveis e regressao de ranking | Medio | Alto retorno para manutencao; deve entrar cedo junto da camada P0 |

### Ordem recomendada de implementacao

1. Evolucao de schema e contratos de API sem quebra
2. Auditoria de versao do motor de sinais
3. Liquidez em notional por lado do book
4. Slippage estimado por tamanho de ordem
5. Score de executabilidade
6. Split entre `interesting_signal` e `operable_signal`
7. Adaptacao do ranking backend com compatibilidade
8. Adaptacao do frontend para leitura dual
9. Dashboard com explicabilidade operacional
10. Workspace Trading Profile
11. Thresholds por perfil operacional
12. Alertas orientados a operabilidade
13. Duracao util do movimento
14. Refinamento da taxonomia de movimentos
15. Historico orientado a analytics operacionais
16. Deduplificacao orientada a semantica do sinal
17. Politica de retencao e compactacao do historico
18. Reweighting por outcome
19. Pipeline incremental de migracao e backfill
20. Separacao entre evento bruto, sinal, projecao e outcome

### Itens que podem ser feitos sem breaking change

- Liquidez em notional por lado do book
- Slippage estimado por tamanho de ordem
- Score de executabilidade
- Split entre `interesting_signal` e `operable_signal`
- Auditoria de versao do motor de sinais
- Dashboard com explicabilidade operacional
- Alertas orientados a operabilidade
- Adaptacao do frontend para leitura dual
- Suite de verificacao e benchmark do motor

### Itens que exigirao migracao mais sensivel

- Separacao entre evento bruto, sinal, projecao e outcome
- Pipeline incremental de migracao e backfill
- Deduplificacao orientada a semantica do sinal
- Politica de retencao e compactacao do historico
- Reweighting por outcome
- Workspace Trading Profile se for persistido com versionamento e retrocompatibilidade de configuracao

### Itens que geram valor mais rapido

- Liquidez em notional por lado do book
- Slippage estimado por tamanho de ordem
- Score de executabilidade
- Split entre `interesting_signal` e `operable_signal`
- Dashboard com explicabilidade operacional

### Sequencia recomendada de execucao

1. Fechar a base P0 de executabilidade sem mexer ainda na estrutura profunda do historico.
2. Colocar o frontend para explicar operabilidade com leitura dual e sem quebrar o fluxo atual.
3. Introduzir `Workspace Trading Profile` e thresholds por perfil para alinhar o ranking ao uso real.
4. Melhorar `duration_minutes`, taxonomia e alertas depois que a camada de executabilidade ja estiver visivel.
5. So entao atacar reweighting por outcome e a separacao estrutural das camadas de persistencia.

### Top 5 itens que mais geram valor

1. Liquidez em notional por lado do book
2. Slippage estimado por tamanho de ordem
3. Score de executabilidade
4. Split entre `interesting_signal` e `operable_signal`
5. Dashboard com explicabilidade operacional

### Top 5 itens com maior risco tecnico

1. Separacao entre evento bruto, sinal, projecao e outcome
2. Reweighting por outcome
3. Pipeline incremental de migracao e backfill
4. Slippage estimado por tamanho de ordem
5. Deduplificacao orientada a semantica do sinal

### Recomendacao final de por onde comecar

Comecar por um pacote P0 pequeno e coeso:

1. `Liquidez em notional`
2. `Slippage estimado`
3. `Score de executabilidade`
4. `Split interesting vs operable`
5. `Dashboard com explicabilidade`

Esse pacote entrega valor operacional rapido, quase todo sem breaking change, e ataca exatamente o maior gap atual: diferenciar o que apenas chama atencao do que realmente da para operar. A reorganizacao mais profunda de persistencia e analytics deve vir depois, quando essa camada nova ja estiver gerando dados reais suficientes para calibracao e quando houver mais seguranca para migrar sem ruir o fluxo atual.
