"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";
import { getConfig, updateConfig } from "@/lib/api";
import type { AppConfig, Exchange } from "@/lib/types";
import { Check, Eye, EyeOff, Info, Loader2, Save } from "lucide-react";

const ALL_EXCHANGES: { id: Exchange; label: string }[] = [
  { id: "novadax", label: "NovaDAX" },
  { id: "mercado_bitcoin", label: "Mercado Bitcoin" },
  { id: "binance", label: "Binance" },
];

const ALL_PAIRS = [
  "BTC_BRL", "ETH_BRL", "SOL_BRL", "ADA_BRL", "XRP_BRL",
  "DOGE_BRL", "DOT_BRL", "AVAX_BRL", "MATIC_BRL", "LINK_BRL",
  "LTC_BRL", "UNI_BRL", "ATOM_BRL", "NEAR_BRL", "APE_BRL",
];

const EXCHANGE_CRED_FIELDS: {
  exchange: Exchange;
  label: string;
  keyField: "novadax_api_key" | "mb_api_key" | "binance_api_key";
  secretField: "novadax_api_secret" | "mb_api_secret" | "binance_api_secret";
}[] = [
  { exchange: "novadax", label: "NovaDAX", keyField: "novadax_api_key", secretField: "novadax_api_secret" },
  { exchange: "mercado_bitcoin", label: "Mercado Bitcoin", keyField: "mb_api_key", secretField: "mb_api_secret" },
  { exchange: "binance", label: "Binance", keyField: "binance_api_key", secretField: "binance_api_secret" },
];

