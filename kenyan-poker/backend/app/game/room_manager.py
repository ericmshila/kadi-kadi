"""
Room Manager

Responsible for:

- Creating rooms
- Finding rooms
- Removing rooms
- Tracking active games

No networking code here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .room import GameRoom, create_room
from app.rules.config import RuleConfig


@dataclass
class RoomManager:
    rooms: dict[str, GameRoom] = field(default_factory=dict)

    # ---------------------------------------------------------
    # Room Lifecycle
    # ---------------------------------------------------------

    def create_room(
        self,
        rules: RuleConfig | None = None,
    ) -> GameRoom:

        room = create_room(rules=rules)

        self.rooms[room.room_id] = room

        return room

    def get_room(
        self,
        room_id: str,
    ) -> GameRoom:

        if room_id not in self.rooms:
            raise KeyError(f"Room not found: {room_id}")

        return self.rooms[room_id]

    def room_exists(
        self,
        room_id: str,
    ) -> bool:

        return room_id in self.rooms

    def remove_room(
        self,
        room_id: str,
    ) -> None:

        if room_id in self.rooms:
            del self.rooms[room_id]

    # ---------------------------------------------------------
    # Utility
    # ---------------------------------------------------------

    def active_room_count(self) -> int:
        return len(self.rooms)

    def clear(self) -> None:
        self.rooms.clear()