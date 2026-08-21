"""
Kenyan Poker / Kadi rules engine.

Pure game logic only.

No FastAPI.
No WebSockets.
No database.
No UI assumptions.

The engine answers:

- Is this action legal?
- What happens next?
- Who plays next?
- Has someone won?
"""

from __future__ import annotations

import random
from typing import Optional

from .actions import (
    ActionType,
    DrawAction,
    PassAction,
    PlayCardsAction,
    PlayerAction,
    SayNikoKadiAction,
)
from .cards import Card, Rank, Suit, shuffled_deck
from .config import RuleConfig
from .events import EventType, GameEvent
from .state import GameState, Phase, Player


class IllegalMove(Exception):
    """
    Raised when a player attempts an illegal move.
    """


# ---------------------------------------------------------------------
# Game setup
# ---------------------------------------------------------------------


def create_initial_state(
    players: list[Player],
    rules: Optional[RuleConfig] = None,
    seed: Optional[int] = None,
) -> tuple[GameState, list[GameEvent]]:
    """
    Create a new game state.

    The first discard is forced to be a plain card to avoid opening
    the game with unresolved draw/question/skip/reverse/wild effects.
    """

    rules = rules or RuleConfig()

    if len(players) < 2:
        raise ValueError("At least two players are required.")

    deck = shuffled_deck(seed=seed)
    draw_pile = list(deck)

    hands: dict[str, tuple[Card, ...]] = {}

    for player in players:
        hand: list[Card] = []

        for _ in range(rules.initial_hand_size):
            hand.append(draw_pile.pop())

        hands[player.id] = tuple(hand)

    first_discard = draw_pile.pop()

    while _is_opening_special_card(first_discard, rules):
        draw_pile.insert(0, first_discard)
        first_discard = draw_pile.pop()

    state = GameState(
        players=tuple(players),
        hands=hands,
        draw_pile=tuple(draw_pile),
        discard_pile=(first_discard,),
        current_player_index=0,
        direction=1,
        phase=Phase.AWAITING_MOVE,
    )

    events = [
        GameEvent(
            type=EventType.GAME_STARTED,
            payload={
                "players": [player.id for player in players],
                "top_card": first_discard.label(),
                "current_player_id": state.current_player.id,
            },
        )
    ]

    return state, events


# ---------------------------------------------------------------------
# Public transition function
# ---------------------------------------------------------------------


def apply_move(
    state: GameState,
    action: PlayerAction,
    rules: RuleConfig,
) -> tuple[GameState, list[GameEvent]]:
    """
    Apply one player action to the current state.

    Returns:
        new_state, events
    """

    if state.phase == Phase.FINISHED or state.winner_id is not None:
        raise IllegalMove("Game is already finished.")

    if isinstance(action, SayNikoKadiAction):
        return _apply_say_niko_kadi(state, action)

    if action.player_id != state.current_player.id:
        raise IllegalMove("It is not this player's turn.")

    if isinstance(action, PlayCardsAction):
        return _apply_play_cards(state, action, rules)

    if isinstance(action, DrawAction):
        return _apply_draw(state, action, rules)

    if isinstance(action, PassAction):
        return _apply_pass(state, action, rules)

    raise IllegalMove(f"Unsupported action type: {action.type}")


# ---------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------


def _apply_say_niko_kadi(
    state: GameState,
    action: SayNikoKadiAction,
) -> tuple[GameState, list[GameEvent]]:

    if action.player_id not in state.hands:
        raise IllegalMove("Unknown player.")

    if len(state.hand_of(action.player_id)) != 1:
        raise IllegalMove("Niko Kadi can only be declared when holding one card.")

    declared = set(state.niko_kadi_declared_by)
    declared.add(action.player_id)

    new_state = state.replace(
        niko_kadi_declared_by=frozenset(declared)
    )

    return new_state, [
        GameEvent(
            type=EventType.NIKO_KADI_DECLARED,
            payload={"player_id": action.player_id},
        )
    ]


