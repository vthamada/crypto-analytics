"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import { emitAppError } from "@/lib/app-errors";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";


export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    emitAppError({
      message: error.message || "Ocorreu uma falha inesperada na aplicação.",
      source: "runtime",
      dedupeKey: error.digest || error.message,
    });
  }, [error]);

  return (
    <div className="mx-auto flex min-h-[calc(100vh-8rem)] max-w-2xl items-center p-4">
      <Card className="w-full border-red-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg font-semibold">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            Falha inesperada nesta tela
          </CardTitle>
          <CardDescription>
            A página encontrou um erro em tempo de execução. Você pode tentar recarregar este trecho sem reiniciar toda a sessão.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl border bg-muted/30 p-4 text-sm text-muted-foreground">
            {error.message || "Erro não identificado."}
          </div>
          <Button type="button" onClick={reset} className="gap-2">
            <RefreshCcw className="h-4 w-4" />
            Tentar novamente
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}