import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  CircleHelp,
  Gauge,
  ShieldAlert,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const signalChecks = [
  "Movimento com volatilidade suficiente para chamar atencao.",
  "Volume e liquidez notional compativeis com o tamanho de ordem configurado.",
  "Spread e slippage estimado dentro do limite do perfil operacional.",
  "Repeticao ou sustentacao do movimento, evitando picos isolados sem saida.",
];

const glossary = [
  {
    term: "Score tecnico",
    text: "Mede o quanto o ativo chama atencao pelo conjunto volatilidade, volume, spread e comportamento recente.",
  },
  {
    term: "Score de operabilidade",
    text: "Mede se o sinal parece executavel na pratica: liquidez, saida, slippage e risco de ficar preso.",
  },
  {
    term: "Sinal interessante",
    text: "Vale observar, mas ainda pode ser ruim para operar se faltar volume, liquidez ou saida.",
  },
  {
    term: "Sinal operavel",
    text: "Passou nos filtros de atencao e tambem nos filtros de executabilidade para o perfil do workspace.",
  },
  {
    term: "Risco de ficar preso",
    text: "Aumenta quando ha volatilidade sem volume, pouca liquidez, spread ruim ou baixa profundidade para vender.",
  },
  {
    term: "Slippage",
    text: "Diferenca estimada entre o preco esperado e o preco real de execucao para o tamanho da ordem.",
  },
];

export default function HelpPage() {
  return (
    <main className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6">
      <section className="overflow-hidden rounded-3xl border bg-[radial-gradient(circle_at_top_left,rgba(59,130,246,0.18),transparent_32%),linear-gradient(135deg,rgba(15,23,42,0.04),transparent)] p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl space-y-3">
            <Badge variant="outline" className="w-fit gap-1">
              <CircleHelp className="h-3.5 w-3.5" />
              Guia do operador
            </Badge>
            <div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Como ler os sinais do Crypto Analytics
              </h1>
              <p className="mt-3 text-sm leading-6 text-muted-foreground sm:text-base">
                O sistema foi pensado para reduzir tempo perdido olhando ativo ruim. Ele nao promete entrada
                automatica: ele organiza oportunidades por atencao, operabilidade e risco de execucao.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/settings" className={cn(buttonVariants({ variant: "outline" }))}>
              Ajustar perfil
            </Link>
            <Link href="/" className={cn(buttonVariants())}>
              Ver dashboard
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary" />
              O que o scanner faz
            </CardTitle>
            <CardDescription>
              Ele coleta mercado, calcula filtros e destaca ativos que merecem atencao.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>O primeiro objetivo e separar ruido de movimento relevante.</p>
            <p>Depois, a camada operacional tenta responder: da para entrar e sair sem ficar preso?</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Gauge className="h-4 w-4 text-primary" />
              Como interpretar score
            </CardTitle>
            <CardDescription>
              Score alto nao e compra automatica. Ele e uma fila de prioridade.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>Use o score para decidir o que olhar primeiro.</p>
            <p>Use operabilidade, volume, liquidez e saida para decidir se vale operar.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-primary" />
              O que descartar
            </CardTitle>
            <CardDescription>
              A regra central: volatilidade sem volume tende a virar prisao.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>Evite sinais bonitos no grafico, mas com baixa liquidez ou spread ruim.</p>
            <p>O sistema deve ajudar a ignorar esses ativos antes que eles consumam tempo.</p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-primary" />
              Checklist de um sinal operavel
            </CardTitle>
            <CardDescription>
              Quanto mais itens abaixo estiverem fortes, mais util o sinal tende a ser na pratica.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {signalChecks.map((item) => (
              <div key={item} className="rounded-xl border bg-muted/20 p-3 text-sm">
                {item}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              Atencao importante
            </CardTitle>
            <CardDescription>
              O sistema e apoio operacional, nao recomendacao financeira.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>
              Um sinal pode estar correto tecnicamente e ainda assim ser ruim para o seu tamanho de ordem,
              horario ou exchange disponivel.
            </p>
            <p>
              Antes de operar, confirme livro, volume comprador/vendedor, spread real e contexto do mercado.
            </p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {glossary.map((item) => (
          <Card key={item.term}>
            <CardHeader>
              <CardTitle className="text-base">{item.term}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-6 text-muted-foreground">{item.text}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-primary" />
            Fluxo recomendado de uso
          </CardTitle>
          <CardDescription>
            Uma rotina simples para usar o produto como assistente operacional.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border bg-muted/20 p-3">
            <p className="font-semibold">1. Configure o perfil</p>
            <p className="mt-1 text-muted-foreground">Defina tamanho de ordem, slippage e liquidez minima.</p>
          </div>
          <div className="rounded-xl border bg-muted/20 p-3">
            <p className="font-semibold">2. Olhe os operaveis</p>
            <p className="mt-1 text-muted-foreground">Priorize sinais com boa executabilidade, nao so score alto.</p>
          </div>
          <div className="rounded-xl border bg-muted/20 p-3">
            <p className="font-semibold">3. Valide saida</p>
            <p className="mt-1 text-muted-foreground">Cheque volume, liquidez, spread e risco de ficar preso.</p>
          </div>
          <div className="rounded-xl border bg-muted/20 p-3">
            <p className="font-semibold">4. Aprenda com outcomes</p>
            <p className="mt-1 text-muted-foreground">Use historico para entender quais sinais continuam funcionando.</p>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