def _apply_play_cards(
    state: GameState,
    action: PlayCardsAction,
    rules: RuleConfig,
) -> tuple[GameState, list[GameEvent]]:

    _validate_play_action_shape(state, action)

    card = action.cards[0]

    if state.phase == Phase.AWAITING_MOVE:
        _validate_normal_turn_play(state, action, rules)

    elif state.phase == Phase.AWAITING_ANSWER:
        _validate_question_response(state, action, rules)

    elif state.phase == Phase.AWAITING_DRAW_RESPONSE:
        _validate_draw_response(state, action, rules)

    elif state.phase == Phase.AWAITING_SKIP_RESPONSE:
        _validate_skip_response(state, action, rules)

    else:
        raise IllegalMove(f"Unsupported phase: {state.phase}")

    return _commit_play_cards(state, action, rules)


def _apply_draw(
    state: GameState,
    action: DrawAction,
    rules: RuleConfig,
) -> tuple[GameState, list[GameEvent]]:

    if state.phase == Phase.AWAITING_SKIP_RESPONSE:
        raise IllegalMove("Player must pass or counter the skip.")

    is_punishment_draw = state.phase == Phase.AWAITING_DRAW_RESPONSE

    if state.phase == Phase.AWAITING_DRAW_RESPONSE:
        draw_count = state.pending_draw_count

    elif state.phase == Phase.AWAITING_ANSWER:
        draw_count = 1

    elif state.phase == Phase.AWAITING_MOVE:
        draw_count = 1

    else:
        raise IllegalMove(f"Cannot draw during phase: {state.phase}")

    new_state, events = _draw_cards_for_player(
        state=state,
        player_id=action.player_id,
        count=draw_count,
    )

    new_state = new_state.replace(
        phase=Phase.AWAITING_MOVE,
        pending_draw_count=0,
        pending_question_player_id=None,
        pending_skip_player_id=None,
    )

    if (
        is_punishment_draw
        and rules.forfeit_hand_size is not None
        and len(new_state.hand_of(action.player_id)) >= rules.forfeit_hand_size
    ):
        new_state, forfeit_events = _forfeit_player(
            state=new_state,
            player_id=action.player_id,
        )
        events.extend(forfeit_events)

        if new_state.phase == Phase.FINISHED:
            return new_state, events

    new_state, turn_events = _advance_turn(new_state, steps=1)
    events.extend(turn_events)

    return new_state, events


def _apply_pass(
    state: GameState,
    action: PassAction,
    rules: RuleConfig,
) -> tuple[GameState, list[GameEvent]]:

    if state.phase != Phase.AWAITING_SKIP_RESPONSE:
        raise IllegalMove("Pass is only allowed when responding to a skip.")

    skipped_player_id = state.current_player.id

    events = [
        GameEvent(
            type=EventType.PLAYER_SKIPPED,
            payload={"player_id": skipped_player_id},
        )
    ]

    new_state = state.replace(
        phase=Phase.AWAITING_MOVE,
        pending_skip_player_id=None,
    )

    new_state, turn_events = _advance_turn(new_state, steps=1)
    events.extend(turn_events)

    return new_state, events


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def _validate_play_action_shape(
    state: GameState,
    action: PlayCardsAction,
) -> None:

    if not action.cards:
        raise IllegalMove("At least one card must be played.")

    hand = list(state.hand_of(action.player_id))

    for card in action.cards:
        if card not in hand:
            raise IllegalMove(f"Player does not have card: {card.label()}")
        hand.remove(card)

    if len(action.cards) > 1:
        first_rank = action.cards[0].rank

        for card in action.cards:
            if card.rank != first_rank:
                raise IllegalMove("Multi-card play requires cards of the same rank.")


def _validate_normal_turn_play(
    state: GameState,
    action: PlayCardsAction,
    rules: RuleConfig,
) -> None:

    card = action.cards[0]

    if _is_ace(card):
        _validate_declared_suit_for_ace(action, rules)
        return

    if _is_joker(card):
        _validate_declared_suit_for_joker(action, rules)
        return

    if not _matches_required_suit_or_rank(state, card):
        raise IllegalMove(
            f"{card.label()} cannot be played on {state.top_card.label()}."
        )


def _validate_question_response(
    state: GameState,
    action: PlayCardsAction,
    rules: RuleConfig,
) -> None:

    card = action.cards[0]

    if _is_ace(card) and rules.ace_can_answer_question:
        _validate_declared_suit_for_ace(action, rules)
        return

    if _is_joker(card) and rules.joker_can_answer_question:
        _validate_declared_suit_for_joker(action, rules)
        return

    if card.rank not in rules.question_answer_ranks:
        raise IllegalMove("This card cannot answer a question.")

    required_suit = _required_suit(state)

    if card.suit != required_suit:
        raise IllegalMove("Question answer must follow the required suit.")


