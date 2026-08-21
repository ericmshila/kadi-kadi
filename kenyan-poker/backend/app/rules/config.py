from __future__ import annotations

from dataclasses import dataclass, field

from .cards import Rank


@dataclass(frozen=True)
class RuleConfig:

    initial_hand_size: int = 4

    # Joker is a punishment card, same family as 2s/3s: playing one
    # forces the next player to draw this many, or counter with
    # another draw card. Stacks with 2s/3s and other Jokers just like
    # they stack with each other (see engine._apply_draw_card_effect).
    draw_ranks: dict[Rank, int] = field(
        default_factory=lambda: {
            Rank.TWO: 2,
            Rank.THREE: 3,
            Rank.JOKER: 5,
        }
    )

    draw_stacking_enabled: bool = True

    question_ranks: set[Rank] = field(
        default_factory=lambda: {
            Rank.EIGHT,
            Rank.QUEEN,
        }
    )

    question_answer_ranks: set[Rank] = field(
        default_factory=lambda: {
            Rank.TWO,
            Rank.THREE,
            Rank.FOUR,
            Rank.FIVE,
            Rank.SIX,
            Rank.SEVEN,
            Rank.NINE,
            Rank.TEN,
        }
    )

    skip_ranks: set[Rank] = field(
        default_factory=lambda: {
            Rank.JACK,
        }
    )

    skip_can_be_countered: bool = True

    reverse_ranks: set[Rank] = field(
        default_factory=lambda: {
            Rank.KING,
        }
    )

    ace_is_wild: bool = True
    ace_requires_declared_suit: bool = True
    ace_counters_punishments: bool = True
    ace_can_answer_question: bool = False
    ace_can_finish: bool = False

    # Joker is always playable regardless of the top card (no suit or
    # rank match required), like Ace — but unlike Ace, it doesn't
    # declare a suit; it triggers a draw-pressure punishment instead
    # (see draw_ranks above).
    joker_can_answer_question: bool = False
    joker_can_finish: bool = False

    must_declare_niko_kadi: bool = True
    strict_niko_kadi: bool = True
    niko_kadi_penalty_cards: int = 2

    finishable_ranks: set[Rank] = field(
        default_factory=lambda: {
            Rank.FOUR,
            Rank.FIVE,
            Rank.SIX,
            Rank.SEVEN,
            Rank.NINE,
            Rank.TEN,
        }
    )

    # ---------------------------------------------------------
    # Forfeit
    # ---------------------------------------------------------

    # A player who is forced to draw an unavoidable punishment stack
    # (a 2/3 draw chain they had no counter or restack for) and ends
    # up holding this many cards or more is eliminated from the game.
    # Their hand is shuffled back into the draw pile. Set to None to
    # disable this rule entirely.
    forfeit_hand_size: int | None = 10
