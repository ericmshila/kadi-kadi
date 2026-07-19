from fastapi import APIRouter, HTTPException

from app.api.schemas import CreateRoomResponse,JoinRoomRequest,StartGameResponse
from app.game.dependencies import room_manager

from app.rules.state import Player

router = APIRouter(
    prefix="/api",
    tags=["rooms"],
)


@router.get("/health")
def health():
    return {
        "status": "ok"
    }


@router.post(
    "/rooms",
    response_model=CreateRoomResponse,
)
def create_room():

    room = room_manager.create_room()

    return CreateRoomResponse(
        room_id=room.room_id,
    )


@router.get("/rooms/{room_id}")
def get_room(room_id: str):

    try:
        room = room_manager.get_room(room_id)

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Room not found",
        )

    return {
        "room_id": room.room_id,
        "player_count": len(room.players),
        "started": room.started,
    }
    
@router.post("/rooms/{room_id}/join")
def join_room(
    room_id: str,
    payload: JoinRoomRequest,
):

    try:
        room = room_manager.get_room(room_id)

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Room not found",
        )

    room.add_player(
        Player(
            id=payload.player_id,
            name=payload.player_name,
        )
    )

    return {
        "room_id": room.room_id,
        "player_count": len(room.players),
    }
    
@router.post(
    "/rooms/{room_id}/start",
    response_model=StartGameResponse,
)
def start_game(room_id: str):

    try:
        room = room_manager.get_room(room_id)

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Room not found",
        )

    try:
        events = room.start_game()

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return StartGameResponse(
        started=True,
        event_count=len(events),
        current_player=room.state.current_player.id,
    )
    
@router.get("/rooms/{room_id}/state")
def get_game_state(room_id: str):

    try:
        room = room_manager.get_room(room_id)

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Room not found",
        )

    if room.state is None:
        raise HTTPException(
            status_code=400,
            detail="Game has not started",
        )

    return {
        "current_player": room.state.current_player.id,
        "phase": room.state.phase.value,
        "top_card": room.state.top_card.label(),
        "direction": room.state.direction,
        "winner_id": room.state.winner_id,
        "players": [
            {
                "id": player.id,
                "card_count": len(
                    room.state.hand_of(player.id)
                ),
            }
            for player in room.state.players
        ],
    }
    
@router.get("/rooms/{room_id}/state")
def get_game_state(room_id: str):

    try:
        room = room_manager.get_room(room_id)

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Room not found",
        )

    if room.state is None:
        raise HTTPException(
            status_code=400,
            detail="Game has not started",
        )

    return {
        "current_player": room.state.current_player.id,
        "phase": room.state.phase.value,
        "top_card": room.state.top_card.label(),
        "direction": room.state.direction,
        "winner_id": room.state.winner_id,
        "players": [
            {
                "id": player.id,
                "card_count": len(room.state.hand_of(player.id)),
            }
            for player in room.state.players
        ],
    }