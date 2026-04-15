# Changelog

Este arquivo passa a registrar mudancas relevantes do repositorio a partir de 2026-04-14.

O formato segue a ideia de "Keep a Changelog", adaptado para um projeto interno em fase inicial.

Convencao deste repositorio:
- cada entrada deve ser registrada na data em que a modificacao foi feita no repositorio, no formato `YYYY-MM-DD`
- `Unreleased` fica reservado apenas para trabalho ainda nao consolidado no dia

## [Unreleased]

- Nenhuma entrada em aberto.

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
