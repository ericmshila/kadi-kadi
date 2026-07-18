from pydantic import BaseModel


class CreateRoomResponse(BaseModel):
    room_id: str


class JoinRoomRequest(BaseModel):
    player_id: str
    player_name: str


class StartGameResponse(BaseModel):
    started: bool
    event_count: int
    current_player: str
    
    
    
    
    