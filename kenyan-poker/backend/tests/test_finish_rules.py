"""
Finishing rule wiring.

Traditional Kadi: only a plain, effect-free rank can literally end
the game. Every power card — Ace, 2, 3, 8, Jack, Queen, King, Joker —
is excluded from `finishable_ranks` (or gated by its own
`ace_can_finish`/`joker_can_finish` toggle) by default, so playing one
as your very last card never wins the game outright.

This is a separate question from whether a player may be LEFT holding
one of these as their only card in the first place — see
test_niko_kadi_finishability.py for that (allowed by default; a
player can freely play their way down to a lone power card, they just
can't finish the game by playing it).
"""

import pytest
from dataclasses import replace

from app.rules.actions import ActionType, PlayCardsAction
from app.rules.cards import Card, Rank, Suit
from app.rules.config import RuleConfig
from app.rules.engine import IllegalMove, apply_move
from app.rules.state import Phase

from tests.test_rules_engine import make_state


def test_cannot_finish_on_joker_by_default():
    rules = RuleConfig()
    assert rules.joker_can_finish is False

    state = make_state(
        hands={
            "a": (Card(Rank.JOKER, None),),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.JOKER, None),),
        declared_suit=Suit.CLUBS,
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)


def test_can_finish_on_joker_when_explicitly_enabled():
    rules = replace(RuleConfig(), joker_can_finish=True)

    state = make_state(
        hands={
            "a": (Card(Rank.JOKER, None),),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.JOKER, None),),
        declared_suit=Suit.CLUBS,
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.phase == Phase.FINISHED
    assert new_state.winner_id == "a"


def test_cannot_finish_on_a_power_card_by_default():
    """
    8 is a question rank (a power card) — it can never be the literal
    winning play by default.
    """

    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (Card(Rank.EIGHT, Suit.HEARTS),),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.EIGHT, Suit.HEARTS),),
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)


def test_can_finish_on_a_power_card_when_explicitly_enabled():
    rules = replace(
        RuleConfig(),
        finishable_ranks=RuleConfig().finishable_ranks | {Rank.EIGHT},
    )

    state = make_state(
        hands={
            "a": (Card(Rank.EIGHT, Suit.HEARTS),),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.EIGHT, Suit.HEARTS),),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.phase == Phase.FINISHED
    assert new_state.winner_id == "a"


def test_can_finish_on_a_plain_rank_by_default():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (Card(Rank.NINE, Suit.HEARTS),),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.NINE, Suit.HEARTS),),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.phase == Phase.FINISHED
    assert new_state.winner_id == "a"
