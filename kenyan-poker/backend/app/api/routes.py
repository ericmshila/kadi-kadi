from fastapi import APIRouter, HTTPException

from app.api.schemas import CreateRoomResponse,JoinRoomRequest
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