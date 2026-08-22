"""
"Niko Kadi" is a promise to win on the very next turn. By default,
every card is playable at the player's whim — including as the lone
remaining card — so this restriction no longer fires under the
default RuleConfig(): a King, an Ace, a Joker, any of them can be left
as the last card in hand.

The underlying mechanism is still there for a stricter, opted-in
config, though (see the "_when_restricted" tests below) — a player
should never be allowed to play their way down to a single card that
that stricter config says can never finish the game. They'd just be
stuck holding it forever, unable to legally end their turn on it.
"""

import pytest
from dataclasses import replace

from app.rules.actions import ActionType, PlayCardsAction
from app.rules.cards import Card, JokerColor, Rank, Suit
from app.rules.config import RuleConfig
from app.rules.engine import IllegalMove, apply_move

from tests.test_rules_engine import make_state


def test_can_declare_niko_kadi_down_to_a_lone_ace_by_default():
    rules = RuleConfig()  # ace_can_finish is True by default

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

    new_state, _events = apply_move(state, action, rules)

    assert new_state.hand_of("a") == (Card(Rank.ACE, Suit.SPADES),)
    assert "a" in new_state.niko_kadi_declared_by


def test_cannot_declare_niko_kadi_down_to_a_lone_ace_when_restricted():
    rules = replace(RuleConfig(), ace_can_finish=False)

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

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)

    # Nothing should have moved out of the hand — the play never went through.


def test_can_declare_niko_kadi_down_to_a_power_card_by_default():
    """
    King is a power/effect card, but it's still in finishable_ranks
    by default now — so being left holding only a King is fine.
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

    new_state, _events = apply_move(state, action, rules)

    assert new_state.hand_of("a") == (Card(Rank.KING, Suit.SPADES),)
    assert "a" in new_state.niko_kadi_declared_by


def test_cannot_declare_niko_kadi_down_to_a_power_card_when_restricted():
    rules = replace(
        RuleConfig(),
        finishable_ranks=RuleConfig().finishable_ranks - {Rank.KING},
    )

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


def test_lone_joker_is_allowed_by_default_but_blocked_when_restricted():
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

    new_state, _events = apply_move(state, action, rules)
    assert new_state.hand_of("a") == (Card(Rank.JOKER, None, JokerColor.BLACK),)

    restrictive_rules = replace(RuleConfig(), joker_can_finish=False)
    with pytest.raises(IllegalMove):
        apply_move(state, action, restrictive_rules)


def test_the_restriction_applies_even_without_declaring_niko_kadi():
    """
    When a stricter config does block a lone card, the block is on
    the state itself (ending up with an unfinishable lone card), not
    just on the declaration flag — so it still fires even if the
    player didn't set declare_niko_kadi on this action.
    """

    rules = replace(RuleConfig(), ace_can_finish=False)

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
