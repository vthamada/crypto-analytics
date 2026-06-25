# Changelog

Este arquivo passa a registrar mudancas relevantes do repositorio a partir de 2026-04-14.

O formato segue a ideia de "Keep a Changelog", adaptado para um projeto interno em fase inicial.

Convencao deste repositorio:
- cada entrada deve ser registrada na data em que a modificacao foi feita no repositorio, no formato `YYYY-MM-DD`
- `Unreleased` fica reservado apenas para trabalho ainda nao consolidado no dia

## [Unreleased]

### Added
- Estado derivado do pipeline em oportunidades (`pipeline_status`, `visibility_reason`, `operationally_visible`) para separar oportunidade operacional de registro tecnico.
- Servico central de visibilidade operacional para bloquear `avoid`, margem negativa, movimento fraco, baixa liquidez e sinal atrasado fora das superficies principais.
- Auditoria persistente do funil de sinais com `scanner_cycle_audits` e `signal_pipeline_events`, incluindo migration `0012_signal_pipeline_audit`.
- Endpoint `GET /api/diagnostics/missed-signal` para investigar por exchange/par/janela onde um sinal foi candidato, descartado, bloqueado, ranqueado ou alertado.
- Eventos compactos do scanner para scan leve, promocao, analise profunda, ranking e entrega/bloqueio de alertas Telegram.
- Tela de configuracoes passou a ter busca de diagnostico de sinal perdido, com resumo por ciclo e linha do tempo do funil.
- Diagnostico de sinal perdido agora inclui causa final, motivo raiz, status do catalogo e contexto do workspace ativo.
- Eventos por workspace registram se cada sinal ficou visivel ou foi bloqueado por exchange/par/threshold/perfil operacional.
- Historico passou a separar visao operacional, auditoria tecnica e visao completa por `visibility=operational|technical|all`.
- Scanner passou a registrar near misses compactos (`event_type=near_miss`) para descartes proximos de threshold e candidatos bloqueados por limite de promocao.
- Endpoint `GET /api/diagnostics/near-misses` lista near misses por periodo, exchange e par sem expor o dataset bruto do scanner.
- Classificacao de valor de alerta em runtime com `alert_worthiness_score`, `alert_trigger_type` e `has_actionable_trigger` nos detalhes de auditoria.
- Bloqueios de Telegram passaram a registrar motivos especificos, incluindo escopo de exchange/par, operabilidade, executabilidade, limite de score, Telegram desativado/nao configurado, cooldown e menor prioridade no top 5.
- Configuracao de limite diario de alertas Telegram por workspace, com bloqueio auditado como `daily_alert_limit_reached`.
- Diagnostico de sinal perdido passou a aceitar periodo customizado na UI e a explicar pares nao monitoraveis por catalogo, provider ou par nao BRL.
- Migration `0013_supabase_rls_hardening` revoga execucao publica da funcao `public.rls_auto_enable()` quando existente no Supabase.
- Provider NovaDAX passou a normalizar formatos alternativos de simbolo (`SOLBRL`, `SOL/BRL`, `baseCurrency`/`quoteCurrency`) e a retornar pares BRL ativos mesmo quando a API variar o payload.
- Campos persistidos de valor de alerta: `alert_worthiness_score`, `alert_trigger_type`, `has_actionable_trigger`, `alert_state_key` e `alert_block_reason`.
- Migration `0015_alert_worthiness_state` adiciona os campos de alerta em oportunidades, snapshots e projecoes por workspace.
- Endpoint `GET /api/diagnostics/funnel-quality` agrega metricas compactas de qualidade do funil a partir de ciclos e eventos de auditoria.
- Taxonomia operacional expandida inicial com `opportunity_subtype`, cobrindo direcional, faixa, hold/continuidade, rompimento, arbitragem cross-exchange, zona de realizacao, observacao e avoid.
- Migration `0016_opportunity_subtype` adiciona `opportunity_subtype` em oportunidades e snapshots.
- Persistencia de temperatura e cooldown por exchange/par em `scanner_pair_states`, mantendo memoria operacional do scanner entre restarts/deploys.
- Migration `0017_scanner_pair_states` adiciona estado operacional persistido do scanner por par.
- Campo explicito `operational_score` em oportunidades, snapshots, API e frontend para separar saude operacional de urgencia de alerta.
- Migration `0018_operational_score` adiciona `operational_score` com backfill a partir de `score`.
- Simulacao de tamanhos de ordem em R$ 25, R$ 300, R$ 1.000, R$ 5.000 e R$ 10.000 por oportunidade, com maior tamanho operavel e rótulo operacional.
- Migration `0019_order_size_simulations` adiciona capacidade operacional por tamanho em oportunidades e snapshots.
- Tese operacional derivada por oportunidade com status de acao, familia operacional, zona de entrada, zona de saida, tamanho sugerido, liquidez, risco, motivo principal e flags de ordem limitada/transferencia.

