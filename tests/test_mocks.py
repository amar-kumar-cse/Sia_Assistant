"""
Mock Providers for Sia Assistant Offline Testing & CI Execution.
Provides standalone test double implementations for Gemini API and Voice Engine.
"""

from typing import List, Dict, Any, Optional


class MockGeminiProvider:
    """Mock Gemini API provider for fast offline unit testing."""

    def __init__(self, mock_response: str = "[EMOTION:happy] Test response from Mock Gemini"):
        self.mock_response = mock_response
        self.call_count = 0
        self.last_prompt: Optional[str] = None

    def generate_content(self, contents: Any, stream: bool = False) -> Any:
        self.call_count += 1
        self.last_prompt = str(contents)

        class MockResponseObj:
            def __init__(self, text):
                self.text = text

        return MockResponseObj(self.mock_response)


class MockVoiceEngine:
    """Mock Voice Engine for headless test environments."""

    def __init__(self):
        self.is_speaking = False
        self.spoken_texts: List[str] = []

    def speak(self, text: str, emotion: str = "default", callback_started=None, callback_finished=None):
        self.is_speaking = True
        self.spoken_texts.append(text)
        if callback_started:
            callback_started()
        self.is_speaking = False
        if callback_finished:
            callback_finished()

    def stop_speaking(self):
        self.is_speaking = False
