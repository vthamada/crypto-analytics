# Backlog

Ultima revisao: 2026-05-08

Este backlog consolida tudo que ainda precisa ser implementado no sistema a partir da especificacao principal em `docs/superpowers/plans/ESPECIFICACAO_COMPLETA_IMPLEMENTACAO.md`.

Legenda: `[x]` concluido, `[~]` parcialmente feito, `[ ]` pendente.

---

## Direcao Do Produto

O sistema deve ser um assistente operacional de oportunidades em cripto BRL, focado inicialmente em Mercado Bitcoin e NovaDAX, que monitora pares relevantes, identifica zonas de compra e venda, detecta lateralizacao, rompimento e continuacao, avalia liquidez, margem e risco de atraso, entrega shortlist qualificada, aprende com outcomes/feedbacks e explica por que cada oportunidade foi alertada, descartada ou perdida.

Decisoes ja tomadas:

| Tema | Decisao |
|---|---|
| Exchanges principais | Mercado Bitcoin e NovaDAX |
| Binance | Opcional, desativada por padrao |
| Scanner | Global, com projecao por workspace |
| Watchlist | Prioridade/filtro pessoal, nao limite do universo |
| Trading | Monitoramento primeiro; paper trading depois; execucao real apenas futuramente |
| Multiusuario | Organization como unidade de cobranca; Workspace como unidade operacional |

---

## Estado Atual Concluido

- [x] Scanner em dois estagios: scan leve amplo e analise profunda apenas de candidatos.
- [x] Mercado Bitcoin e NovaDAX habilitadas por padrao; Binance opcional/desativada.
- [x] Catalogo dinamico de pares por exchange com status tecnico e diagnostico por par.
- [x] Dashboard usando endpoints resumidos e detalhe sob demanda para reduzir egress.
- [x] Score tecnico, executabilidade, margem operacional e classificacao `trade`, `hold`, `observe`, `avoid`.
- [x] Fase do movimento, risco de entrada tardia e faixa operacional reaproveitavel.
- [x] Ranking comparativo por ciclo e alertas Telegram mais seletivos.
- [x] Outcomes enriquecidos com 5m, 15m, 1h, 4h, 24h, MFE/MAE e label.
- [x] Feedback manual de sinais.
- [x] Auditoria P0 do funil com `scanner_cycle_audits`, `signal_pipeline_events` e endpoint de sinal perdido.
- [x] UI inicial de auditoria em Settings, com causa final, status do workspace e status do catalogo.
- [x] Explicabilidade por workspace para sinais visiveis/bloqueados e motivos especificos de alerta.
- [x] Watchlist deixou de limitar dashboard, historico e scan; pares selecionados viraram destaque/diagnostico.
- [x] Modo de universo de pares configuravel: todos os pares BRL ou apenas watchlist.
- [x] Hardening inicial do Supabase revogando execucao publica da funcao `public.rls_auto_enable()` quando existir.
- [x] Multiusuario base: users, organizations, workspaces, memberships, invites, refresh token, auditoria administrativa.
- [x] Worker dedicado e API capaz de ler estado compartilhado.

---

## P0 - Confiabilidade Operacional Imediata

### Auditoria e Diagnostico

- [x] **Periodo customizado na auditoria operacional**
  Permitir selecionar `from` e `to` diretamente na UI, alem das janelas moveis atuais de 1h, 4h, 24h e 72h.
  Criterio de aceite: o usuario consegue investigar qualquer janela dentro da retencao de auditoria.

- [x] **Explicabilidade por workspace**
  Quando um sinal existe no scanner global mas nao aparece em um workspace, registrar e exibir o motivo: exchange desabilitada, par fora da configuracao, thresholds, operable_only, score minimo, perfil operacional ou Telegram desabilitado.
  Criterio de aceite: o diagnostico de sinal perdido diferencia falha global de bloqueio por workspace.

- [x] **Enriquecer o endpoint de sinal perdido**
  Incluir status de catalogo, status da exchange, status do par, ultima atualizacao do catalogo e se o par era monitoravel no intervalo.
  Criterio de aceite: `GET /api/diagnostics/missed-signal` responde se a falha ocorreu em catalogo, provider, filtro, ranking, workspace ou alerta.

- [x] **Motivos padronizados para par nao monitoravel**
  Registrar explicitamente `exchange_disabled`, `pair_not_in_catalog`, `pair_inactive`, `pair_not_tradable`, `not_brl_pair`, `cache_empty`, `cache_stale`.
  Criterio de aceite: nenhum par relevante termina sem motivo quando nao entra no scan.

