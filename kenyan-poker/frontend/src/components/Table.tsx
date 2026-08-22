import { useEffect, useRef, useState } from "react";
import { useGameSocket } from "../useGameSocket";
import { PlayingCard } from "./PlayingCard";
import { SuitPicker } from "./SuitPicker";
import { QuitConfirm } from "./QuitConfirm";
import { ChatPanel } from "./ChatPanel";
import { EventLog } from "./EventLog";
import { ShuffleOverlay } from "./ShuffleOverlay";
import * as sound from "../sound";
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
  const { status, room, lastEvents, chatMessages, error, send } =
    useGameSocket(roomId, playerId);
  // Indices into state.my_hand. Multi-card plays require same-rank
  // cards, so selecting a card of a different rank starts a fresh
  // selection rather than mixing ranks.
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
    new Set(),
  );
  // Set once the player commits a play that includes a wild card, so
  // the suit picker can show before the message actually goes out.
  const [pendingCards, setPendingCards] = useState<CardView[] | null>(null);
  const [muted, setMuted] = useState<boolean>(() => sound.isMuted());
  const [showQuitConfirm, setShowQuitConfirm] = useState(false);
  // Set locally the moment this player confirms quitting, so the
  // "you're out" message can say "you left" rather than the
  // punishment-forfeit wording below — the server only tracks
  // eliminated-or-not, not why, so this distinction has to live
  // client-side.
  const [voluntarilyLeft, setVoluntarilyLeft] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  // Bumped for every chat message that arrives while the panel is
  // closed, shown as a badge on the toggle button; cleared the moment
  // the panel opens. Tracked separately from chatMessages.length so a
  // full history replay (there isn't one today, but future-proofing)
  // wouldn't spuriously count as "unread".
  const [unreadChatCount, setUnreadChatCount] = useState(0);
  const lastSeenChatCount = useRef(0);
  // Plays once, right when the table first mounts for a freshly
  // started game — a plain useState(true) rather than anything tied
  // to `status`, so a mid-game reconnect never replays it. Leaving
  // and rejoining a fresh game remounts Table entirely, which is
  // exactly when it should play again.
  const [showShuffle, setShowShuffle] = useState(true);

  // Core-moment sound effects, driven straight off the same event
  // batch the EventLog renders — see sound.ts for what's covered
  // (deliberately not everything, to avoid constant noise) and why
  // this is safe to fire on every lastEvents change: the server only
  // ever sends the events from the action that just happened, never
  // history (a fresh connection starts with events: []), so this
  // never replays sounds for a game already in progress.
  useEffect(() => {
    // A punishment draw and a normal/voluntary draw both produce a
    // "cards_drawn" event with the same shape — the only thing that
    // tells them apart is a companion "draw_stack_cleared" event in
    // the same batch, which the engine only emits when the draw
    // resolved an active draw-pressure stack (see
    // engine._draw_cards_for_player). Checked once per batch rather
    // than per-event since it's a property of the whole batch, not
    // any single event.
    const wasPunishmentDraw = lastEvents.some(
      (event) => event.type === "draw_stack_cleared",
    );

    for (const event of lastEvents) {
      switch (event.type) {
        case "card_played":
          sound.playCardPlayed();
          break;

        case "cards_drawn":
          if (wasPunishmentDraw) {
            sound.playPunishmentDraw();
          } else {
            sound.playNormalDraw();
          }
          break;

        case "turn_advanced":
          if (event.payload.current_player_id === playerId) {
            sound.playYourTurn();
          }
          break;

        case "player_won":
          if (event.payload.player_id === playerId) {
            sound.playWin();
          } else {
            sound.playLose();
          }
          break;

        default:
          break;
      }
    }
  }, [lastEvents, playerId]);

  // Tracks how many chat messages have arrived since the panel was
  // last open, so the toggle button can show an unread badge without
  // the panel itself needing to be mounted while closed.
  useEffect(() => {
    if (chatOpen) {
      lastSeenChatCount.current = chatMessages.length;
      setUnreadChatCount(0);
      return;
    }

    if (chatMessages.length > lastSeenChatCount.current) {
      setUnreadChatCount(chatMessages.length - lastSeenChatCount.current);
    }
  }, [chatMessages.length, chatOpen]);

  const state = room?.state ?? null;

  if (showShuffle) {
    return (
      <div className="table">
        <ShuffleOverlay onDone={() => setShowShuffle(false)} />
      </div>
    );
  }

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

  // Deliberately NOT sorted by hand position — a Set already preserves
  // insertion order in JS, so this keeps cards in the order the player
  // actually clicked them (and re-clicking a card after deselecting it
  // moves it to the end, as the most recently chosen).
  const selectedCards = [...selectedIndices]
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
    // The suit picker only makes sense when the Ace is being played
    // offensively, on a normal turn — countering a pending
    // question/draw/skip with it is reactive and doesn't grant the
    // "declare the next suit" power (see engine._apply_ace_effect),
    // so there's nothing to ask for in those phases.
    const isOffensiveTurn = state.phase === "awaiting_move";

    if (
      isOffensiveTurn &&
      selectedCards.some((card) => WILD_RANKS.has(card.rank))
    ) {
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

  const canQuit =
    state.phase !== "finished" && !me?.is_eliminated && !voluntarilyLeft;

  const confirmQuit = () => {
    send({ type: "quit" });
    setVoluntarilyLeft(true);
    setShowQuitConfirm(false);
  };

  const sendChat = (text: string) => {
    send({ type: "chat", text });
  };

  return (
    <div className="table">
      <div className="table-topbar">
        {canQuit && (
          <button
            type="button"
            className="quit-link"
            onClick={() => setShowQuitConfirm(true)}
          >
            Quit game
          </button>
        )}
        <button
          type="button"
          className="chat-toggle"
          onClick={() => setChatOpen((prev) => !prev)}
          aria-label={chatOpen ? "Close chat" : "Open chat"}
          title={chatOpen ? "Close chat" : "Open chat"}
        >
          💬
          {!chatOpen && unreadChatCount > 0 && (
            <span className="chat-badge">
              {unreadChatCount > 9 ? "9+" : unreadChatCount}
            </span>
          )}
        </button>
        <button
          type="button"
          className="sound-toggle"
          onClick={() => setMuted(sound.toggleMuted())}
          aria-label={muted ? "Unmute sound" : "Mute sound"}
          title={muted ? "Unmute sound" : "Mute sound"}
        >
          {muted ? "🔇" : "🔊"}
        </button>
      </div>

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
              {voluntarilyLeft
                ? "You left the game. Watching the rest of the game play out."
                : `You were eliminated for reaching ${
                    me.card_count === 0 ? "too many" : me.card_count
                  } cards from an unavoidable draw. Watching the rest of the game play out.`}
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

      {showQuitConfirm && (
        <QuitConfirm
          onConfirm={confirmQuit}
          onCancel={() => setShowQuitConfirm(false)}
        />
      )}

      <ChatPanel
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        messages={chatMessages}
        playerId={playerId}
        onSend={sendChat}
      />
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
