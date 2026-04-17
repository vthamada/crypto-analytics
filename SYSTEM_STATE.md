# Estado Atual do Sistema

Ultima revisao: 2026-04-17

## Objetivo deste documento

Este documento descreve o estado real do sistema hoje, como a arquitetura esta organizada, como os sinais sao gerados fim a fim e quais pontos merecem refinamento.

Ele foi escrito a partir do codigo em execucao no repositorio atual, nao apenas da documentacao historica.

## Resumo executivo

Hoje o sistema funciona como uma plataforma de monitoramento de oportunidades em cripto com dois blocos principais:

- `backend/`: API FastAPI, autenticacao, gestao de workspaces, persistencia, historico, analytics, auditoria, WebSocket, worker de scan dedicado e alertas Telegram.
- `frontend/`: aplicacao Next.js que autentica o usuario, escolhe o workspace ativo, consome REST e WebSocket e expoe dashboard, historico, analytics e configuracoes operacionais.

O ponto mais importante para entender o comportamento atual e este:

- o scanner e global
- as oportunidades detectadas sao globais
- cada oportunidade agora carrega tambem uma camada paralela de executabilidade
- a visibilidade final e recalculada por workspace
- o historico persistido e global, mas filtrado por workspace na leitura
- o WebSocket e isolado por workspace
- os alertas Telegram sao enviados por workspace

Em outras palavras, o produto ja tem autenticacao e autorizacao multi-workspace na camada de acesso e configuracao, mas ainda nao opera um pipeline fisicamente isolado por tenant.

## Arquitetura atual

Visao logica simplificada:

```text
Browser (Next.js)
    |
    | HTTP + WebSocket
    v
FastAPI
    |
    | usa contexto de sessao + workspace
    |
    +--> Rotas REST
    +--> Gerenciador WebSocket por workspace

Worker de scan
  |
  +--> Providers de exchange
  |       - NovaDAX
  |       - Mercado Bitcoin
  |       - Binance
  |
  +--> Filtros e score
  +--> Estado compartilhado em banco
  +--> Projecao por workspace
  +--> Alertas Telegram por workspace
```

Visao por modulo:

- `backend/app/main.py`: inicializa banco, bootstrap de admin, publica REST + WebSocket e pode opcionalmente subir o scanner local quando `SCANNER_ENABLED=true`.
- `backend/app/api/routes.py`: autentica a sessao, resolve o workspace, expoe dashboard, oportunidades, historico, analytics, configuracao, usuarios, invites e auditoria.
- `backend/app/api/websocket.py`: autentica conexoes e isola streams por workspace.
- `backend/app/services/scanner.py`: executa a coleta nas exchanges, aplica filtros, classifica o movimento, calcula score tecnico, calcula executabilidade e enriquece arbitragem cross-exchange.
- `backend/app/services/persistence.py`: persiste historico, le configuracoes por workspace, agrega configuracoes para o scanner global e recalcula score por workspace na leitura.
- `backend/app/services/shared_state.py`: persiste estado compartilhado entre worker e API, incluindo `scanner_runtime_state`, `opportunity_snapshots`, `technical_signals`, `workspace_signal_projections`, `signal_outcomes` e `repetition_counts`.
- `backend/app/worker.py`: processo dedicado de scan usado no fluxo padrao do `docker-compose.yml`.
- `backend/app/services/auth.py`: cuida de login, tokens, bootstrap do admin, organizacoes, workspaces, memberships, usuarios, invites e auditoria.
- `backend/app/services/pairs.py`: constroi o catalogo de pares disponiveis por exchange e filtra os pares realmente escaneaveis.
- `backend/app/services/telegram.py`: envia alertas e aplica cooldown por destino.
- `frontend/src/lib/api.ts`: cliente REST com tokens, refresh automatico e workspace ativo em storage.
- `frontend/src/lib/websocket.ts`: cliente WebSocket com reconexao e troca automatica quando a sessao ou o workspace mudam.
- `frontend/src/hooks/use-opportunities.ts`: carrega oportunidades e stats, assina o canal em tempo real e mantem polling de fallback.
- `frontend/src/app/settings/page.tsx`: area administrativa e operacional do workspace.
- `frontend/src/app/page.tsx`: dashboard em tempo real.
- `frontend/src/app/history/page.tsx`: historico e analytics.

