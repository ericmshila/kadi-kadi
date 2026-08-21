import { useState } from "react";
import { useGameSocket } from "../useGameSocket";
import { PlayingCard } from "./PlayingCard";
import { SuitPicker } from "./SuitPicker";
import { EventLog } from "./EventLog";
import type { CardView, Phase, Suit } from "../types";

interface TableProps {
  roomId: string;
  playerId: string;
  onLeave: () => void;
}

const WILD_RANKS = new Set(["A", "JOKER"]);

function initialOf(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "?";
}

export function Table({ roomId, playerId, onLeave }: TableProps) {
  const { status, room, lastEvents, error, send } = useGameSocket(
    roomId,
    playerId,
  );
  const [pendingCard, setPendingCard] = useState<CardView | null>(null);

  const state = room?.state ?? null;

  if (status === "connecting" && !room) {
    return (
      <div className="status-line">
        <p>Connecting…</p>
        <button className="leave-link" onClick={onLeave}>
          Leave game
        </button>
      </div>
    );
  }

  if (status === "closed" && !room) {
    return (
      <div className="status-line">
        <p className="error">
          Couldn't reach the game (the server may have restarted).
        </p>
        <button className="leave-link" onClick={onLeave}>
          Leave game
        </button>
      </div>
    );
  }

  if (!state) {
    return <p className="status-line">Waiting for game state…</p>;
  }

  const isMyTurn = state.current_player === playerId;
  // Single-card plays only in this UI: if my hand has exactly 2 cards,
  // playing one leaves exactly 1 — Niko Kadi must be declared with it.
  const mustDeclareNikoKadi = state.my_hand.length === 2;

  const playCard = (card: CardView, declaredSuit?: Suit) => {
    send({
      type: "play_cards",
      cards: [{ rank: card.rank, suit: card.suit }],
      declared_suit: declaredSuit ?? null,
      declare_niko_kadi: mustDeclareNikoKadi,
    });
    setPendingCard(null);
  };

  const handleCardClick = (card: CardView) => {
    if (!isMyTurn) {
      return;
    }

    if (WILD_RANKS.has(card.rank)) {
      setPendingCard(card);
    } else {
      playCard(card);
    }
  };

  const opponents = state.players.filter((player) => player.id !== playerId);
  const me = state.players.find((player) => player.id === playerId);
  const winner = state.players.find((player) => player.id === state.winner_id);

  return (
    <div className="table">
      {status === "closed" && (
        <div className="connection-banner">
          <p>Connection lost (the server may have restarted).</p>
          <button className="leave-link" onClick={onLeave}>
            Leave game
          </button>
        </div>
      )}

      <div className="opponents">
        {opponents.map((player) => (
          <div
            key={player.id}
            className={[
              "opponent",
              player.is_current_player ? "current" : "",
              player.is_eliminated ? "eliminated" : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <span className="avatar">{initialOf(player.name)}</span>
            <span className="name">{player.name}</span>
            {player.is_eliminated ? (
              <span className="count">Eliminated</span>
            ) : (
              <span className="count">
                {player.card_count} card{player.card_count === 1 ? "" : "s"}
              </span>
            )}
          </div>
        ))}
      </div>

      <div className="board">
        <div className="discard-pile">
          <PlayingCard card={state.top_card} />
          {state.active_suit && (
            <span className="active-suit">Declared: {state.active_suit}</span>
          )}
        </div>

        <div className="table-status">
          {state.phase === "finished" ? (
            <p className="winner">
              {state.winner_id === playerId
                ? "You won! 🎉"
                : `${winner?.name ?? "A player"} won.`}
            </p>
          ) : me?.is_eliminated ? (
            <p className="hint">
              You were eliminated for reaching {me.card_count === 0 ? "too many" : me.card_count}{" "}
              cards from an unavoidable draw. Watching the rest of the game play out.
            </p>
          ) : (
            <>
              <p>
                {isMyTurn
                  ? "Your turn"
                  : `Waiting on ${
                      state.players.find(
                        (player) => player.id === state.current_player,
                      )?.name ?? "…"
                    }`}
              </p>
              {state.phase === "awaiting_draw_response" && (
                <p className="hint">
                  Draw pressure: {state.pending_draw_count}
                </p>
              )}
              {state.phase === "awaiting_skip_response" && (
                <p className="hint">Skip pending</p>
              )}
              {state.phase === "awaiting_answer" && (
                <p className="hint">A question was asked</p>
              )}
            </>
          )}
        </div>

        <ActionBar
          phase={state.phase}
          isMyTurn={isMyTurn}
          pendingDrawCount={state.pending_draw_count}
          onDraw={() => send({ type: "draw" })}
          onPass={() => send({ type: "pass" })}
        />
      </div>

      <div className="my-hand">
        <p className="hand-label">
          {me?.name ?? "You"} ({state.my_hand.length} card
          {state.my_hand.length === 1 ? "" : "s"})
        </p>
        <div className="hand-cards">
          {state.my_hand.map((card, index) => (
            <PlayingCard
              key={`${card.rank}-${card.suit ?? "none"}-${index}`}
              card={card}
              disabled={!isMyTurn}
              onClick={() => handleCardClick(card)}
            />
          ))}
        </div>
        {isMyTurn && mustDeclareNikoKadi && (
          <p className="hint">
            Playing a card now will declare "Niko Kadi" for you.
          </p>
        )}
      </div>

      <EventLog events={lastEvents} players={state.players} />

      {error && <p className="error toast">{error}</p>}

      {pendingCard && (
        <SuitPicker
          onPick={(suit) => playCard(pendingCard, suit)}
          onCancel={() => setPendingCard(null)}
        />
      )}
    </div>
  );
}

interface ActionBarProps {
  phase: Phase;
  isMyTurn: boolean;
  pendingDrawCount: number;
  onDraw: () => void;
  onPass: () => void;
}

function ActionBar({
  phase,
  isMyTurn,
  pendingDrawCount,
  onDraw,
  onPass,
}: ActionBarProps) {
  if (!isMyTurn || phase === "finished") {
    return null;
  }

  if (phase === "awaiting_skip_response") {
    return (
      <div className="action-bar">
        <button type="button" className="btn-secondary" onClick={onPass}>
          Accept skip (pass)
        </button>
      </div>
    );
  }

  if (phase === "awaiting_draw_response") {
    return (
      <div className="action-bar">
        <button type="button" onClick={onDraw}>
          Draw {pendingDrawCount} cards
        </button>
      </div>
    );
  }

  return (
    <div className="action-bar">
      <button type="button" onClick={onDraw}>
        Draw a card
      </button>
    </div>
  );
}
