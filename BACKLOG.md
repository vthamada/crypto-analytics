# Backlog

Ultima revisao: 2026-04-15. Itens derivados da analise tecnica e das decisoes de produto.

Legenda: `[x]` concluido · `[ ]` pendente · `[~]` parcialmente feito

---

## Concluido (historico)

### Seguranca e acesso
- [x] Proteger `/api/config` com autenticacao e autorizacao
- [x] Impedir leitura de segredos no frontend e no endpoint de configuracao
- [x] Restringir CORS no backend para dominios confiaveis
- [x] Senha admin com hash (PBKDF2-SHA256), token assinado com `token_version`
- [x] Revocacao automatica de tokens ao trocar senha

### Qualidade e estabilidade
- [x] Testes unitarios para filtros e score
- [x] Testes de integracao para rotas principais do backend (14 passando)
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
- [x] Login admin com credenciais, token JWT, sessao de 8h
- [x] Seletor de workspace no frontend
- [x] Configuracao e auditoria isoladas por workspace

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

- [ ] **Criar usuarios pelo admin** — endpoint `POST /api/users` (admin cria contas com usuario+senha temporaria) e tela "Usuarios" no frontend para listar, criar e desativar contas. Sem isso o pai nao tem conta propria.

- [ ] **Refresh token** — sessao atual expira em 8h sem renovacao silenciosa. Implementar refresh token de 30 dias: o access token (8h) e renovado automaticamente enquanto o refresh token for valido. Usuario so ve tela de login apos 30 dias de inatividade.

- [ ] **Redefinicao de senha** — se alguem esquecer a senha o unico caminho e alterar as vars de ambiente e reiniciar o servidor. Implementar fluxo de reset gerado pelo admin (gera token temporario que o usuario usa no primeiro login).

---

## P1 — Bloqueia crescimento para mais usuarios

- [ ] **Pares dinamicos por exchange** — substituir lista hardcoded de pares por descoberta dinamica via `get_available_pairs()` (ja existe nos providers). Cache no backend com TTL de 1h. UI de selecao com busca e indicador por exchange:
  ```
  BTC/BRL   [NovaDAX ✓] [Mercado BTC ✓] [Binance ✓]
  PEPE/BRL  [NovaDAX ✗] [Mercado BTC ✗] [Binance ✓]
  ```
  Endpoint `GET /api/pairs/available`. Resolve o problema de pares renomeados (ex: MATIC→POL).

- [ ] **Mobile responsivo** — tabela do dashboard tem 10 colunas, quebra em celular. Implementar visao em cards para telas pequenas (`sm:`). A maioria dos usuarios externos vai acessar pelo celular.

- [ ] **Onboarding de novos usuarios** — quando uma pessoa entra pela primeira vez nao ha nenhuma orientacao. Implementar tela de boas-vindas com checklist: configurar Telegram, selecionar pares, entender os scores.

- [ ] **Scanner hot-reload de configuracao** — verificar e garantir que mudar exchanges/pares habilitados na UI recarregue o scanner imediatamente sem reiniciar o servidor. O CHANGELOG indica que foi parcialmente resolvido mas precisa de validacao.

- [ ] **Teste de Telegram na UI** — botao "Enviar mensagem de teste" nas Configuracoes que dispara uma mensagem real para o bot configurado. Elimina a incerteza de "sera que esta funcionando?".

- [ ] **Validacao de API keys das exchanges** — apos salvar chaves de API, validar com uma chamada autenticada simples (ex: buscar saldo ou permissoes). Mostrar status: chave valida/invalida/sem permissao de trading.

---

## P2 — Qualidade e confiabilidade

- [ ] **Politica de retencao do historico** — banco cresce indefinidamente mesmo com deduplicacao. Implementar job periodico que deleta registros com mais de 90 dias (configuravel). Critico para plataforma com muitos usuarios.

- [ ] **Testes E2E do frontend** — login, troca de workspace, configuracao isolada, dashboard em tempo real. Hoje zero cobertura automatizada de interface.

- [ ] **Testes de workspace e membership no backend** — cobertura atual nao cobre cenarios de multi-tenant: criacao de workspace, configuracao isolada por tenant, projecao de score por workspace.

