"""
Finishing rule wiring.

`RuleConfig.joker_can_finish` should gate whether a Joker is allowed to
be the last card played, matching how `ace_can_finish` gates Aces.
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


def test_can_finish_on_joker_when_enabled():
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


def test_finishable_ranks_still_enforced_for_number_cards():
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
