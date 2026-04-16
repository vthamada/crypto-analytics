import type { Opportunity } from "./types";
import { emitAppError } from "./app-errors";
import {
  getStoredAuthToken,
  getStoredWorkspaceId,
  SESSION_STORAGE_EVENT,
} from "./api";

type MessageHandler = (data: {
  type: string;
  data?: Opportunity[];
  timestamp?: string;
  count?: number;
}) => void;

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

type WebSocketFactory = (url: string) => WebSocket;

function createWebSocket(url: string): WebSocket {
  if (typeof window !== "undefined") {
    const factory = (
      window as typeof window & {
        __CRYPTO_ANALYTICS_WEBSOCKET_FACTORY__?: WebSocketFactory;
      }
    ).__CRYPTO_ANALYTICS_WEBSOCKET_FACTORY__;
    if (factory) {
      return factory(url);
    }
  }
  return new WebSocket(url);
}


function buildConnectionUrl(): string | null {
  const token = getStoredAuthToken();
  const workspaceId = getStoredWorkspaceId();
  if (!token || !workspaceId) {
    return null;
  }

  const url = new URL(WS_URL);
  url.searchParams.set("token", token);
  url.searchParams.set("workspace_id", workspaceId);
  return url.toString();
}

class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 2000;
  private manualDisconnect = false;
  private reportedConnectionIssue = false;
  private activeUrl: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      window.addEventListener(SESSION_STORAGE_EVENT, () => {
        this.handleSessionChange();
      });
    }
  }

  private handleSessionChange(): void {
    const nextUrl = buildConnectionUrl();
    if (!nextUrl) {
      this.disconnect();
      return;
    }

    if (!this.handlers.size) {
      this.activeUrl = nextUrl;
      return;
    }

    if (this.activeUrl !== nextUrl) {
      this.reconnect();
    }
  }

  connect(): void {
    const nextUrl = buildConnectionUrl();
    if (!nextUrl) {
      return;
    }
    if (this.ws?.readyState === WebSocket.OPEN && this.activeUrl === nextUrl) return;

    if (this.ws && this.activeUrl !== nextUrl) {
      this.manualDisconnect = true;
      this.ws.close();
      this.ws = null;
    }

    this.manualDisconnect = false;
    this.activeUrl = nextUrl;

    try {
      this.ws = createWebSocket(nextUrl);

      this.ws.onopen = () => {
        this.reconnectDelay = 2000;
        this.reportedConnectionIssue = false;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handlers.forEach((handler) => handler(data));
        } catch {
          emitAppError({
            source: "websocket",
            message: "Foi recebida uma mensagem invalida no canal em tempo real.",
            dedupeKey: "websocket:parse-error",
          });
        }
      };

      this.ws.onclose = (event) => {
        const shouldReconnect = !this.manualDisconnect && event.code !== 1008;
        this.ws = null;
        this.activeUrl = null;
        if (!this.manualDisconnect) {
          this.reportConnectionIssue();
        }
        if (event.code === 1008) {
          emitAppError({
            source: "websocket",
            message: "Canal em tempo real recusado para o workspace ativo. Atualize a sessao e tente novamente.",
            dedupeKey: "websocket:policy-violation",
          });
          return;
        }
        if (shouldReconnect) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = () => {
        this.ws?.close();
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 30000);
      this.connect();
    }, this.reconnectDelay);
  }

  private reconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.manualDisconnect = true;
    this.ws?.close();
    this.ws = null;
    this.activeUrl = null;
    this.manualDisconnect = false;
    this.connect();
  }

  private reportConnectionIssue(): void {
    if (this.reportedConnectionIssue) {
      return;
    }
    this.reportedConnectionIssue = true;
    emitAppError({
      source: "websocket",
      message: "Conexao em tempo real interrompida. Tentando reconectar automaticamente.",
      dedupeKey: "websocket:connection-lost",
    });
  }

  subscribe(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      this.connect();
    }
    return () => {
      this.handlers.delete(handler);
    };
  }

  disconnect(): void {
    this.manualDisconnect = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    this.activeUrl = null;
  }
}

export const wsClient = new WebSocketClient();