- [~] **Completar motivos de bloqueio de alerta**
  Adicionar eventos para `not_in_top_shortlist`, `lower_than_competing_signals`, `opportunity_type_not_alertable`, `movement_too_late`, `high_late_entry_risk`, `insufficient_operational_margin`, `telegram_send_failed`.
  Criterio de aceite: todo sinal elegivel que nao foi alertado possui `alert_block_reason`.
  Status: implementados `lower_than_competing_signals`, `opportunity_type_not_alertable`, `exchange_not_in_alert_scope`, `pair_not_in_alert_scope`, `not_operable_for_alert_scope`, `below_min_executability`, `below_alert_threshold`, `telegram_disabled`, `telegram_not_configured` e `cooldown_active`.

- [x] **Limite diario de alertas por workspace**
  Implementar limite configuravel por workspace para evitar excesso de notificacoes.
  Criterio de aceite: quando o limite for atingido, o bloqueio fica auditado como `daily_alert_limit_reached`.

- [ ] **Cache vazio nao pode ser catalogo valido**
  Reforcar regra para catalogo vazio ou parcialmente falho: usar ultimo catalogo valido, marcar `stale` ou `error`, nunca `ok`.
  Criterio de aceite: falha temporaria de provider nao apaga o universo monitoravel nem fica silenciosa.

- [ ] **Retencao da auditoria validada em producao**
  Validar `run_audit_retention_if_due` e politicas de retencao em API/worker com volume real.
  Criterio de aceite: eventos detalhados expiram conforme TTL e resumos por ciclo continuam disponiveis.

### Persistencia De Estado Operacional

- [ ] **Persistir cooldown por provider/par**
  Hoje parte do cooldown e temperatura ainda depende de memoria do processo. Persistir falhas recorrentes e cooldown para sobreviver a restart.
  Criterio de aceite: apos restart, pares com erro recorrente nao voltam imediatamente ao scan profundo.

- [ ] **Persistir temperatura dinamica (`hot`, `warm`, `cold`)**
  Salvar estado de frequencia dinamica por par/exchange de forma compacta.
  Criterio de aceite: o scanner preserva prioridade dinamica entre ciclos e reinicios.

- [ ] **Persistir agregados seletivos de descartes**
  Manter agregados por ciclo/exchange/par sem gravar dados brutos pesados.
  Criterio de aceite: analytics de descarte continua disponivel sem inflar Supabase.

### Producao

- [ ] **Deploy de producao endurecido**
  Garantir Postgres como padrao, HTTPS, CORS restrito, rotacao de segredos, health check externo, logs e Sentry configurados.
  Criterio de aceite: ambiente de producao sobe com checks claros e sem segredos expostos.

- [ ] **Validacao pos-deploy automatizada**
  Criar checklist/script para validar API, worker, migrations, Vercel, Render, Supabase, catalogo, scanner, Telegram e auth apos deploy.
  Criterio de aceite: um deploy pode ser validado sem inspecao manual extensa.

---

## P1 - Auditoria Operacional Completa

- [ ] **Tela dedicada de auditoria operacional**
  Criar pagina propria para auditoria, separada de Settings.
  Criterio de aceite: usuario ve estado operacional do sistema sem navegar por configuracoes administrativas.

- [ ] **Funil visual por ciclo**
  Mostrar pares vistos, descartados, promovidos, analisados profundamente, sinais criados, shortlist, alertas criados, alertas enviados e alertas bloqueados.
  Criterio de aceite: cada ciclo pode ser entendido em uma tela.

- [ ] **Historico de alertas bloqueados**
  Exibir bloqueios por motivo, workspace, par, exchange e horario.
  Criterio de aceite: o usuario consegue responder "por que nao recebi Telegram?".

- [ ] **Indicadores de falsos negativos**
  Criar fluxo para marcar "o sistema deveria ter avisado" e associar a um par/periodo.
  Criterio de aceite: falso negativo vira evento persistido e pesquisavel.

- [ ] **Busca avancada no diagnostico**
  Filtros por etapa do pipeline, status, motivo, tipo de movimento, workspace e oportunidade.
  Criterio de aceite: diagnostico localiza rapidamente falhas especificas.

