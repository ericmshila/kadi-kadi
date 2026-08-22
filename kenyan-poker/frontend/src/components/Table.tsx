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

// Only Ace needs a suit declared before it goes out — Joker is a
// punishment card now (like a 2/3, just worth more), so it plays
// immediately with no suit picker.
const WILD_RANKS = new Set(["A"]);

function initialOf(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "?";
}

export function Table({ roomId, playerId, onLeave }: TableProps) {
  const { status, room, lastEvents, error, send } = useGameSocket(
    roomId,
    playerId,
  );
  // Indices into state.my_hand. Multi-card plays require same-rank
  // cards, so selecting a card of a different rank starts a fresh
  // selection rather than mixing ranks.
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
    new Set(),
  );
  // Set once the player commits a play that includes a wild card, so
  // the suit picker can show before the message actually goes out.
  const [pendingCards, setPendingCards] = useState<CardView[] | null>(null);

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

  const selectedCards = [...selectedIndices]
    .sort((a, b) => a - b)
    .map((index) => state.my_hand[index])
    .filter((card): card is CardView => card !== undefined);

  // Playing the current selection would leave exactly one card in
  // hand — Niko Kadi must be declared with this play.
  const willDeclareNikoKadi =
    selectedCards.length > 0 &&
    state.my_hand.length - selectedCards.length === 1;

  const commitPlay = (declaredSuit?: Suit) => {
    if (selectedCards.length === 0) {
      return;
    }

    send({
      type: "play_cards",
      cards: selectedCards.map((card) => ({
        rank: card.rank,
        suit: card.suit,
        joker_color: card.joker_color,
      })),
      declared_suit: declaredSuit ?? null,
      declare_niko_kadi: willDeclareNikoKadi,
    });
    setSelectedIndices(new Set());
    setPendingCards(null);
  };

  const handlePlayClick = () => {
    if (selectedCards.some((card) => WILD_RANKS.has(card.rank))) {
      setPendingCards(selectedCards);
    } else {
      commitPlay();
    }
  };

  const toggleCardSelection = (index: number) => {
    if (!isMyTurn) {
      return;
    }

    setSelectedIndices((prev) => {
      if (prev.has(index)) {
        const next = new Set(prev);
        next.delete(index);
        return next;
      }

      const [firstSelected] = prev;
      const selectedRank =
        firstSelected !== undefined
          ? state.my_hand[firstSelected]?.rank
          : undefined;
      const clickedRank = state.my_hand[index]?.rank;

      // A different rank than what's already selected starts a fresh
      // selection instead of mixing ranks (the server would reject
      // that anyway — this just avoids the round trip).
      if (selectedRank && clickedRank !== selectedRank) {
        return new Set([index]);
      }

      return new Set(prev).add(index);
    });
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
            <>
              <p className="winner">
                {state.winner_id === playerId
                  ? "You won! 🎉"
                  : `${winner?.name ?? "A player"} won.`}
              </p>
              {state.winner_id === playerId ? (
                <button
                  type="button"
                  className="play-again"
                  onClick={() => send({ type: "restart" })}
                >
                  Play again
                </button>
              ) : (
                <p className="hint">
                  Waiting for {winner?.name ?? "the winner"} to start a new
                  game.
                </p>
              )}
            </>
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
              key={`${card.rank}-${card.suit ?? card.joker_color ?? "none"}-${index}`}
              card={card}
              disabled={!isMyTurn}
              selected={selectedIndices.has(index)}
              onClick={() => toggleCardSelection(index)}
            />
          ))}
        </div>
        {isMyTurn && selectedCards.length > 0 && (
          <div className="selection-bar">
            <p className="hint">
              {selectedCards.length === 1
                ? "1 card selected"
                : `${selectedCards.length} cards selected (same rank, played together)`}
              {willDeclareNikoKadi && " — this will declare \"Niko Kadi\""}
            </p>
            <div className="selection-actions">
              <button type="button" onClick={handlePlayClick}>
                Play {selectedCards.length === 1 ? "card" : `${selectedCards.length} cards`}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setSelectedIndices(new Set())}
              >
                Clear
              </button>
            </div>
          </div>
        )}
        {isMyTurn && selectedCards.length === 0 && (
          <p className="hint">
            Tap a card to select it — tap more of the same rank to play
            them together.
          </p>
        )}
      </div>

      <EventLog events={lastEvents} players={state.players} />

      {error && <p className="error toast">{error}</p>}

      {pendingCards && (
        <SuitPicker
          onPick={(suit) => commitPlay(suit)}
          onCancel={() => setPendingCards(null)}
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
