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
    trap: { label: "⚠️ Armadilha", variant: "bg-red-500/15 text-red-500" },
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

  const filtered = opportunities.filter((o) => {
    if (search && !o.pair.toLowerCase().includes(search.toLowerCase())) return false;
    if (exchangeFilter !== "all" && o.exchange !== exchangeFilter) return false;
    if (movementFilter !== "all" && o.movement_type !== movementFilter) return false;
    return true;
  });

  return (
    <Card className="rounded-2xl">
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-lg">Oportunidades Detectadas</CardTitle>
          <div className="flex gap-2">
            <Input
              placeholder="Buscar par..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-9 w-40"
            />
            <Select value={exchangeFilter} onValueChange={(v) => setExchangeFilter(v ?? "all")}>
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
            <Select value={movementFilter} onValueChange={(v) => setMovementFilter(v ?? "all")}>
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
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={10} className="h-32 text-center text-muted-foreground">
                    Nenhuma oportunidade encontrada
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((opp) => (
                  <TableRow
                    key={opp.id}
                    className={cn(
                      "cursor-pointer transition-colors",
                      opp.score >= 70 && "bg-emerald-500/5 hover:bg-emerald-500/10",
                      opp.score >= 40 && opp.score < 70 && "hover:bg-yellow-500/5",
                    )}
                    onClick={() => onSelect?.(opp)}
                  >
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={cn("font-bold tabular-nums", scoreColor(opp.score))}
                      >
                        {opp.score}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{opp.pair}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {exchangeLabel(opp.exchange)}
                    </TableCell>
                    <TableCell className="tabular-nums">
                      R$ {opp.last_price.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "tabular-nums font-medium",
                          opp.change_pct >= 0 ? "text-emerald-500" : "text-red-500"
                        )}
                      >
                        {opp.change_pct >= 0 ? "+" : ""}
                        {opp.change_pct.toFixed(2)}%
                      </span>
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {opp.volatility_pct.toFixed(2)}%
                    </TableCell>
                    <TableCell className="tabular-nums">
                      R$ {(opp.quote_volume_24h / 1000).toFixed(0)}K
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {opp.liquidity_units.toLocaleString("pt-BR")}
                    </TableCell>
                    <TableCell className="tabular-nums">
                      {opp.spread_pct.toFixed(4)}%
                    </TableCell>
                    <TableCell>{movementBadge(opp.movement_type)}</TableCell>
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
