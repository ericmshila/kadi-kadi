"""
Application-level shared dependencies.

For MVP we keep a single in-memory RoomManager.
"""

from app.game.room_manager import RoomManager

room_manager = RoomManager()