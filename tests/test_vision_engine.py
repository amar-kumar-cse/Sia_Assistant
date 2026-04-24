import unittest
from unittest import mock


class TestVisionEngine(unittest.TestCase):
    @mock.patch("engine.vision_engine.pyautogui.screenshot")
    @mock.patch("engine.vision_engine.analyze_image")
    def test_analyze_screen_uses_screenshot_and_gemini(self, mock_analyze, mock_shot):
        from engine import vision_engine
        mock_shot.return_value = mock.Mock(save=lambda *_args, **_kwargs: None)
        mock_analyze.return_value = "ok"
        res = vision_engine.analyze_screen("what is on screen")
        self.assertIsNotNone(res)
        self.assertTrue(mock_shot.called)

    @mock.patch("engine.vision_engine.pyautogui.screenshot")
    @mock.patch("engine.vision_engine.analyze_image", side_effect=Exception("api down"))
    def test_analyze_screen_offline_fallback_on_gemini_error(self, _a, _b):
        from engine import vision_engine
        res = vision_engine.analyze_screen("check")
        self.assertIsInstance(res, str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
