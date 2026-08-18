"""
WebSocket endpoint tests.

Room creation / joining / starting still happens over REST; the
WebSocket is exercised for connection handshakes and live gameplay.
"""

import pytest
from fastapi.testclient import TestClient

from app.game.dependencies import connection_manager, room_manager
from app.main import app


@pytest.fixture(autouse=True)
def _reset_shared_state():
    """
    room_manager / connection_manager are process-wide singletons
    (see app.game.dependencies), so tests must not leak state between
    each other.
    """
    room_manager.clear()
    connection_manager.active_connections.clear()
    yield
    room_manager.clear()
    connection_manager.active_connections.clear()


def _create_and_start_room(client: TestClient, player_ids=("p1", "p2")):
    room_id = client.post("/api/rooms").json()["room_id"]

    for player_id in player_ids:
        client.post(
            f"/api/rooms/{room_id}/join",
            json={"player_id": player_id, "player_name": player_id},
        )

    client.post(f"/api/rooms/{room_id}/start")

    return room_id


def test_connect_without_player_id_is_rejected():
    client = TestClient(app)
    room_id = _create_and_start_room(client)

    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/ws/rooms/{room_id}"):
            pass


def test_connect_to_unknown_room_is_rejected():
    client = TestClient(app)

    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws/rooms/does-not-exist?player_id=p1"):
            pass


def test_connect_as_non_member_is_rejected():
    client = TestClient(app)
    room_id = _create_and_start_room(client)

    with pytest.raises(Exception):
        with client.websocket_connect(
            f"/api/ws/rooms/{room_id}?player_id=stranger"
        ):
            pass


def test_connect_receives_initial_personalized_state():
    client = TestClient(app)
    room_id = _create_and_start_room(client)

    with client.websocket_connect(f"/api/ws/rooms/{room_id}?player_id=p1") as ws:
        message = ws.receive_json()

        assert message["type"] == "state"
        assert message["room"]["room_id"] == room_id
        assert message["room"]["state"] is not None
        # p1 should see their own hand and only card counts for others.
        assert "my_hand" in message["room"]["state"]
        assert len(message["room"]["state"]["my_hand"]) > 0


def test_illegal_move_returns_error_to_sender_only():
    client = TestClient(app)
    room_id = _create_and_start_room(client)

    with client.websocket_connect(f"/api/ws/rooms/{room_id}?player_id=p1") as ws1:
        ws1.receive_json()  # initial state

        with client.websocket_connect(
            f"/api/ws/rooms/{room_id}?player_id=p2"
        ) as ws2:
            ws2.receive_json()  # initial state
            ws1.receive_json()  # player_connected notice for p2

            # p2 is not the current player yet (p1 goes first) — any
            # action from p2 must be rejected.
            ws2.send_json({"type": "draw"})

            error = ws2.receive_json()
            assert error["type"] == "error"


def test_valid_move_broadcasts_state_to_all_connected_players():
    client = TestClient(app)
    room_id = _create_and_start_room(client)

    room = room_manager.get_room(room_id)
    current_player_id = room.state.current_player.id
    other_player_id = next(
        p.id for p in room.players if p.id != current_player_id
    )

    with client.websocket_connect(
        f"/api/ws/rooms/{room_id}?player_id={current_player_id}"
    ) as ws_current:
        ws_current.receive_json()  # initial state

        with client.websocket_connect(
            f"/api/ws/rooms/{room_id}?player_id={other_player_id}"
        ) as ws_other:
            ws_other.receive_json()  # initial state
            ws_current.receive_json()  # player_connected notice

            # Draw is always legal on a fresh turn.
            ws_current.send_json({"type": "draw"})

            update_current = ws_current.receive_json()
            update_other = ws_other.receive_json()

            assert update_current["type"] == "state"
            assert update_other["type"] == "state"
            assert any(
                event["type"] == "cards_drawn"
                for event in update_current["events"]
            )