## Modelo de operacao atual

### 1. Inicializacao do backend

Quando a API sobe, o `lifespan` do FastAPI executa este fluxo:

1. roda `init_db()` para aplicar migracoes e compatibilidade de schema
2. roda `ensure_admin_bootstrap()` para garantir usuario admin e workspace default quando configurados por ambiente
3. publica REST + WebSocket
4. se `SCANNER_ENABLED=true`, carrega configuracoes de workspace, monta a configuracao agregada e inicia o `scan_loop()` local

Observacao importante:

- o modo padrao do repositorio no `docker-compose.yml` e subir `backend` em modo API-only (`SCANNER_ENABLED=false`) e `worker` como processo dedicado de scan
- a API ainda suporta scanner local para execucao simples ou debug, mas esse nao e mais o fluxo operacional padrao do repositorio

## 2. Autenticacao, sessao e contexto de workspace

O sistema atual usa tokens assinados com HMAC a partir de `AUTH_SECRET_KEY` ou, como fallback, `ADMIN_TOKEN`.

Fluxo atual:

1. o usuario faz login em `/api/auth/login`
2. o backend valida usuario e senha no banco
3. o backend emite access token e refresh token
4. o frontend salva os tokens em `localStorage`
5. o frontend salva tambem o `workspace_id` ativo
6. as chamadas REST passam `Authorization`, `X-Admin-Token` e `X-Workspace-Id`
7. o WebSocket usa `token` e `workspace_id` na query string

Papeis atualmente relevantes:

- papel global de usuario: `admin` ou `member`
- papel dentro do workspace: `owner`, `admin` ou `member`

Regras operacionais importantes:

- dashboard, oportunidades, historico e analytics exigem sessao autenticada e workspace acessivel
- configuracao do workspace e auditoria exigem `owner` ou `admin` no workspace
- usuarios e invites exigem `owner` do workspace
- criacao de workspace hoje depende do papel global `admin` ou `owner` na sessao

## 3. Como o sistema gera um sinal hoje

Esta e a cadeia completa, do carregamento da configuracao ate a entrega na UI e no Telegram.

### Etapa A. Carregamento das configuracoes dos workspaces

No inicio de cada ciclo, o backend le todas as configuracoes armazenadas em `workspace_configs`.

Em seguida ele monta uma configuracao agregada para o scanner global com estas regras:

- `enabled_exchanges`: uniao de todas as exchanges habilitadas nos workspaces
- `enabled_pairs`: uniao de todos os pares habilitados nos workspaces
- `scan_interval_seconds`: menor intervalo entre todos os workspaces
- thresholds:
  - usa o menor `min_volatility_pct`
  - usa o menor `min_volume_brl`
  - usa o menor `min_volume_brl_small`
  - usa o menor `min_liquidity_units`
  - usa o maior `max_spread_pct`
- pesos: a configuracao agregada ainda carrega `weights=configs[0].weights` para o `score` operacional do scanner, mas a semantica duravel do motor tecnico agora e dada por `technical_score` neutro e `score_version`

O racional dessa agregacao e ampliar cobertura do scanner global para nao perder oportunidades relevantes para nenhum workspace.

Implicacao pratica:

- o motor global passa a escanear a uniao de tudo que algum workspace quer ver
- a decisao final de visibilidade e score e feita depois, por workspace

### Etapa B. Catalogo de pares disponiveis por exchange

Antes do scan, o sistema cruza os pares habilitados com um catalogo de disponibilidade por exchange.

Esse catalogo:

- consulta `get_available_pairs()` em NovaDAX, Mercado Bitcoin e Binance
- normaliza os pares em formato interno
- guarda cache por 1 hora
- expoe esse estado em `/api/pairs/available`

