"""
Finishing rule wiring.

Every card is playable at the player's whim by default — including as
the very last card in hand — so `joker_can_finish` and
`finishable_ranks` are permissive out of the box. The toggles
themselves still exist and are still enforced when a stricter config
opts back into them (see the "_when_restricted" tests below); they're
just not the default anymore.
"""

import pytest
from dataclasses import replace

from app.rules.actions import ActionType, PlayCardsAction
from app.rules.cards import Card, Rank, Suit
from app.rules.config import RuleConfig
from app.rules.engine import IllegalMove, apply_move
from app.rules.state import Phase

from tests.test_rules_engine import make_state


def test_can_finish_on_joker_by_default():
    rules = RuleConfig()
    assert rules.joker_can_finish is True

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


def test_cannot_finish_on_joker_when_restricted():
    rules = replace(RuleConfig(), joker_can_finish=False)

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


def test_can_finish_on_a_power_card_by_default():
    """
    8 is a question rank (a power card) — it's still allowed to end
    the game by default, unlike the old, more restrictive ruleset.
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

    new_state, events = apply_move(state, action, rules)

    assert new_state.phase == Phase.FINISHED
    assert new_state.winner_id == "a"


def test_finishable_ranks_still_enforced_when_explicitly_restricted():
    rules = replace(
        RuleConfig(),
        finishable_ranks=RuleConfig().finishable_ranks - {Rank.EIGHT},
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

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)
