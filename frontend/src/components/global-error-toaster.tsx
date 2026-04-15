"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle, WifiOff, X } from "lucide-react";
import { APP_ERROR_EVENT, type AppErrorDetail } from "@/lib/app-errors";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type ToastItem = AppErrorDetail & {
  id: string;
};


export function GlobalErrorToaster() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const recentKeysRef = useRef<Map<string, number>>(new Map());

  useEffect(() => {
    function handleError(event: Event) {
      const customEvent = event as CustomEvent<AppErrorDetail>;
      const detail = customEvent.detail;
      if (!detail?.message) {
        return;
      }

      const dedupeKey = detail.dedupeKey ?? `${detail.source}:${detail.status ?? 0}:${detail.message}`;
      const now = Date.now();
      const lastShownAt = recentKeysRef.current.get(dedupeKey) ?? 0;
      if (now - lastShownAt < 15000) {
        return;
      }
      recentKeysRef.current.set(dedupeKey, now);

      const toast: ToastItem = {
        ...detail,
        dedupeKey,
        id: `${now}-${Math.random().toString(36).slice(2, 8)}`,
      };

      setToasts((current) => [...current.slice(-2), toast]);
      window.setTimeout(() => {
        setToasts((current) => current.filter((item) => item.id !== toast.id));
      }, 5000);
    }

    window.addEventListener(APP_ERROR_EVENT, handleError as EventListener);
    return () => window.removeEventListener(APP_ERROR_EVENT, handleError as EventListener);
  }, []);

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className="pointer-events-none fixed right-4 top-4 z-[100] flex w-full max-w-sm flex-col gap-3">
      {toasts.map((toast) => (
        <Card key={toast.id} className="pointer-events-auto border-red-500/20 bg-background/95 shadow-xl backdrop-blur">
          <CardContent className="flex items-start gap-3 p-4">
            <div className="mt-0.5 shrink-0 text-red-500">
              {toast.source === "websocket" ? <WifiOff className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold">{titleForSource(toast.source)}</p>
              <p className="mt-1 text-sm text-muted-foreground" data-testid="global-error-toast">
                {toast.message}
              </p>
            </div>
            <Button
              type="button"
              size="icon-xs"
              variant="ghost"
              className="shrink-0"
              onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))}
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function titleForSource(source: AppErrorDetail["source"]) {
  switch (source) {
    case "websocket":
      return "Tempo real indisponivel";
    case "runtime":
      return "Falha inesperada";
    default:
      return "Erro de comunicação";
  }
}