"""
Real-time gameplay over WebSocket.

Responsibilities:
- Accept a connection for a player already seated in a room (joining a
  room still happens over REST — see ``app.api.routes``).
- Track that connection via the shared ConnectionManager.
- Translate incoming JSON messages into rules-engine PlayerActions.
- Broadcast a personalized game state to every connected player after
  each successful move.

No game rules live here — all legality checks happen in
``app.rules.engine``. This module is a thin translation layer between
JSON and the engine's action/event objects.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.game.dependencies import connection_manager, room_manager
from app.game.serializers import serialize_room_for_player
from app.rules.actions import (
    ActionType,
    DrawAction,
    PassAction,
    PlayCardsAction,
    PlayerAction,
    SayNikoKadiAction,
)
from app.rules.cards import Card, Rank, Suit
from app.rules.engine import IllegalMove
from app.rules.events import GameEvent


router = APIRouter(
    prefix="/api",
    tags=["websocket"],
)


@router.websocket("/ws/rooms/{room_id}")
async def room_websocket(
    websocket: WebSocket,
    room_id: str,
) -> None:

    player_id = websocket.query_params.get("player_id")

    if not player_id:
        await websocket.close(code=4000, reason="player_id query param is required")
        return

    try:
        room = room_manager.get_room(room_id)
    except KeyError:
        await websocket.close(code=4004, reason="Room not found")
        return

    if not any(player.id == player_id for player in room.players):
        await websocket.close(
            code=4003,
            reason="Player has not joined this room. Join over REST first.",
        )
        return

    await connection_manager.connect(room_id, player_id, websocket)

    await _send_state(room_id, player_id, events=[])

    await connection_manager.broadcast_to_room(
        room_id,
        {"type": "player_connected", "player_id": player_id},
        exclude_player_id=player_id,
    )

    try:
        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                raise
            except Exception:
                await connection_manager.send_to_player(
                    room_id,
                    player_id,
                    {"type": "error", "detail": "Malformed message. Expected JSON."},
                )
                continue

            await _handle_message(room_id, player_id, message)

    except WebSocketDisconnect:
        connection_manager.disconnect(room_id, player_id)

        await connection_manager.broadcast_to_room(
            room_id,
            {"type": "player_disconnected", "player_id": player_id},
        )


# ---------------------------------------------------------------------
# Message handling
# ---------------------------------------------------------------------


async def _handle_message(
    room_id: str,
    player_id: str,
    message: dict[str, Any],
) -> None:

    try:
        room = room_manager.get_room(room_id)
    except KeyError:
        await connection_manager.send_to_player(
            room_id,
            player_id,
            {"type": "error", "detail": "Room not found"},
        )
        return

    if room.state is None:
        await connection_manager.send_to_player(
            room_id,
            player_id,
            {"type": "error", "detail": "Game has not started"},
        )
        return

    try:
        action = _parse_action(player_id, message)
    except (ValueError, KeyError, TypeError) as exc:
        await connection_manager.send_to_player(
            room_id,
            player_id,
            {"type": "error", "detail": f"Invalid message: {exc}"},
        )
        return

    try:
        events = room.apply(action)
    except IllegalMove as exc:
        await connection_manager.send_to_player(
            room_id,
            player_id,
            {"type": "error", "detail": str(exc)},
        )
        return

    await _broadcast_state(room_id, events)


def _parse_action(
    player_id: str,
    message: dict[str, Any],
) -> PlayerAction:
    """
    Translate a raw JSON message into a PlayerAction.

    Expected shapes:

    {"type": "play_cards", "cards": [{"rank": "5", "suit": "hearts"}],
     "declared_suit": null, "declare_niko_kadi": false}
    {"type": "draw"}
    {"type": "pass"}
    {"type": "say_niko_kadi"}
    """

    action_type = message.get("type")

    if action_type == "play_cards":
        cards_payload = message.get("cards") or []

        if not cards_payload:
            raise ValueError("At least one card is required.")

        cards = tuple(
            Card(
                rank=Rank(card["rank"]),
                suit=(
                    Suit(card["suit"])
                    if card.get("suit") is not None
                    else None
                ),
            )
            for card in cards_payload
        )

        declared_suit = message.get("declared_suit")

        return PlayCardsAction(
            player_id=player_id,
            type=ActionType.PLAY_CARDS,
            cards=cards,
            declared_suit=(
                Suit(declared_suit) if declared_suit is not None else None
            ),
            declare_niko_kadi=bool(message.get("declare_niko_kadi", False)),
        )

    if action_type == "draw":
        return DrawAction(
            player_id=player_id,
            type=ActionType.DRAW,
        )

    if action_type == "pass":
        return PassAction(
            player_id=player_id,
            type=ActionType.PASS,
        )

    if action_type == "say_niko_kadi":
        return SayNikoKadiAction(
            player_id=player_id,
            type=ActionType.SAY_NIKO_KADI,
        )

    raise ValueError(f"Unknown action type: {action_type!r}")


# ---------------------------------------------------------------------
# Broadcasting
# ---------------------------------------------------------------------


async def _send_state(
    room_id: str,
    player_id: str,
    events: list[GameEvent],
) -> None:

    room = room_manager.get_room(room_id)

    await connection_manager.send_to_player(
        room_id,
        player_id,
        {
            "type": "state",
            "room": serialize_room_for_player(room, player_id),
            "events": _serialize_events(events),
        },
    )


async def _broadcast_state(
    room_id: str,
    events: list[GameEvent],
) -> None:

    room = room_manager.get_room(room_id)
    serialized_events = _serialize_events(events)

    connected_player_ids = list(
        connection_manager.active_connections.get(room_id, {}).keys()
    )

    for connected_player_id in connected_player_ids:
        await connection_manager.send_to_player(
            room_id,
            connected_player_id,
            {
                "type": "state",
                "room": serialize_room_for_player(room, connected_player_id),
                "events": serialized_events,
            },
        )


def _serialize_events(events: list[GameEvent]) -> list[dict]:
    return [
        {"type": event.type.value, "payload": event.payload}
        for event in events
    ]
