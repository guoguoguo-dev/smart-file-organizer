"""Smart File Organizer — automatically sort files into folders by type."""
from .organizer import ExecutionReport, Move, MoveResult, Organizer, Plan

__version__ = "0.1.0"
__all__ = ["Organizer", "Plan", "Move", "MoveResult", "ExecutionReport"]