- [ ] **Tratamento de erros no frontend** — crashes silenciosos quando a API retorna erro. Implementar error boundary global e feedback visual para o usuario (toast de erro, estado de falha nos componentes).

- [ ] **Convite por link** — admin gera link de convite com prazo de validade. Usuario abre, define senha e ja entra no workspace correto. Mais elegante que senha temporaria.

---

## P3 — Plataforma multi-tenant madura

- [ ] **Modelo de permissoes por workspace** — roles `owner`, `admin`, `member` com operacoes distintas. Ex: member ve dashboard mas nao altera configuracoes; admin configura mas nao cria workspaces.

- [ ] **Scanner dedicado por worker** — hoje o scanner roda no mesmo processo da API FastAPI. Extrair para `backend/app/worker.py` (scaffold ja existe) com comunicacao via DB ou Redis pub/sub. Permite escalar a API horizontalmente sem duplicar o scanner.

- [ ] **Notificacoes por workspace** — cada workspace configura seu proprio bot Telegram. Hoje o Telegram e global. Com multi-tenant real cada usuario recebe alertas no proprio canal.

- [ ] **Auditoria expandida no frontend** — hoje existe endpoint `/api/admin/audit-log` mas nenhuma tela de auditoria no frontend. Implementar pagina de auditoria para admins verem historico de acoes.

- [ ] **Deploy de producao endurecido** — Postgres como padrao (nao SQLite), rotacao de segredos, ALLOWED_ORIGINS configurado, HTTPS obrigatorio, health check conectado a monitoramento externo (UptimeRobot ou similar).

---

## P4 — Fundacao para trading automatizado

> Estas features representam uma evolucao significativa de arquitetura. Implementar apenas apos o produto de monitoramento estar validado com usuarios reais.

- [ ] **Metadados de trading por par** — enriquecer cache de pares com: tamanho minimo de ordem, precisao de preco (step size), status de trading (ativo/suspenso). Necessario para qualquer execucao automatizada sem erros da exchange.

- [ ] **Busca de saldo por exchange** — quando API keys estao configuradas, exibir saldo disponivel por exchange e moeda. Pre-requisito para calcular tamanho de posicao.

- [ ] **Paper trading (simulacao)** — simular entradas e saidas com base nas oportunidades detectadas, sem dinheiro real. Registrar resultado hipotetico de cada trade. Permite validar a qualidade do scoring antes de arriscar capital.
  - Entidade `SimulatedTrade`: par, exchange, entrada, saida, resultado %
  - Dashboard de performance do paper trading

- [ ] **Gestao de posicoes** — entidade `Position` com: par, exchange, preco de entrada, quantidade, stop-loss, target, status (aberta/fechada/stopada).

- [ ] **Motor de execucao de ordens** — modulo isolado que recebe sinal de oportunidade, verifica saldo, calcula tamanho de posicao e executa ordem via API privada da exchange. Deve ter:
  - Circuit breaker (parar se perda acumulada > limite)
  - Log imutavel de todas as ordens
  - Modo manual (confirma antes de executar) e automatico (executa direto)

- [ ] **Gestao de risco** — regras configuradas por workspace:
  - Exposicao maxima por exchange (ex: max 30% do capital na Binance)
  - Exposicao maxima por par (ex: max 10% em DOGE)
  - Stop global diario (ex: parar se perda > 2% do portfolio no dia)
  - Tamanho de posicao por score (score 80+ = 2x tamanho padrao)

- [ ] **Portfolio e P&L** — visao consolidada de todas as posicoes abertas e historico de trades fechados, com resultado em BRL e percentual.

---

## Decisoes de produto em aberto

| Decisao | Opcoes | Status |
|---|---|---|
| Usuario cadastra sozinho ou apenas admin cria? | Autoregistro aberto vs convite | Pendente — depende de se vai ser SaaS publico ou plataforma fechada |
| Scanner global ou por workspace? | Global (eficiente) vs por workspace (isolado) | Decidir antes de escalar para 10+ workspaces |
| Trading: manual confirmado ou totalmente automatico? | Manual tem menos risco, automatico e o objetivo final | Comecar com manual, evoluir para automatico |
| Qual exchange priorizar para trading? | NovaDAX (BR, menor liquidez) vs Binance (global, maior liquidez) | Validar com paper trading primeiro |