def _validate_draw_response(
    state: GameState,
    action: PlayCardsAction,
    rules: RuleConfig,
) -> None:

    card = action.cards[0]

    if _is_ace(card) and rules.ace_counters_punishments:
        _validate_declared_suit_for_ace(action, rules)
        return

    if not rules.draw_stacking_enabled:
        raise IllegalMove("Draw stacking is disabled. Player must draw.")

    if card.rank not in rules.draw_ranks:
        raise IllegalMove("Only another draw card or Ace can respond to draw pressure.")


def _validate_skip_response(
    state: GameState,
    action: PlayCardsAction,
    rules: RuleConfig,
) -> None:

    if not rules.skip_can_be_countered:
        raise IllegalMove("Skip cannot be countered under the current rules.")

    card = action.cards[0]

    if _is_ace(card) and rules.ace_counters_punishments:
        _validate_declared_suit_for_ace(action, rules)
        return

    if card.rank not in rules.skip_ranks:
        raise IllegalMove("Skip can only be countered by Jack or Ace.")


def _validate_declared_suit_for_ace(
    action: PlayCardsAction,
    rules: RuleConfig,
) -> None:

    if rules.ace_requires_declared_suit and action.declared_suit is None:
        raise IllegalMove("Playing Ace requires declaring the next suit.")


def _validate_declared_suit_for_joker(
    action: PlayCardsAction,
    rules: RuleConfig,
) -> None:

    if rules.joker_requires_declared_suit and action.declared_suit is None:
        raise IllegalMove("Playing Joker requires declaring the next suit.")


# ---------------------------------------------------------------------
# Commit play
# ---------------------------------------------------------------------


def _commit_play_cards(
    state: GameState,
    action: PlayCardsAction,
    rules: RuleConfig,
) -> tuple[GameState, list[GameEvent]]:

    player_id = action.player_id
    cards = action.cards
    first_card = cards[0]
    last_card = cards[-1]

    events: list[GameEvent] = []

    new_hand = _remove_cards_from_hand(
        hand=state.hand_of(player_id),
        cards=cards,
    )

    _validate_finish_rules(
        player_id=player_id,
        remaining_cards=len(new_hand),
        last_card=last_card,
        rules=rules,
    )

    new_hands = dict(state.hands)
    new_hands[player_id] = tuple(new_hand)

    new_discard_pile = tuple(list(state.discard_pile) + list(cards))

    declared = set(state.niko_kadi_declared_by)

    if action.declare_niko_kadi:
        declared.add(player_id)
        events.append(
            GameEvent(
                type=EventType.NIKO_KADI_DECLARED,
                payload={"player_id": player_id},
            )
        )

    _validate_niko_kadi(
        player_id=player_id,
        remaining_cards=len(new_hand),
        declared=declared,
        rules=rules,
    )

    for card in cards:
        events.append(
            GameEvent(
                type=EventType.CARD_PLAYED,
                payload={
                    "player_id": player_id,
                    "card": card.label(),
                },
            )
        )

    new_state = state.replace(
        hands=new_hands,
        discard_pile=new_discard_pile,
        niko_kadi_declared_by=frozenset(declared),
    )

    if len(new_hand) == 0:
        new_state = new_state.replace(
            phase=Phase.FINISHED,
            winner_id=player_id,
        )

        events.extend(
            [
                GameEvent(
                    type=EventType.PLAYER_WON,
                    payload={"player_id": player_id},
                ),
                GameEvent(
                    type=EventType.GAME_FINISHED,
                    payload={"winner_id": player_id},
                ),
            ]
        )

        return new_state, events

    return _apply_card_effects(
        state=new_state,
        played_card=first_card,
        action=action,
        rules=rules,
        events=events,
    )


# ---------------------------------------------------------------------
# Card effects
# ---------------------------------------------------------------------