### Fixed
- Dashboard, shortlist, WebSocket e `/api/opportunities` passaram a ocultar ruido tecnico por padrao; registros tecnicos podem ser incluidos explicitamente com `include_technical=true`.
- `/api/history` e `/api/history/summary` retornam historico operacional por padrao, mantendo descartes e bloqueios acessiveis apenas na visao tecnica/auditoria.
- Telegram agora possui uma defesa final para nao enviar sinais nao operacionais, mesmo quando configuracoes de `high_score` ou arbitragem estiverem ativas.
- Telegram deixou de enviar `accumulation`, `preparation` ou estado neutro sem gatilho acionavel, bloqueando como `accumulation_only`, `preparation_without_trigger`, `no_actionable_operation` ou `insufficient_alert_worthiness`.
- Elegibilidade e ranking de Telegram agora usam `alert_worthiness_score`, mantendo `operational_score` apenas como contexto operacional.
- Sinais sem nenhum tamanho minimo executavel passam a ser bloqueados como baixa liquidez.
- Badges do frontend evitam mostrar combinacoes contraditorias como `Operavel` junto com `Evitar` ou margem negativa.
- Provider NovaDAX passou a calcular `change_pct_24h` a partir de `open24h` quando a API nao retorna `change24h`, evitando descarte total dos pares por erro de ticker no scan leve.
- Catalogo de pares deixou de cachear resposta totalmente vazia como estado valido; quando um provider retorna vazio apos sucesso anterior, o sistema usa o ultimo catalogo valido e marca status `stale`.
- Telegram agora bloqueia repeticao do mesmo estado de alerta para o mesmo destino/par como `no_state_change`, evitando reenviar moeda parada na mesma fase depois do cooldown temporal.
- Watchlist de pares deixou de limitar dashboard, historico e universo de scan; o scanner agora avalia o catalogo BRL descoberto e usa pares selecionados apenas como destaque/diagnostico.
- Configuracao `pair_universe_mode` permite escolher entre monitorar todos os pares BRL das exchanges habilitadas ou restringir scan/dashboard/historico apenas a watchlist.
- O detalhe do sinal agora mostra o subtipo operacional, preparando a UI para separar movimentos direcionais, faixas, spread interno e arbitragem.
- Dashboard, detalhe de oportunidade e Telegram passaram a priorizar a leitura operacional pratica em vez de score tecnico: o usuario ve por que olhar, onde entrar/sair, quanto cabe operar e qual risco principal.
- Migration `0014_revoke_public_execute` remove permissao herdada de `PUBLIC` na funcao `public.rls_auto_enable()` sem bloquear deploys quando o usuario do app nao e dono da funcao.

## [2026-05-07]

### Added
- Classificacao de fase do movimento, risco de entrada tardia e motivo operacional do alerta.
- Faixa operacional reaproveitavel com zonas de compra/venda, margem, confiabilidade, liquidez e capacidade estimada.
- Diagnostico individual de par por exchange em `GET /api/pairs/diagnostics/{exchange}/{pair}`.
- Outcomes enriquecidos com janela de 24h, maior/menor preco pos-sinal, MFE/MAE, volume, continuidade, rompimento confirmado e label.
- Feedback manual de sinais via `POST /api/signals/feedback` e botoes rapidos no detalhe do sinal.
- Migrations `0010_movement_phase_fields` e `0011_operational_range_outcomes_feedback`.

### Changed
- Ranking do ciclo, shortlist e Telegram passaram a considerar fase, liquidez, margem, qualidade da faixa e risco de sinal atrasado.
- Alertas Telegram agora exibem fase, momento, motivo, faixa operacional, margem e capacidade estimada.
- NovaDAX deixou de falhar silenciosamente quando a listagem de pares falha, usando erro explicito ou ultimo catalogo valido.

