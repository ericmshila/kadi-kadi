"""
Game Room

A GameRoom owns:

- Players
- Room rules
- Current state

It acts as a thin wrapper around the rules engine.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.rules.actions import PlayerAction
from app.rules.config import RuleConfig
from app.rules.engine import apply_move, create_initial_state
from app.rules.events import GameEvent
from app.rules.state import GameState, Phase, Player

# Deliberately short and easy to read aloud/type on a phone: 30
# characters ^ 5 = ~24M possible codes, no I/L/O/0/1 (easy to mix up
# in handwriting or over voice chat while setting up a LAN game).
_ROOM_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_ROOM_CODE_LENGTH = 5


def generate_room_code() -> str:
    return "".join(
        random.choice(_ROOM_CODE_ALPHABET) for _ in range(_ROOM_CODE_LENGTH)
    )


@dataclass
class GameRoom:
    room_id: str

    rules: RuleConfig

    players: list[Player] = field(default_factory=list)

    state: GameState | None = None

    started: bool = False

    # ---------------------------------------------------------
    # Player Management
    # ---------------------------------------------------------

    def add_player(
        self,
        player: Player,
    ) -> None:

        if self.started:
            raise ValueError(
                "Cannot join a room after the game has started."
            )

        if any(p.id == player.id for p in self.players):
            raise ValueError(
                f"Player already exists: {player.id}"
            )

        self.players.append(player)

    # ---------------------------------------------------------
    # Game Lifecycle
    # ---------------------------------------------------------

    def start_game(
        self,
        seed: int | None = None,
    ) -> list[GameEvent]:

        if self.started:
            raise ValueError(
                "Game already started."
            )

        if len(self.players) < 2:
            raise ValueError(
                "At least two players are required."
            )

        state, events = create_initial_state(
            players=self.players,
            rules=self.rules,
            seed=seed,
        )

        self.state = state
        self.started = True

        return events

    def restart(
        self,
        player_id: str,
        seed: int | None = None,
    ) -> list[GameEvent]:
        """
        Starts a fresh round for the same group of players once the
        current one has finished — a new shuffle, new hands, nobody
        eliminated. Only the winner of the round that just ended may
        trigger this (there's still no persistent host/owner concept
        beyond that — it's whoever won THIS round, which can be a
        different player each time).

        Players who left the room mid-game are not removed, and no
        new players can be added here — the room's ``players`` list
        (who joined before the very first ``start_game``) carries
        over unchanged. Rejoining a fresh set of players is a
        separate feature (create a new room).
        """

        if self.state is None:
            raise ValueError(
                "Game has not started."
            )

        if self.state.phase != Phase.FINISHED:
            raise ValueError(
                "Current round is still in progress."
            )

        if player_id != self.state.winner_id:
            raise ValueError(
                "Only the winner of the last round can start a new game."
            )

        state, events = create_initial_state(
            players=self.players,
            rules=self.rules,
            seed=seed,
        )

        self.state = state

        return events

    # ---------------------------------------------------------
    # Gameplay
    # ---------------------------------------------------------

    def apply(
        self,
        action: PlayerAction,
    ) -> list[GameEvent]:

        if self.state is None:
            raise ValueError(
                "Game has not started."
            )

        new_state, events = apply_move(
            state=self.state,
            action=action,
            rules=self.rules,
        )

        self.state = new_state

        return events

    # ---------------------------------------------------------
    # Convenience Properties
    # ---------------------------------------------------------

    @property
    def has_started(self) -> bool:
        return self.started

    @property
    def is_finished(self) -> bool:

        if self.state is None:
            return False

        return self.state.winner_id is not None


def create_room(
    rules: RuleConfig | None = None,
) -> GameRoom:

    return GameRoom(
        room_id=generate_room_code(),
        rules=rules or RuleConfig(),
    )