import type { GameEventView, PlayerView } from "../types";

function nameOf(players: PlayerView[], id: unknown): string {
  const found = players.find((player) => player.id === id);
  return found ? found.name : String(id);
}

function describe(event: GameEventView, players: PlayerView[]): string {
  const payload = event.payload;

  switch (event.type) {
    case "card_played":
      return `${nameOf(players, payload.player_id)} played ${payload.card}`;
    case "cards_drawn":
      return `${nameOf(players, payload.player_id)} drew ${payload.count} card(s)`;
    case "turn_advanced":
      return `${nameOf(players, payload.current_player_id)}'s turn`;
    case "direction_reversed":
      return "Direction reversed";
    case "draw_stack_started":
      return `Draw pressure started: ${payload.pending_draw_count}`;
    case "draw_stack_increased":
      return `Draw pressure increased to ${payload.pending_draw_count}`;
    case "draw_stack_cleared":
      return `${nameOf(players, payload.player_id)} cleared the draw pressure`;
    case "question_asked": {
      const count = typeof payload.card_count === "number" ? payload.card_count : 1;
      const prefix = count > 1 ? `Question asked (${count} cards)` : "Question asked";
      return `${prefix} — ${nameOf(players, payload.target_player_id)} must answer`;
    }
    case "question_answered":
      return `${nameOf(players, payload.player_id)} answered the question`;
    case "question_failed":
      return `${nameOf(players, payload.player_id)} failed to answer`;
    case "skip_started": {
      const count = typeof payload.skip_count === "number" ? payload.skip_count : 1;
      const suffix = count > 1 ? ` (${count} players)` : "";
      return `Skip aimed at ${nameOf(players, payload.target_player_id)}${suffix}`;
    }
    case "skip_countered":
      return `${nameOf(players, payload.player_id)} countered the skip`;
    case "player_skipped":
      return `${nameOf(players, payload.player_id)} was skipped`;
    case "ace_counter_played":
      return `${nameOf(players, payload.player_id)} countered with an Ace`;
    case "punishment_cleared":
      return "Punishment cleared";
    case "suit_declared":
      return `${nameOf(players, payload.player_id)} declared ${payload.suit}`;
    case "niko_kadi_declared":
      return `${nameOf(players, payload.player_id)} declared "Niko Kadi"`;
    case "niko_kadi_penalty":
      return `${nameOf(players, payload.player_id)} was penalized for not declaring "Niko Kadi"`;
    case "player_won":
      return `${nameOf(players, payload.player_id)} won the game!`;
    case "player_eliminated":
      return `${nameOf(players, payload.player_id)} was eliminated (reached ${payload.hand_size} cards)`;
    case "game_started":
      return "Game started";
    case "game_finished":
      return "Game finished";
    default:
      return event.type.replace(/_/g, " ");
  }
}

interface EventLogProps {
  events: GameEventView[];
  players: PlayerView[];
}

export function EventLog({ events, players }: EventLogProps) {
  const visible = events.filter(
    (event) => event.type !== "turn_advanced",
  );

  if (visible.length === 0) {
    return null;
  }

  return (
    <div className="event-log">
      {visible.map((event, index) => (
        <p key={`${event.type}-${index}`}>{describe(event, players)}</p>
      ))}
    </div>
  );
}
