"""
"Play again" — starting a fresh round for the same group of players
once one round finishes, without having to leave the room and
re-create it.

No host/owner concept: any player still seated can trigger a restart
(see GameRoom.restart's docstring), it just requires the previous
round to actually be over.
"""

import pytest
from fastapi.testclient import TestClient

from app.game.dependencies import connection_manager, room_manager
from app.game.room import create_room
from app.main import app
from app.rules.state import Phase, Player


@pytest.fixture(autouse=True)
def _reset_shared_state():
    room_manager.clear()
    connection_manager.active_connections.clear()
    yield
    room_manager.clear()
    connection_manager.active_connections.clear()


def _two_player_room():
    room = create_room()
    room.add_player(Player(id="a", name="Amina"))
    room.add_player(Player(id="b", name="Brian"))
    return room


def test_restart_before_first_start_raises():
    room = _two_player_room()

    with pytest.raises(ValueError):
        room.restart()


def test_restart_while_round_in_progress_raises():
    room = _two_player_room()
    room.start_game()

    assert room.state.phase != Phase.FINISHED

    with pytest.raises(ValueError):
        room.restart()


def test_restart_after_finish_deals_a_fresh_round():
    room = _two_player_room()
    room.start_game()

    # Force the round to a finished state directly rather than
    # playing it out card by card — restart() only cares that
    # phase == FINISHED, not how it got there.
    room.state = room.state.replace(
        phase=Phase.FINISHED,
        winner_id="a",
        eliminated_player_ids=frozenset({"b"}),
    )

    events = room.restart()

    assert room.state.phase != Phase.FINISHED
    assert room.state.winner_id is None
    assert room.state.eliminated_player_ids == frozenset()
    # Same two players carry over into the new round.
    assert {p.id for p in room.state.players} == {"a", "b"}
    assert any(event.type.value == "game_started" for event in events)


def test_restart_keeps_same_room_and_players_list():
    room = _two_player_room()
    room.start_game()
    room.state = room.state.replace(phase=Phase.FINISHED, winner_id="a")

    room.restart()

    assert len(room.players) == 2
    assert {p.id for p in room.players} == {"a", "b"}


def test_websocket_restart_message_broadcasts_fresh_state():
    client = TestClient(app)

    room_id = client.post("/api/rooms").json()["room_id"]
    client.post(
        f"/api/rooms/{room_id}/join",
        json={"player_id": "a", "player_name": "Amina"},
    )
    client.post(
        f"/api/rooms/{room_id}/join",
        json={"player_id": "b", "player_name": "Brian"},
    )
    client.post(f"/api/rooms/{room_id}/start")

    room = room_manager.get_room(room_id)
    room.state = room.state.replace(phase=Phase.FINISHED, winner_id="a")

    with client.websocket_connect(
        f"/api/ws/rooms/{room_id}?player_id=a"
    ) as ws:
        ws.receive_json()  # initial state on connect

        ws.send_json({"type": "restart"})

        message = ws.receive_json()

        assert message["type"] == "state"
        assert message["room"]["state"]["phase"] != "finished"
        assert message["room"]["state"]["winner_id"] is None


def test_websocket_restart_before_finish_sends_error():
    client = TestClient(app)

    room_id = client.post("/api/rooms").json()["room_id"]
    client.post(
        f"/api/rooms/{room_id}/join",
        json={"player_id": "a", "player_name": "Amina"},
    )
    client.post(
        f"/api/rooms/{room_id}/join",
        json={"player_id": "b", "player_name": "Brian"},
    )
    client.post(f"/api/rooms/{room_id}/start")

    with client.websocket_connect(
        f"/api/ws/rooms/{room_id}?player_id=a"
    ) as ws:
        ws.receive_json()  # initial state on connect

        ws.send_json({"type": "restart"})

        message = ws.receive_json()

        assert message["type"] == "error"
