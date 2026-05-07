# Architecture

## Visao geral

O projeto e um monorepo com dois blocos principais:

- `backend/`: API FastAPI, worker dedicado de scan, persistencia e integracoes externas
- `frontend/`: aplicacao Next.js que consome REST e WebSocket para exibir dashboard, historico, analytics e configuracoes

No fluxo padrao do repositorio:

1. a API sobe em modo `api_only`
2. o worker executa o scan global usando configuracao agregada dos workspaces
3. o worker grava snapshots, sinais tecnicos, projecoes e outcomes no banco
4. a API le estado local quando existe e faz fallback para o estado compartilhado em banco
5. o frontend consome REST, assina WebSocket e usa polling de fallback

Para detalhes operacionais completos, use [SYSTEM_STATE.md](SYSTEM_STATE.md) como documento principal.

## Estrutura de diretorios

### Backend

- `backend/app/main.py`: bootstrap da API, CORS, lifespan e scanner local opcional
- `backend/app/worker.py`: processo dedicado de scan
- `backend/app/api/routes.py`: endpoints REST operacionais e administrativos
- `backend/app/api/websocket.py`: gerenciamento de conexoes WebSocket por workspace
- `backend/app/services/scanner.py`: coleta, filtros, score e enriquecimento cross-exchange
- `backend/app/services/shared_state.py`: contrato compartilhado entre worker e API
- `backend/app/services/persistence.py`: historico, configuracoes, analytics e score por workspace
- `backend/app/services/auth.py`: autenticacao, workspaces, memberships, convites e auditoria
- `backend/app/services/telegram.py`: envio de alertas e cooldown por destino
- `backend/app/providers/`: adaptadores das exchanges
- `backend/app/filters/`: regras de filtragem e componentes do score
- `backend/app/models/`: schemas Pydantic e modelos SQLAlchemy

### Frontend

- `frontend/src/app/page.tsx`: dashboard principal
- `frontend/src/app/history/page.tsx`: historico e analytics
- `frontend/src/app/settings/page.tsx`: configuracoes e administracao do workspace
- `frontend/src/hooks/use-opportunities.ts`: carga inicial, WebSocket e polling de fallback
- `frontend/src/lib/api.ts`: cliente REST com sessao e refresh token
- `frontend/src/lib/websocket.ts`: cliente WebSocket com reconexao
- `frontend/src/lib/opportunity-operability.ts`: helpers de leitura dual, ranking e explicabilidade operacional

## Componentes principais

### 1. API

A API e responsavel por:

- autenticacao e contexto de workspace
- leitura de oportunidades correntes, historico e analytics
- configuracao operacional por workspace
- auditoria, usuarios, convites e workspaces
- distribuicao em tempo real via WebSocket

### 2. Worker de scan

O worker:

- carrega configuracao agregada dos workspaces
- instancia providers por exchange
- usa Mercado Bitcoin e NovaDAX como nucleo BRL padrao; Binance so entra no ciclo quando estiver habilitada manualmente
- grava auditoria compacta do funil em `scanner_cycle_audits` e `signal_pipeline_events`, permitindo explicar se um par foi candidato, descartado, ranqueado, bloqueado ou alertado sem persistir candles/order book brutos
- faz triagem leve por `ticker`/volume/movimento antes de chamadas caras
- usa temperatura em memoria e cooldown por provider/par para reduzir chamadas repetidas em pares frios ou problemáticos
- coleta `order_book` e `klines` somente para candidatos promovidos ao estagio profundo
- aplica filtros, calcula score tecnico e camada de executabilidade
- enriquece arbitragem cross-exchange
- classifica o sinal como `interesting_signal` e `operable_signal`
- grava o estado compartilhado do ciclo
- projeta oportunidades por workspace e dispara alertas Telegram
- avalia outcomes pendentes de sinais anteriores

### 3. Estado compartilhado

O contrato compartilhado entre API e worker usa banco para persistir:

- `scanner_runtime_state`
- `opportunity_snapshots`
- `technical_signals`
- `workspace_signal_projections`
- `signal_outcomes`
- `repetition_counts`

Isso permite que a API opere sem scanner local e continue servindo leituras REST a partir do estado do worker.

### 4. Multi-tenant

O modelo atual separa:

- autenticacao em nivel de usuario
- configuracao e preferencia em nivel de workspace
- unidade de cobranca em `Organization`
- auditoria com escopo de workspace

O scanner continua global e a visibilidade final e recalculada por workspace.

Com a camada de executabilidade atual:

- o motor global continua produzindo `score` e `technical_score`
- a operabilidade entra como camada paralela via `executability_score`
- a projecao por workspace preserva a semantica de executabilidade e recalcula apenas o ranking contextual do workspace