## [2026-05-06]

### Added
- Scanner em dois estagios: triagem leve por ticker/volume/movimento antes de buscar order book e candles.
- Temperatura de scan em memoria (`hot`, `warm`, `cold`) para reduzir rechecagem de pares frios.
- Cooldown exponencial por provider/par apos falhas de ticker, order book, klines ou excecoes de scan.
- Telemetria agregada do scan leve em `/api/health`, com total de pares, pulos por temperatura/cooldown, descartes por motivo, candidatos profundos e oportunidades geradas.
- Endpoint leve `GET /api/dashboard/summary` com stats e shortlist operacional em payload reduzido.
- Endpoints leves `GET /api/opportunities/active` e `GET /api/opportunities/shortlist` com `OpportunitySummary`.
- Diagnostico de catalogo em `GET /api/pairs/available`, incluindo status por provider, quantidade de pares retornados, pares BRL detectados, exemplos e mensagens de erro.
- Cliente frontend tipado para os endpoints leves de dashboard e oportunidades.

### Changed
- O scanner agora limita analise profunda aos melhores candidatos por exchange, reduzindo chamadas caras para pares sem volume ou sem movimento preliminar.
- Dashboard principal passou a carregar `/api/dashboard/summary` por padrao e buscar `/api/opportunities/{id}` apenas ao abrir o detalhe do sinal.
- A tela de configuracoes passou a mostrar o estado do catalogo por exchange e o status tecnico de cada par/provedor.
- O catalogo de pares agora preserva metadados de normalizacao (`base_asset`, `quote_asset`, `normalized_symbol`, disponibilidade, tradabilidade e status por exchange).
- Escopo operacional padrao alinhado ao mercado BRL: Mercado Bitcoin e NovaDAX ficam ativas por padrao, Binance fica opcional/desativada ate ativacao manual.
- `GET /api/pairs/available` passou a aceitar `enabled_exchanges` e o catalogo agora evita consultar providers desativados, marcando-os como `disabled`.
- A tela de configuracoes passou a solicitar o catalogo conforme as exchanges habilitadas no workspace, permitindo ativar Binance manualmente sem contaminar o fluxo BRL padrao.

## [2026-05-05]

### Added
- Score de margem operacional com `estimated_trade_margin_pct`, `operational_friction_pct`, `estimated_net_trade_edge_pct` e `trade_margin_score`.
- Classificacao pratica da oportunidade em `trade`, `hold`, `observe` ou `avoid`.
- Endpoint consolidado `GET /api/dashboard` para entregar stats e oportunidades em um unico payload.
- Endpoint `GET /api/history/summary` com payload reduzido para listagem historica.
- Migration `0008_operational_margin_classification` para persistir margem operacional e classificacao.

### Changed
- Dashboard inicial passou a usar payload agregado e derivar stats dos eventos WebSocket, evitando refetch duplicado de `/dashboard/stats`.
- Historico passou a carregar analytics operacional apenas sob demanda; a listagem usa resumo paginado em vez do historico completo.
- Analytics operacional agora agrega distribuicao por tipo de oportunidade e margem liquida media por tipo a partir de linhas compactas no backend.
- Configuracao default de pares passou para modo descoberta BRL ampla; uma lista manual continua funcionando como watchlist.
- Retencao historica agora limpa tambem `technical_signals`, `workspace_signal_projections`, `raw_market_observations` e `signal_outcomes`.

## [2026-04-24]

### Added
- Release E concluida: `AppConfig` agora inclui `trading_profile`, `order_notional_brl`, limites de slippage de entrada/saida, `min_quote_volume_brl` e `telegram_operable_only`.
- Tela de configuracoes passou a expor perfil operacional, tamanho de ordem, volume notional minimo, slippage de entrada/saida e politica de alertas Telegram.
- Testes E2E cobrem a renderizacao dos novos campos operacionais na UI administrativa.