Esse passo evita tentar escanear um par em uma exchange que nao o suporta.

Se o catalogo falha, o sistema degrada para um comportamento mais permissivo:

- usa todos os pares habilitados para todas as exchanges ativas

### Etapa C. Execucao do scan por exchange e par

O `Scanner` instancia um provider para cada exchange habilitada.

Para cada combinacao valida de `exchange + pair`, ele executa em paralelo:

- `get_ticker(pair)`
- `get_order_book(pair)`
- `get_klines(pair, interval="5m", limit=50)`

Se qualquer uma dessas chamadas falha para aquele par, o sinal e descartado naquele ciclo.

### Etapa D. Filtros obrigatorios

Se os dados forem carregados com sucesso, o scanner aplica os filtros na seguinte ordem:

1. volatilidade minima
2. volume minimo
3. liquidez minima
4. spread maximo

Na pratica, o par so continua se passar por todos.

Thresholds usados hoje:

- volatilidade: `min_volatility_pct`
- volume: `min_volume_brl` ou `min_volume_brl_small`
- liquidez: `min_liquidity_units`
- spread: `max_spread_pct`

### Etapa E. Classificacao do tipo de movimento

Depois dos filtros, o sistema classifica o movimento recente com base nos candles mais recentes.

Classes atuais:

- `strong_range`: movimento relativamente consistente e com conviccao
- `spike`: candle final dominante, sugerindo esticao brusca
- `weak`: sinal fraco ou sem confirmacao suficiente
- `trap`: movimento com cara de reversao ou armadilha

Essa classificacao usa:

- proporcao entre corpo e sombra dos candles
- consistencia de direcao
- tendencia de volume
- presenca de reversao recente

### Etapa F. Calculo do score base, do score tecnico e da camada de executabilidade

O sistema hoje trabalha com dois conceitos relacionados, mas distintos:

- `score`: score operacional da oportunidade no ciclo corrente
- `technical_score`: score tecnico neutro, persistido com `score_version` e independente dos pesos do workspace
- `executability_score`: score paralelo de operabilidade, persistido com `executability_version` e sem sobrescrever o score tecnico

Ambos usam cinco componentes, todos normalizados para escala `0..1` antes da combinacao ponderada:

- volatilidade
- volume
- liquidez
- spread
- repeticao

Pesos default atuais:

- volatilidade: `0.30`
- volume: `0.25`
- liquidez: `0.20`
- spread: `0.15`
- repeticao: `0.10`

Como a repeticao funciona hoje:

- o scanner mantem um contador por `exchange + pair`
- quanto mais vezes o mesmo sinal reaparece em ciclos consecutivos, maior o componente de repeticao
- esse contador e restaurado de `repetition_counts` no inicio do ciclo e decai automaticamente quando fica inativo por muito tempo

Depois da soma ponderada, o sistema aplica um modificador por tipo de movimento:

- `strong_range`: `1.15`
- `spike`: `1.05`
- `weak`: `0.70`
- `trap`: `0.50`

O `technical_score` e calculado com pesos default fixos em `shared_state.py` e versionado por `SCORE_VERSION`.

Em paralelo, a camada de executabilidade usa os dados do order book para responder se o sinal parece operavel de verdade.

Componentes atuais da executabilidade:

- liquidez em notional nos dois lados do book
- slippage estimado de compra para uma ordem baseline
- slippage estimado de venda para uma ordem baseline
- spread efetivo
- volume em quote
- notional preenchivel dentro do cap de slippage

Campos produzidos hoje no `Opportunity`:

- `bid_notional_top_n`
- `ask_notional_top_n`
- `total_notional_top_n`
- `estimated_buy_slippage_bps`
- `estimated_sell_slippage_bps`
- `fillable_notional_within_slippage_cap`
- `executability_score`
- `executability_band`

Bandas atuais de executabilidade:

- `strong`
- `good`
- `fair`
- `poor`

Classificacoes operacionais derivadas:

- `interesting_signal`: heuristica inicial baseada no score tecnico/base
- `operable_signal`: heuristica inicial baseada em `executability_score`, cap de slippage de saida e spread efetivo

