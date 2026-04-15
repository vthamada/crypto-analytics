"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import { emitAppError } from "@/lib/app-errors";
import { Button } from "@/components/ui/button";


export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    emitAppError({
      message: error.message || "Ocorreu uma falha global na aplicação.",
      source: "runtime",
      dedupeKey: error.digest || error.message,
    });
  }, [error]);

  return (
    <html lang="pt-BR">
      <body className="flex min-h-screen items-center justify-center bg-background p-4 text-foreground">
        <div className="w-full max-w-2xl rounded-3xl border border-red-500/20 bg-background p-8 shadow-xl">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-1 h-5 w-5 text-red-500" />
            <div>
              <h1 className="text-xl font-semibold">Falha global da aplicação</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Um erro afetou a árvore principal do app. Tente reiniciar a renderização para recuperar a interface.
              </p>
            </div>
          </div>
          <div className="mt-5 rounded-xl border bg-muted/30 p-4 text-sm text-muted-foreground">
            {error.message || "Erro não identificado."}
          </div>
          <Button type="button" onClick={reset} className="mt-5 gap-2">
            <RefreshCcw className="h-4 w-4" />
            Tentar novamente
          </Button>
        </div>
      </body>
    </html>
  );
}