### Changed
- Scanner passou a calcular slippage e `operable_signal` com thresholds do workspace em vez de constantes globais.
- Alertas Telegram passaram a respeitar operabilidade, tipos configurados e cooldown por workspace, com mensagem focada em volume, liquidez, slippage e facilidade de saida.
- `render.yaml` move o worker para `region: frankfurt` para reduzir risco de HTTP 451 de providers em regioes restritas dos EUA.
- Provider Binance passou a usar `data-api.binance.vision` para chamadas publicas/read-only de mercado, evitando bloqueios `HTTP 451` em `api.binance.com`.

## [2026-04-18]

### Added
- `workspace_profiles.py` com presets operacionais por workspace (`conservador`, `intraday_liquido`, `agressivo`, `scalp`) e thresholds derivados para notional, slippage e volume minimo.
- Migration `0007_operational_profiles_and_history_layers` adicionando `reweighting_version`, `semantic_signal_key`, `movement_regime`, `baseline_order_notional_brl` e a nova tabela `raw_market_observations`.
- Endpoint administrativo `/api/analytics/operational` para expor analytics recalculados com buckets de executabilidade, distribuicao de regime e perfil ativo do workspace.
- Persistencia dual-write de `raw_market_observations` por ciclo, consolidando a separacao entre observacao bruta, sinal tecnico, projecao por workspace e outcome.

### Changed
- `project_workspace_opportunity()` e a serializacao do historico agora recalculam executabilidade e operabilidade por workspace com base no perfil operacional atual, sem quebrar o score tecnico.
- O scanner passou a produzir `movement_regime`, `movement_persistence_score`, `duration_minutes`, `baseline_order_notional_brl`, `semantic_signal_key` e `reweighting_version`.
- A deduplicacao do historico deixou de ser apenas `exchange+pair` por janela fixa e passou a considerar a chave semantica do sinal.
- A calibracao historica agora usa `signal_outcomes` reais para reweighting conservador, mantendo o fator final entre `0.90` e `1.15`.
- Alertas Telegram passaram a respeitar perfil operacional, `telegram_operable_only`, score minimo de executabilidade e escopo por exchange/par.
- A tela de settings ganhou edicao do perfil operacional por workspace; a de historico passou a consumir analytics operacionais.

### Fixed
- Fallback da API para snapshots compartilhados voltou a funcionar em cenarios sem estado local apos a introducao dos filtros operacionais.

## [2026-04-17]

### Added
- Campos aditivos de executabilidade no contrato de oportunidades e historico: `executability_score`, `executability_band`, `interesting_signal`, `operable_signal`, metricas de notional/slippage e versionamento explicito (`executability_version`, `movement_version`, `profile_version`).
- Compatibilidade de schema no startup para acrescentar colunas operacionais novas sem depender de uma migracao bloqueante unica.
- `backend/app/filters/executability.py` com calculo de slippage estimado, notional preenchivel e `calculate_executability_score()`.
- Metricas de book em notional (`bid_notional_top_n`, `ask_notional_top_n`, `total_notional_top_n`) no pipeline do scanner.
- Ordenacao por executabilidade e filtro `operable_only` em `/api/opportunities`.
- Suite de testes cobrindo score de executabilidade, books rasos/profundos, contrato aditivo e preservacao da camada de executabilidade na projecao por workspace.

### Changed
- O scanner agora produz uma camada paralela de operabilidade sem substituir o ranking tecnico existente.
- A heuristica inicial de classificacao operacional passou a separar `interesting_signal` de `operable_signal`.
- `project_workspace_opportunity()` preserva `executability_score`, `executability_band` e flags operacionais, recalculando apenas o score contextual do workspace.
- `main.py` e `worker.py` passaram a materializar `score_version`, `executability_version`, `movement_version` e `profile_version` junto das projecoes do ciclo.
- O dashboard passou a suportar leitura dual entre payload legado e payload novo, com ordenacao por operabilidade, badges operacionais, modal de detalhe explicando liquidez/slippage e melhor leitura mobile.
- `useHasAuthenticatedWorkspace()` e a pagina inicial do dashboard foram ajustados para evitar mismatch de hidratacao entre SSR e cliente.
- `README.md`, `ARCHITECTURE.md`, `SYSTEM_STATE.md`, `BACKLOG.md` e o plano `docs/superpowers/plans/2026-04-17-operational-executability-plan.md` foram atualizados para refletir a conclusao das Releases A, B, C e D.

## [2026-04-16]

