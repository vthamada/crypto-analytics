# Changelog

Este arquivo passa a registrar mudancas relevantes do repositorio a partir de 2026-04-14.

O formato segue a ideia de "Keep a Changelog", adaptado para um projeto interno em fase inicial.

## [Unreleased]

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

### Known Issues
- A camada multi-tenant ainda esta orientada a operadores internos; ainda nao existe onboarding completo de usuarios finais nem convite/recuperacao de conta.

## [2026-04-14]

### Noted
- Repositorio identificado como monorepo com `backend` em FastAPI/Python e `frontend` em Next.js/React.
- Documentacao existente concentrada em `SPEC.md` e `DEPLOY.md`.
- Frontend com dashboard, historico e configuracoes ja implementados.
- Backend com scanner, persistencia, WebSocket e integracoes com NovaDAX, Mercado Bitcoin e Binance.
