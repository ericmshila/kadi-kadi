"""
Ace rule wiring.

RuleConfig exposes several ace-related toggles. These tests confirm the
engine actually enforces them (as opposed to the flag existing but being
silently ignored).
"""

import pytest
from dataclasses import replace

from app.rules.actions import ActionType, PlayCardsAction
from app.rules.cards import Card, Rank, Suit
from app.rules.config import RuleConfig
from app.rules.engine import IllegalMove, apply_move
from app.rules.state import Phase

from tests.test_rules_engine import make_state


def test_ace_cannot_answer_question_by_default():
    rules = RuleConfig()
    assert rules.ace_can_answer_question is False

    state = make_state(
        current_player_index=1,
        phase=Phase.AWAITING_ANSWER,
        pending_question_player_id="b",
        hands={
            "a": tuple(),
            "b": (
                Card(Rank.ACE, Suit.HEARTS),
                Card(Rank.FOUR, Suit.CLUBS),
            ),
        },
        discard_pile=(Card(Rank.QUEEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="b",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.ACE, Suit.HEARTS),),
        declared_suit=Suit.HEARTS,
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)


def test_ace_can_answer_question_when_enabled():
    rules = replace(RuleConfig(), ace_can_answer_question=True)

    state = make_state(
        current_player_index=1,
        phase=Phase.AWAITING_ANSWER,
        pending_question_player_id="b",
        hands={
            "a": tuple(),
            "b": (
                Card(Rank.ACE, Suit.HEARTS),
                Card(Rank.FOUR, Suit.CLUBS),
            ),
        },
        discard_pile=(Card(Rank.QUEEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="b",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.ACE, Suit.HEARTS),),
        declared_suit=Suit.HEARTS,
        declare_niko_kadi=True,
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.phase == Phase.AWAITING_MOVE
    assert new_state.active_suit == Suit.HEARTS


def test_ace_cannot_finish_by_default():
    rules = RuleConfig()
    assert rules.ace_can_finish is False

    state = make_state(
        hands={
            "a": (Card(Rank.ACE, Suit.SPADES),),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.ACE, Suit.SPADES),),
        declared_suit=Suit.CLUBS,
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)


def test_ace_can_finish_when_enabled():
    rules = replace(RuleConfig(), ace_can_finish=True)

    state = make_state(
        hands={
            "a": (Card(Rank.ACE, Suit.SPADES),),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.ACE, Suit.SPADES),),
        declared_suit=Suit.CLUBS,
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.phase == Phase.FINISHED
    assert new_state.winner_id == "a"