### Added
- `backend/app/services/shared_state.py` com contrato compartilhado entre scanner/worker e API: runtime state, snapshots de oportunidades, sinais tecnicos, projecoes por workspace, outcome tracking e repeticao persistente.
- Migracao `0006_p2_robustness_tables` criando 6 tabelas: `scanner_runtime_state`, `opportunity_snapshots`, `technical_signals`, `workspace_signal_projections`, `signal_outcomes` e `repetition_counts`, alem de 3 colunas em `opportunities` (`technical_score`, `score_version`, `technical_signal_id`).
- `technical_score` neutro (pesos fixos default, sem dependencia de `configs[0].weights`) com `score_version` para versionamento do motor de score.
- Dual-write de `technical_signals` com deduplicacao por janela de 5 minutos; cada oportunidade persistida recebe `technical_signal_id`.
- `workspace_signal_projections` materializado por ciclo de scan, com `workspace_score`, `visible`, `alert_eligible` e `projection_reason`.
- `signal_outcomes` com campos para avaliacao temporal em 5m, 15m, 1h e 4h.
- `backend/app/services/outcome_evaluator.py` — job que busca preco atual para outcomes pendentes e preenche campos de 5m/15m/1h/4h com calculo de `outcome_pct`.
- `repetition_counts` persistido em banco, com decay automatico de contagens inativas ha mais de 30 minutos.
- Fallback da API para snapshots do banco quando nao ha scanner local (`_effective_opportunities`), permitindo modo API-only.
- `SCANNER_ENABLED` em `Settings` — permite desligar o scan loop para rodar a API em modo API-only.
- Campo `mode` no `/api/health` (`scanner` ou `api_only`) e `scanner_state` com estado do ultimo ciclo vindo do banco.
- `telegram_alert_threshold`, `telegram_alert_cooldown_seconds` e `telegram_alert_types` em `AppConfig` e `ConfigUpdate`.
- `backend/tests/test_contract_integration.py` com 10 testes de contrato cobrindo `/api/dashboard/stats`, `/api/opportunities`, `/api/health` e `/api/config` incluindo fallback para snapshots, campos tecnicos e politica de Telegram.
- `backend/tests/test_outcome_evaluator.py` com 8 testes cobrindo janelas temporais e avaliacao de outcomes com mocks de providers.
- Metodo `Scanner.load_repetition_counts()` para restaurar contagens persistidas na inicializacao.

### Changed
- Documentacao operacional e arquitetural alinhada ao runtime atual: `README.md`, `ARCHITECTURE.md`, `SYSTEM_STATE.md`, `HANDOFF.md`, `DEPLOY.md`, `SPEC.md` e `frontend/README.md` agora refletem o fluxo padrao com API em modo `api_only` + worker dedicado, health check com `mode`, autenticacao por sessao/workspace e outcome evaluator ativo.
- `docker-compose.yml` agora separa API (com `SCANNER_ENABLED=false`) e worker (`python -m app.worker`) em servicos distintos.
- `main.py` e `api/websocket.py` agora repropagam snapshots persistidos para clientes WebSocket conectados mesmo quando a API roda em `api_only` e o scan fica em um worker separado.
- `scan_loop()` em `main.py` passou a escrever snapshots, sinais tecnicos, projecoes, outcomes e repeticao a cada ciclo, a registrar `scanner_runtime_state` com inicio, duracao, erro e sucesso, e a executar `evaluate_pending_outcomes` a cada ciclo.
- `worker.py` recebeu a mesma integracao de `shared_state` que `main.py`, tornando-o produtor equivalente do scan, incluindo avaliacao de outcomes.
- `scanner.py` passou a computar `technical_score` e `score_version` em cada oportunidade e a aceitar contagens de repeticao vindas do banco.
- `persistence.py` passou a persistir `technical_score`, `score_version` e `technical_signal_id` em `OpportunityRecord`, e `serialize_history_record` inclui os novos campos.
- `routes.py` passou a usar `_effective_opportunities()` em `/api/dashboard/stats`, `/api/opportunities` e `/api/opportunities/{id}`, caindo para snapshots do banco quando nao ha estado local.
- Alertas Telegram no scan loop passaram a usar `telegram_alert_threshold` configurado por workspace em vez do corte fixo `score >= 60`.
- Logs de fim de ciclo passaram a incluir `signals_saved`, `projections_saved`, `alerts_sent` e `alerts_suppressed`.
- `DEPLOY.md` foi reescrito para priorizar a topologia `Supabase + Render + Vercel`, com API em `api_only`, worker dedicado e checklist de smoke test aderente ao runtime atual.