### Etapa G. Calibracao historica

Depois do score base, o sistema aplica um fator adicional por par usando historico recente.

Essa calibracao olha aproximadamente as ultimas `168` horas de historico e calcula um fator entre `0.9` e `1.15`, considerando:

- media historica de score do par
- quantidade de ocorrencias do par
- media do gap cross-exchange do par

Objetivo pratico:

- dar um pequeno ajuste para pares que historicamente aparecem com melhor qualidade ou maior recorrencia

### Etapa H. Enriquecimento cross-exchange e arbitragem

Depois de detectar as oportunidades individualmente, o scanner agrupa os resultados por par.

Se o mesmo par existir em mais de uma exchange no mesmo ciclo, ele calcula:

- exchange mais barata
- exchange mais cara
- gap percentual entre os precos
- referencia de preco e exchange para comparacao

O sistema tambem estima uma friccao simples:

- spread da exchange mais barata
- spread da exchange mais cara
- mais `0.2` como folga fixa

Se o gap for maior que essa friccao estimada:

- `arbitrage_available = true`
- o score da oportunidade recebe um boost adicional de `5%`

### Etapa I. Persistencia do historico e do estado compartilhado

As oportunidades detectadas alimentam mais de uma camada de persistencia.

Camadas persistidas no ciclo atual:

- `opportunity_snapshots`: snapshot corrente compartilhado entre worker e API
- `technical_signals`: identidade semantica do sinal tecnico com `technical_score` e `score_version`
- `workspace_signal_projections`: materializacao por workspace para auditoria e analytics
- `signal_outcomes`: outcomes pendentes e avaliados em janelas de 5m, 15m, 1h e 4h
- `opportunities`: historico global resumido, mantido por compatibilidade operacional
- `repetition_counts`: estado persistido da repeticao entre ciclos

O historico em `opportunities` guarda, entre outros campos:

- exchange
- pair
- score
- volatilidade
- volume
- liquidez
- spread
- tipo de movimento
- preco
- gap cross-exchange
- flag de arbitragem
- componentes individuais de score
- `technical_score`
- `score_version`
- `technical_signal_id`
- `executability_score`
- `executability_band`
- `interesting_signal`
- `operable_signal`
- metricas de notional e slippage do book
- `executability_version`, `movement_version`, `profile_version`

Existe uma deduplicacao simples:

- o mesmo `exchange + pair` so e salvo uma vez a cada 5 minutos

Efeito pratico:

- evita crescer uma linha por ciclo para sinais estaveis
- reduz granularidade historica para sinais que persistem por muitos ciclos

Existe tambem uma retencao periodica:

- registros antigos sao removidos conforme `history_retention_days`

Em paralelo, o sistema cria outcomes pendentes para novos sinais tecnicos e avalia resultados de sinais anteriores em janelas configuradas a partir do preco de entrada.

### Etapa J. Projecao por workspace

Depois que as oportunidades globais sao geradas, o sistema recalcula a visibilidade e o score para cada workspace.

Para cada workspace, ele faz:

1. verifica se a oportunidade respeita os filtros do workspace
2. verifica se a exchange esta habilitada nesse workspace
3. verifica se o par esta habilitado nesse workspace
4. recalcula o `workspace_score` com os pesos do workspace a partir dos componentes tecnicos
5. preserva os componentes tecnicos, o fator historico e a camada de executabilidade

Esse passo e feito por `project_workspace_opportunity()`.

O que isso significa na pratica:

- uma oportunidade pode existir no estado global, mas nao aparecer para um workspace especifico
- dois workspaces podem ver scores diferentes para a mesma oportunidade base
- a projecao por workspace preserva `executability_score`, `executability_band` e `operable_signal`; ela recalcula apenas o `workspace_score`
- essa projecao tambem pode ser materializada em `workspace_signal_projections` para auditoria e analytics

### Etapa K. Entrega em tempo real

Depois da projecao por workspace, o backend envia uma mensagem WebSocket separada para cada workspace:

- tipo: `opportunities_update`
- dados: lista de oportunidades visiveis para aquele workspace
- timestamp do ciclo
- quantidade de sinais

O `ConnectionManager` mantem listas de conexoes em memoria por `workspace_id`.

Para leitura REST, a API agora usa o estado em memoria local quando ele existe e faz fallback para `opportunity_snapshots` quando esta rodando em modo API-only.

No frontend:

1. o dashboard faz carga inicial via REST
2. o hook `useOpportunities()` assina o WebSocket
3. quando recebe `opportunities_update`, ele atualiza a tabela
4. o frontend tambem refaz os stats
5. existe polling de fallback a cada 30 segundos

### Etapa L. Alertas Telegram

Depois da projecao por workspace, o sistema verifica cada workspace separadamente.

Um alerta so e enviado se:

- o workspace tem Telegram habilitado
- existe `telegram_bot_token`
- existe `telegram_chat_id`
- existem oportunidades acima do `telegram_alert_threshold` configurado para aquele workspace

O cooldown atual:

- e aplicado por destino, nao globalmente
- a chave considera `chat_id + digest do token + exchange + pair`

Isso evita que um workspace silencie o outro quando ambos usam destinos diferentes.

## 4. O que cada endpoint representa operacionalmente

Leituras operacionais:

- `/api/dashboard/stats`: usa o estado atual em memoria ou faz fallback para `opportunity_snapshots`, sempre projetando para o workspace atual
- `/api/opportunities`: lista as oportunidades correntes em memoria ou no snapshot compartilhado, ja filtradas e re-scoreadas para o workspace atual, com suporte a ordenacao por `score` ou `executability` e filtro `operable_only`
- `/api/opportunities/{id}`: detalhe do sinal corrente
- `/api/history`: le o historico persistido e reaplica filtros do workspace
- `/api/analytics`: agrega o historico filtrado para o workspace
- `/api/pairs/available`: mostra o catalogo de pares e disponibilidade por exchange
- `/api/health`: expande o status com `mode` (`scanner` ou `api_only`), `scanner_state`, providers e conexoes WebSocket

Gestao e operacao:

- `/api/config`: le e atualiza a configuracao do workspace atual
- `/api/config/validate-exchanges`: valida credenciais das exchanges para o workspace
- `/api/config/telegram/test`: envia mensagem de teste para o Telegram do workspace
- `/api/admin/audit-log`: lista a auditoria do workspace
- `/api/workspaces`: lista workspaces acessiveis ou cria novos
- `/api/users`: lista ou cria usuarios do workspace
- `/api/invites`: lista ou cria convites do workspace

## 5. Modelo de dados atual

Entidades persistidas mais importantes:

- `organizations`: organizacao logica do usuario e dos workspaces
- `users`: identidade do usuario autenticado
- `workspaces`: unidades de configuracao e visibilidade
- `workspace_memberships`: papel do usuario dentro do workspace
- `workspace_configs`: configuracao operacional por workspace
- `invites`: convites para entrada de novos usuarios
- `audit_logs`: trilha de auditoria
- `opportunities`: historico global das oportunidades detectadas
- `scanner_runtime_state`: ultimo ciclo do scanner, duracao, erro, ultimo sucesso e score versionado
- `opportunity_snapshots`: estado corrente compartilhado entre worker e API
- `technical_signals`: identidade semantica do sinal tecnico
- `workspace_signal_projections`: projecao materializada por workspace
- `signal_outcomes`: tracking de resultado temporal por sinal tecnico
- `repetition_counts`: estado persistido da repeticao entre ciclos
- `config`: tabela legada, mantida por compatibilidade com o workspace default

Ponto importante:

- as oportunidades persistidas nao carregam `workspace_id`
- o isolamento por workspace acontece na leitura e na projecao, nao na escrita do historico bruto

## 6. Como o frontend opera hoje

### Dashboard

O dashboard principal:

- exige token + workspace ativo
- carrega `stats` e `opportunities` por REST
- escuta WebSocket por workspace
- mostra KPIs, checklist de onboarding e tabela de oportunidades
- suporta leitura dual entre payload legado e payload com executabilidade
- permite alternar o ranking principal entre score tecnico e operabilidade
- destaca `interesting_signal` e `operable_signal` com badges e razoes operacionais
- abre modal de detalhe com os dados do sinal selecionado, incluindo liquidez BRL, slippage e banda de executabilidade quando disponiveis

### Historico e analytics

A tela de historico:

- exige token + workspace ativo
- consome `/history` e `/analytics`
- permite recorte temporal por horas
- mostra distribuicao de scores, top pares, movimentos, distribuicao horaria e registros historicos

### Configuracoes

A tela de configuracoes hoje concentra:

- login e refresh de sessao
- troca do workspace ativo
- leitura e atualizacao de thresholds, pesos, exchanges, pares e Telegram
- autosave da configuracao operacional
- validacao de credenciais das exchanges
- teste de Telegram
- criacao de workspace
- gestao de usuarios e invites
- auditoria do workspace

Capacidades exibidas na UI variam conforme o papel do usuario no workspace atual.

## 7. O que o sistema e hoje, e o que ele ainda nao e

O sistema e hoje:

- um scanner global de oportunidades de mercado
- uma separacao operacional entre API e worker no fluxo padrao do repositorio
- uma camada autenticada de isolamento de acesso por workspace
- uma camada de configuracao operacional por workspace
- uma interface em tempo real por workspace
- uma trilha basica de auditoria e operacao

O sistema ainda nao e:

- um pipeline fisicamente isolado por tenant
- uma arquitetura distribuida para escalar horizontalmente o scanner e o streaming
- um sistema com persistencia historica nativamente segregada por workspace
- um motor de score calibrado por feedback real de performance de sinais
- um frontend que explique toda a camada de executabilidade com boa UX; isso ainda entra na Release D do plano operacional

## 8. Pontos de refinamento mais importantes

Os pontos abaixo sao os que mais importam se o objetivo for evoluir o produto com menos ambiguidade operacional.

### Refinamento 1. Isolamento real por workspace

Hoje o isolamento e forte na autorizacao e na entrega, mas nao no pipeline bruto.

Sintoma atual:

- o scanner e global
- a escrita de historico e global
- o workspace so entra na etapa de projecao e leitura

Quando isso pode ser suficiente:

- operacao interna
- baixo numero de workspaces
- workspaces com preferencias semelhantes

Quando isso passa a doer:

- workspaces com regras muito diferentes
- necessidade de auditoria estrita por tenant
- necessidade de custo por tenant
- necessidade de SLA por tenant

Refinamento sugerido:

- separar claramente `evento bruto detectado` de `sinal publicado para workspace`
- decidir se a persistencia historica deve armazenar tambem a projecao por workspace ou se deve existir uma camada de materializacao por tenant

### Refinamento 2. Semantica da configuracao agregada

Hoje o scanner global usa a uniao de exchanges e pares e thresholds mais permissivos para cobrir todos os workspaces.

Isso funciona para nao perder cobertura, mas tem custo:

- aumenta volume de scan para workspaces pequenos
- o score operacional do scanner usa pesos do primeiro workspace carregado
- a configuracao efetiva do motor global nao representa fielmente nenhum workspace individual

Refinamento sugerido:

- consolidar `technical_score` como semantica neutra principal do motor
- reduzir dependencias restantes do `score` operacional agregado quando ele nao for estritamente necessario
- manter ranking final por workspace como derivacao posterior

### Refinamento 3. Scanner local opcional vs worker dedicado

Hoje a API suporta scanner local, mas o fluxo padrao do repositorio usa worker dedicado e API em modo `api_only`.

Riscos atuais:

- se houver mais de um scanner ativo ao mesmo tempo, pode haver duplicacao de scan e alertas
- o WebSocket continua dependente de memoria local da instancia da API
- o estado corrente ainda depende de snapshot compartilhado e nao de barramento distribuido

Refinamento sugerido:

