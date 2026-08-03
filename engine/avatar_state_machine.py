"""
Formal State Machine for Sia Assistant Avatar.
Manages avatar state transitions cleanly and thread-safely.
"""

from enum import Enum, auto
import threading
from typing import Callable, List, Optional
from .logger import get_logger

logger = get_logger(__name__)


class AvatarState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class AvatarStateMachine:
    """Thread-safe state machine controlling avatar state transitions and UI callbacks."""

    def __init__(self, initial_state: AvatarState = AvatarState.IDLE):
        self._state = initial_state
        self._lock = threading.RLock()
        self._listeners: List[Callable[[AvatarState, AvatarState], None]] = []

    @property
    def current_state(self) -> AvatarState:
        with self._lock:
            return self._state

    def add_listener(self, callback: Callable[[AvatarState, AvatarState], None]) -> None:
        """Register a callback (old_state, new_state) -> None."""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[AvatarState, AvatarState], None]) -> None:
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def transition_to(self, new_state: AvatarState) -> bool:
        """Attempt to transition to a new avatar state. Returns True if state changed."""
        with self._lock:
            if self._state == new_state:
                return False

            old_state = self._state
            self._state = new_state
            logger.info(f"🔄 Avatar state transition: {old_state.value} ➡️ {new_state.value}")

            # Notify listeners safely
            for listener in list(self._listeners):
                try:
                    listener(old_state, new_state)
                except Exception as e:
                    logger.error(f"Error in state transition listener: {e}")

            return True

    def reset_to_idle(self) -> bool:
        """Convenience method to return avatar to IDLE state."""
        return self.transition_to(AvatarState.IDLE)


# Global singleton instance for app-wide state tracking
avatar_state_machine = AvatarStateMachine()
