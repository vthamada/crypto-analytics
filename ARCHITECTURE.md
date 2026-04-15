# Architecture

## Visao Geral

O projeto e um monorepo com dois blocos principais:
- `backend/`: API FastAPI, scanner assincrono, persistencia e integracoes externas.
- `frontend/`: aplicacao Next.js que consome REST e WebSocket para exibir o painel.

Fluxo principal:
1. O backend inicia, sobe o banco, garante bootstrap de usuario admin e workspace default.
2. O backend monta uma configuracao de scan agregada a partir dos `workspace_configs`.
3. Um loop de scan consulta exchanges e produz oportunidades com componentes de score.
4. O backend persiste oportunidades globais e recalcula score/filtros por workspace nas leituras.
5. O frontend consome dados iniciais por REST, seleciona o workspace ativo e recebe atualizacoes por WebSocket.

## Estrutura de Diretorios

### Backend
- `backend/app/main.py`: bootstrap da aplicacao, lifespan, scanner loop, CORS.
- `backend/app/api/routes.py`: endpoints REST para dashboard, oportunidades, historico, analytics e configuracao.
- `backend/app/api/websocket.py`: gerenciamento de conexoes WebSocket.
- `backend/app/services/scanner.py`: orquestracao da coleta, filtros e score.
- `backend/app/services/persistence.py`: gravacao e leitura no banco.
- `backend/app/services/telegram.py`: envio de alertas.
- `backend/app/providers/`: adaptadores das exchanges.
- `backend/app/filters/`: regras de filtragem e score.
- `backend/app/models/`: schemas Pydantic e modelos SQLAlchemy.
- `backend/app/config.py`: configuracao via ambiente.

### Frontend
- `frontend/src/app/page.tsx`: dashboard principal.
- `frontend/src/app/history/page.tsx`: historico e analytics.
- `frontend/src/app/settings/page.tsx`: configuracoes operacionais.
- `frontend/src/components/`: componentes de UI e dashboard.
- `frontend/src/lib/api.ts`: cliente REST.
- `frontend/src/lib/websocket.ts`: cliente WebSocket com reconexao.
- `frontend/src/hooks/use-opportunities.ts`: carga inicial e sincronizacao de oportunidades.

## Componentes Principais

### 1. Scanner

O scanner:
- instancia providers por exchange habilitada
- percorre os pares habilitados
- coleta `ticker`, `order_book` e `klines`
- aplica filtros de volatilidade, volume, liquidez e spread
- classifica movimento
- calcula score
- gera objetos `Opportunity`

Arquivo central:
- `backend/app/services/scanner.py`

## 2. Providers

Cada provider implementa a interface comum:
- `get_ticker`
- `get_order_book`
- `get_trades`
- `get_klines`
- `normalize_pair`
- `get_available_pairs`

Objetivo:
- esconder diferencas entre as APIs das exchanges
- entregar contratos internos uniformes para o scanner

## 3. Persistencia

Persistencia atual:
- oportunidades em tabela `opportunities`
- configuracao legada em tabela `config`
- configuracao por tenant em `workspace_configs`
- usuarios em `users`
- workspaces em `workspaces`
- memberships em `workspace_memberships`
- auditoria em `audit_logs`

Implementacao:
- SQLAlchemy async
- deduplicacao simples por `exchange + pair` numa janela curta para historico

Arquivo central:
- `backend/app/services/persistence.py`

## 4. Multi-Tenant

O modelo atual separa:
- autenticacao em nivel de usuario
- configuracao e preferencias em nivel de workspace
- auditoria com escopo de workspace

Desenho atual:
- o scanner continua sendo um processo global
- o scan usa configuracao mesclada de todos os workspaces para nao perder cobertura
- score, filtros e visibilidade final sao recalculados por workspace nas rotas REST

Arquivos centrais:
- `backend/app/services/auth.py`
- `backend/app/api/routes.py`
- `frontend/src/lib/api.ts`
- `frontend/src/app/settings/page.tsx`

## 4. API REST

Principais grupos de endpoints:
- `/api/dashboard/stats`
- `/api/opportunities`
- `/api/history`
- `/api/analytics`
- `/api/config`
- `/api/health`

Caracteristicas:
- dashboard atual usa estado em memoria para oportunidades correntes
- historico e analytics usam banco
- configuracao e persistida em banco

## 5. WebSocket

O backend mantem conexoes WebSocket em memoria e publica:
- lista atual de oportunidades
- timestamp do scan
- quantidade de sinais

O frontend:
- abre conexao unica
- reconecta em caso de falha
- atualiza a tabela em tempo real

## Modelo de Dados

Entidades principais:
- `Ticker`
- `OrderBook`
- `Trade`
- `Kline`
- `Opportunity`
- `AppConfig`
- `DashboardStats`

Persistido em banco:
- `OpportunityRecord`
- `ConfigRecord`

## Decisoes Atuais de Arquitetura

### Escolhas boas para o estagio atual
- separacao clara entre provider, filtro, servico e modelo
- uso de Pydantic para contrato interno
- backend assincrono para IO externo
- frontend tipado e alinhado com os contratos do backend

### Limitacoes atuais
- scanner roda dentro do mesmo processo da API
- estado de oportunidades correntes fica em memoria
- configuracao administrativa nao tem autenticacao
- segredo operacional pode ser exposto pela API/UI
- sem testes automatizados cobrindo o comportamento principal

## Pontos de Atencao

### Seguranca
- `/api/config` hoje e um ponto sensivel
- CORS esta permissivo
- credenciais aparecem no modelo de configuracao

### Escalabilidade
- mais de um worker pode duplicar scanner e alertas
- WebSocket atual nao esta preparado para broadcast entre multiplos processos

### Confiabilidade
- providers dependem de APIs externas com limites e indisponibilidade eventual
- Telegram ainda nao tem mecanismo robusto de deduplicacao de alerta

## Evolucao Recomendada

### Curto prazo
1. Adicionar autenticacao para rotas administrativas.
2. Corrigir reconfiguracao do scanner em runtime.
3. Ajustar cooldown dos alertas.
4. Alinhar build Docker do frontend.
5. Corrigir dependencias do backend.

### Medio prazo
1. Extrair scanner para worker dedicado.
2. Adotar migracoes com Alembic.
3. Adicionar testes de integracao e unitarios.
4. Melhorar observabilidade.

### Longo prazo
1. Introduzir analytics cross-exchange.
2. Evoluir score com calibracao historica.
3. Separar estado em memoria de um barramento/event stream mais robusto.