No frontend atual:

- a leitura continua funcionando com payload legado, sem exigir os novos campos
- o dashboard usa payload resumido por padrao e busca detalhe completo sob demanda ao abrir o modal
- quando `executability_score` existe, o dashboard passa a explicar o sinal com badges, ranking por operabilidade e detalhe operacional

## Modelo de dados principal

Entidades de runtime e API:

- `Opportunity`
- `AppConfig`
- `DashboardStats`
- `WorkspaceSummary`
- `UserSession`

Entidades persistidas mais relevantes:

- `OpportunityRecord`
- `ScannerRuntimeStateRecord`
- `OpportunitySnapshotRecord`
- `TechnicalSignalRecord`
- `WorkspaceSignalProjectionRecord`
- `SignalOutcomeRecord`
- `RepetitionCountRecord`
- `WorkspaceConfigRecord`
- `AuditLogRecord`

Campos operacionais recentes relevantes em `Opportunity` e nas camadas persistidas:

- `technical_score`, `score_version`
- `executability_score`, `executability_band`, `executability_version`
- `interesting_signal`, `operable_signal`
- `bid_notional_top_n`, `ask_notional_top_n`, `total_notional_top_n`
- `estimated_buy_slippage_bps`, `estimated_sell_slippage_bps`
- `fillable_notional_within_slippage_cap`
- `movement_persistence_score`, `movement_version`, `profile_version`

## Decisoes arquiteturais atuais

### Escolhas consistentes com o estagio atual

- separacao entre API e worker no fluxo padrao do repositorio
- `technical_score` neutro e versionado por `score_version`
- scanner em dois estagios para monitorar mercado BRL amplo sem consultar book/candles de todos os pares
- temperatura/cooldown em memoria como primeira etapa incremental antes de persistir scheduler por par
- telemetria agregada de triagem em `/api/health`, sem persistir descartes detalhados de todos os pares
- endpoints leves (`/api/dashboard/summary`, `/api/opportunities/active`, `/api/opportunities/shortlist`) para reduzir payload em telas operacionais
- catalogo de pares observavel com status por provider em `/api/pairs/available`
- fallback da API para snapshots compartilhados
- WebSocket isolado por workspace
- backend assincrono para IO externo
- frontend tipado e alinhado com contratos do backend

### Limitacoes ainda abertas

- o scanner continua global, nao isolado fisicamente por tenant
- o WebSocket depende de memoria local da instancia da API
- o `score` operacional do scanner ainda usa configuracao agregada com pesos do primeiro workspace carregado
- a camada de executabilidade ja e parametrizada por workspace, mas ainda nao modela duracao util do movimento nem reweighting automatico por outcome
- nao ha barramento pub/sub dedicado; em `api_only` a API observa o estado compartilhado e repropaga snapshots, mas isso ainda nao equivale a broadcast distribuido entre multiplas replicas

## Pontos de atencao

### Historico e automacao futura

- muitas paginas de registros no historico sao esperadas para um scanner continuo, mas nao devem crescer indefinidamente sem governanca
- o historico tem valor para paper trading e trading automatizado somente se preservar rastreabilidade entre observacao, sinal, projecao, decisao, execucao e outcome
- `opportunities` deve continuar como feed/historico operacional de compatibilidade, nao como unica fonte de verdade para automacao
- `raw_market_observations`, `technical_signals`, `workspace_signal_projections` e `signal_outcomes` formam a base correta para evoluir analytics e calibracao
- antes de qualquer execucao automatica, ainda sera necessario introduzir entidades explicitas de decisao e execucao, alem de politica real de retencao/compactacao por camada
- a funcao de retencao existe no backend, mas a execucao periodica precisa ser validada no fluxo real do worker/API para evitar acumulo silencioso

### Escalabilidade

- mais de um scanner ativo pode duplicar scan e alertas
- WebSocket atual nao faz broadcast entre multiplas replicas da API

### Confiabilidade

- providers dependem de APIs externas com rate limit e indisponibilidade eventual
- o frontend depende de polling de fallback quando nao recebe broadcast em tempo real

### Multi-tenant

- historico bruto continua global
- projecao por workspace acontece depois da deteccao

## Evolucao recomendada

Os proximos passos arquiteturais estao em [BACKLOG.md](BACKLOG.md), com foco principal em:

1. feature gates e monetizacao por plano
2. endurecimento de deploy e operacao
3. melhoria do transporte em tempo real entre worker e API
4. evolucao incremental do motor de sinais com indicadores adicionais e outcomes