def _apply_card_effects(
    state: GameState,
    played_card: Card,
    action: PlayCardsAction,
    rules: RuleConfig,
    events: list[GameEvent],
) -> tuple[GameState, list[GameEvent]]:

    player_id = action.player_id

    if _is_ace(played_card):
        return _apply_ace_effect(state, action, events)

    if _is_joker(played_card):
        return _apply_joker_effect(state, action, events)

    if played_card.rank in rules.draw_ranks:
        return _apply_draw_card_effect(state, played_card, rules, events)

    if played_card.rank in rules.question_ranks:
        return _apply_question_effect(state, played_card, events)

    if played_card.rank in rules.skip_ranks:
        return _apply_skip_effect(state, played_card, events)

    if played_card.rank in rules.reverse_ranks:
        return _apply_reverse_effect(state, played_card, events)

    if state.phase == Phase.AWAITING_ANSWER:
        events.append(
            GameEvent(
                type=EventType.QUESTION_ANSWERED,
                payload={"player_id": player_id},
            )
        )

    new_state = state.replace(
        phase=Phase.AWAITING_MOVE,
        pending_draw_count=0,
        pending_question_player_id=None,
        pending_skip_player_id=None,
        active_suit=None,
    )

    new_state, turn_events = _advance_turn(new_state, steps=1)
    events.extend(turn_events)

    return new_state, events


def _apply_ace_effect(
    state: GameState,
    action: PlayCardsAction,
    events: list[GameEvent],
) -> tuple[GameState, list[GameEvent]]:

    player_id = action.player_id

    if state.phase in {
        Phase.AWAITING_ANSWER,
        Phase.AWAITING_DRAW_RESPONSE,
        Phase.AWAITING_SKIP_RESPONSE,
    }:
        events.append(
            GameEvent(
                type=EventType.ACE_COUNTER_PLAYED,
                payload={"player_id": player_id},
            )
        )

        events.append(
            GameEvent(
                type=EventType.PUNISHMENT_CLEARED,
                payload={"player_id": player_id},
            )
        )

    events.append(
        GameEvent(
            type=EventType.SUIT_DECLARED,
            payload={
                "player_id": player_id,
                "suit": action.declared_suit.value if action.declared_suit else None,
            },
        )
    )

    new_state = state.replace(
        phase=Phase.AWAITING_MOVE,
        pending_draw_count=0,
        pending_question_player_id=None,
        pending_skip_player_id=None,
        active_suit=action.declared_suit,
    )

    new_state, turn_events = _advance_turn(new_state, steps=1)
    events.extend(turn_events)

    return new_state, events


def _apply_joker_effect(
    state: GameState,
    action: PlayCardsAction,
    events: list[GameEvent],
) -> tuple[GameState, list[GameEvent]]:

    player_id = action.player_id

    events.append(
        GameEvent(
            type=EventType.SUIT_DECLARED,
            payload={
                "player_id": player_id,
                "suit": action.declared_suit.value if action.declared_suit else None,
            },
        )
    )

    new_state = state.replace(
        phase=Phase.AWAITING_MOVE,
        active_suit=action.declared_suit,
    )

    new_state, turn_events = _advance_turn(new_state, steps=1)
    events.extend(turn_events)

    return new_state, events


def _apply_draw_card_effect(
    state: GameState,
    played_card: Card,
    rules: RuleConfig,
    events: list[GameEvent],
) -> tuple[GameState, list[GameEvent]]:

    added = rules.draw_ranks[played_card.rank]
    pending_total = state.pending_draw_count + added

    new_state = state.replace(
        phase=Phase.AWAITING_DRAW_RESPONSE,
        pending_draw_count=pending_total,
        active_suit=None,
    )

    event_type = (
        EventType.DRAW_STACK_INCREASED
        if state.pending_draw_count > 0
        else EventType.DRAW_STACK_STARTED
    )

    events.append(
        GameEvent(
            type=event_type,
            payload={"pending_draw_count": pending_total},
        )
    )

    new_state, turn_events = _advance_turn(new_state, steps=1)
    events.extend(turn_events)

    return new_state, events