- [ ] **Comparacao com sinais concorrentes**
  No diagnostico, mostrar quais sinais estavam acima do par investigado no mesmo ciclo.
  Criterio de aceite: fica claro se o par perdeu prioridade por ranking comparativo.

- [ ] **Agregados de motivos de descarte e bloqueio**
  Endpoints e UI para ranking de motivos por exchange/par/periodo.
  Criterio de aceite: produto mostra gargalos recorrentes do funil.

---

## P1 - Qualidade Do Motor Operacional

- [ ] **Refinar lateralizacao + rompimento**
  Evoluir heuristicas para detectar compressao de range, rompimento limpo, expansao de volume e continuidade.
  Criterio de aceite: casos como lateralizacao seguida de disparo sao classificados cedo e com motivo visivel.

- [ ] **Score dedicado de rompimento**
  Calcular `breakout_strength_score`, `volume_expansion_score`, `breakout_confirmation_score` e `continuation_potential_score`.
  Criterio de aceite: ranking diferencia alta isolada de rompimento operacional.

- [ ] **Refinar score de fase do movimento**
  Melhorar classificacao entre `accumulation`, `early_breakout`, `continuation`, `extended`, `distribution_or_profit_zone`, `exhaustion`.
  Criterio de aceite: alertas tardios sao penalizados e rotulados com confianca.

- [ ] **Refinar score de faixa operacional**
  Melhorar zonas de compra/venda, margem, reuse count, confiabilidade da faixa, liquidez por zona e capacidade de capital.
  Criterio de aceite: oportunidades com faixa reaproveitavel sobem no ranking e sinais sem margem caem.

- [ ] **Duracao util do movimento**
  Tornar `duration_minutes` e `movement_persistence_score` mais reais, usando ciclos consecutivos, estabilidade de spread, liquidez e continuidade.
  Criterio de aceite: sinais validos deixam de aparecer com duracao artificial e impulsos mortos sao penalizados.

- [ ] **Regua contextual para ativos de alta liquidez**
  Promover ativos muito liquidos quando o movimento for atipico em relacao ao proprio historico, mesmo com variacao percentual menor.
  Criterio de aceite: BTC/USDT/SOL ou equivalentes nao sao fixamente favorecidos, mas movimentos relevantes em ativos liquidos nao somem.

- [ ] **Alertas por momento mais explicativos**
  Diferenciar claramente preparacao, rompimento inicial, continuacao, movimento esticado e zona de realizacao.
  Criterio de aceite: Telegram e dashboard evitam linguagem implicita de compra quando o sinal esta tardio.

- [ ] **Integrar fase/faixa/outcome aos eventos de auditoria**
  Eventos de pipeline devem carregar campos resumidos de fase, margem, score operacional e classificacao.
  Criterio de aceite: timeline explica decisao operacional sem exigir abrir payload completo da oportunidade.

---

## P1 - Analytics, Outcomes E Feedback

- [ ] **Analytics de outcomes por bucket**
  Agregar por exchange, par, tipo de oportunidade, fase, faixa operacional, score, perfil e momento do alerta.
  Criterio de aceite: dashboard interno responde "quais tipos de sinal funcionam?".

- [ ] **Relatorio de sinais uteis vs falsos positivos**
  Mostrar win rate, retorno medio, MFE/MAE, labels de outcome e feedback manual.
  Criterio de aceite: usuario consegue avaliar qualidade historica do motor.

- [ ] **Calibracao conservadora por outcomes**
  Evoluir `historical_confidence` para considerar buckets de outcome reais com limites de variacao seguros.
  Criterio de aceite: ranking melhora com dados reais sem oscilacoes extremas.

- [ ] **Feedback manual em analytics**
  Expandir `feedback_distribution` para cortes por par, exchange, workspace e tipo de sinal.
  Criterio de aceite: feedback do usuario aparece como dado operacional, nao apenas registro bruto.

- [ ] **Exportacao de feedback e outcomes**
  Criar endpoint/export CSV ou JSON para analise externa.
  Criterio de aceite: dados de feedback/outcomes podem ser usados para calibracao futura.

- [ ] **Registrar falso negativo do usuario**
  Adicionar feedback especifico de "deveria ter avisado" com par, exchange, periodo e nota.
  Criterio de aceite: falsos negativos ficam correlacionaveis com pipeline auditado.

---

## P1 - Produto E UX Operacional

