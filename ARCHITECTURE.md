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
- coleta `ticker`, `order_book` e `klines`
- aplica filtros e calcula score
- enriquece arbitragem cross-exchange
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

## Decisoes arquiteturais atuais

### Escolhas consistentes com o estagio atual

- separacao entre API e worker no fluxo padrao do repositorio
- `technical_score` neutro e versionado por `score_version`
- fallback da API para snapshots compartilhados
- WebSocket isolado por workspace
- backend assincrono para IO externo
- frontend tipado e alinhado com contratos do backend

### Limitacoes ainda abertas

- o scanner continua global, nao isolado fisicamente por tenant
- o WebSocket depende de memoria local da instancia da API
- o `score` operacional do scanner ainda usa configuracao agregada com pesos do primeiro workspace carregado
- nao ha barramento pub/sub dedicado; em `api_only` a API observa o estado compartilhado e repropaga snapshots, mas isso ainda nao equivale a broadcast distribuido entre multiplas replicas

## Pontos de atencao

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
