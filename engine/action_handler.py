"""
Action Handler Factory for Sia Assistant
Implements factory pattern for action handlers to reduce code duplication.
"""

from typing import Optional, Dict, Callable, Any
from .logger import get_logger
from .base_service import BaseService

logger = get_logger(__name__)


class ActionHandler(BaseService):
    """Factory class for handling different types of actions."""

    def __init__(self):
        super().__init__("action_handler")
        self._handlers: Dict[str, Callable[[str], Optional[str]]] = {}
        self._register_handlers()

    def _register_handlers(self):
        """Register all action handlers."""
        # Vision handlers
        self._handlers.update({
            'vision_screen': self._handle_vision_screen,
            'vision_webcam': self._handle_vision_webcam,
            'vision_error': self._handle_vision_error,
            'vision_window': self._handle_vision_window,
        })

        # OS automation handlers
        self._handlers.update({
            'open_app': self._handle_open_app,
            'generate_script': self._handle_generate_script,
            'volume': self._handle_volume,
            'system_info': self._handle_system_info,
            'organize_files': self._handle_organize_files,
        })

        # Web search handlers
        self._handlers.update({
            'web_search': self._handle_web_search,
            'news': self._handle_news,
            'weather': self._handle_weather,
        })

        # Knowledge base handlers
        self._handlers.update({
            'index_files': self._handle_index_files,
            'kb_search': self._handle_kb_search,
        })

        # Mood and memory handlers
        self._handlers.update({
            'mood_detection': self._handle_mood_detection,
            'learn_fact': self._handle_learn_fact,
        })

    def execute(self, action_type: str, command: str) -> Optional[str]:
        """
        Execute an action handler.

        Args:
            action_type: Type of action to execute
            command: Command string for the action

        Returns:
            Result of the action or None if not found
        """
        if not self._validate_input(action_type, str, "action_type"):
            return None

        if not self._validate_input(command, str, "command"):
            return None

        handler = self._handlers.get(action_type.lower())
        if handler:
            try:
                return handler(command)
            except Exception as e:
                return self._handle_error(e, f"executing {action_type}", f"{action_type.title()} failed")
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return None

    def get_available_actions(self) -> list[str]:
        """Get list of available action types."""
        return list(self._handlers.keys())

    # Vision handlers
    def _handle_vision_screen(self, user_text: str) -> Optional[str]:
        """Handle screen analysis request."""
        try:
            from . import vision_engine
            return vision_engine.analyze_screen(user_text)
        except Exception as e:
            return self._handle_error(e, "screen analysis", "Screen analysis failed")

    def _handle_vision_webcam(self, user_text: str) -> Optional[str]:
        """Handle webcam analysis request."""
        try:
            from . import vision_engine
            return vision_engine.analyze_webcam(user_text)
        except Exception as e:
            return self._handle_error(e, "webcam analysis", "Webcam analysis failed")

    def _handle_vision_error(self, user_text: str) -> Optional[str]:
        """Handle error detection on screen."""
        try:
            from . import vision_engine
            return vision_engine.analyze_error_on_screen()
        except Exception as e:
            return self._handle_error(e, "error detection", "Error detection failed")

    def _handle_vision_window(self, user_text: str) -> Optional[str]:
        """Handle active window analysis request."""
        try:
            from . import vision_engine
            return vision_engine.analyze_active_window(user_text)
        except Exception as e:
            return self._handle_error(e, "window analysis", "Window analysis failed")

    # OS automation handlers
    def _handle_open_app(self, cmd: str) -> Optional[str]:
        """Extract app name and open it."""
        try:
            from . import os_automation
            app_name = self._extract_app_name(cmd)
            if app_name:
                return os_automation.open_app(app_name)
            return None
        except Exception as e:
            return self._handle_error(e, "app opening", "App open failed")

    def _handle_generate_script(self, cmd: str) -> Optional[str]:
        """Handle PC automation scripting request."""
        try:
            from . import os_automation
            return os_automation.generate_and_run_script(cmd)
        except Exception as e:
            return self._handle_error(e, "script generation", "Script automation failed")

    def _handle_volume(self, cmd: str) -> Optional[str]:
        """Handle volume commands."""
        try:
            from . import os_automation
            return self._process_volume_command(cmd)
        except Exception as e:
            return self._handle_error(e, "volume control", "Volume control failed")

    def _handle_system_info(self, cmd: str) -> Optional[str]:
        """Get system information."""
        try:
            from . import os_automation
            return os_automation.get_system_info()
        except Exception as e:
            return self._handle_error(e, "system info", "System info failed")

    def _handle_organize_files(self, cmd: str) -> Optional[str]:
        """Handle file organization."""
        try:
            from . import os_automation
            folder = self._extract_folder_path(cmd)
            return os_automation.organize_files(folder)
        except Exception as e:
            return self._handle_error(e, "file organization", "File organization failed")

    # Web search handlers
    def _handle_web_search(self, cmd: str) -> Optional[str]:
        """Handle web search request."""
        try:
            from . import web_search
            query = self._extract_query(cmd, ["search", "dhundho", "internet pe", "google", "search karo"])
            if query:
                return web_search.search_web(query)
            return None
        except Exception as e:
            return self._handle_error(e, "web search", "Web search failed")

    def _handle_news(self, cmd: str) -> Optional[str]:
        """Handle news request."""
        try:
            from . import web_search
            topic = self._extract_query(cmd, ["news", "khabar", "headlines"])
            if not topic:
                topic = "India technology"
            return web_search.get_latest_news(topic)
        except Exception as e:
            return self._handle_error(e, "news fetch", "News fetch failed")

    def _handle_weather(self, cmd: str) -> Optional[str]:
        """Handle weather request."""
        try:
            city = self._extract_city(cmd)
            return f"SHOW_WIDGET:WEATHER:{city}"
        except Exception as e:
            return self._handle_error(e, "weather fetch", "Weather fetch failed")

    # Knowledge base handlers
    def _handle_index_files(self, cmd: str) -> Optional[str]:
        """Handle knowledge base indexing request."""
        try:
            from . import knowledge_base
            path = self._extract_path(cmd)
            return knowledge_base.index_project(path)
        except Exception as e:
            return self._handle_error(e, "file indexing", "File indexing failed")

    def _handle_kb_search(self, cmd: str) -> Optional[str]:
        """Handle knowledge base search."""
        try:
            from . import knowledge_base
            query = self._extract_query(cmd, ["dhundho", "find", "search", "code", "file"])
            result = knowledge_base.search_knowledge(query)
            return result or "❌ Knowledge base mein kuch nahi mila. Pehle files index karo."
        except Exception as e:
            return self._handle_error(e, "KB search", "KB search failed")

    # Mood and memory handlers
    def _handle_mood_detection(self, cmd: str) -> Optional[str]:
        """Detect user's mood from their speech."""
        try:
            from .actions import _handle_mood_detection as mood_handler
            return mood_handler(cmd)
        except Exception as e:
            return self._handle_error(e, "mood detection", "Mood detection failed")

    def _handle_learn_fact(self, cmd: str) -> Optional[str]:
        """Extract and learn a user fact."""
        try:
            from .actions import _handle_learn_fact as learn_handler
            return learn_handler(cmd)
        except Exception as e:
            return self._handle_error(e, "fact learning", "Fact learning failed")

    # Helper methods
    def _extract_app_name(self, cmd: str) -> Optional[str]:
        """Extract app name from command."""
        app_name = cmd
        for trigger in ["open", "kholo", "chalu karo", "start", "launch"]:
            if trigger in app_name:
                app_name = app_name.split(trigger, 1)[1].strip()
                break
        return app_name if app_name else None

    def _process_volume_command(self, cmd: str) -> Optional[str]:
        """Process volume command."""
        from . import os_automation

        if "mute" in cmd:
            return os_automation.mute_volume()

        import re
        numbers = re.findall(r'\d+', cmd)
        if numbers:
            level = int(numbers[0])
            return os_automation.set_volume(level)

        if "up" in cmd or "badhao" in cmd:
            return os_automation.set_volume(80)
        elif "down" in cmd or "kam" in cmd:
            return os_automation.set_volume(30)

        return None

    def _extract_folder_path(self, cmd: str) -> Optional[str]:
        """Extract folder path from command."""
        import os
        if "desktop" in cmd:
            return os.path.join(os.path.expanduser("~"), "Desktop")
        elif "download" in cmd:
            return os.path.join(os.path.expanduser("~"), "Downloads")
        return None

    def _extract_query(self, cmd: str, triggers: list[str]) -> Optional[str]:
        """Extract query from command using triggers."""
        query = cmd
        for trigger in triggers:
            if trigger in query:
                query = query.split(trigger, 1)[1].strip()
                break
        return query if query != cmd else None

    def _extract_city(self, cmd: str) -> str:
        """Extract city from weather command."""
        city = "Roorkee"  # Default
        for word in ["weather", "mausam"]:
            if word in cmd:
                parts = cmd.split(word, 1)[1].strip()
                if parts:
                    # Remove common words
                    for remove in ["in", "of", "ka", "ki", "ke", "mein", "dikhao", "batao", "aaj", "ka"]:
                        parts = parts.replace(remove, "").strip()
                    if parts:
                        city = parts.strip().title()
        return city

    def _extract_path(self, cmd: str) -> str:
        """Extract path from command."""
        import os
        if "desktop" in cmd:
            return os.path.join(os.path.expanduser("~"), "Desktop")
        elif "project" in cmd or "sia" in cmd:
            return os.path.dirname(os.path.abspath(__file__))
        else:
            return os.path.dirname(os.path.abspath(__file__))  # Default to Sia project

    def health_check(self) -> bool:
        """Check if action handler is healthy."""
        try:
            return len(self._handlers) > 0
        except Exception:
            return False


# Global action handler instance
action_handler = ActionHandler()