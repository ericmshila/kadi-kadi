"""
Skip (Jack) rule wiring.

`RuleConfig.skip_can_be_countered` should actually gate whether a skip
can be answered with a Jack/Ace, rather than always allowing it.
"""

import pytest
from dataclasses import replace

from app.rules.actions import ActionType, PassAction, PlayCardsAction
from app.rules.cards import Card, Rank, Suit
from app.rules.config import RuleConfig
from app.rules.engine import IllegalMove, apply_move
from app.rules.events import EventType
from app.rules.state import Phase

from tests.test_rules_engine import make_state


def test_skip_can_be_countered_by_default():
    rules = RuleConfig()
    assert rules.skip_can_be_countered is True

    state = make_state(
        player_count=3,
        current_player_index=1,
        phase=Phase.AWAITING_SKIP_RESPONSE,
        pending_skip_player_id="b",
        hands={
            "a": tuple(),
            "b": (
                Card(Rank.JACK, Suit.CLUBS),
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.SIX, Suit.SPADES),
            ),
            "c": tuple(),
        },
        discard_pile=(Card(Rank.JACK, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="b",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.JACK, Suit.CLUBS),),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.phase == Phase.AWAITING_SKIP_RESPONSE
    assert any(event.type == EventType.SKIP_STARTED for event in events)


def test_skip_cannot_be_countered_when_disabled():
    rules = replace(RuleConfig(), skip_can_be_countered=False)

    state = make_state(
        player_count=3,
        current_player_index=1,
        phase=Phase.AWAITING_SKIP_RESPONSE,
        pending_skip_player_id="b",
        hands={
            "a": tuple(),
            "b": (Card(Rank.JACK, Suit.CLUBS),),
            "c": tuple(),
        },
        discard_pile=(Card(Rank.JACK, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="b",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.JACK, Suit.CLUBS),),
        declare_niko_kadi=True,
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)


def test_pass_still_works_when_skip_cannot_be_countered():
    rules = replace(RuleConfig(), skip_can_be_countered=False)

    state = make_state(
        player_count=3,
        current_player_index=1,
        phase=Phase.AWAITING_SKIP_RESPONSE,
        pending_skip_player_id="b",
        hands={
            "a": tuple(),
            "b": (Card(Rank.FOUR, Suit.CLUBS),),
            "c": tuple(),
        },
        discard_pile=(Card(Rank.JACK, Suit.HEARTS),),
    )

    action = PassAction(player_id="b", type=ActionType.PASS)

    new_state, events = apply_move(state, action, rules)

    assert new_state.phase == Phase.AWAITING_MOVE
    assert new_state.current_player.id == "c"
