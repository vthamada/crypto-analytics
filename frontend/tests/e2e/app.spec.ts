import { expect, test, type Locator, type Page, type Route } from "@playwright/test";

const AUTH_TOKEN = "test-access-token";
const REFRESH_TOKEN = "test-refresh-token";

type MockApiState = {
  stats: {
    total_opportunities: number;
    active_opportunities: number;
    monitored_pairs: number;
    total_volume_24h: number;
    best_score: number;
    exchanges_online: number;
    arbitrage_opportunities: number;
    last_scan: string | null;
  };
  opportunities: Array<Record<string, unknown>>;
  configs: Record<string, Record<string, unknown>>;
  historyErrorMessage?: string;
  analyticsErrorMessage?: string;
};

test("login administrativo carrega configuracao isolada por workspace", async ({ page }) => {
  const state = createMockApiState();
  await mockApi(page, state);

  await page.goto("/settings");

  await loginAsAdmin(page);
  await page.getByText("Intervalo de varredura (seg)").scrollIntoViewIfNeeded();
  await expect(page.getByTestId("settings-scan-interval")).toHaveValue("15");

  await page.getByTestId("settings-workspace-ws-beta").click();
  await page.getByText("Intervalo de varredura (seg)").scrollIntoViewIfNeeded();
  await expect(page.getByTestId("settings-scan-interval")).toHaveValue("45");
});

test("dashboard aplica atualizacao em tempo real via websocket mockado", async ({ page }) => {
  const state = createMockApiState();
  await mockApi(page, state);

  await page.goto("/settings");
  await loginAsAdmin(page);
  await installMockWebSocket(page);
  await page.goto("/");

  await expect(page.locator('[data-testid="opportunity-opp-alpha"]:visible')).toBeVisible();
  await expect(page.getByTestId("kpi-value-opportunities")).toHaveText("1");

  state.opportunities = [
    buildOpportunity({
      id: "opp-live",
      pair: "ETH_BRL",
      exchange: "binance",
      score: 92,
      arbitrage_available: true,
      cross_exchange_gap_pct: 1.8,
    }),
  ];
  state.stats = {
    ...state.stats,
    total_opportunities: 3,
    active_opportunities: 2,
    monitored_pairs: 2,
    best_score: 92,
    arbitrage_opportunities: 1,
  };

  await page.evaluate(() => {
    (window as unknown as { __dispatchMockSocketMessage?: (payload: unknown) => void }).__dispatchMockSocketMessage?.({
      type: "opportunities_update",
      data: [
        {
          id: "opp-live",
          exchange: "binance",
          pair: "ETH_BRL",
          score: 92,
          volatility_pct: 4.1,
          volume_24h: 2200000,
          quote_volume_24h: 2200000,
          liquidity_units: 3100,
          spread_pct: 0.35,
          movement_type: "spike",
          last_price: 18432.11,
          change_pct: 5.4,
          detected_at: "2025-01-15T10:00:00.000Z",
          duration_minutes: 12,
          cross_exchange_gap_pct: 1.8,
          cross_exchange_reference_exchange: "novadax",
          cross_exchange_reference_price: 18105.22,
          arbitrage_available: true,
          historical_confidence: 0.91,
        },
      ],
    });
  });

  await expect(page.locator('[data-testid="opportunity-opp-live"]:visible')).toBeVisible();
  await expect(page.getByTestId("kpi-value-opportunities")).toHaveText("3");
});

test("dashboard continua funcional com payload legado sem executabilidade", async ({ page }) => {
  const state = createMockApiState({
    opportunities: [
      buildOpportunity({
        id: "opp-legacy",
        pair: "BTC_BRL",
        exchange: "novadax",
        score: 81,
      }),
    ],
  });
  await mockApi(page, state);

  await page.goto("/settings");
  await loginAsAdmin(page);
  await page.goto("/");

  await expect(page.locator('[data-testid="opportunity-opp-legacy"]:visible')).toBeVisible();
  await expect(page.getByText("Payload atual ainda nao traz executabilidade. Mantendo leitura tecnica.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Operabilidade" })).toBeDisabled();
});

