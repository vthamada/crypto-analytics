# Backlog

Ultima revisao: 2026-04-15

Legenda: `[x]` concluido · `[ ]` pendente · `[~]` parcialmente feito

---

## Decisoes tomadas

| Decisao | Escolha |
|---|---|
| Registro de usuarios | Autoregistro por convite (beta) → autoregistro aberto + Free tier (SaaS publico) |
| Scanner | Global com recalculo por workspace na leitura — 1 scan serve todos sem multiplicar chamadas as exchanges |
| Trading | Sequencial: Monitoramento → Paper trading → Manual confirmado → Automatico |
| Exchange prioritaria | **Binance** — maior liquidez em BRL, API mais madura, rate limits generosos, 0.1% de fee |
| Unidade de cobranca (SaaS) | `Organization` — e a conta que paga; `Workspace` e subdivisao operacional dentro dela |
| Modelo de planos | Free / Pro / Trading / Enterprise (ver tabela em P3) |

---

## Arquitetura alvo

```
Organization  ← unidade de cobranca (tem plano, Stripe customer)
  ├── Plan: free | pro | trading | enterprise
  ├── Members: usuario A (owner), usuario B (admin), ...
  ├── Workspace "Scalping"
  │     └── Config: thresholds proprios, pares, pesos de score, Telegram
  └── Workspace "Swing Trade"
        └── Config: thresholds diferentes
```

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
- [x] Testes de integracao para rotas principais do backend
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
- [x] Login com credenciais, access token assinado e refresh token
- [x] Seletor de workspace no frontend
- [x] Configuracao administrativa e auditoria isoladas por workspace

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

- [x] **Criar usuarios pelo admin** — endpoint `POST /api/users` (admin cria contas com usuario+senha temporaria) e tela "Usuarios" no frontend para listar, criar e desativar contas. Sem isso o pai nao tem conta propria.

- [x] **Refresh token** — sessao atual expira em 8h sem renovacao silenciosa. Implementar refresh token de 30 dias: o access token (8h) e renovado automaticamente enquanto o refresh token for valido. Usuario so ve tela de login apos 30 dias de inatividade.

- [x] **Redefinicao de senha** — se alguem esquecer a senha o unico caminho e alterar as vars de ambiente e reiniciar o servidor. Fluxo de reset gerado pelo admin agora emite credencial temporaria e obriga troca no primeiro login.

---

## P1 — Bloqueia crescimento para mais usuarios

- [x] **Autoregistro por convite**
  Admin gera link com codigo unico e prazo de validade (ex: 7 dias, uso unico).
  Usuario abre o link, preenche email + senha — conta criada sem admin precisar estar online.
  Fundacao para autoregistro aberto do SaaS: so troca o guard de "codigo valido" por "email verificado".

- [x] **Entidade Organization (fundacao do SaaS)**
  Criar `Organization` como unidade de cobranca acima dos workspaces atuais.
  `User` pertence a uma `Organization`; `Workspace` e subdivisao dela.
  Campos: `plan`, `stripe_customer_id`, `subscription_status`, `trial_ends_at`.
  Implementar agora evita refatoracao maior quando o SaaS for lancado.

- [x] **Pares dinamicos por exchange** — catalogo e UI usam descoberta via `get_available_pairs()` com cache no backend de 1h. Novos workspaces recebem selecao inicial derivada do catalogo, e o scanner cruza `enabled_pairs` com a disponibilidade real por exchange antes de consultar os providers:
  ```
  BTC/BRL   [NovaDAX ✓] [Mercado BTC ✓] [Binance ✓]
  PEPE/BRL  [NovaDAX ✗] [Mercado BTC ✗] [Binance ✓]
  ```
  Endpoint `GET /api/pairs/available`. Resolve o problema de pares renomeados (ex: MATIC→POL).

