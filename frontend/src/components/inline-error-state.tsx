"use client";

import { AlertTriangle, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export function InlineErrorState({
  title = "Falha ao carregar dados",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Card className="border-red-500/20 bg-red-500/[0.03]">
      <CardContent className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
          <div>
            <p className="text-sm font-semibold">{title}</p>
            <p className="mt-1 text-sm text-muted-foreground">{message}</p>
          </div>
        </div>
        {onRetry ? (
          <Button type="button" variant="outline" onClick={onRetry} className="gap-2">
            <RefreshCcw className="h-4 w-4" />
            Tentar novamente
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}