def _apply_question_effect(
    state: GameState,
    played_card: Card,
    events: list[GameEvent],
) -> tuple[GameState, list[GameEvent]]:
    """
    The player who plays a question card (8 or Q) must immediately
    answer it themselves — the turn does NOT pass to the next player.

    They stay the current player and must follow up with a valid
    answer card (or draw, if they have none) before their turn ends.
    """

    asking_player = state.current_player

    new_state = state.replace(
        phase=Phase.AWAITING_ANSWER,
        pending_question_player_id=asking_player.id,
        active_suit=None,
    )

    events.append(
        GameEvent(
            type=EventType.QUESTION_ASKED,
            payload={
                "question_card": played_card.label(),
                "target_player_id": asking_player.id,
            },
        )
    )

    return new_state, events


def _apply_skip_effect(
    state: GameState,
    played_card: Card,
    events: list[GameEvent],
) -> tuple[GameState, list[GameEvent]]:

    next_index = _calculate_next_index(state, steps=1)
    next_player = state.players[next_index]

    new_state = state.replace(
        phase=Phase.AWAITING_SKIP_RESPONSE,
        pending_skip_player_id=next_player.id,
        active_suit=None,
    )

    events.append(
        GameEvent(
            type=EventType.SKIP_STARTED,
            payload={
                "skip_card": played_card.label(),
                "target_player_id": next_player.id,
            },
        )
    )

    new_state, turn_events = _advance_turn(new_state, steps=1)
    events.extend(turn_events)

    return new_state, events


def _apply_reverse_effect(
    state: GameState,
    played_card: Card,
    events: list[GameEvent],
) -> tuple[GameState, list[GameEvent]]:

    new_direction = state.direction * -1

    new_state = state.replace(
        direction=new_direction,
        phase=Phase.AWAITING_MOVE,
        active_suit=None,
    )

    events.append(
        GameEvent(
            type=EventType.DIRECTION_REVERSED,
            payload={"direction": new_direction},
        )
    )

    new_state, turn_events = _advance_turn(new_state, steps=1)
    events.extend(turn_events)

    return new_state, events


# ---------------------------------------------------------------------
# Draw helpers
# ---------------------------------------------------------------------


def _draw_cards_for_player(
    state: GameState,
    player_id: str,
    count: int,
) -> tuple[GameState, list[GameEvent]]:

    if count <= 0:
        return state, []

    draw_pile = list(state.draw_pile)
    discard_pile = list(state.discard_pile)
    drawn: list[Card] = []
    events: list[GameEvent] = []

    for _ in range(count):
        if not draw_pile:
            draw_pile, discard_pile = _reshuffle_discard_into_draw_pile(
                draw_pile=draw_pile,
                discard_pile=discard_pile,
            )

        if not draw_pile:
            break

        drawn.append(draw_pile.pop())

    hand = list(state.hand_of(player_id))
    hand.extend(drawn)

    new_hands = dict(state.hands)
    new_hands[player_id] = tuple(hand)

    new_state = state.replace(
        hands=new_hands,
        draw_pile=tuple(draw_pile),
        discard_pile=tuple(discard_pile),
    )

    events.append(
        GameEvent(
            type=EventType.CARDS_DRAWN,
            payload={
                "player_id": player_id,
                "count": len(drawn),
            },
        )
    )

    if state.pending_draw_count > 0:
        events.append(
            GameEvent(
                type=EventType.DRAW_STACK_CLEARED,
                payload={"player_id": player_id},
            )
        )

    return new_state, events


def _reshuffle_discard_into_draw_pile(
    draw_pile: list[Card],
    discard_pile: list[Card],
) -> tuple[list[Card], list[Card]]:

    if len(discard_pile) <= 1:
        return draw_pile, discard_pile

    top_card = discard_pile[-1]
    recyclable = discard_pile[:-1]

    random.shuffle(recyclable)

    return recyclable, [top_card]


# ---------------------------------------------------------------------
# Forfeit helpers
# ---------------------------------------------------------------------


