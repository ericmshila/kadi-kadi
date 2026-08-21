"""
Joker as a punishment card.

A Joker is no longer a wild "declare the next suit" card. It behaves
like a 2/3: playing one forces the next player to draw (5, by
default) or counter. It stacks with 2s/3s and other Jokers the same
way they stack with each other.

The one Joker-specific rule: countering an *active* Joker (i.e. the
top of the discard pile is currently a Joker) with a plain 2 or 3
requires that 2/3 to match the Joker's colour. Another Joker, or an
Ace, always counters regardless of colour.
"""

import pytest

from app.rules.actions import ActionType, PlayCardsAction
from app.rules.cards import Card, JokerColor, Rank, Suit
from app.rules.config import RuleConfig
from app.rules.engine import IllegalMove, apply_move
from app.rules.events import EventType
from app.rules.state import Phase

from tests.test_rules_engine import make_state


def test_joker_forces_a_draw_of_five():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.JOKER, None, JokerColor.BLACK),
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.JOKER, None, JokerColor.BLACK),),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.pending_draw_count == 5
    assert new_state.phase == Phase.AWAITING_DRAW_RESPONSE
    assert new_state.current_player.id == "b"

    draw_events = [e for e in events if e.type == EventType.DRAW_STACK_STARTED]
    assert len(draw_events) == 1
    assert draw_events[0].payload["pending_draw_count"] == 5


def test_joker_is_always_playable_without_declaring_a_suit():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.JOKER, None, JokerColor.RED),
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
            "b": tuple(),
        },
        # Top card shares neither rank nor suit with the Joker — a
        # normal card couldn't be played here, but a Joker always can.
        discard_pile=(Card(Rank.NINE, Suit.DIAMONDS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.JOKER, None, JokerColor.RED),),
        declared_suit=None,
    )

    new_state, _events = apply_move(state, action, rules)

    assert new_state.phase == Phase.AWAITING_DRAW_RESPONSE
    assert new_state.active_suit is None


def test_two_jokers_together_stack_to_ten():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.JOKER, None, JokerColor.BLACK),
                Card(Rank.JOKER, None, JokerColor.RED),
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(
            Card(Rank.JOKER, None, JokerColor.BLACK),
            Card(Rank.JOKER, None, JokerColor.RED),
        ),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.pending_draw_count == 10

    draw_events = [e for e in events if e.type == EventType.DRAW_STACK_STARTED]
    assert draw_events[0].payload["pending_draw_count"] == 10


def test_matching_color_two_counters_and_stacks_on_top_of_joker():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": tuple(),
            "b": (
                Card(Rank.TWO, Suit.SPADES),  # black, matches the black Joker
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
        },
        current_player_index=1,
        phase=Phase.AWAITING_DRAW_RESPONSE,
        pending_draw_count=5,
        discard_pile=(Card(Rank.JOKER, None, JokerColor.BLACK),),
    )

    action = PlayCardsAction(
        player_id="b",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.TWO, Suit.SPADES),),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.pending_draw_count == 7  # stacks: 5 + 2, doesn't cancel
    assert new_state.phase == Phase.AWAITING_DRAW_RESPONSE

    increase_events = [
        e for e in events if e.type == EventType.DRAW_STACK_INCREASED
    ]
    assert increase_events[0].payload["pending_draw_count"] == 7


def test_wrong_color_two_cannot_counter_joker():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": tuple(),
            "b": (
                Card(Rank.TWO, Suit.HEARTS),  # red, does NOT match black Joker
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
        },
        current_player_index=1,
        phase=Phase.AWAITING_DRAW_RESPONSE,
        pending_draw_count=5,
        discard_pile=(Card(Rank.JOKER, None, JokerColor.BLACK),),
    )

    action = PlayCardsAction(
        player_id="b",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.TWO, Suit.HEARTS),),
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)


def test_any_joker_counters_a_joker_regardless_of_color():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": tuple(),
            "b": (
                Card(Rank.JOKER, None, JokerColor.RED),
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
        },
        current_player_index=1,
        phase=Phase.AWAITING_DRAW_RESPONSE,
        pending_draw_count=5,
        discard_pile=(Card(Rank.JOKER, None, JokerColor.BLACK),),
    )

    action = PlayCardsAction(
        player_id="b",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.JOKER, None, JokerColor.RED),),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.pending_draw_count == 10  # 5 + 5, stacks


def test_ace_still_clears_joker_punishment_outright():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": tuple(),
            "b": (
                Card(Rank.ACE, Suit.HEARTS),
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
        },
        current_player_index=1,
        phase=Phase.AWAITING_DRAW_RESPONSE,
        pending_draw_count=5,
        discard_pile=(Card(Rank.JOKER, None, JokerColor.BLACK),),
    )

    action = PlayCardsAction(
        player_id="b",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.ACE, Suit.HEARTS),),
        declared_suit=Suit.HEARTS,
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.pending_draw_count == 0
    assert new_state.phase == Phase.AWAITING_MOVE

    cleared = [e for e in events if e.type == EventType.PUNISHMENT_CLEARED]
    assert len(cleared) == 1


def test_wrong_color_still_valid_once_a_plain_two_is_on_top():
    """
    The colour restriction only applies while a Joker is directly on
    top of the discard pile. Once someone stacks a plain 2/3 on top
    of it, normal 2/3-vs-2/3 stacking rules resume (any 2 or 3
    counters, no colour check) — matching how 2s and 3s already
    counter each other regardless of suit.
    """

    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.THREE, Suit.DIAMONDS),  # red 3, "wrong" colour
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
            "b": tuple(),
        },
        phase=Phase.AWAITING_DRAW_RESPONSE,
        pending_draw_count=7,
        # A black-Joker punishment already had a black 2 stacked on
        # top of it, so the discard top is now that plain 2, not the
        # Joker itself.
        discard_pile=(
            Card(Rank.JOKER, None, JokerColor.BLACK),
            Card(Rank.TWO, Suit.SPADES),
        ),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(Card(Rank.THREE, Suit.DIAMONDS),),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.pending_draw_count == 10  # 7 + 3, no colour check applied