### Removed
- `refatoracao_implementacao.md` removido para evitar drift documental apos o plano ter sido absorvido por `BACKLOG.md`, `SYSTEM_STATE.md` e demais documentos ativos.

## [2026-04-15]

### Added
- `CHANGELOG.md` para registrar mudancas relevantes do projeto.
- `HANDOFF.md` com estado atual do sistema, arquitetura, riscos e proximos passos.
- `BACKLOG.md` com prioridades tecnicas e de produto derivadas da analise do repositorio.
- `.env.example` com as variaveis esperadas por backend e frontend.
- `ARCHITECTURE.md` com visao estrutural do sistema.
- Suite inicial de testes do backend cobrindo filtros, scanner, persistencia e rotas administrativas.
- `README.md` na raiz com onboarding rapido do monorepo.
- Login administrativo opcional via credenciais em `/api/admin/login`.
- Estrutura inicial de worker dedicado em `backend/app/worker.py`.
- Scaffold de migracoes com Alembic em `backend/alembic` e `backend/alembic.ini`.
- Persistencia de administrador em banco com trilha de auditoria em `admin_users` e `audit_logs`.
- Endpoints administrativos para sessao atual, troca de senha e auditoria recente.
- Fundacao multi-tenant com `users`, `workspaces`, `workspace_memberships` e `workspace_configs`.
- Seletor de workspace no frontend e criacao de novos workspaces na tela de configuracoes.
- Endpoints de gestao de usuarios por workspace: `GET /api/users`, `POST /api/users`, `PATCH /api/users/{user_id}` e `POST /api/users/{user_id}/reset-password`.
- Fluxo de refresh token de 30 dias com `POST /api/auth/refresh` e rotacao de tokens apos login e troca de senha.
- Migracao `0004_user_management` com `must_change_password` e `created_by_user_id` em `users`.
- Catalogo dinamico de pares em `GET /api/pairs/available`, com cache agregado por exchange e TTL de 1 hora.
- Gestao de usuarios na tela de configuracoes, com criacao, desativacao, redefinicao de senha e aviso de credencial temporaria.
- Selecao dinamica de pares no frontend com busca, indicador por exchange e fallback para pares legados ainda configurados.
- Testes adicionais de backend para refresh token, membership de usuarios criados por admin e cache/catalogo de pares.
- Migracao `0005_organization_invites_onboarding` com `organizations`, `invites`, backfill de organizacao padrao e campos de onboarding/email.
- Endpoints para convites, aceite de convite, status do workspace, conclusao de onboarding e validacao de credenciais de exchange.
- Servico de validacao autenticada de credenciais para Binance, NovaDAX e Mercado Bitcoin.
- Pagina publica de aceite de convite em `/invite/[code]` com criacao de conta e login imediato.
- Card de onboarding no dashboard com checklist inicial e persistencia de conclusao por usuario.
- Politica configuravel de retencao do historico com limpeza periodica no backend e testes dedicados para expiracao e throttling.
- Suite Playwright em `frontend/tests/e2e/app.spec.ts` cobrindo login administrativo, isolamento por workspace, dashboard em tempo real e falhas de historico.
- Infra de resiliencia no frontend com `app/error.tsx`, `app/global-error.tsx`, `GlobalErrorToaster` e `InlineErrorState`.