- [x] **Mobile responsivo** — tabela do dashboard tem 10 colunas, quebra em celular. Implementada visao em cards para telas pequenas (`sm:`) mantendo a tabela completa no desktop.

- [x] **Onboarding de novos usuarios** — quando uma pessoa entra pela primeira vez nao ha nenhuma orientacao. Implementada checklist inicial no dashboard com conclusao persistida por usuario.

- [x] **Scanner hot-reload de configuracao** — mudar exchanges/pares habilitados na UI agora sinaliza wake-up imediato do scanner sem reiniciar o servidor.

- [x] **Teste de Telegram na UI** — botao "Enviar mensagem de teste" nas Configuracoes dispara uma mensagem real para o bot configurado, usando os valores digitados ou as credenciais persistidas do workspace.

- [x] **Validacao de API keys das exchanges** — apos salvar chaves de API, o sistema valida acesso real e mostra status por exchange: ausente, valida, invalida, sem permissao de trade ou erro.

---

## P2 — Qualidade e confiabilidade

- [x] **Politica de retencao do historico** — scanner e worker agora executam limpeza periodica configuravel (`HISTORY_RETENTION_DAYS`, `HISTORY_RETENTION_CHECK_MINUTES`) para remover registros antigos sem depender de manutencao manual.

- [x] **Testes E2E do frontend** — Playwright cobre login administrativo, troca de workspace com configuracao isolada, dashboard em tempo real e falha de historico com feedback visual.

- [x] **Testes de workspace e membership no backend** — cobertura agora valida isolamento de config por tenant, membership por workspace e projecao de score recalculada por workspace.

- [x] **Tratamento de erros no frontend** — app ganhou `error.tsx`, `global-error.tsx`, toaster global para falhas de API/WebSocket/runtime e estados inline de erro no dashboard e historico.

---

## P3 — Plataforma SaaS e multi-tenant madura

- [ ] **Feature gates por plano**
  Middleware que verifica `organization.plan` antes de servir cada feature.
  Retorna `402 Payment Required` com mensagem clara quando limite e atingido.
  Ex: workspace adicional bloqueado no Free; Telegram bloqueado no Free; paper trading so no Trading+.

- [ ] **Stripe integration (cobranca)**
  Tres eventos criticos a reagir:
  - `checkout.session.completed` → ativa o plano
  - `invoice.payment_failed` → aviso, bloqueia apos grace period
  - `customer.subscription.deleted` → downgrade para Free
  Self-service billing portal (Stripe fornece pagina pronta — so redirecionar).

- [ ] **Planos e limites**
  | | Free | Pro (~R$49/mes) | Trading (~R$149/mes) | Enterprise (~R$499/mes) |
  |---|---|---|---|---|
  | Pares | 3 | Ilimitado | Ilimitado | Ilimitado |
  | Exchanges | 1 | 3 | 3 | 3 |
  | Telegram | Nao | Sim | Sim | Sim |
  | Historico | 7 dias | 90 dias | 180 dias | 1 ano |
  | Paper trading | Nao | Nao | Sim | Sim |
  | Execucao manual | Nao | Nao | Sim | Sim |
  | Execucao automatica | Nao | Nao | Nao | Sim |
  | Membros por org | 1 | 2 | 3 | 10 |
  | Trial gratuito | 14 dias | — | — | — |

- [ ] **Autoregistro aberto com Free tier**
  Remover guard de convite, adicionar verificacao de email.
  Free tier com limites automaticamente aplicados.
  Stripe Checkout para upgrade de plano.

- [x] **Modelo de permissoes por workspace**
  Rotas e UI agora usam a membership do workspace ativo, em vez do papel global do usuario.
  Roles `owner`, `admin`, `member`:
  - `member`: visualiza dashboard e historico
  - `admin`: configura thresholds, pares, Telegram e auditoria
  - `owner`: + gerencia membros e convites do workspace

