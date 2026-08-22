/**
 * Types mirroring the backend's JSON shapes.
 *
 * Kept intentionally close to app/api/schemas.py, app/game/serializers.py
 * and app/rules/events.py on the backend so the two sides don't quietly
 * drift apart.
 */

export type Suit = "spades" | "hearts" | "diamonds" | "clubs";

export type Rank =
  | "2"
  | "3"
  | "4"
  | "5"
  | "6"
  | "7"
  | "8"
  | "9"
  | "10"
  | "J"
  | "Q"
  | "K"
  | "A"
  | "JOKER";

export type JokerColor = "red" | "black";

export interface CardView {
  rank: Rank;
  suit: Suit | null;
  joker_color: JokerColor | null;
  label: string;
}

export type Phase =
  | "awaiting_move"
  | "awaiting_answer"
  | "awaiting_draw_response"
  | "awaiting_skip_response"
  | "finished";

export interface PlayerView {
  id: string;
  name: string;
  card_count: number;
  is_current_player: boolean;
  is_you: boolean;
  is_eliminated: boolean;
}

export interface RoomPlayerSummary {
  id: string;
  name: string;
}

export interface GameStateView {
  current_player: string;
  phase: Phase;
  top_card: CardView;
  direction: number;
  winner_id: string | null;
  pending_draw_count: number;
  pending_question_player_id: string | null;
  pending_skip_player_id: string | null;
  active_suit: Suit | null;
  players: PlayerView[];
  my_hand: CardView[];
}

export interface RoomView {
  room_id: string;
  started: boolean;
  players: RoomPlayerSummary[];
  state: GameStateView | null;
}

export interface GameEventView {
  type: string;
  payload: Record<string, unknown>;
}

export type ServerMessageType =
  | "state"
  | "error"
  | "player_connected"
  | "player_disconnected"
  | "chat";

export interface ServerMessage {
  type: ServerMessageType;
  room?: RoomView;
  events?: GameEventView[];
  detail?: string;
  player_id?: string;
  name?: string;
  text?: string;
}

// The hook-local, accumulated view of a chat message — `id` is
// generated client-side (the server doesn't assign one) purely so
// React has a stable list key.
export interface ChatMessageView {
  id: string;
  playerId: string;
  name: string;
  text: string;
}
