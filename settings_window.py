"""Settings window for Sia desktop assistant."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingsWindow(QWidget):
    settings_applied = pyqtSignal(dict)
    prepare_videos_requested = pyqtSignal()

    def __init__(self, settings_path: str = "cache/ui_settings.json", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings_path = Path(settings_path)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

        self.setWindowTitle("Sia Settings")
        self.resize(380, 260)

        root = QVBoxLayout(self)
        title = QLabel("Sia Configuration")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        root.addWidget(title)

        form = QFormLayout()

        self.voice_select = QComboBox(self)
        self.voice_select.addItems([
            "hi-IN-SwaraNeural",
            "en-US-JennyNeural",
            "en-IN-NeerjaNeural",
        ])
        form.addRow("TTS Voice", self.voice_select)

        self.position_x = QSpinBox(self)
        self.position_x.setRange(0, 5000)
        self.position_y = QSpinBox(self)
        self.position_y.setRange(0, 5000)

        pos_row = QHBoxLayout()
        pos_row.addWidget(self.position_x)
        pos_row.addWidget(self.position_y)
        pos_wrap = QWidget(self)
        pos_wrap.setLayout(pos_row)
        form.addRow("Position X / Y", pos_wrap)

        self.wake_word = QLineEdit(self)
        form.addRow("Wake Word", self.wake_word)

        self.gemini_key = QLineEdit(self)
        self.gemini_key.setEchoMode(QLineEdit.Password)
        form.addRow("Gemini API Key", self.gemini_key)

        root.addLayout(form)

        controls = QHBoxLayout()
        self.prepare_btn = QPushButton("Prepare Videos", self)
        self.save_btn = QPushButton("Save", self)
        self.close_btn = QPushButton("Close", self)
        controls.addWidget(self.prepare_btn)
        controls.addWidget(self.save_btn)
        controls.addWidget(self.close_btn)
        root.addLayout(controls)

        self.prepare_btn.clicked.connect(self.prepare_videos_requested.emit)
        self.save_btn.clicked.connect(self._save)
        self.close_btn.clicked.connect(self.hide)

        self._load()

    def _load(self) -> None:
        settings = self._load_dict()
        self.voice_select.setCurrentText(settings.get("voice", "hi-IN-SwaraNeural"))
        self.position_x.setValue(int(settings.get("pos_x", 0)))
        self.position_y.setValue(int(settings.get("pos_y", 0)))
        self.wake_word.setText(settings.get("wake_word", "hey sia"))
        self.gemini_key.setText(settings.get("gemini_api_key", ""))

    def _load_dict(self) -> Dict[str, object]:
        if not self.settings_path.exists():
            return {}
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        payload = {
            "voice": self.voice_select.currentText(),
            "pos_x": self.position_x.value(),
            "pos_y": self.position_y.value(),
            "wake_word": self.wake_word.text().strip() or "hey sia",
            "gemini_api_key": self.gemini_key.text().strip(),
        }
        self.settings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.settings_applied.emit(payload)