### Changed
- `/api/config` agora exige `X-Admin-Token` e nao retorna segredos salvos.
- A tela de configuracoes do frontend passou a exigir token administrativo ou login administrativo e nao preenche segredos vindos da API.
- O scanner agora reconstroi a configuracao em runtime quando o `AppConfig` muda.
- Alertas do Telegram passaram a respeitar cooldown configuravel.
- O frontend passou a declarar `output: "standalone"` para alinhar com o Dockerfile.
- O `backend/pyproject.toml` passou a incluir `aiosqlite`.
- O backend passou a usar lista configuravel de origens CORS em vez de `*`.
- O endpoint `/api/analytics` passou a aceitar os mesmos filtros de historico, incluindo `hours`.
- O frontend de historico passou a buscar analytics filtrados pelo periodo selecionado.
- O `frontend/README.md` deixou de ser boilerplate e passou a documentar o app real.
- Foi adicionada uma pipeline CI em `.github/workflows/ci.yml`.
- `/api/health` passou a expor metricas de scanner, providers e conexoes WebSocket.
- O backend passou a suportar integracao opcional com Sentry via `SENTRY_DSN`.
- Os providers passaram a registrar falhas, rate limit e latencia para observabilidade.
- A persistencia passou a armazenar contexto cross-exchange e fator de confianca historica.
- O dashboard e o historico passaram a expor filtros avancados, analytics expandidos e indicadores de arbitragem.
- O scanner passou a enriquecer oportunidades com gap cross-exchange, arbitragem simples e calibracao historica.
- A inicializacao do banco passou a usar Alembic como caminho principal de schema management, com compatibilidade para bases existentes.
- A autenticacao administrativa passou a usar senha com hash, token assinado com `token_version` e revogacao ao trocar senha.
- A tela de configuracoes passou a exibir estado da sessao administrativa, permitir logout e trocar a senha persistida.
- O backend passou a isolar configuracao, auditoria e preferencias por workspace.
- Dashboard, historico, analytics e configuracoes passaram a respeitar o workspace ativo enviado pelo cliente.
- O scanner passou a operar com configuracao mesclada dos workspaces e a nota final e recalculada por tenant com base nos componentes do score.
- `/api/config` e `/api/admin/audit-log` passaram a exigir role `admin`, mesmo quando a sessao ja esta autenticada.
- A sessao do frontend passou a renovar o access token silenciosamente em respostas `401`, sincronizar storage entre componentes e manter `refresh_token` junto do workspace ativo.
- A tela de configuracoes passou a suportar sessao de membro, troca obrigatoria de senha temporaria e administracao de usuarios do workspace ativo.
- O catalogo de pares substituiu a lista hardcoded de ativos no frontend e passou a refletir a disponibilidade real por exchange.
- O dashboard passou a renderizar oportunidades em cards no mobile, com filtros usaveis em largura estreita e tabela completa preservada a partir de `sm`.
- A tela de configuracoes passou a permitir teste real de Telegram com feedback imediato, usando credenciais digitadas na sessao ou o fallback salvo no workspace.
- O frontend deixou de depender de `next/font/google` em runtime de build e passou a usar font stacks locais para evitar falhas intermitentes do Turbopack na resolucao da Inter.
- A autenticacao passou a aceitar login por usuario ou email e a sessao agora expone organizacao, email e estado de onboarding.
- `Workspace` e `User` passaram a carregar referencia de `Organization`, preparando billing e feature gates futuros sem nova refatoracao estrutural.
- A tela de configuracoes passou a exibir contexto de organizacao, gestao de convites e status de validacao das chaves de exchange.
- O header passou a mostrar a organizacao ativa e o scanner passou a acordar imediatamente quando a configuracao do workspace muda.
- O scanner principal e o worker passaram a executar retencao configuravel de historico dentro do proprio loop operacional.
- Dashboard, historico e cliente HTTP/WebSocket passaram a expor falhas com feedback visual consistente em vez de erros silenciosos.
- O frontend passou a expor seletores estaveis para os fluxos criticos cobertos por E2E sem alterar a experiencia do usuario.

### Fixed
- A criacao de usuarios pelo admin agora vincula imediatamente o usuario ao workspace ativo, evitando login bem-sucedido seguido de falta de acesso ao tenant.
- A redefinicao de senha passou a invalidar access tokens e refresh tokens anteriores por `token_version`.
- A troca de pares/exchanges no workspace deixou de depender do proximo sleep do scanner para surtir efeito.

### Known Issues
- A camada multi-tenant ainda nao possui feature gates por plano, billing com Stripe ou scanner dedicado desacoplado do processo web.

## [2026-04-14]

### Noted
- Repositorio identificado como monorepo com `backend` em FastAPI/Python e `frontend` em Next.js/React.
- Documentacao existente concentrada em `SPEC.md` e `DEPLOY.md`.
- Frontend com dashboard, historico e configuracoes ja implementados.
- Backend com scanner, persistencia, WebSocket e integracoes com NovaDAX, Mercado Bitcoin e Binance.
