"""
Multi-card plays: dropping two or more cards of the same rank in one
move.

The engine already validated the "same rank" shape rule before this
was wired up end-to-end — what was missing was that effect-bearing
cards (2/3 draw, Jack skip, King reverse) only ever applied their
effect once, using just the first card, regardless of how many were
actually played. These tests cover the fix: effects now apply once
per card.
"""

import pytest

from app.rules.actions import ActionType, PlayCardsAction
from app.rules.cards import Card, Rank, Suit
from app.rules.config import RuleConfig
from app.rules.engine import IllegalMove, apply_move
from app.rules.events import EventType
from app.rules.state import Phase

from tests.test_rules_engine import make_state


def test_multi_card_play_requires_same_rank():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.TWO, Suit.HEARTS),
                Card(Rank.THREE, Suit.HEARTS),
            ),
            "b": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(
            Card(Rank.TWO, Suit.HEARTS),
            Card(Rank.THREE, Suit.HEARTS),
        ),
    )

    with pytest.raises(IllegalMove):
        apply_move(state, action, rules)


def test_two_twos_stack_draw_pressure_by_four_not_two():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.TWO, Suit.HEARTS),
                Card(Rank.TWO, Suit.SPADES),
                # Filler so playing both 2s leaves 2 cards, not 0 or 1
                # — a bare win or a Niko Kadi requirement would mask
                # what this test is actually checking (draw stacking).
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
            Card(Rank.TWO, Suit.HEARTS),
            Card(Rank.TWO, Suit.SPADES),
        ),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.pending_draw_count == 4
    assert new_state.phase == Phase.AWAITING_DRAW_RESPONSE
    assert len(new_state.hand_of("a")) == 2

    draw_events = [e for e in events if e.type == EventType.DRAW_STACK_STARTED]
    assert len(draw_events) == 1
    assert draw_events[0].payload["pending_draw_count"] == 4


def test_stacking_two_more_twos_onto_existing_pressure():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": tuple(),
            "b": (
                Card(Rank.TWO, Suit.HEARTS),
                Card(Rank.TWO, Suit.CLUBS),
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
        },
        current_player_index=1,
        phase=Phase.AWAITING_DRAW_RESPONSE,
        pending_draw_count=2,
        discard_pile=(Card(Rank.TWO, Suit.SPADES),),
    )

    action = PlayCardsAction(
        player_id="b",
        type=ActionType.PLAY_CARDS,
        cards=(
            Card(Rank.TWO, Suit.HEARTS),
            Card(Rank.TWO, Suit.CLUBS),
        ),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.pending_draw_count == 6

    increase_events = [
        e for e in events if e.type == EventType.DRAW_STACK_INCREASED
    ]
    assert len(increase_events) == 1
    assert increase_events[0].payload["pending_draw_count"] == 6


def test_two_jacks_skip_two_players_ahead():
    rules = RuleConfig()

    state = make_state(
        player_count=3,
        hands={
            "a": (
                Card(Rank.JACK, Suit.HEARTS),
                Card(Rank.JACK, Suit.SPADES),
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
            "b": tuple(),
            "c": tuple(),
        },
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(
            Card(Rank.JACK, Suit.HEARTS),
            Card(Rank.JACK, Suit.SPADES),
        ),
    )

    new_state, events = apply_move(state, action, rules)

    # a -> (skip 2) -> c is the one left holding the response
    assert new_state.pending_skip_player_id == "c"
    assert new_state.current_player.id == "c"
    assert new_state.phase == Phase.AWAITING_SKIP_RESPONSE

    skip_events = [e for e in events if e.type == EventType.SKIP_STARTED]
    assert len(skip_events) == 1
    assert skip_events[0].payload["skip_count"] == 2
    assert skip_events[0].payload["target_player_id"] == "c"


def test_two_kings_cancel_out_direction():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.KING, Suit.HEARTS),
                Card(Rank.KING, Suit.SPADES),
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
            "b": tuple(),
        },
        direction=1,
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.KING, Suit.SPADES),
        ),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.direction == 1  # unchanged: two flips cancel out

    reverse_events = [e for e in events if e.type == EventType.DIRECTION_REVERSED]
    assert len(reverse_events) == 1
    assert reverse_events[0].payload["direction"] == 1


def test_three_kings_nets_a_single_reverse():
    rules = RuleConfig()

    state = make_state(
        player_count=3,
        hands={
            "a": (
                Card(Rank.KING, Suit.HEARTS),
                Card(Rank.KING, Suit.SPADES),
                Card(Rank.KING, Suit.CLUBS),
                Card(Rank.FOUR, Suit.CLUBS),
                Card(Rank.FIVE, Suit.CLUBS),
            ),
            "b": tuple(),
            "c": tuple(),
        },
        direction=1,
        discard_pile=(Card(Rank.SEVEN, Suit.HEARTS),),
    )

    action = PlayCardsAction(
        player_id="a",
        type=ActionType.PLAY_CARDS,
        cards=(
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.KING, Suit.SPADES),
            Card(Rank.KING, Suit.CLUBS),
        ),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.direction == -1


def test_two_question_cards_ask_only_once():
    rules = RuleConfig()

    state = make_state(
        hands={
            "a": (
                Card(Rank.EIGHT, Suit.HEARTS),
                Card(Rank.EIGHT, Suit.SPADES),
                Card(Rank.FOUR, Suit.HEARTS),
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
            Card(Rank.EIGHT, Suit.HEARTS),
            Card(Rank.EIGHT, Suit.SPADES),
        ),
    )

    new_state, events = apply_move(state, action, rules)

    assert new_state.phase == Phase.AWAITING_ANSWER
    assert new_state.current_player.id == "a"  # asker answers their own question

    question_events = [e for e in events if e.type == EventType.QUESTION_ASKED]
    assert len(question_events) == 1
    assert question_events[0].payload["card_count"] == 2
