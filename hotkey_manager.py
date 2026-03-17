"""
Global Hotkey Manager for Sia
Enables system-wide keyboard shortcuts to control Sia from anywhere

Hotkeys:
- Alt+Space: Toggle Sia visibility
- Ctrl+Shift+S: Screenshot + Vision analysis
- Ctrl+Shift+V: Quick voice input
"""

import keyboard
import threading
import time

class HotkeyManager:
    """Manages global hotkeys for Sia."""
    
    def __init__(self, main_window=None):
        self.main_window = main_window
        self.enabled = True
        self._registered = False
        
    def register_hotkeys(self):
        """Register all global hotkeys."""
        if self._registered:
            return
        
        try:
            # Alt+Space: Toggle Sia window
            keyboard.add_hotkey(
                'alt+space',
                self._toggle_window,
                suppress=True
            )
            
            # Ctrl+Shift+S: Screenshot analysis
            keyboard.add_hotkey(
                'ctrl+shift+s',
                self._quick_screenshot,
                suppress=True
            )
            
            # Ctrl+Shift+V: Quick voice input
            keyboard.add_hotkey(
                'ctrl+shift+v',
                self._quick_voice,
                suppress=True
            )
            
            self._registered = True
            print("✅ Global hotkeys registered:")
            print("   Alt+Space → Toggle Sia")
            print("   Ctrl+Shift+S → Screenshot Analysis")
            print("   Ctrl+Shift+V → Quick Voice Input")
            
        except Exception as e:
            print(f"⚠️ Hotkey registration failed: {e}")
            print("   (May need administrator privileges)")
    
    def unregister_hotkeys(self):
        """Unregister all hotkeys."""
        if not self._registered:
            return
        
        try:
            keyboard.unhook_all_hotkeys()
            self._registered = False
            print("🔓 Global hotkeys unregistered")
        except Exception as e:
            print(f"⚠️ Hotkey unregistration failed: {e}")
    
    def _toggle_window(self):
        """Toggle Sia window visibility."""
        if not self.main_window or not self.enabled:
            return
        
        try:
            if self.main_window.isVisible():
                self.main_window.hide()
                print("👻 Sia hidden (Alt+Space to show)")
            else:
                self.main_window.show()
                self.main_window.activateWindow()
                self.main_window.raise_()
                print("👋 Sia shown")
        except Exception as e:
            print(f"❌ Toggle error: {e}")
    
    def _quick_screenshot(self):
        """Quick screenshot + vision analysis."""
        if not self.main_window or not self.enabled:
            return
        
        try:
            # Show window
            self.main_window.show()
            self.main_window.activateWindow()
            
            # Trigger screenshot analysis
            if hasattr(self.main_window, 'trigger_screenshot_analysis'):
                threading.Thread(
                    target=self.main_window.trigger_screenshot_analysis,
                    daemon=True
                ).start()
                print("📸 Screenshot analysis triggered")
        except Exception as e:
            print(f"❌ Screenshot error: {e}")
    
    def _quick_voice(self):
        """Quick voice input."""
        if not self.main_window or not self.enabled:
            return
        
        try:
            # Show window
            self.main_window.show()
            self.main_window.activateWindow()
            
            # Trigger voice input
            if hasattr(self.main_window, 'activate_voice_input'):
                self.main_window.activate_voice_input()
                print("🎤 Voice input activated")
        except Exception as e:
            print(f"❌ Voice error: {e}")
    
    def enable(self):
        """Enable hotkey processing."""
        self.enabled = True
    
    def disable(self):
        """Disable hotkey processing."""
        self.enabled = False


# Global instance
_hotkey_manager = None

def get_hotkey_manager(main_window=None):
    """Get or create the global hotkey manager."""
    global _hotkey_manager
    
    if _hotkey_manager is None:
        _hotkey_manager = HotkeyManager(main_window)
    elif main_window is not None:
        _hotkey_manager.main_window = main_window
    
    return _hotkey_manager


# Utility function for testing
if __name__ == "__main__":
    print("Testing hotkey manager...")
    print("Press Alt+Space to test (Ctrl+C to exit)")
    
    manager = HotkeyManager()
    manager.register_hotkeys()
    
    try:
        # Keep alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.unregister_hotkeys()
        print("\nExiting...")
