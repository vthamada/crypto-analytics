"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Opportunity } from "@/lib/types";
import { cn } from "@/lib/utils";

interface OpportunitiesTableProps {
  opportunities: Opportunity[];
  loading?: boolean;
  onSelect?: (opportunity: Opportunity) => void;
}

function scoreColor(score: number): string {
  if (score >= 70) return "bg-emerald-500/15 text-emerald-500 border-emerald-500/20";
  if (score >= 40) return "bg-yellow-500/15 text-yellow-500 border-yellow-500/20";
  return "bg-red-500/15 text-red-500 border-red-500/20";
}

function movementBadge(type: string) {
  const map: Record<string, { label: string; variant: string }> = {
    strong_range: { label: "📈 Forte", variant: "bg-emerald-500/15 text-emerald-500" },
    spike: { label: "⚡ Spike", variant: "bg-yellow-500/15 text-yellow-500" },
    weak: { label: "😐 Fraco", variant: "bg-muted text-muted-foreground" },
    trap: { label: "⚠ Armadilha", variant: "bg-red-500/15 text-red-500" },
  };
  const info = map[type] || { label: type, variant: "bg-muted text-muted-foreground" };
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", info.variant)}>
      {info.label}
    </span>
  );
}

function exchangeLabel(exchange: string): string {
  const map: Record<string, string> = {
    novadax: "NovaDAX",
    mercado_bitcoin: "Mercado BTC",
    binance: "Binance",
  };
  return map[exchange] || exchange;
}

export function OpportunitiesTable({
  opportunities,
  loading,
  onSelect,
}: OpportunitiesTableProps) {
  const [search, setSearch] = useState("");
  const [exchangeFilter, setExchangeFilter] = useState<string>("all");
  const [movementFilter, setMovementFilter] = useState<string>("all");
  const [minScore, setMinScore] = useState("0");
  const [sortBy, setSortBy] = useState<string>("score");
  const [arbitrageOnly, setArbitrageOnly] = useState(false);

  const filtered = opportunities.filter((opportunity) => {
    if (search && !opportunity.pair.toLowerCase().includes(search.toLowerCase())) return false;
    if (exchangeFilter !== "all" && opportunity.exchange !== exchangeFilter) return false;
    if (movementFilter !== "all" && opportunity.movement_type !== movementFilter) return false;
    if (Number(minScore) > 0 && opportunity.score < Number(minScore)) return false;
    if (arbitrageOnly && !opportunity.arbitrage_available) return false;
    return true;
  });

  const sorted = [...filtered].sort((left, right) => {
    switch (sortBy) {
      case "gap":
        return right.cross_exchange_gap_pct - left.cross_exchange_gap_pct;
      case "volume":
        return right.quote_volume_24h - left.quote_volume_24h;
      case "volatility":
        return right.volatility_pct - left.volatility_pct;
      case "spread":
        return left.spread_pct - right.spread_pct;
      default:
        return right.score - left.score;
    }
  });

  return (
    <Card className="rounded-2xl">
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-lg">Oportunidades Detectadas</CardTitle>
          <div className="flex flex-wrap gap-2">
            <Input
              placeholder="Buscar par..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="h-9 w-40"
            />
            <Input
              placeholder="Score min."
              type="number"
              value={minScore}
              onChange={(event) => setMinScore(event.target.value)}
              className="h-9 w-28"
            />
            <Select value={exchangeFilter} onValueChange={(value) => setExchangeFilter(value ?? "all")}>
              <SelectTrigger className="h-9 w-36">
                <SelectValue placeholder="Exchange" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                <SelectItem value="novadax">NovaDAX</SelectItem>
                <SelectItem value="mercado_bitcoin">Mercado BTC</SelectItem>
                <SelectItem value="binance">Binance</SelectItem>
              </SelectContent>
            </Select>
            <Select value={movementFilter} onValueChange={(value) => setMovementFilter(value ?? "all")}>
              <SelectTrigger className="h-9 w-36">
                <SelectValue placeholder="Movimento" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="strong_range">Forte</SelectItem>
                <SelectItem value="spike">Spike</SelectItem>
                <SelectItem value="weak">Fraco</SelectItem>
                <SelectItem value="trap">Armadilha</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sortBy} onValueChange={(value) => setSortBy(value ?? "score")}>
              <SelectTrigger className="h-9 w-36">
                <SelectValue placeholder="Ordenar" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="score">Score</SelectItem>
                <SelectItem value="gap">Gap</SelectItem>
                <SelectItem value="volume">Volume</SelectItem>
                <SelectItem value="volatility">Volatilidade</SelectItem>
                <SelectItem value="spread">Spread</SelectItem>
              </SelectContent>
            </Select>
            <label className="flex h-9 items-center gap-2 rounded-md border px-3 text-sm text-muted-foreground">
              <input
                type="checkbox"
                checked={arbitrageOnly}
                onChange={(event) => setArbitrageOnly(event.target.checked)}
              />
              Arbitragem
            </label>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[500px]">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <TableHead className="w-16">Score</TableHead>
                <TableHead>Par</TableHead>
                <TableHead>Exchange</TableHead>
                <TableHead>Preco</TableHead>
                <TableHead>Variacao</TableHead>
                <TableHead>Volatilidade</TableHead>
                <TableHead>Volume 24h</TableHead>
                <TableHead>Liquidez</TableHead>
                <TableHead>Spread</TableHead>
                <TableHead>Movimento</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 10 }).map((_, j) => (
                      <TableCell key={j}>
                        <div className="h-4 w-full animate-pulse rounded bg-muted" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : sorted.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="h-32 text-center text-muted-foreground">
                    Nenhuma oportunidade encontrada
                  </TableCell>
                </TableRow>
              ) : (
                sorted.map((opportunity) => (
                  <TableRow
                    key={opportunity.id}
                    className={cn(
                      "cursor-pointer transition-colors",
                      opportunity.score >= 70 && "bg-emerald-500/5 hover:bg-emerald-500/10",
                      opportunity.score >= 40 && opportunity.score < 70 && "hover:bg-yellow-500/5",
                      opportunity.arbitrage_available && "ring-1 ring-blue-500/20",
                    )}
                    onClick={() => onSelect?.(opportunity)}
                  >
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={cn("font-bold tabular-nums", scoreColor(opportunity.score))}
                      >
                        {opportunity.score}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{opportunity.pair}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {exchangeLabel(opportunity.exchange)}
                    </TableCell>
                    <TableCell className="tabular-nums">
                      R$ {opportunity.last_price.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "tabular-nums font-medium",
                          opportunity.change_pct >= 0 ? "text-emerald-500" : "text-red-500"
                        )}
                      >
                        {opportunity.change_pct >= 0 ? "+" : ""}
                        {opportunity.change_pct.toFixed(2)}%
                      </span>
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {opportunity.volatility_pct.toFixed(2)}%
                    </TableCell>
                    <TableCell className="tabular-nums">
                      R$ {(opportunity.quote_volume_24h / 1000).toFixed(0)}K
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {opportunity.liquidity_units.toLocaleString("pt-BR")}
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {opportunity.spread_pct.toFixed(4)}%
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        {movementBadge(opportunity.movement_type)}
                        {opportunity.arbitrage_available ? (
                          <span className="text-[11px] font-medium text-blue-500">
                            Gap {opportunity.cross_exchange_gap_pct.toFixed(2)}%
                          </span>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
