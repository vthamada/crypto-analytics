import type { Opportunity } from "./types";

type MessageHandler = (data: {
  type: string;
  data?: Opportunity[];
  timestamp?: string;
  count?: number;
}) => void;

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 2000;

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    try {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        this.reconnectDelay = 2000;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handlers.forEach((handler) => handler(data));
        } catch {
          // ignore parse errors
        }
      };

      this.ws.onclose = () => {
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
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }
}

export const wsClient = new WebSocketClient();
