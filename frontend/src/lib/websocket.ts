import type { Opportunity } from "./types";
import { emitAppError } from "./app-errors";

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

class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 2000;
  private manualDisconnect = false;
  private reportedConnectionIssue = false;

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.manualDisconnect = false;

    try {
      this.ws = createWebSocket(WS_URL);

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

      this.ws.onclose = () => {
        if (!this.manualDisconnect) {
          this.reportConnectionIssue();
        }
        this.scheduleReconnect();
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
  }
}

export const wsClient = new WebSocketClient();
