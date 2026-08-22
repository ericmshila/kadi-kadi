import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "./api";
import type { ChatMessageView, GameEventView, RoomView, ServerMessage } from "./types";

// Keeps memory bounded on a long-running session — old messages
// simply scroll out rather than the array growing forever.
const MAX_CHAT_HISTORY = 200;

// Derived from the same API_BASE_URL used for REST calls (see
// api.ts), so the WebSocket automatically follows whatever host —
// localhost, LAN IP, or Hamachi/Tailscale IP — the page was loaded
// from. Override with VITE_WS_BASE_URL only if the WS endpoint lives
// somewhere different from the REST API.
const WS_BASE_URL: string =
  (import.meta.env.VITE_WS_BASE_URL as string | undefined) ??
  API_BASE_URL.replace(/^http/, "ws");

export type ConnectionStatus = "connecting" | "open" | "closed";

interface UseGameSocketResult {
  status: ConnectionStatus;
  room: RoomView | null;
  lastEvents: GameEventView[];
  chatMessages: ChatMessageView[];
  error: string | null;
  send: (payload: Record<string, unknown>) => void;
}

/**
 * Owns the WebSocket connection for one room + player.
 *
 * Reconnects whenever roomId/playerId change (e.g. moving from the
 * lobby into a started game) and tears the socket down on unmount.
 */
export function useGameSocket(
  roomId: string | null,
  playerId: string | null,
): UseGameSocketResult {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [room, setRoom] = useState<RoomView | null>(null);
  const [lastEvents, setLastEvents] = useState<GameEventView[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessageView[]>([]);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  // Client-generated list key — the server doesn't assign chat
  // message ids, and a Set-free counter is simpler than pulling in
  // crypto.randomUUID() just for this.
  const chatIdRef = useRef(0);

  useEffect(() => {
    if (!roomId || !playerId) {
      return;
    }

    setStatus("connecting");
    setError(null);

    const socket = new WebSocket(
      `${WS_BASE_URL}/api/ws/rooms/${roomId}?player_id=${encodeURIComponent(
        playerId,
      )}`,
    );
    socketRef.current = socket;

    socket.onopen = () => setStatus("open");
    socket.onclose = () => setStatus("closed");
    socket.onerror = () => setStatus("closed");

    socket.onmessage = (event: MessageEvent<string>) => {
      let message: ServerMessage;

      try {
        message = JSON.parse(event.data) as ServerMessage;
      } catch {
        return;
      }

      if (message.type === "state" && message.room) {
        setRoom(message.room);
        setLastEvents(message.events ?? []);
        setError(null);
      } else if (message.type === "error") {
        setError(message.detail ?? "Unknown error");
      } else if (
        message.type === "chat" &&
        message.player_id &&
        message.name &&
        message.text
      ) {
        chatIdRef.current += 1;

        const playerId = message.player_id;
        const name = message.name;
        const text = message.text;

        setChatMessages((prev) => {
          const next = [
            ...prev,
            { id: String(chatIdRef.current), playerId, name, text },
          ];

          return next.length > MAX_CHAT_HISTORY
            ? next.slice(next.length - MAX_CHAT_HISTORY)
            : next;
        });
      }
    };

    return () => {
      socket.close();
      if (socketRef.current === socket) {
        socketRef.current = null;
      }
    };
  }, [roomId, playerId]);

  const send = useCallback((payload: Record<string, unknown>) => {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
    }
  }, []);

  return { status, room, lastEvents, chatMessages, error, send };
}
