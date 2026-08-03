"""
Plugin Manager for Sia Assistant.
Enables dynamic loading of custom skills & tools from the plugins/ directory.
"""

import os
import sys
import importlib.util
from typing import Dict, Any, Callable, List, Optional
from .logger import get_logger

logger = get_logger(__name__)


class PluginManager:
    """Discovers, loads, and manages dynamic plugin extensions for Sia Assistant."""

    def __init__(self, plugins_dir: Optional[str] = None):
        if not plugins_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            plugins_dir = os.path.join(base_dir, "plugins")
        self.plugins_dir = plugins_dir
        self.plugins: Dict[str, Any] = {}
        self.registered_actions: Dict[str, Callable[..., Any]] = {}
        os.makedirs(self.plugins_dir, exist_ok=True)

    def load_plugins(self) -> Dict[str, Any]:
        """Scan plugins directory and load valid python plugin modules."""
        if not os.path.exists(self.plugins_dir):
            return {}

        for fname in os.listdir(self.plugins_dir):
            if fname.endswith(".py") and not fname.startswith("_"):
                mod_name = fname[:-3]
                file_path = os.path.join(self.plugins_dir, fname)
                try:
                    spec = importlib.util.spec_from_file_location(f"sia_plugin_{mod_name}", file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        self.plugins[mod_name] = module
                        logger.info(f"🧩 Plugin loaded successfully: {mod_name}")

                        # Register exported action handlers if defined
                        if hasattr(module, "register_actions"):
                            actions = module.register_actions()
                            if isinstance(actions, dict):
                                self.registered_actions.update(actions)
                except Exception as e:
                    logger.error(f"Failed loading plugin {fname}: {e}")

        return self.plugins

    def execute_plugin_action(self, action_name: str, *args, **kwargs) -> Optional[Any]:
        """Execute a registered action exported by a plugin."""
        if action_name in self.registered_actions:
            try:
                return self.registered_actions[action_name](*args, **kwargs)
            except Exception as e:
                logger.error(f"Error executing plugin action {action_name}: {e}")
                return f"❌ Plugin action error: {e}"
        return None


plugin_manager = PluginManager()