- manter `backend/app/worker.py` como produtor principal do scan
- manter a API apenas como camada de leitura, configuracao e streaming
- evitar uso acidental de scanner local em producao sem coordenacao explicita

### Refinamento 4. WebSocket em memoria

O gerenciamento de conexoes e feito em memoria no processo FastAPI.

Consequencias:

- simples e suficiente para uma unica instancia
- inadequado para multiplas replicas sem barramento externo

Refinamento sugerido:

- se houver necessidade de escalar, introduzir Redis Pub/Sub, fila ou event bus entre worker e API

### Refinamento 5. Historico deduplicado por 5 minutos

A deduplicacao atual reduz ruida operacional, mas perde resolucao temporal.

Impacto:

- bom para evitar explosao de linhas
- ruim para analise fina de recorrencia, duracao e estabilidade do sinal

Refinamento sugerido:

- separar historico resumido de eventos de scan
- ou salvar eventos completos em outra tabela com TTL diferente

### Refinamento 6. Score ainda e heuristico

O score atual e coerente, mas ainda e uma heuristica estatica.

Limites atuais:

- ja existe feedback de resultado apos o sinal em `signal_outcomes`, mas ainda falta volume historico suficiente para calibracao seria
- sem validacao empirica de thresholds por par ou exchange
- sem ajuste por horario, regime de mercado ou liquidez real de execucao

Refinamento sugerido:

- registrar outcome posterior do sinal
- validar taxa de acerto por faixa de score
- validar taxa de acerto tambem por faixa de `executability_score`
- calibrar pesos com historico real, nao apenas com heuristica manual

### Refinamento 7. Segredos operacionais

As credenciais ficam armazenadas na configuracao do workspace e sao sanitizadas quando lidas pela API, mas continuam existindo como segredo operacional persistido.

Refinamento sugerido:

- decidir se as credenciais devem permanecer no banco
- ou se devem migrar para secret store externo por ambiente ou por workspace

### Refinamento 8. Observabilidade ainda basica

Ja existe `scan_monitor`, health enriquecido, Sentry opcional e agregacao HTTP de logs opcional.

Ainda falta maturidade para operacao mais forte em producao:

- dashboards externos
- alertas de falha de provider
- metricas historicas de latencia, erro e volume por exchange
- rastreabilidade mais facil entre mudanca de config e comportamento do scanner

## 9. Perguntas que ajudam a decidir os proximos refinamentos

Se voce quiser avaliar o proximo passo do produto, estas sao as perguntas que mais reduzem ambiguidade:

1. O objetivo e manter uma operacao interna controlada ou virar SaaS multi-tenant mais estrito?
2. O historico precisa representar sinais globais do motor ou sinais publicados por workspace?
3. O score precisa refletir uma heuristica comum do sistema ou uma preferencia propria de cada workspace?
4. A politica de Telegram por workspace esta adequada ou precisa de mais dimensoes como tipos de alerta, cooldown e regras por movimento?
5. O scanner precisa escalar horizontalmente em breve, ou uma unica instancia dedicada ainda resolve?
6. Existe necessidade de provar isolamento forte entre workspaces para fins operacionais ou comerciais?

## 10. Conclusao pratica

Hoje o sistema ja esta acima de um MVP simples:

- ha autenticacao real
- ha contexto de workspace
- ha configuracao operacional por workspace
- ha separacao API/worker no fluxo padrao do repositorio
- ha streaming isolado por workspace
- ha historico, analytics, auditoria e alertas Telegram por workspace

Mas o nucleo de geracao do sinal ainda e um motor global com projecao posterior por workspace, mesmo com a separacao operacional entre API e worker.

Esse continua sendo o principal ponto arquitetural a ter em mente ao decidir refinamentos futuros. Se a ambicao continuar sendo uma plataforma interna com alguns workspaces, o desenho atual pode servir bem. Se a ambicao for um produto multi-tenant mais estrito e escalavel, a prioridade tecnica passa a ser separar melhor a geracao bruta, a materializacao por workspace e o transporte em tempo real.