test("dashboard explica operabilidade quando o payload novo esta disponivel", async ({ page }) => {
  const state = createMockApiState({
    opportunities: [
      buildOpportunity({
        id: "opp-operable",
        pair: "ETH_BRL",
        exchange: "binance",
        score: 88,
        technical_score: 84.2,
        score_version: "v1",
        executability_version: "v1",
        executability_score: 76.4,
        executability_band: "good",
        interesting_signal: true,
        operable_signal: true,
        bid_notional_top_n: 12000,
        ask_notional_top_n: 11800,
        total_notional_top_n: 23800,
        estimated_buy_slippage_bps: 8.2,
        estimated_sell_slippage_bps: 9.4,
        fillable_notional_within_slippage_cap: 2600,
      }),
    ],
  });
  await mockApi(page, state);

  await page.goto("/settings");
  await loginAsAdmin(page);
  await page.goto("/");

  await page.getByRole("button", { name: "Operabilidade" }).click();
  const opportunityCard = page.locator('[data-testid="opportunity-opp-operable"]:visible');
  await expect(opportunityCard.getByText("Operavel").first()).toBeVisible();
  await expect(opportunityCard.getByText("Liquidez OK")).toBeVisible();

  await opportunityCard.click();
  await expect(page.getByText("Leitura operacional")).toBeVisible();
  await expect(page.getByText("Slippage compra")).toBeVisible();
  await expect(page.getByText("Executabilidade")).toBeVisible();
});

test("history exibe erro inline e toast global quando a API falha", async ({ page }) => {
  const state = createMockApiState({
    historyErrorMessage: "Serviço de histórico indisponível.",
    analyticsErrorMessage: "Serviço de histórico indisponível.",
  });
  await mockApi(page, state);

  await page.goto("/settings");
  await loginAsAdmin(page);
  await page.goto("/history");

  await expect(page.getByText("Falha ao carregar dados")).toBeVisible();
  await expect(page.getByRole("main").getByText("Serviço de histórico indisponível.")).toBeVisible();
  await expect(page.getByTestId("global-error-toast")).toContainText("Serviço de histórico indisponível.");
});