def _forfeit_player(
    state: GameState,
    player_id: str,
) -> tuple[GameState, list[GameEvent]]:
    """
    Eliminate a player who was punished up to the forfeit hand size
    with no way to avoid it.

    Their hand is shuffled back into the draw pile so those cards
    stay in circulation for the remaining players. If only one player
    is left standing after this, the game ends and they win.
    """

    hand_size = len(state.hand_of(player_id))

    returned_cards = list(state.draw_pile) + list(state.hand_of(player_id))
    random.shuffle(returned_cards)

    new_hands = dict(state.hands)
    new_hands[player_id] = tuple()

    eliminated = set(state.eliminated_player_ids)
    eliminated.add(player_id)

    new_state = state.replace(
        hands=new_hands,
        draw_pile=tuple(returned_cards),
        eliminated_player_ids=frozenset(eliminated),
    )

    events = [
        GameEvent(
            type=EventType.PLAYER_ELIMINATED,
            payload={"player_id": player_id, "hand_size": hand_size},
        )
    ]

    if new_state.active_player_count == 1:
        winner_id = next(
            player.id
            for player in new_state.players
            if player.id not in new_state.eliminated_player_ids
        )

        new_state = new_state.replace(
            phase=Phase.FINISHED,
            winner_id=winner_id,
        )

        events.extend(
            [
                GameEvent(
                    type=EventType.PLAYER_WON,
                    payload={"player_id": winner_id},
                ),
                GameEvent(
                    type=EventType.GAME_FINISHED,
                    payload={"winner_id": winner_id},
                ),
            ]
        )

    return new_state, events


# ---------------------------------------------------------------------
# Turn helpers
# ---------------------------------------------------------------------


def _advance_turn(
    state: GameState,
    steps: int,
) -> tuple[GameState, list[GameEvent]]:

    next_index = _calculate_next_index(state, steps=steps)

    new_state = state.replace(current_player_index=next_index)

    return new_state, [
        GameEvent(
            type=EventType.TURN_ADVANCED,
            payload={"current_player_id": new_state.current_player.id},
        )
    ]


def _calculate_next_index(
    state: GameState,
    steps: int,
) -> int:
    """
    Find the seat `steps` hops away in the current direction,
    skipping over eliminated players' seats.
    """

    if state.active_player_count <= 1:
        return state.current_player_index

    index = state.current_player_index
    hops_remaining = steps

    while hops_remaining > 0:
        index = (index + state.direction) % state.player_count

        if state.players[index].id not in state.eliminated_player_ids:
            hops_remaining -= 1

    return index


# ---------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------


def _matches_required_suit_or_rank(
    state: GameState,
    card: Card,
) -> bool:

    required_suit = _required_suit(state)

    if card.suit == required_suit:
        return True

    if card.rank == state.top_card.rank:
        return True

    return False


def _required_suit(state: GameState) -> Optional[Suit]:
    return state.active_suit or state.top_card.suit


def _is_ace(card: Card) -> bool:
    return card.rank == Rank.ACE


def _is_joker(card: Card) -> bool:
    return card.rank == Rank.JOKER


def _is_opening_special_card(
    card: Card,
    rules: RuleConfig,
) -> bool:

    if _is_ace(card) or _is_joker(card):
        return True

    if card.rank in rules.draw_ranks:
        return True

    if card.rank in rules.question_ranks:
        return True

    if card.rank in rules.skip_ranks:
        return True

    if card.rank in rules.reverse_ranks:
        return True

    return False


def _remove_cards_from_hand(
    hand: tuple[Card, ...],
    cards: tuple[Card, ...],
) -> list[Card]:
    new_hand = list(hand)

    for card in cards:
        new_hand.remove(card)

    return new_hand


def _validate_finish_rules(
    player_id: str,
    remaining_cards: int,
    last_card: Card,
    rules: RuleConfig,
) -> None:

    if remaining_cards != 0:
        return

    if _is_ace(last_card):
        if rules.ace_can_finish:
            return
        raise IllegalMove(
            f"Player {player_id} cannot finish on {last_card.label()}."
        )

    if _is_joker(last_card):
        if rules.joker_can_finish:
            return
        raise IllegalMove(
            f"Player {player_id} cannot finish on {last_card.label()}."
        )

    if last_card.rank not in rules.finishable_ranks:
        raise IllegalMove(
            f"Player {player_id} cannot finish on {last_card.label()}."
        )


def _validate_niko_kadi(
    player_id: str,
    remaining_cards: int,
    declared: set[str],
    rules: RuleConfig,
) -> None:

    if not rules.must_declare_niko_kadi:
        return

    if remaining_cards != 1:
        return

    if player_id in declared:
        return

    if rules.strict_niko_kadi:
        raise IllegalMove(
            'Player must declare "Niko Kadi" when going down to one card.'
        )