- [ ] **Scanner dedicado por worker**
  Extrair scanner de `backend/app/worker.py` (scaffold ja existe) para processo separado.
  Comunicacao via banco ou Redis pub/sub.
  Obrigatorio antes de ter dezenas de tenants ativos.

- [x] **Notificacoes por workspace**
  O dispatch agora projeta oportunidades por workspace e envia alertas usando o bot/chat configurado naquele workspace, sem depender do token/chat mesclado global.

- [x] **Isolamento do tempo real e leituras publicas**
  Leituras operacionais agora exigem sessao autenticada, e o WebSocket autentica a conexao e publica somente para o workspace ativo.

- [x] **Auditoria no frontend**
  Pagina de configuracoes exibe auditoria recente do workspace ativo para administradores.

- [ ] **Deploy de producao endurecido**
  Postgres como padrao, rotacao de segredos, HTTPS obrigatorio, `cors_allowed_origins` configurado,
  health check conectado a monitoramento externo.

---

## P4 — Fundacao para trading (Binance prioritaria)

> Implementar apos o produto de monitoramento estar validado com usuarios reais e receita recorrente estabelecida. Cada fase valida a anterior antes de arriscar capital real.

- [ ] **Metadados de trading por par (Binance)**
  Enriquecer cache de pares com: tamanho minimo de ordem, precisao de preco (step size), status de trading.
  Pre-requisito para qualquer execucao sem erros da exchange.

- [ ] **Busca de saldo por exchange**
  Quando API keys estao configuradas, exibir saldo disponivel.
  Pre-requisito para calcular tamanho de posicao.

- [ ] **Paper trading — Fase 1 do trading**
  Simula entradas e saidas com base nos sinais detectados, sem dinheiro real.
  Entidade `SimulatedTrade`: par, exchange, preco de entrada, preco de saida, resultado %.
  Dashboard de performance: win rate, retorno medio, drawdown maximo.
  Validacao obrigatoria antes de colocar capital real. Disponivel no plano Trading.

- [ ] **Execucao manual confirmada — Fase 2 do trading**
  Sinal detectado → alerta Telegram com botao "Executar".
  Usuario confirma → ordem executada via API privada da Binance.
  Log imutavel de todas as ordens.
  Disponivel no plano Trading.

- [ ] **Gestao de posicoes**
  Entidade `Position`: par, exchange, preco de entrada, quantidade, stop-loss, target, status.
  Historico de posicoes fechadas com resultado em BRL e percentual.

- [ ] **Gestao de risco (obrigatoria antes do automatico)**
  Regras por workspace:
  - Exposicao maxima por exchange (ex: max 30% do capital na Binance)
  - Exposicao maxima por par (ex: max 10% em DOGE)
  - Stop global diario (ex: parar se perda > 2% no dia)
  - Tamanho de posicao por faixa de score (score 80+ = 2x tamanho padrao)

- [ ] **Motor de execucao automatica — Fase 3 do trading**
  Pipeline: sinal → verificacao de risco → calculo de tamanho → ordem → monitoramento → saida.
  Circuit breaker: parar se perda acumulada > limite configurado.
  Disponivel no plano Enterprise.

- [ ] **Portfolio e P&L**
  Visao consolidada de posicoes abertas e trades fechados.
  Resultado em BRL e percentual por exchange e por par.

---

## Proximos passos (ordem de implementacao)

1. **P3** — Feature gates por plano + Stripe
  *Liga monetizacao em cima da arquitetura de Organization ja implantada*

2. **P3** — Scanner dedicado por worker
  *Isola carga operacional do app web antes de escalar tenants e frequencia de scans*

3. **P3** — Autoregistro aberto com Free tier
  *Abre a entrada self-service do produto sem depender de convite manual para o plano inicial*

4. **P3** — Deploy de producao endurecido
  *Fecha os requisitos operacionais minimos antes de tratar o ambiente como producao real*

5. **P4** — Paper trading → execucao manual → automatica (nao pula fases)
