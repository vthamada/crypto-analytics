# Backlog

Backlog inicial derivado da analise tecnica do repositorio em 2026-04-14.

## P0 - Corrigir antes de expor em producao

- [x] Proteger `/api/config` com autenticacao e autorizacao.
- [x] Impedir leitura de segredos no frontend e no endpoint de configuracao.
- [x] Restringir CORS no backend para dominios confiaveis.
- [x] Fazer o `Scanner` reagir corretamente a mudancas de configuracao em runtime.
- [x] Adicionar cooldown/deduplicacao para alertas do Telegram.
- [x] Ajustar `frontend/next.config.ts` para `output: "standalone"` ou corrigir o `frontend/Dockerfile`.
- [x] Adicionar `aiosqlite` ao `backend/pyproject.toml` ou trocar o banco padrao.

## P1 - Estabilizar o produto

- [x] Criar testes unitarios para filtros e score.
- [x] Criar testes de integracao para rotas principais do backend.
- [x] Criar mocks/fakes para providers de exchange.
- [x] Tratar melhor erros e rate limit nos providers.
- [x] Garantir que analytics respeitem filtros de periodo usados na tela de historico.
- [x] Revisar persistencia para registrar eventos sem perder contexto relevante do sinal.
- [x] Melhorar logs estruturados do scanner e dos providers.

## P2 - Operacao e manutencao

- [x] Criar `.env.example` com todas as variaveis de ambiente necessarias.
- [x] Substituir `frontend/README.md` boilerplate por documentacao real do projeto.
- [x] Adicionar pipeline CI para lint, build e testes.
- [x] Incluir log aggregation externa.
- [x] Incluir health checks mais completos.
- [x] Incluir integracao opcional com Sentry.
- [x] Avaliar migracoes com Alembic em vez de `create_all`.
- [x] Documentar fluxo local de desenvolvimento e troubleshooting.

## P3 - Evolucao funcional

- [x] Adicionar filtros mais avancados no dashboard.
- [x] Expandir analytics historicos no frontend.
- [x] Implementar comparacao cross-exchange e arbitragem simples.
- [x] Evoluir scoring com calibracao baseada em historico.
- [x] Preparar separacao do scanner para worker dedicado.

## Decisoes Atuais

- [x] A tela de configuracoes continua permitindo atualizar credenciais sensiveis, mas a leitura desses valores pela UI e pela API permanece bloqueada.
- [x] O projeto agora possui base multiusuario com `users + workspaces`, mantendo `ADMIN_TOKEN` apenas como fallback legado.
- [x] O historico permanece orientado a eventos deduplicados, agora enriquecidos com contexto cross-exchange e fator historico.
- [x] SQLite continua como default local; o backend aceita troca de `DATABASE_URL` para Postgres e o schema agora passa por Alembic.

## Proximos Passos

1. Evoluir onboarding de usuarios: convite, recuperacao de senha e criacao de membros sem depender do bootstrap por variavel de ambiente.
2. Definir a estrategia de execucao por tenant: manter scanner global com configuracao mesclada ou migrar para processamento isolado por workspace.
3. Adicionar testes E2E do frontend para login, troca de workspace, configuracao isolada e auditoria.
4. Endurecer o deploy de producao: Postgres como alvo principal, rotacao de segredos e observabilidade externa completa.
5. Refinar o modelo de permissoes por workspace para suportar owner/admin/member com operacoes diferentes no frontend e na API.
