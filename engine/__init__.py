"""
Engine module exports for Sia Assistant.
"""

from .logger import get_logger
from .brain import think, detect_mood, think_streaming, think_with_vision
from .voice_engine import speak, stop, get_speaking_state, speak_async
from .listen_engine import listen, listen_for_wake_word
from .actions import perform_action
from .memory import (
    get_all_memory_as_string,
    load_memory,
    save_memory,
    add_memory_log,
    get_preference,
    set_preference,
    update_skill,
    get_file_path,
    update_file_path,
    learn_fact,
    get_recent_facts,
    forget_fact,
    add_todo,
    list_todos,
    complete_todo,
    delete_todo,
    get_morning_briefing_data,
)

__all__ = [
    "get_logger",
    "think",
    "detect_mood",
    "think_streaming",
    "think_with_vision",
    "speak",
    "stop",
    "get_speaking_state",
    "speak_async",
    "listen",
    "listen_for_wake_word",
    "perform_action",
    "get_all_memory_as_string",
    "load_memory",
    "save_memory",
    "add_memory_log",
    "get_preference",
    "set_preference",
    "update_skill",
    "get_file_path",
    "update_file_path",
    "learn_fact",
    "get_recent_facts",
    "forget_fact",
    "add_todo",
    "list_todos",
    "complete_todo",
    "delete_todo",
    "get_morning_briefing_data",
]
