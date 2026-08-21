"""
Game state models.

This module defines:
- Players
- Game phases
- Immutable game state

No game logic should live here.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Optional

from .cards import Card, Suit


class Phase(str, Enum):
    """
    Current game phase.

    Different phases allow different legal actions.
    """

    AWAITING_MOVE = "awaiting_move"

    AWAITING_ANSWER = "awaiting_answer"

    AWAITING_DRAW_RESPONSE = "awaiting_draw_response"

    AWAITING_SKIP_RESPONSE = "awaiting_skip_response"

    FINISHED = "finished"


@dataclass(frozen=True)
class Player:
    """
    Lightweight player model.

    Keep player data minimal.
    Profile information belongs elsewhere.
    """

    id: str
    name: str


@dataclass(frozen=True)
class GameState:
    """
    Immutable snapshot of a game.

    Every move produces a NEW GameState.
    """

    # ---------------------------------------------------------
    # Players
    # ---------------------------------------------------------

    players: tuple[Player, ...]

    # ---------------------------------------------------------
    # Player hands
    # ---------------------------------------------------------

    hands: dict[str, tuple[Card, ...]]

    # ---------------------------------------------------------
    # Decks
    # ---------------------------------------------------------

    draw_pile: tuple[Card, ...]

    discard_pile: tuple[Card, ...]

    # ---------------------------------------------------------
    # Turn tracking
    # ---------------------------------------------------------

    current_player_index: int = 0

    direction: int = 1

    # ---------------------------------------------------------
    # Game flow
    # ---------------------------------------------------------

    phase: Phase = Phase.AWAITING_MOVE

    # ---------------------------------------------------------
    # Pending effects
    # ---------------------------------------------------------

    pending_draw_count: int = 0

    active_suit: Optional[Suit] = None

    # Player currently being questioned
    pending_question_player_id: Optional[str] = None

    # Player currently under skip pressure
    pending_skip_player_id: Optional[str] = None

    # ---------------------------------------------------------
    # Niko Kadi
    # ---------------------------------------------------------

    niko_kadi_declared_by: frozenset[str] = field(
        default_factory=frozenset
    )

    # ---------------------------------------------------------
    # Forfeits
    # ---------------------------------------------------------

    # Players who were eliminated for being punished up to the
    # forfeit hand size with no way to avoid it. They keep their seat
    # in `players` (for history/UI) but are skipped in turn order and
    # hold an empty hand.
    eliminated_player_ids: frozenset[str] = field(
        default_factory=frozenset
    )

    # ---------------------------------------------------------
    # Winner
    # ---------------------------------------------------------

    winner_id: Optional[str] = None

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    @property
    def top_card(self) -> Card:
        return self.discard_pile[-1]

    @property
    def player_count(self) -> int:
        return len(self.players)

    @property
    def active_player_count(self) -> int:
        return len(self.players) - len(self.eliminated_player_ids)

    def hand_of(self, player_id: str) -> tuple[Card, ...]:
        return self.hands[player_id]

    def replace(self, **changes) -> "GameState":
        """
        Convenience wrapper around dataclasses.replace()
        to preserve immutable workflow.
        """

        return replace(self, **changes)