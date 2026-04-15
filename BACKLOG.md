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

- [ ] **Autoregistro por convite**
  Admin gera link com codigo unico e prazo de validade (ex: 7 dias, uso unico).
  Usuario abre o link, preenche email + senha — conta criada sem admin precisar estar online.
  Fundacao para autoregistro aberto do SaaS: so troca o guard de "codigo valido" por "email verificado".

- [ ] **Entidade Organization (fundacao do SaaS)**
  Criar `Organization` como unidade de cobranca acima dos workspaces atuais.
  `User` pertence a uma `Organization`; `Workspace` e subdivisao dela.
  Campos: `plan`, `stripe_customer_id`, `subscription_status`, `trial_ends_at`.
  Implementar agora evita refatoracao maior quando o SaaS for lancado.

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

- [ ] **Modelo de permissoes por workspace**
  Roles `owner`, `admin`, `member`:
  - `member`: visualiza dashboard e historico
  - `admin`: configura thresholds, pares, Telegram
  - `owner`: + gerencia membros e plano de cobranca

- [ ] **Scanner dedicado por worker**
  Extrair scanner de `backend/app/worker.py` (scaffold ja existe) para processo separado.
  Comunicacao via banco ou Redis pub/sub.
  Obrigatorio antes de ter dezenas de tenants ativos.

- [ ] **Notificacoes por workspace**
  Cada workspace usa seu proprio bot Telegram.
  Hoje o Telegram le do `.env` — ja esta na estrutura de config, falta o dispatch correto.

- [ ] **Auditoria no frontend**
  Endpoint `/api/admin/audit-log` existe mas sem tela. Pagina de auditoria para admins.

- [ ] **Deploy de producao endurecido**
  Postgres como padrao, rotacao de segredos, HTTPS obrigatorio, ALLOWED_ORIGINS configurado,
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

1. **P0** — Criar usuarios + refresh token + reset de senha
   *Permite que seu pai tenha conta propria com sessao confortavel*

2. **P1** — Autoregistro por convite + entidade Organization
   *Estrutura certa desde o inicio; zero retrabalho quando o SaaS chegar*

3. **P1** — Pares dinamicos por exchange
   *Zera manutencao manual da lista; resolve MATIC/POL e listagens futuras*

4. **P1** — Mobile responsivo + onboarding
   *Qualquer pessoa convidada consegue usar sem orientacao presencial*

5. **P3** — Feature gates + Stripe
   *Liga o modelo de negocio sem mudar a arquitetura*

6. **P4** — Paper trading → execucao manual → automatica (nao pula fases)**
