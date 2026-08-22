"""
"Niko Kadi" is a promise to win on the very next turn — so a player
should never be allowed to play their way down to a single card that
could never actually finish the game (an unfinishable rank like a
King, or an Ace/Joker when the rule config doesn't let those finish).
They'd just be stuck holding it forever, unable to legally end their
turn on it.
"""

import pytest
from dataclasses import replace

from app.rules.actions import ActionType, PlayCardsAction
from app.rules.cards import Card, JokerColor, Rank, Suit
from app.rules.config import RuleConfig
from app.rules.engine import IllegalMove, apply_move

from tests.test_rules_engine import make_state


def test_cannot_declare_niko_kadi_down_to_a_lone_ace_by_default():
    rules = RuleConfig()  # ace_can_finish is False by default

    state = make_state(
        hands={
            "a": (
                Card(Rank.SIX, Suit.HEARTS),  # legal to play on the 7 of hearts
                Card(Rank.ACE, Suit.SPADES),  # would be the only card left
            ),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.SIX, Suit.HEARTS),),
        declare_niko_kadi=True,
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)

    # Nothing should have moved out of the hand — the play never went through.


def test_cannot_declare_niko_kadi_down_to_a_power_card():
    """
    King isn't in finishable_ranks by default (power/effect cards
    can't end the game) — so being left holding only a King is just
    as blocked as an unfinishable Ace.
    """

    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.SIX, Suit.HEARTS),
                Card(Rank.KING, Suit.SPADES),
            ),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.SIX, Suit.HEARTS),),
        declare_niko_kadi=True,
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)


def test_can_declare_niko_kadi_down_to_a_finishable_card():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.SIX, Suit.HEARTS),
                Card(Rank.NINE, Suit.SPADES),  # finishable, in the default set
            ),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.SIX, Suit.HEARTS),),
        declare_niko_kadi=True,
    )

    new_state, _events = apply_move(state, action, rules)

    assert new_state.hand_of("a") == (Card(Rank.NINE, Suit.SPADES),)
    assert "a" in new_state.niko_kadi_declared_by


def test_lone_ace_is_allowed_when_ace_can_finish_is_enabled():
    rules = replace(RuleConfig(), ace_can_finish=True)

    state = make_state(
        hands={
            "a": (
                Card(Rank.SIX, Suit.HEARTS),
                Card(Rank.ACE, Suit.SPADES),
            ),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.SIX, Suit.HEARTS),),
        declare_niko_kadi=True,
    )

    new_state, _events = apply_move(state, action, rules)

    assert new_state.hand_of("a") == (Card(Rank.ACE, Suit.SPADES),)


def test_lone_joker_is_blocked_by_default_but_allowed_when_enabled():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.SIX, Suit.HEARTS),
                Card(Rank.JOKER, None, JokerColor.BLACK),
            ),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.SIX, Suit.HEARTS),),
        declare_niko_kadi=True,
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)

    permissive_rules = replace(RuleConfig(), joker_can_finish=True)
    new_state, _events = apply_move(state, action, permissive_rules)
    assert new_state.hand_of("a") == (Card(Rank.JOKER, None, JokerColor.BLACK),)


def test_this_restriction_applies_even_without_declaring_niko_kadi():
    """
    The block is on the state itself (ending up with an unfinishable
    lone card), not just on the declaration flag — so it still fires
    even if the player didn't set declare_niko_kadi on this action.
    """

    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.SIX, Suit.HEARTS),
                Card(Rank.ACE, Suit.SPADES),
            ),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.SIX, Suit.HEARTS),),
        declare_niko_kadi=False,
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)