test("settings mantém labels acentuados e controles compactos na UI administrativa", async ({ page }) => {
  const state = createMockApiState();
  await mockApi(page, state);

  await page.goto("/settings");
  await loginAsAdmin(page);

  await expect(page.getByRole("link", { name: "Configurações" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Histórico" })).toBeVisible();
  await expect(page.getByText("Usuários do workspace")).toBeVisible();
  await expect(page.getByText("Volatilidade mínima (%)")).toBeVisible();
  await expect(page.getByText("Catálogo (2)")).toBeVisible();

  const inviteButton = page.getByTestId("settings-create-invite-button");
  await inviteButton.scrollIntoViewIfNeeded();
  await expect(inviteButton).toBeVisible();

  const userButton = page.getByTestId("settings-create-user-button");
  await userButton.scrollIntoViewIfNeeded();
  await expect(userButton).toBeVisible();

  const volatilityControl = page.getByTestId("settings-threshold-volatility");
  await volatilityControl.scrollIntoViewIfNeeded();
  await expect(volatilityControl).toBeVisible();

  const weightControl = page.getByTestId("settings-weight-volatility");
  await weightControl.scrollIntoViewIfNeeded();
  await expect(weightControl).toBeVisible();

  const inviteWidth = await widthOf(inviteButton);
  const userWidth = await widthOf(userButton);
  const volatilityWidth = await widthOf(volatilityControl);
  const weightWidth = await widthOf(weightControl);

  expect(inviteWidth).toBeLessThan(220);
  expect(userWidth).toBeLessThan(220);
  expect(volatilityWidth).toBeGreaterThan(260);
  expect(volatilityWidth).toBeLessThan(410);
  expect(weightWidth).toBeGreaterThan(260);
  expect(weightWidth).toBeLessThan(410);
});

function createMockApiState(overrides?: Partial<MockApiState>): MockApiState {
  return {
    stats: {
      total_opportunities: 1,
      active_opportunities: 1,
      monitored_pairs: 1,
      total_volume_24h: 1500000,
      best_score: 81,
      exchanges_online: 3,
      arbitrage_opportunities: 0,
      last_scan: "2025-01-15T10:00:00.000Z",
    },
    opportunities: [
      buildOpportunity({
        id: "opp-alpha",
        pair: "BTC_BRL",
        exchange: "novadax",
        score: 81,
      }),
    ],
    configs: {
      "ws-alpha": buildConfig({
        scan_interval_seconds: 15,
        enabled_pairs: ["BTC_BRL"],
        telegram_chat_id: "1001",
      }),
      "ws-beta": buildConfig({
        scan_interval_seconds: 45,
        enabled_pairs: ["ETH_BRL", "SOL_BRL"],
        telegram_chat_id: "2002",
      }),
    },
    ...overrides,
  };
}

async function mockApi(page: Page, state: MockApiState) {
  await page.route("**/api/**", async (route) => {
    await fulfillMockApi(route, state);
  });
}

async function loginAsAdmin(page: Page) {
  await page.getByPlaceholder("Usuário ou e-mail admin").fill("admin@example.com");
  await page.getByPlaceholder("Senha admin").fill("Secret123456!");
  await page.getByRole("button", { name: "Login por credenciais" }).click();
  await expect(page.getByRole("heading", { name: "Configurações" })).toBeVisible();
}

async function fulfillMockApi(route: Route, state: MockApiState) {
  const request = route.request();
  const url = new URL(request.url());
  const path = url.pathname.replace(/^\/api/, "");
  const method = request.method();
  const workspaceId = request.headers()["x-workspace-id"] ?? "ws-alpha";
  const config = state.configs[workspaceId] ?? state.configs["ws-alpha"];

  if (method === "OPTIONS") {
    await route.fulfill({ status: 204, headers: corsHeaders() });
    return;
  }

  if (method === "POST" && path === "/auth/login") {
    await json(route, {
      access_token: AUTH_TOKEN,
      refresh_token: REFRESH_TOKEN,
      token_type: "bearer",
      expires_in_seconds: 28800,
      refresh_expires_in_seconds: 2592000,
      session: mockSession(),
    });
    return;
  }

  if (method === "POST" && path === "/auth/refresh") {
    await json(route, {
      access_token: AUTH_TOKEN,
      refresh_token: REFRESH_TOKEN,
      token_type: "bearer",
      expires_in_seconds: 28800,
      refresh_expires_in_seconds: 2592000,
      session: mockSession(),
    });
    return;
  }

  if (method === "GET" && path === "/auth/session") {
    await json(route, mockSession());
    return;
  }

  if (method === "GET" && path === "/dashboard/stats") {
    await json(route, state.stats);
    return;
  }

  if (method === "GET" && path === "/opportunities") {
    await json(route, state.opportunities);
    return;
  }

  if (method === "GET" && path === "/workspace/status") {
    await json(route, {
      workspace: mockSession().workspaces.find((workspace) => workspace.id === workspaceId) ?? mockSession().workspaces[0],
      organization: mockSession().organization,
      configured_pairs_count: Array.isArray(config.enabled_pairs) ? config.enabled_pairs.length : 0,
      enabled_exchange_count: Array.isArray(config.enabled_exchanges) ? config.enabled_exchanges.length : 0,
      telegram_configured: Boolean(config.telegram_chat_id),
      exchange_credentials_configured: {
        novadax: true,
        mercado_bitcoin: true,
        binance: true,
      },
      onboarding_completed_at: "2025-01-15T09:00:00.000Z",
    });
    return;
  }

  if (method === "GET" && path === "/history") {
    if (state.historyErrorMessage) {
      await error(route, 503, state.historyErrorMessage);
      return;
    }
    await json(route, [buildHistoryRecord()]);
    return;
  }

  if (method === "GET" && path === "/analytics") {
    if (state.analyticsErrorMessage) {
      await error(route, 503, state.analyticsErrorMessage);
      return;
    }
    await json(route, {
      total_records: 1,
      top_pairs: [{ pair: "BTC_BRL", count: 1 }],
      avg_score_by_exchange: [{ exchange: "novadax", avg_score: 81 }],
      score_distribution: { "80-100": 1 },
      movement_distribution: { strong_range: 1 },
      hourly_distribution: { "10": 1 },
      arbitrage_count: 0,
      avg_cross_exchange_gap_pct: 0,
    });
    return;
  }

  if (method === "GET" && path === "/config") {
    await json(route, {
      config,
      configured_secrets: {
        telegram_bot_token: Boolean(config.telegram_bot_token),
        telegram_chat_id: Boolean(config.telegram_chat_id),
        novadax_api_key: Boolean(config.novadax_api_key),
        novadax_api_secret: Boolean(config.novadax_api_secret),
        mb_api_key: Boolean(config.mb_api_key),
        mb_api_secret: Boolean(config.mb_api_secret),
        binance_api_key: Boolean(config.binance_api_key),
        binance_api_secret: Boolean(config.binance_api_secret),
      },
    });
    return;
  }

  if (method === "PUT" && path === "/config") {
    const payload = JSON.parse(request.postData() || "{}");
    state.configs[workspaceId] = { ...config, ...payload };
    await json(route, {
      config: {
        ...state.configs[workspaceId],
        telegram_bot_token: "",
        telegram_chat_id: "",
        novadax_api_key: "",
        novadax_api_secret: "",
        mb_api_key: "",
        mb_api_secret: "",
        binance_api_key: "",
        binance_api_secret: "",
      },
      configured_secrets: {
        telegram_bot_token: Boolean(state.configs[workspaceId].telegram_bot_token),
        telegram_chat_id: Boolean(state.configs[workspaceId].telegram_chat_id),
        novadax_api_key: Boolean(state.configs[workspaceId].novadax_api_key),
        novadax_api_secret: Boolean(state.configs[workspaceId].novadax_api_secret),
        mb_api_key: Boolean(state.configs[workspaceId].mb_api_key),
        mb_api_secret: Boolean(state.configs[workspaceId].mb_api_secret),
        binance_api_key: Boolean(state.configs[workspaceId].binance_api_key),
        binance_api_secret: Boolean(state.configs[workspaceId].binance_api_secret),
      },
    });
    return;
  }

  if (method === "GET" && path === "/admin/audit-log") {
    await json(route, []);
    return;
  }

  if (method === "GET" && path === "/users") {
    await json(route, [
      {
        id: "user-admin",
        username: "admin",
        email: "admin@example.com",
        role: "admin",
        is_active: true,
        must_change_password: false,
        created_at: "2025-01-10T10:00:00.000Z",
        updated_at: "2025-01-15T09:30:00.000Z",
        password_last_changed_at: "2025-01-15T09:00:00.000Z",
        created_by_user_id: null,
        token_version: 3,
      },
    ]);
    return;
  }

  if (method === "GET" && path === "/invites") {
    await json(route, []);
    return;
  }

  if (method === "GET" && path === "/pairs/available") {
    await json(route, {
      generated_at: "2025-01-15T09:00:00.000Z",
      expires_at: "2025-01-15T10:00:00.000Z",
      pairs: [
        {
          pair: "BTC_BRL",
          display_name: "BTC/BRL",
          availability: {
            novadax: true,
            mercado_bitcoin: true,
            binance: true,
          },
        },
        {
          pair: "ETH_BRL",
          display_name: "ETH/BRL",
          availability: {
            novadax: true,
            mercado_bitcoin: false,
            binance: true,
          },
        },
      ],
    });
    return;
  }

  if (method === "POST" && path === "/onboarding/complete") {
    await json(route, { completed: true, completed_at: "2025-01-15T10:10:00.000Z" });
    return;
  }

  if (method === "POST" && path === "/config/validate-exchanges") {
    await json(route, {
      results: [
        {
          exchange: "novadax",
          state: "valid",
          checked_at: "2025-01-15T09:10:00.000Z",
          can_trade: true,
          message: "Credenciais válidas.",
        },
      ],
    });
    return;
  }

  if (method === "POST" && path === "/config/telegram/test") {
    await json(route, { delivered: true });
    return;
  }

  await error(route, 404, `Rota mockada não encontrada: ${method} ${path}`);
}

async function widthOf(locator: Locator) {
  const box = await locator.boundingBox();
  expect(box).not.toBeNull();
  return box?.width ?? 0;
}

async function installMockWebSocket(page: Page) {
  await page.addInitScript(() => {
    const sockets: Array<MockWebSocket> = [];

    class MockWebSocket {
      static readonly CONNECTING = 0;
      static readonly OPEN = 1;
      static readonly CLOSING = 2;
      static readonly CLOSED = 3;

      readyState = MockWebSocket.CONNECTING;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent<string>) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;

      constructor(url: string) {
        void url;
        sockets.push(this);
        window.setTimeout(() => {
          this.readyState = MockWebSocket.OPEN;
          this.onopen?.(new Event("open"));
        }, 0);
      }

      close() {
        this.readyState = MockWebSocket.CLOSED;
        this.onclose?.(new CloseEvent("close"));
      }

      send() {}
    }

    (
      window as unknown as {
        __CRYPTO_ANALYTICS_WEBSOCKET_FACTORY__?: (url: string) => MockWebSocket;
      }
    ).__CRYPTO_ANALYTICS_WEBSOCKET_FACTORY__ = (url: string) => new MockWebSocket(url);

    (window as unknown as { __dispatchMockSocketMessage?: (payload: unknown) => void }).__dispatchMockSocketMessage = (
      payload: unknown,
    ) => {
      const message = { data: JSON.stringify(payload) } as MessageEvent<string>;
      sockets.forEach((socket) => socket.onmessage?.(message));
    };
  });
}

function buildConfig(overrides?: Record<string, unknown>) {
  return {
    thresholds: {
      min_volatility_pct: 2,
      min_volume_brl: 500000,
      min_volume_brl_small: 120000,
      min_liquidity_units: 1000,
      max_spread_pct: 1.5,
    },
    weights: {
      volatility: 0.25,
      volume: 0.2,
      liquidity: 0.2,
      spread: 0.15,
      repetition: 0.2,
    },
    enabled_exchanges: ["novadax", "mercado_bitcoin", "binance"],
    enabled_pairs: ["BTC_BRL"],
    scan_interval_seconds: 15,
    telegram_enabled: true,
    telegram_bot_token: "bot-token",
    telegram_chat_id: "123456",
    novadax_api_key: "nova-key",
    novadax_api_secret: "nova-secret",
    mb_api_key: "mb-key",
    mb_api_secret: "mb-secret",
    binance_api_key: "bin-key",
    binance_api_secret: "bin-secret",
    ...overrides,
  };
}

function buildOpportunity(overrides?: Record<string, unknown>) {
  return {
    id: "opp-default",
    exchange: "novadax",
    pair: "BTC_BRL",
    score: 81,
    volatility_pct: 3.2,
    volume_24h: 1500000,
    quote_volume_24h: 1500000,
    liquidity_units: 2300,
    spread_pct: 0.45,
    movement_type: "strong_range",
    last_price: 301245.44,
    change_pct: 2.8,
    detected_at: "2025-01-15T10:00:00.000Z",
    duration_minutes: 18,
    cross_exchange_gap_pct: 0,
    cross_exchange_reference_exchange: null,
    cross_exchange_reference_price: null,
    arbitrage_available: false,
    historical_confidence: 0.84,
    ...overrides,
  };
}

function buildHistoryRecord() {
  return {
    id: "hist-1",
    exchange: "novadax",
    pair: "BTC_BRL",
    score: 81,
    volatility_pct: 3.2,
    volume_24h: 1500000,
    quote_volume_24h: 1500000,
    liquidity_units: 2300,
    spread_pct: 0.45,
    movement_type: "strong_range",
    last_price: 301245.44,
    change_pct: 2.8,
    detected_at: "2025-01-15T10:00:00.000Z",
    duration_minutes: 18,
    cross_exchange_gap_pct: 0,
    cross_exchange_reference_exchange: null,
    cross_exchange_reference_price: null,
    arbitrage_available: false,
    historical_confidence: 0.84,
  };
}

function mockSession() {
  return {
    user_id: "user-admin",
    username: "admin",
    email: "admin@example.com",
    role: "admin",
    auth_mode: "password",
    token_version: 3,
    password_last_changed_at: "2025-01-15T09:00:00.000Z",
    must_change_password: false,
    onboarding_completed_at: "2025-01-15T09:00:00.000Z",
    organization: {
      id: "org-1",
      name: "Orbital Capital",
      slug: "orbital-capital",
      plan: "growth",
      subscription_status: "active",
      stripe_customer_id: null,
      trial_ends_at: null,
    },
    workspaces: [
      {
        id: "ws-alpha",
        slug: "alpha-desk",
        name: "Alpha Desk",
        role: "admin",
        is_active: true,
      },
      {
        id: "ws-beta",
        slug: "beta-desk",
        name: "Beta Desk",
        role: "admin",
        is_active: true,
      },
    ],
  };
}

async function json(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    headers: corsHeaders(),
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function error(route: Route, status: number, detail: string) {
  await json(route, { detail }, status);
}

function corsHeaders() {
  return {
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "*",
    "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
  };
}