- [ ] **Painel de mercado BRL**
  Mostrar universo elegivel por exchange, principais pares, pares quentes/mornos/frios, volume agregado e estado do mercado.
  Criterio de aceite: usuario entende o mercado monitorado alem da shortlist.

- [ ] **Motivo de ausencia de par**
  Na UI de catalogo/watchlist, explicar por que um par nao aparece ou nao e monitoravel.
  Criterio de aceite: pares esperados como `TON_BRL` ou `LAB_BRL` podem ser diagnosticados sem olhar logs.

- [ ] **Watchlist como prioridade configuravel**
  Permitir marcar favoritos para maior frequencia/visibilidade sem limitar o scanner global.
  Criterio de aceite: watchlist influencia prioridade, mas nao exclui o restante do mercado BRL.

- [ ] **Shortlist com explicabilidade de ranking**
  Mostrar principais fatores que colocaram um sinal acima de outro: liquidez, margem, fase, score, outcome, feedback.
  Criterio de aceite: usuario entende por que uma oportunidade foi ranqueada no topo.

- [ ] **Historico operacional melhorado**
  Filtros por fase, faixa operacional, momento do alerta, outcome label, feedback e motivo de bloqueio.
  Criterio de aceite: historico vira ferramenta de analise operacional, nao apenas lista de sinais.

---

## P2 - Aprendizado E Evolucao Do Motor

- [ ] **Ranking adaptativo por feedback**
  Usar feedback manual para ajustar pesos e reduzir falsos positivos recorrentes.
  Criterio de aceite: feedback afeta ranking apenas com limites, versao e auditoria.

- [ ] **Ranking adaptativo por falso negativo**
  Comparar eventos "deveria ter avisado" com pipeline e ajustar thresholds.
  Criterio de aceite: oportunidades perdidas recorrentes reduzem chance de novo descarte silencioso.

- [ ] **Sugestao automatica de novos pares para watchlist**
  Sugerir pares com historico de bons sinais ou falsos negativos.
  Criterio de aceite: usuario recebe sugestoes justificadas por dados.

- [ ] **Thresholds automaticos por exchange**
  Ajustar limites de volume, spread, liquidez e movimento conforme comportamento real de cada exchange.
  Criterio de aceite: Mercado Bitcoin e NovaDAX podem ter sensibilidades diferentes sem configuracao manual excessiva.

- [ ] **Modelo supervisionado com outcomes**
  Considerar somente apos 4-8 semanas de dados confiaveis.
  Criterio de aceite: modelo e versionado, auditavel e comparado contra heuristica antes de influenciar ranking.

- [ ] **Evolucao opcional da Binance**
  Robustecer Binance como modulo opcional, isolado de erros regulatorios/HTTP 451.
  Criterio de aceite: ativar Binance nao contamina o health de Mercado Bitcoin/NovaDAX.

---

## P2 - Persistencia, Custo E Egress

- [ ] **Catalogo persistido em banco, se necessario**
  Migrar cache em memoria para banco apenas se volume/instancias exigirem.
  Criterio de aceite: catalogo sobrevive a restart e mantem ultimo estado valido sem custo excessivo.

- [ ] **Governanca completa de retencao por camada**
  Definir TTL para `raw_market_observations`, `opportunities`, `technical_signals`, `workspace_signal_projections`, `signal_outcomes`, auditoria e agregados.
  Criterio de aceite: pruning/compactacao roda automaticamente e preserva agregados importantes.

- [ ] **Materializacoes ou agregados para analytics pesados**
  Evitar consultas longas no Supabase para dashboard/analytics.
  Criterio de aceite: analytics usa agregados ou endpoints resumidos e nao explode egress.

- [ ] **Benchmark de egress por tela**
  Medir payload e chamadas de dashboard, settings, history, analytics e auditoria.
  Criterio de aceite: cada tela tem orcamento de payload conhecido e monitoravel.

- [ ] **Revisao continua dos endpoints**
  Garantir payload minimo por tela, detalhes sob demanda e cache client/server quando aplicavel.
  Criterio de aceite: novas features nao reintroduzem historico completo ou dados brutos no frontend.

---

## P3 - SaaS E Multi-Tenant Maduro

- [ ] **Feature gates por plano**
  Middleware por `organization.plan` para limitar workspaces, Telegram, historico, auditoria, paper trading e membros.
  Criterio de aceite: rotas retornam bloqueio claro quando o plano nao permite a feature.

