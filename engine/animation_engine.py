"""
Sia Animation Engine v2 — Alpha-Blending Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Smooth cross-fade transitions between all frames.
No more hard cuts — every frame change is blended.

Key exports:
  AnimationEngine  — main state machine
  AvatarState      — idle / listening / thinking / speaking
  BlendFrame       — (frame_key, alpha 0-255) render instruction
"""

import math
import random
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class AvatarState(Enum):
    IDLE      = auto()
    LISTENING = auto()
    THINKING  = auto()
    SPEAKING  = auto()
    HAPPY     = auto()
    SAD       = auto()


@dataclass
class BlendFrame:
    """
    Render instruction for paintEvent.
    Draw frame_from at (255 - alpha), frame_to at alpha.
    When alpha reaches 255 the transition is complete.
    """
    frame_from: str   # key: 'idle' | 'blink' | 'semi' | 'open'
    frame_to:   str
    alpha:      int   # 0 = fully from, 255 = fully to


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BLINK CONTROLLER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BlinkController:
    """
    Human-like random blink generator.
    Blink = close (idle→blink, 80ms) + hold (blink, 50ms) + open (blink→idle, 80ms).
    """
    INTERVAL_MIN  = 2.0    # seconds between blinks
    INTERVAL_MAX  = 5.0
    CLOSE_MS      = 100    # ms for eye-close phase (0.1s crossfade)
    HOLD_MS       = 50     # ms eyes stay closed
    OPEN_MS       = 100    # ms for eye-open phase (0.1s crossfade)

    def __init__(self):
        self._t0      = time.monotonic()
        self._next    = self._rand()
        self._phase   = None   # None | 'closing' | 'holding' | 'opening'
        self._phase_t = 0.0

    def _rand(self) -> float:
        return random.uniform(self.INTERVAL_MIN, self.INTERVAL_MAX)

    def update(self) -> BlendFrame:
        """
        Returns a BlendFrame describing the current blink sub-phase.
        alpha=0   → idle (no blink)
        alpha=255 → fully blinking
        """
        now = time.monotonic()
        elapsed = (now - self._phase_t) * 1000  # ms

        if self._phase is None:
            if now - self._t0 >= self._next:
                self._phase   = 'closing'
                self._phase_t = now
                elapsed = 0
            else:
                return BlendFrame('idle', 'blink', 0)

        if self._phase == 'closing':
            a = min(255, int(elapsed / self.CLOSE_MS * 255))
            if elapsed >= self.CLOSE_MS:
                self._phase   = 'holding'
                self._phase_t = now
            return BlendFrame('idle', 'blink', a)

        if self._phase == 'holding':
            if elapsed >= self.HOLD_MS:
                self._phase   = 'opening'
                self._phase_t = now
                elapsed = 0
            return BlendFrame('idle', 'blink', 255)

        if self._phase == 'opening':
            a = max(0, 255 - int(elapsed / self.OPEN_MS * 255))
            if elapsed >= self.OPEN_MS:
                self._phase = None
                self._t0    = now
                self._next  = self._rand()
                return BlendFrame('idle', 'blink', 0)
            return BlendFrame('idle', 'blink', a)

        return BlendFrame('idle', 'blink', 0)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LIP-SYNC CONTROLLER  (blended)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class LipSyncController:
    """
    Drives a smooth idle↔semi↔open cycle while speaking.
    Uses a sine wave mapped to 3 frames so transitions are gradual.
    """
    CYCLE_SPEED = 5.0   # radians/second (higher = faster mouth)

    def __init__(self):
        self._tick   = 0.0
        self._active = False
        self._fallback_tick = 0.0

    def reset(self):
        self._tick   = 0.0
        self._active = False
        self._fallback_tick = 0.0

    def activate(self):
        self._active = True

    def update(self, dt: float = 0.05) -> BlendFrame:
        """
        dt = seconds since last call (default 50ms @ 20fps).
        Returns BlendFrame for the current lip phase driven by audio frequency (Heartbeat Loop).
        """
        if not self._active:
            return BlendFrame('idle', 'idle', 255)

        try:
            from engine.voice_engine import get_audio_frequency
            freq = get_audio_frequency()  # 0.0 to 1.0
        except Exception:
            # Fallback if amplitude source is unavailable:
            # deterministic closed->semi->open->semi rhythm.
            self._fallback_tick = (self._fallback_tick + dt * 4.0) % 4.0
            if self._fallback_tick < 1.0:
                freq = 0.2
            elif self._fallback_tick < 2.0:
                freq = 0.5
            elif self._fallback_tick < 3.0:
                freq = 0.9
            else:
                freq = 0.5

        # freq controls how open the mouth is. 
        # 0.0 to 0.3 -> idle to semi
        if freq < 0.3:
            a = min(255, int(freq / 0.3 * 255))
            return BlendFrame('idle', 'semi', a)
        # 0.3 to 1.0 -> semi to open
        else:
            a = min(255, int((freq - 0.3) / 0.7 * 255))
            return BlendFrame('semi', 'open', a)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN ANIMATION ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AnimationEngine:
    """
    Central animation state machine.

    Call tick() every 50ms.
    Read .blend to get a BlendFrame render instruction.
    Read .breath_offset (float px) for Y-axis breathing float.
    Read .glow_alpha (int 0-255) for ambient neon ring.

    paintEvent pseudocode:
        bf = anim.blend
        p.setOpacity((255 - bf.alpha) / 255)
        p.drawPixmap(frame_pixmaps[bf.frame_from])
        p.setOpacity(bf.alpha / 255)
        p.drawPixmap(frame_pixmaps[bf.frame_to])
        p.setOpacity(1.0)
    """

    # ── Breathing parameters per state ──
    _BREATH = {
        AvatarState.IDLE:      (1.5, 5.0),   # (freq, amplitude px) - ~5px breathing
        AvatarState.LISTENING: (2.5, 3.0),
        AvatarState.THINKING:  (2.0, 3.5),
        AvatarState.SPEAKING:  (3.5, 1.5),   # subtle during speech
        AvatarState.HAPPY:     (2.1, 3.0),
        AvatarState.SAD:       (1.4, 2.2),
    }

    def __init__(self):
        self._state      = AvatarState.IDLE
        self._tick       = 0.0

        self._blink      = BlinkController()
        self._lip        = LipSyncController()

        # Public outputs
        self.blend        = BlendFrame('idle', 'idle', 255)
        self.breath_offset = 0.0
        self.glow_alpha   = 18
        self.pulse_scale  = 1.0
        self._emotion_until = 0.0

    # ── State management ─────────────────────────────────
    def set_state(self, state: AvatarState):
        if state == self._state:
            return
        prev = self._state
        self._state = state
        if state == AvatarState.SPEAKING:
            self._lip.activate()
        elif prev == AvatarState.SPEAKING:
            self._lip.reset()

    def set_emotion(self, emotion: str):
        em = (emotion or "neutral").strip().lower()
        if em == "happy":
            self.set_state(AvatarState.HAPPY)
            self._emotion_until = time.monotonic() + 3.0
        elif em == "sad":
            self.set_state(AvatarState.SAD)
            self._emotion_until = time.monotonic() + 3.0
        elif em == "thinking":
            self.set_state(AvatarState.THINKING)
            self._emotion_until = time.monotonic() + 2.0
        else:
            self.set_state(AvatarState.IDLE)
            self._emotion_until = 0.0

    def get_state(self) -> AvatarState:
        return self._state

    # ── frame_key shim (backward compat) ─────────────────
    @property
    def frame_key(self) -> str:
        """Simple non-blended frame key for callers that don't use BlendFrame."""
        return self.blend.frame_to if self.blend.alpha > 127 else self.blend.frame_from

    @property
    def lip_index(self) -> int:
        k = self.frame_key
        return {'idle': 0, 'semi': 1, 'open': 2}.get(k, 0)

    # ── Main tick ─────────────────────────────────────────
    def tick(self, dt: float = 0.05):
        """Advance one frame (~50ms). Returns self for chaining."""
        self._tick += dt

        state = self._state
        if self._emotion_until and time.monotonic() >= self._emotion_until and state in {AvatarState.HAPPY, AvatarState.SAD, AvatarState.THINKING}:
            self._emotion_until = 0.0
            self.set_state(AvatarState.IDLE)
            state = self._state
        freq, amp = self._BREATH.get(state, (1.5, 3.0))
        self.breath_offset = math.sin(self._tick * freq) * amp

        # Glow
        if state == AvatarState.IDLE:
            self.glow_alpha = int(18 + 10 * math.sin(self._tick * 1.8))
        elif state == AvatarState.LISTENING:
            self.glow_alpha = int(35 + 22 * math.sin(self._tick * 3.2))
        elif state == AvatarState.THINKING:
            self.glow_alpha = int(22 + 14 * math.sin(self._tick * 2.2))
        else:
            self.glow_alpha = 0

        # Frame blend
        if state == AvatarState.SPEAKING:
            self.blend = self._lip.update(dt)
            # Dynamic pulse mirroring speech
            try:
                from engine.voice_engine import get_audio_frequency
                freq = get_audio_frequency()
            except ImportError:
                freq = 0.5
            self.pulse_scale = 1.0 + (freq * 0.025)
        elif state == AvatarState.IDLE:
            self.blend = self._blink.update()
            self.pulse_scale = 1.0 + math.sin(self._tick * 1.5) * 0.005 # minor ambient pulse
        else:
            self._blink._t0 = time.monotonic()   # reset blink timer when not idle
            self.blend = BlendFrame('idle', 'idle', 255)
            self.pulse_scale = 1.0 + math.sin(self._tick * 2.0) * 0.008

        return self
