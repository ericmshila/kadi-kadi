from __future__ import annotations

from dataclasses import dataclass, field

from .cards import Rank


@dataclass(frozen=True)
class RuleConfig:

    initial_hand_size: int = 4

    draw_ranks: dict[Rank, int] = field(
        default_factory=lambda: {
            Rank.TWO: 2,
            Rank.THREE: 3,
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

    joker_is_wild: bool = True
    joker_requires_declared_suit: bool = True
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