export default function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

  useEffect(() => {
    getConfig()
      .then(setConfig)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const updated = await updateConfig(config);
      setConfig(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const toggleExchange = (exchange: Exchange) => {
    if (!config) return;
    const exchanges = config.enabled_exchanges.includes(exchange)
      ? config.enabled_exchanges.filter((e) => e !== exchange)
      : [...config.enabled_exchanges, exchange];
    setConfig({ ...config, enabled_exchanges: exchanges });
  };

  const togglePair = (pair: string) => {
    if (!config) return;
    const pairs = config.enabled_pairs.includes(pair)
      ? config.enabled_pairs.filter((p) => p !== pair)
      : [...config.enabled_pairs, pair];
    setConfig({ ...config, enabled_pairs: pairs });
  };

  const toggleShow = (field: string) =>
    setShowSecrets((prev) => ({ ...prev, [field]: !prev[field] }));

  if (loading || !config) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4 pt-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Configurações</h1>
          <p className="text-sm text-muted-foreground">
            Ajuste os parâmetros de detecção sem alterar código
          </p>
        </div>
        <Button onClick={handleSave} disabled={saving} className="gap-2">
          {saving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : saved ? (
            <Check className="h-4 w-4" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          {saved ? "Salvo!" : "Salvar"}
        </Button>
      </div>

      {/* Thresholds */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Filtros e Thresholds</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          <SettingRow label="Volatilidade mínima (%)" description="Variação percentual mínima para considerar um sinal">
            <div className="flex items-center gap-3">
              <Slider
                value={[config.thresholds.min_volatility_pct]}
                min={0.5}
                max={10}
                step={0.5}
                className="w-48"
                onValueChange={(v) => {
                  const val = Array.isArray(v) ? v[0] : v;
                  setConfig({
                    ...config,
                    thresholds: { ...config.thresholds, min_volatility_pct: val },
                  });
                }}
              />
              <span className="w-12 text-right text-sm font-semibold tabular-nums">
                {config.thresholds.min_volatility_pct}%
              </span>
            </div>
          </SettingRow>

          <Separator />

          <SettingRow label="Volume mínimo (grandes)" description="Volume em BRL para pares principais (BTC, ETH)">
            <Input
              type="number"
              value={config.thresholds.min_volume_brl}
              onChange={(e) =>
                setConfig({
                  ...config,
                  thresholds: { ...config.thresholds, min_volume_brl: Number(e.target.value) },
                })
              }
              className="h-9 w-36 font-medium"
            />
          </SettingRow>

          <Separator />

          <SettingRow label="Volume mínimo (altcoins)" description="Volume em BRL para altcoins">
            <Input
              type="number"
              value={config.thresholds.min_volume_brl_small}
              onChange={(e) =>
                setConfig({
                  ...config,
                  thresholds: { ...config.thresholds, min_volume_brl_small: Number(e.target.value) },
                })
              }
              className="h-9 w-36 font-medium"
            />
          </SettingRow>

          <Separator />

          <SettingRow label="Liquidez mínima (unidades)" description="Quantidade mínima no livro de ordens">
            <Input
              type="number"
              value={config.thresholds.min_liquidity_units}
              onChange={(e) =>
                setConfig({
                  ...config,
                  thresholds: { ...config.thresholds, min_liquidity_units: Number(e.target.value) },
                })
              }
              className="h-9 w-36 font-medium"
            />
          </SettingRow>

          <Separator />

          <SettingRow label="Spread máximo (%)" description="Spread máximo entre compra e venda">
            <div className="flex items-center gap-3">
              <Slider
                value={[config.thresholds.max_spread_pct]}
                min={0.1}
                max={5}
                step={0.1}
                className="w-48"
                onValueChange={(v) => {
                  const val = Array.isArray(v) ? v[0] : v;
                  setConfig({
                    ...config,
                    thresholds: { ...config.thresholds, max_spread_pct: val },
                  });
                }}
              />
              <span className="w-12 text-right text-sm font-semibold tabular-nums">
                {config.thresholds.max_spread_pct.toFixed(1)}%
              </span>
            </div>
          </SettingRow>
        </CardContent>
      </Card>

      {/* Score Weights */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Pesos do Score</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {(["volatility", "volume", "liquidity", "spread", "repetition"] as const).map(
            (key) => {
              const labels: Record<string, string> = {
                volatility: "Volatilidade",
                volume: "Volume",
                liquidity: "Liquidez",
                spread: "Spread",
                repetition: "Repetição",
              };
              return (
                <div key={key} className="flex items-center justify-between">
                  <span className="text-sm font-medium">{labels[key]}</span>
                  <div className="flex items-center gap-3">
                    <Slider
                      value={[config.weights[key] * 100]}
                      min={0}
                      max={50}
                      step={5}
                      className="w-48"
                      onValueChange={(v) => {
                        const val = Array.isArray(v) ? v[0] : v;
                        setConfig({
                          ...config,
                          weights: { ...config.weights, [key]: val / 100 },
                        });
                      }}
                    />
                    <span className="w-12 text-right text-sm font-semibold tabular-nums">
                      {(config.weights[key] * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              );
            }
          )}
        </CardContent>
      </Card>

      {/* Exchanges */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Exchanges</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {ALL_EXCHANGES.map(({ id, label }) => (
            <div key={id} className="flex items-center justify-between">
              <span className="text-sm font-medium">{label}</span>
              <Switch
                checked={config.enabled_exchanges.includes(id)}
                onCheckedChange={() => toggleExchange(id)}
              />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Pairs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Pares Monitorados</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {ALL_PAIRS.map((pair) => {
              const active = config.enabled_pairs.includes(pair);
              return (
                <Badge
                  key={pair}
                  variant={active ? "default" : "outline"}
                  className="cursor-pointer select-none font-semibold"
                  onClick={() => togglePair(pair)}
                >
                  {pair.replace("_", "/")}
                </Badge>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* General */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Geral</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <SettingRow label="Intervalo de varredura (seg)" description="Tempo entre cada ciclo de coleta">
            <Input
              type="number"
              value={config.scan_interval_seconds}
              onChange={(e) =>
                setConfig({ ...config, scan_interval_seconds: Number(e.target.value) })
              }
              className="h-9 w-36 font-medium"
            />
          </SettingRow>
        </CardContent>
      </Card>

      {/* Telegram */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Notificações Telegram</CardTitle>
          <CardDescription>
            Configure o bot de alertas. Obtenha o token em{" "}
            <span className="font-semibold text-foreground">@BotFather</span> e o Chat ID
            abrindo{" "}
            <span className="font-mono text-xs">api.telegram.org/bot&lt;TOKEN&gt;/getUpdates</span>{" "}
            após enviar qualquer mensagem ao bot.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold">Alertas ativos</p>
              <p className="text-xs text-muted-foreground">Enviar notificações via bot</p>
            </div>
            <Switch
              checked={config.telegram_enabled}
              onCheckedChange={(v) => setConfig({ ...config, telegram_enabled: v })}
            />
          </div>

          <Separator />

          <div className="space-y-3">
            <CredentialField
              label="Bot Token"
              placeholder="123456789:AAH..."
              value={config.telegram_bot_token}
              show={!!showSecrets["telegram_bot_token"]}
              onToggle={() => toggleShow("telegram_bot_token")}
              onChange={(v) => setConfig({ ...config, telegram_bot_token: v })}
            />
            <CredentialField
              label="Chat ID"
              placeholder="987654321"
              value={config.telegram_chat_id}
              show={!!showSecrets["telegram_chat_id"]}
              onToggle={() => toggleShow("telegram_chat_id")}
              onChange={(v) => setConfig({ ...config, telegram_chat_id: v })}
            />
          </div>

          <div className="flex items-start gap-2 rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" />
            <p className="text-xs text-muted-foreground">
              Alertas são enviados para oportunidades com <span className="font-semibold text-foreground">score ≥ 60</span>.
              Deixe os campos em branco para usar as variáveis de ambiente do servidor (.env).
            </p>
          </div>
        </CardContent>
      </Card>

      {/* API Keys */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-semibold">Chaves de API das Exchanges</CardTitle>
          <CardDescription>
            <span className="inline-flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
              Todos os dados de mercado (preço, ordem, histórico) são{" "}
              <span className="font-semibold text-foreground">APIs públicas</span> — nenhuma chave é
              necessária para leitura.
            </span>
            <br />
            Preencha apenas se quiser usar funcionalidades de conta (saldo, ordens) no futuro.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {EXCHANGE_CRED_FIELDS.map(({ exchange, label, keyField, secretField }) => (
            <div key={exchange} className="space-y-3">
              <p className="text-sm font-semibold text-muted-foreground">{label}</p>
              <CredentialField
                label="API Key"
                placeholder="Chave pública da API"
                value={config[keyField]}
                show={!!showSecrets[keyField]}
                onToggle={() => toggleShow(keyField)}
                onChange={(v) => setConfig({ ...config, [keyField]: v })}
              />
              <CredentialField
                label="API Secret"
                placeholder="Chave secreta da API"
                value={config[secretField]}
                show={!!showSecrets[secretField]}
                onToggle={() => toggleShow(secretField)}
                onChange={(v) => setConfig({ ...config, [secretField]: v })}
              />
              {exchange !== "binance" && <Separator />}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function SettingRow({
  label,
  description,
  children,
}: {
  label: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-semibold">{label}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      {children}
    </div>
  );
}

function CredentialField({
  label,
  placeholder,
  value,
  show,
  onToggle,
  onChange,
}: {
  label: string;
  placeholder: string;
  value: string;
  show: boolean;
  onToggle: () => void;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 shrink-0 text-xs font-medium text-muted-foreground">{label}</span>
      <div className="relative flex-1">
        <Input
          type={show ? "text" : "password"}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="pr-9 font-mono text-sm"
          autoComplete="off"
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          tabIndex={-1}
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}