- [ ] **Stripe integration**
  Checkout, webhook de pagamento, falha de cobranca, downgrade e billing portal.
  Criterio de aceite: plano da organizacao muda automaticamente por eventos Stripe.

- [ ] **Planos e limites**
  Definir e aplicar Free, Pro, Trading e Enterprise.
  Criterio de aceite: limites sao enforceados no backend e comunicados na UI.

- [ ] **Autoregistro aberto com Free tier**
  Remover dependencia de convite para cadastro publico, adicionar verificacao de email.
  Criterio de aceite: usuario cria conta self-service com limites Free.

- [ ] **Email transacional**
  Convites, verificacao de email, reset de senha e avisos de billing.
  Criterio de aceite: fluxos criticos nao dependem de copiar senha manualmente.

- [ ] **Administracao de organizacao**
  Tela para plano, membros, workspaces, billing, limites e status.
  Criterio de aceite: owner gerencia a organizacao sem acesso direto ao banco.

---

## P4 - Fundacao Para Trading Futuro

Nao implementar antes de validar o produto de monitoramento com usuarios reais.

- [ ] **Governanca de historico para trading**
  Separar claramente observacao, sinal, projecao, outcome, decisao e execucao.
  Criterio de aceite: nenhuma decisao de trading usa `opportunities` diretamente.

- [ ] **Metadados de trading por par**
  Tamanho minimo de ordem, precisao, step size, status de trading e limites por exchange.
  Criterio de aceite: ordens futuras nao falham por metadados ausentes.

- [ ] **Consulta de saldo por exchange**
  Exibir saldo quando API keys privadas forem configuradas.
  Criterio de aceite: sistema calcula capacidade real antes de qualquer simulacao/ordem.

- [ ] **Paper trading**
  Simular entrada, saida, P&L, drawdown, win rate e decisoes.
  Criterio de aceite: performance de sinais e validada sem capital real.

- [ ] **Execucao manual confirmada**
  Telegram/UI com confirmacao explicita antes de ordem real.
  Criterio de aceite: toda ordem tem decisao auditada e log imutavel.

- [ ] **Gestao de posicoes**
  Entidade `Position`, status, stop, alvo, historico e resultado.
  Criterio de aceite: usuario ve posicoes abertas e fechadas por exchange/par.

- [ ] **Gestao de risco**
  Exposicao maxima por exchange/par, stop diario, tamanho por score, circuit breaker.
  Criterio de aceite: nenhuma execucao real ocorre sem regras de risco.

- [ ] **Execucao automatica**
  Apenas Enterprise/futuro. Pipeline: sinal versionado, decisao, risco, ordem, monitoramento, saida.
  Criterio de aceite: automacao e desligavel, auditavel e protegida por circuit breaker.

- [ ] **Portfolio e P&L**
  Visao consolidada em BRL por exchange, par, workspace e periodo.
  Criterio de aceite: usuario mede resultado real/simulado de forma confiavel.

---

## Itens Que Nao Devem Ser Priorizados Agora

- [ ] `raw_market_events` detalhado para todos os pares/ciclos.
- [ ] Machine learning antes de outcomes confiaveis.
- [ ] Trading automatico antes de paper trading e gestao de risco.
- [ ] Binance como fonte principal antes de consolidar Mercado Bitcoin/NovaDAX.
- [ ] Persistir candles/order book brutos de todo o mercado sem TTL e justificativa de custo.

---

## Ordem Recomendada De Execucao

1. Periodo customizado e enriquecimento do diagnostico de sinal perdido.
2. Explicabilidade por workspace e motivos completos de bloqueio de alerta.
3. Persistencia de cooldown/temperatura por provider/par.
4. Tela dedicada de auditoria operacional com funil por ciclo.
5. Refinamento de lateralizacao/rompimento e scores de fase/faixa.
6. Analytics de outcomes/feedback/falsos positivos.
7. Fluxo de falso negativo marcado pelo usuario.
8. Governanca de retencao por camada e benchmark de egress.
9. Feature gates por plano e Stripe.
10. Paper trading somente depois que outcomes e auditoria estiverem maduros.

---

## Criterio De Confianca Operacional

O sistema so deve ser considerado confiavel quando cumprir esta regra:

> Se uma oportunidade boa aparecer dentro do universo monitoravel, o sistema deve alertar, mostrar na shortlist, registrar como observavel, descartar com motivo claro ou registrar erro tecnico. Nunca deve simplesmente nao acontecer nada.
