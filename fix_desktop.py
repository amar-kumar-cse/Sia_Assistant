import sys

with open('sia_desktop.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 2. Silent Error Swallowing in sia_desktop.py -> WakeWordThread. Add logging.
content = content.replace(
    '            except Exception as e:\n                time.sleep(1)',
    '            except Exception as e:\n                app_logger.error(f"WakeWordThread error: {e}")\n                time.sleep(1)'
)

# 5. UI Race Conditions & Annoying Behaviors in sia_desktop.py
content = content.replace(
    '        self.typewriter_timer.stop()\n        if self.current_state == "thinking" or not getattr(self, \'bubble_display_text\', \'\').startswith("Sia"):\n             self.bubble_display_text = "Sia 🧡: "\n             self.current_state = "speaking"\n             self._set_status("🧡 Speaking")',
    '        self.typewriter_timer.stop()\n        if self.current_state == "thinking" or not getattr(self, \'bubble_display_text\', \'\').startswith("Sia"):\n             self.bubble_text = "Sia 🧡: "\n             self.bubble_display_text = "Sia 🧡: "\n             self.current_state = "speaking"\n             self._set_status("🧡 Speaking")'
)

content = content.replace(
    '        self.bubble_display_text += clean_chunk',
    '        self.bubble_text += clean_chunk\n        self.bubble_display_text += clean_chunk'
)

# Thread leaks fixes for think_thread and speak_thread in sia_desktop.py
# Fix in _on_text_recognized
content = content.replace(
    '        self.think_thread = ThinkThread(text)',
    '        if self.think_thread and self.think_thread.isRunning():\n            self.think_thread.terminate()\n            self.think_thread.wait(1000)\n        self.think_thread = ThinkThread(text)'
)

# Fix in _on_response_ready and proactive speak for SpeakThread
content = content.replace(
    '        self.speak_thread = SpeakThread(response, emotion=emotion)',
    '        if self.speak_thread and self.speak_thread.isRunning():\n            self.speak_thread.terminate()\n            self.speak_thread.wait(1000)\n        self.speak_thread = SpeakThread(response, emotion=emotion)'
)
content = content.replace(
    '        self.speak_thread = SpeakThread(text, emotion="SMILE")',
    '        if self.speak_thread and self.speak_thread.isRunning():\n            self.speak_thread.terminate()\n            self.speak_thread.wait(1000)\n        self.speak_thread = SpeakThread(text, emotion="SMILE")'
)
content = content.replace(
    '        self.speak_thread = SpeakThread(text, emotion="HAPPY")',
    '        if self.speak_thread and self.speak_thread.isRunning():\n            self.speak_thread.terminate()\n            self.speak_thread.wait(1000)\n        self.speak_thread = SpeakThread(text, emotion="HAPPY")'
)
content = content.replace(
    '        self.speak_thread = SpeakThread(message, "SMILE")',
    '        if self.speak_thread and self.speak_thread.isRunning():\n            self.speak_thread.terminate()\n            self.speak_thread.wait(1000)\n        self.speak_thread = SpeakThread(message, "SMILE")'
)


# Fix the annoying enterEvent (remove _show_panel call)
content = content.replace(
    '    def enterEvent(self, event):\n        """On hover → show side panel."""\n        self._show_panel()\n        self.target_opacity = 1.0',
    '    def enterEvent(self, event):\n        """On hover."""\n        self.target_opacity = 1.0'
)

# Fix Vision Thread leak in _run_proactive_vision_loop
content = content.replace(
    '        self.proactive_vision_thread = ProactiveVisionThread()\n        self.proactive_vision_thread.result_ready.connect(self._proactive_speak)',
    '        if getattr(self, "proactive_vision_thread", None) and self.proactive_vision_thread.isRunning():\n            self.proactive_vision_thread.terminate()\n            self.proactive_vision_thread.wait(1000)\n        self.proactive_vision_thread = ProactiveVisionThread()\n        self.proactive_vision_thread.result_ready.connect(self._proactive_speak)'
)


with open('sia_desktop.py', 'w', encoding='utf-8') as f:
    f.write(content)
