export type AppErrorSource = "api" | "websocket" | "runtime";

export type AppErrorDetail = {
  message: string;
  source: AppErrorSource;
  status?: number;
  dedupeKey?: string;
};

export const APP_ERROR_EVENT = "crypto-analytics-app-error";

export function emitAppError(detail: AppErrorDetail) {
  if (typeof window === "undefined") return;

  window.dispatchEvent(
    new CustomEvent<AppErrorDetail>(APP_ERROR_EVENT, {
      detail: {
        ...detail,
        dedupeKey: detail.dedupeKey ?? `${detail.source}:${detail.status ?? 0}:${detail.message}`,
      },
    }),
  );
}