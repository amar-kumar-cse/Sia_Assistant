# REVISED TRD - Sia Desktop Companion v1 (Implementation-Ready)

Date: 2026-04-15
Target Platform: Windows 11 (personal use)
Runtime: Python 3.11
UI: PyQt6 (compat mode allowed for current PyQt5 code until migration complete)

This TRD focuses only on real technical gaps in the current implementation and gives concrete, build-ready specifications.

---

## 1. Revised Architecture Diagram (Text)

```text
+------------------------- Desktop Process -------------------------+
|                                                                  |
|  run_sia.py                                                      |
|      |                                                           |
|      v                                                           |
|  sia_desktop.py (MainWindow / Orchestrator)                     |
|   |- UI Thread (Qt main loop)                                    |
|   |   |- AvatarFrameWidget (QLabel + QPixmap blend render)       |
|   |   |- BubbleWidget                                             |
|   |   |- Status/Controls                                          |
|   |                                                               |
|   |- Worker Threads (QThread / daemon thread)                    |
|   |   |- ListenThread (wake + STT)                               |
|   |   |- ThinkThread (brain.stream)                              |
|   |   |- StreamingManager (chunk->TTS queue)                     |
|   |   |- AudioPlaybackWorker (voice_engine)                      |
|   |   |- LipSyncScheduler (UI-safe frame schedule emit)          |
|   |   |- TelemetryWriter (async sqlite writer)                   |
|   |   |- ProactiveEngine loop                                    |
|   |                                                               |
|   |- engine.brain.py                                              |
|   |   |- Gemini request + key rotation                           |
|   |   |- mood tagging + response contract                        |
|   |                                                               |
|   |- engine.voice_engine.py                                       |
|   |   |- ElevenLabs -> edge-tts -> pyttsx3                       |
|   |   |- audio cache + envelope sidecar cache                    |
|   |                                                               |
|   |- engine.memory.py (memory.db)                                |
|   |   |- user_facts, conversations, preferences, todos, etc.     |
|   |   |- telemetry_event (persistent, async writes)              |
|   |                                                               |
|   |- engine.actions.py -> action_handler.py -> os/dev_tools      |
|   |   |- validation gate before dispatch                          |
|   |   |- confirmation gate for risky intents                      |
|                                                                  |
+------------------------------------------------------------------+
```

Threading policy:
1. No blocking network/audio call on Qt main thread.
2. QThread for UI-coupled workers, daemon thread for background loops where safe.
3. Cross-thread communication only via Qt signals/slots or thread-safe Queue.

---

## 2. Problem-by-Problem Fix Specifications

## Problem 1 - Avatar Frame System

### 1A. Exact QLabel + QPixmap rendering approach

Use a dedicated QLabel subclass that receives frame keys and alpha values from animation_engine, then composites transparent pixmaps into one output pixmap and sets it on itself.

```python
# avatar_frame_widget.py
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty
from PyQt6.QtGui import QPixmap, QPainter

class AvatarFrameWidget(QLabel):
    def __init__(self, frame_map: dict[str, QPixmap], parent=None):
        super().__init__(parent)
        self.frame_map = frame_map
        self.current_from = "idle"
        self.current_to = "idle"
        self.current_alpha = 255
        self._breath_scale = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

    @pyqtProperty(float)
    def breath_scale(self):
        return self._breath_scale

    @breath_scale.setter
    def breath_scale(self, v: float):
        self._breath_scale = v
        self.render_current_frame()

    def set_blend(self, frame_from: str, frame_to: str, alpha: int):
        self.current_from = frame_from
        self.current_to = frame_to
        self.current_alpha = max(0, min(255, alpha))
        self.render_current_frame()

    def render_current_frame(self):
        w, h = self.width(), self.height()
        canvas = QPixmap(w, h)
        canvas.fill(Qt.GlobalColor.transparent)

        px_from = self.frame_map.get(self.current_from) or self.frame_map["idle"]
        px_to = self.frame_map.get(self.current_to) or self.frame_map["idle"]

        p = QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # breathing via scale transform (no geometry re-layout)
        p.translate(w / 2, h / 2)
        p.scale(self._breath_scale, self._breath_scale)
        p.translate(-w / 2, -h / 2)

        p.setOpacity((255 - self.current_alpha) / 255.0)
        p.drawPixmap(0, 0, px_from.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
        p.setOpacity(self.current_alpha / 255.0)
        p.drawPixmap(0, 0, px_to.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
        p.end()

        self.setPixmap(canvas)
```

Transparent window requirements:
1. Top-level widget flags: Frameless + AlwaysOnTop.
2. WA_TranslucentBackground enabled at both top window and avatar label.
3. PNG must preserve alpha channel (RGBA).

### 1B. Frame state machine transitions

Animated transitions:
1. idle <-> blink (close/open)
2. talk_closed <-> talk_semi <-> talk_open
3. think <-> idle (short crossfade)

Instant transitions:
1. sad -> happy, happy -> sad
2. surprise entry (instant), surprise -> idle (animated 120-180 ms)

Transition timing constants:
1. crossfade default: 100 ms
2. expression switch: max 150 ms
3. surprise hold: 250 ms

### 1C. Breathing implementation (exact)

Use QPropertyAnimation on breath_scale property (not geometry) to avoid layout jitter.

```python
self.breath_anim = QPropertyAnimation(self.avatar_widget, b"breath_scale")
self.breath_anim.setStartValue(0.992)
self.breath_anim.setEndValue(1.008)
self.breath_anim.setDuration(2800)
self.breath_anim.setLoopCount(-1)
self.breath_anim.start()
```

During speaking, reduce amplitude:
1. idle scale range: 0.992 to 1.008
2. speaking range: 0.996 to 1.004

### 1D. Blink spec

1. Random interval timer: 3 to 7 seconds.
2. Close transition: 90 ms.
3. Hold blink frame: 60 ms.
4. Open transition: 90 ms.

### 1E. Emotion tag mapping from brain.py

1. IDLE -> idle
2. SMILE, HAPPY, EXCITED -> happy
3. SAD, CONCERNED, STRESSED -> sad
4. CONFUSED, THINKING, ANALYZING -> think
5. SURPRISED -> surprise
6. SPEAKING state overrides expression mouth with talk frames while preserving expression base for non-mouth region.

If unknown tag:
1. log warning
2. fallback to idle

---

## Problem 2 - Lip-Sync Audio Sync (Critical)

### 2A. Exact flow

```text
text chunk
  -> voice_engine generate_or_load_audio(text)
      -> returns audio_path
      -> returns envelope (load from sidecar or compute)
  -> playback_worker starts audio
  -> lip_sync_scheduler receives (start_ts, envelope, duration)
  -> UI timer reads schedule against monotonic clock
  -> emits talk_closed / talk_semi / talk_open states
```

### 2B. Amplitude to timestamps conversion

Use librosa RMS envelope:
1. y, sr = librosa.load(audio_path, sr=16000, mono=True)
2. rms = librosa.feature.rms(y=y, frame_length=512, hop_length=160)[0]
3. normalize rms to 0..1
4. frame_time = hop_length / sr
5. timestamp i = i * frame_time

Mapping thresholds:
1. rms < 0.20 -> talk_closed
2. 0.20 <= rms < 0.55 -> talk_semi
3. rms >= 0.55 -> talk_open

Apply smoothing to avoid jitter:
1. moving average window 3
2. minimum hold per mouth state 60 ms

### 2C. Threading model synchronization

1. Audio playback thread owns actual playback start.
2. It emits playback_started(monotonic_start, duration, schedule).
3. UI thread runs QTimer every 33 ms (30 FPS), reads elapsed and applies mouth frame.
4. No direct QWidget calls from playback thread.

### 2D. Cache hit path

Store sidecar json for each cached mp3:
1. cache/audio_hash.mp3
2. cache/audio_hash.envelope.json

Sidecar payload:
1. version
2. sample_rate
3. hop_length
4. duration_sec
5. states list as [timestamp, frame_key]

On cache hit:
1. load mp3
2. load sidecar if exists
3. if sidecar missing/corrupt, compute lightweight fallback envelope

### 2E. If librosa too slow fallback

Fallback mode:
1. Skip librosa for text shorter than 120 chars.
2. Generate deterministic synthetic envelope from punctuation and token density.
3. Keep deterministic loop: closed -> semi -> open -> semi with 80 ms step.

### 2F. Pseudocode

```python
def prepare_lipsync(audio_path: str, text: str) -> list[tuple[float, str]]:
    sidecar = audio_path.replace(".mp3", ".envelope.json")
    if exists(sidecar):
        return load_states(sidecar)

    if should_use_librosa(text, audio_path):
        states = librosa_states(audio_path)
    else:
        states = synthetic_states(text, estimate_duration(audio_path))

    save_states(sidecar, states)
    return states


def librosa_states(audio_path):
    y, sr = librosa.load(audio_path, sr=16000, mono=True)
    rms = librosa.feature.rms(y=y, frame_length=512, hop_length=160)[0]
    rms = smooth(normalize(rms))
    out = []
    t = 0.0
    step = 160 / 16000
    for v in rms:
        if v < 0.20:
            f = "talk_closed"
        elif v < 0.55:
            f = "talk_semi"
        else:
            f = "talk_open"
        out.append((t, f))
        t += step
    return hold_min_duration(out, min_ms=60)
```

---

## Problem 3 - Memory Schema Upgrade

### 3A. Complete revised schema (SQLite)

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS app_session (
  session_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  client_version TEXT,
  platform TEXT
);

CREATE TABLE IF NOT EXISTS user_facts (
  fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
  fact_key TEXT NOT NULL,
  fact_value TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 0.5,
  source TEXT NOT NULL,              -- user_explicit | inferred | imported
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  hit_count INTEGER NOT NULL DEFAULT 1,
  is_active INTEGER NOT NULL DEFAULT 1,
  UNIQUE(fact_key, fact_value)
);

CREATE INDEX IF NOT EXISTS idx_user_facts_key ON user_facts(fact_key);
CREATE INDEX IF NOT EXISTS idx_user_facts_active_conf ON user_facts(is_active, confidence DESC, last_seen_at DESC);

CREATE TABLE IF NOT EXISTS conversations (
  convo_id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,                -- user | sia
  message TEXT NOT NULL,
  mood_tag TEXT,                     -- HAPPY, SAD, etc.
  topic_tag TEXT,                    -- debugging, planning, personal
  created_at TEXT NOT NULL,
  token_count INTEGER,
  FOREIGN KEY(session_id) REFERENCES app_session(session_id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_session_time ON conversations(session_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_topic_time ON conversations(topic_tag, created_at DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
  message,
  content='conversations',
  content_rowid='convo_id'
);

CREATE TABLE IF NOT EXISTS user_preferences (
  pref_key TEXT PRIMARY KEY,
  pref_value TEXT NOT NULL,
  value_type TEXT NOT NULL,          -- str | int | float | bool | json
  confidence REAL NOT NULL DEFAULT 0.8,
  source TEXT NOT NULL,              -- explicit | inferred
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS todos (
  todo_id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  priority INTEGER NOT NULL DEFAULT 2,
  created_at TEXT NOT NULL,
  completed_at TEXT,
  source TEXT
);

CREATE INDEX IF NOT EXISTS idx_todos_status_created ON todos(status, created_at DESC);

CREATE TABLE IF NOT EXISTS telemetry_event (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  ts TEXT NOT NULL,
  session_id TEXT,
  metric_value REAL,
  payload_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_telemetry_type_ts ON telemetry_event(event_type, ts DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_session_ts ON telemetry_event(session_id, ts DESC);
```

### 3B. Weekly pruning SQL

```sql
-- 1) deactivate low-confidence stale inferred facts
UPDATE user_facts
SET is_active = 0
WHERE source = 'inferred'
  AND confidence < 0.45
  AND last_seen_at < datetime('now', '-30 days');

-- 2) hard-delete inactive facts older than 90 days
DELETE FROM user_facts
WHERE is_active = 0
  AND last_seen_at < datetime('now', '-90 days');

-- 3) trim conversations older than 30 days except important topics
DELETE FROM conversations
WHERE created_at < datetime('now', '-30 days')
  AND (topic_tag IS NULL OR topic_tag NOT IN ('long_term_goal', 'critical_issue'));

-- 4) cleanup completed todos older than 30 days
DELETE FROM todos
WHERE status = 'done'
  AND completed_at < datetime('now', '-30 days');

-- 5) telemetry retention 21 days
DELETE FROM telemetry_event
WHERE ts < datetime('now', '-21 days');

VACUUM;
```

### 3C. Memory injection strategy without vectors

Use hybrid scoring from:
1. keyword overlap
2. confidence
3. recency
4. usage count

Candidate query:

```sql
WITH q AS (
  SELECT :q AS user_q
),
fact_candidates AS (
  SELECT
    fact_key,
    fact_value,
    confidence,
    hit_count,
    last_seen_at,
    (
      CASE WHEN lower(fact_key || ' ' || fact_value) LIKE '%' || lower(:kw1) || '%' THEN 1 ELSE 0 END +
      CASE WHEN lower(fact_key || ' ' || fact_value) LIKE '%' || lower(:kw2) || '%' THEN 1 ELSE 0 END
    ) AS kw_hits
  FROM user_facts
  WHERE is_active = 1
)
SELECT fact_key, fact_value
FROM fact_candidates
ORDER BY (kw_hits * 2.0) + confidence + (min(hit_count, 5) * 0.1) DESC, last_seen_at DESC
LIMIT 8;
```

Conversation context query:

```sql
SELECT role, message, mood_tag, topic_tag, created_at
FROM conversations
WHERE session_id = :session_id
ORDER BY created_at DESC
LIMIT 12;
```

### 3D. Max DB size target and enforcement

Target:
1. hard cap 128 MB
2. warning at 96 MB

Enforcement check:

```sql
PRAGMA page_count;
PRAGMA page_size;
```

If page_count * page_size > cap:
1. run prune job immediately
2. run VACUUM
3. if still above cap, drop oldest telemetry and oldest non-critical conversations first

---

## Problem 4 - dev_tools.py Sandboxing

### 4A. Safe whitelist (read-only git only)

Allowed v1 commands:
1. git status
2. git log --oneline -n N
3. git diff --stat
4. git branch --show-current
5. git remote -v

Blocked v1:
1. git add
2. git commit
3. git push
4. git reset
5. git rebase
6. any file delete/move operation
7. any .env file read/print action
8. email send without preview confirmation

### 4B. Confirmation dialog in PyQt6

```python
from PyQt6.QtWidgets import QMessageBox

def confirm_risky(parent, title: str, details: str) -> bool:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText("This action changes system state.")
    box.setInformativeText(details)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    return box.exec() == QMessageBox.StandardButton.Yes
```

### 4C. validation.py extension for intent risk prefilter

Add:
1. risky intent classifier by keywords
2. command policy checker returning ALLOW, CONFIRM, DENY

```python
def classify_intent_risk(text: str) -> str:
    t = text.lower()
    deny = ["delete file", "remove file", "show env", "read .env", "send email now"]
    confirm = ["git commit", "git push", "install", "shutdown", "restart"]
    if any(k in t for k in deny):
        return "DENY"
    if any(k in t for k in confirm):
        return "CONFIRM"
    return "ALLOW"
```

Flow requirement:
1. validation gate executes before actions.perform_action dispatch.
2. DENY never reaches action_handler.
3. CONFIRM routes to UI confirmation.

---

## Problem 5 - Streaming Pipeline Completion

### 5A. Verified flow

```text
brain.think_streaming
  -> yields token chunks
  -> streaming_manager buffers chunks
  -> on sentence boundary or >= 70 chars
        start voice_engine.speak_chunk
  -> UI bubble appends same chunk immediately
  -> lip_sync scheduler starts with first audio chunk
```

Chunk start threshold:
1. sentence end punctuation, or
2. 70 chars buffered, whichever comes first

### 5B. UI bubble and voice sync

1. Bubble updates per chunk on UI thread.
2. TTS starts once first speakable chunk formed.
3. Later chunks enqueue to audio queue.
4. Bubble display does not wait for TTS completion.

### 5C. Gemini stream drop mid-response

Behavior:
1. keep accumulated text
2. flush accumulated chunk to TTS queue
3. mark response as partial-recovered
4. optionally append short recovery suffix in UI
5. save recovered response in conversations table

### 5D. VoiceInterruptMonitor exact behavior

Spec:
1. Monitor mic RMS every 50 ms while Sia speaking.
2. If RMS > threshold for 300 ms continuous:
   1. voice_engine.stop()
   2. clear TTS pending queue
   3. set state to listening
   4. show bubble: interruption acknowledged

Pseudo:

```python
def on_vad_tick(rms):
    if not voice_engine.get_speaking_state():
        reset_counter(); return
    if rms > INTERRUPT_THRESHOLD:
        over_ms += 50
    else:
        over_ms = 0
    if over_ms >= 300:
        voice_engine.stop()
        streaming_manager.stop_streaming()
        ui_signal_interrupt.emit()
        over_ms = 0
```

---

## Problem 6 - Telemetry Persistence

### 6A. Minimal persistent telemetry schema

Use telemetry_event table (defined in schema above).

Tracked events:
1. session_start
2. response_latency
3. tts_latency
4. vision_trigger
5. api_key_rotation
6. error_type

Payload examples:
1. response_latency: metric_value seconds
2. error_type: payload_json with module and exception
3. api_key_rotation: payload_json old_key_suffix/new_key_suffix

### 6B. Non-blocking write path

1. UI and engine workers call telemetry.record_event in memory queue.
2. TelemetryWriter daemon thread batches inserts every 1 second or 50 events.
3. sqlite connection is dedicated to writer thread.

```python
# daemon thread
while running:
    batch = drain_queue(max_items=50, timeout=1.0)
    if batch:
        insert_many(batch)
```

### 6C. Query example

Show average response time this week:

```sql
SELECT round(avg(metric_value), 3) AS avg_response_sec
FROM telemetry_event
WHERE event_type = 'response_latency'
  AND ts >= datetime('now', '-7 days');
```

---

## Problem 7 - Test Coverage Gaps

Test framework target:
1. pytest
2. pytest-mock
3. pytest-qt for UI signal/slot validation

### 7A. Vision engine tests

```python
def test_analyze_screen_uses_screenshot_and_gemini(mocker):
    ...

def test_analyze_screen_offline_fallback_on_gemini_error(mocker):
    ...
```

Asserts:
1. pyautogui.screenshot called once
2. Gemini called with image path
3. fallback text returned on exception

### 7B. Key rotation tests

```python
def test_key_rotation_on_429_switches_key_and_recovers(mocker):
    ...

def test_key_rotation_logs_telemetry_event(mocker):
    ...
```

Asserts:
1. first key throws 429
2. next key invoked
3. final response returned without hard failure
4. telemetry api_key_rotation recorded

### 7C. Proactive engine tests

```python
def test_proactive_alert_triggers_on_high_cpu(mocker):
    ...

def test_proactive_alert_triggers_on_low_battery(mocker):
    ...
```

Asserts:
1. mocked stats cross threshold
2. correct alert intent generated
3. cooldown respected (no spam)

### 7D. Memory pruning tests

```python
def test_weekly_prune_deletes_old_done_todos(tmp_path):
    ...

def test_weekly_prune_deactivates_low_confidence_facts(tmp_path):
    ...
```

Asserts:
1. old completed todos removed
2. old low-confidence inferred facts deactivated/deleted by policy

### 7E. Lip-sync tests

```python
def test_amplitude_to_frames_threshold_mapping():
    ...

def test_lipsync_schedule_has_monotonic_timestamps():
    ...

def test_lipsync_cache_hit_loads_sidecar_without_librosa(mocker):
    ...
```

Asserts:
1. known amplitude array maps to expected closed/semi/open sequence
2. timestamps strictly increasing
3. cache hit bypasses librosa path

---

## 3. Revised File Structure (Add/Modify)

Add:
1. engine/avatar_frame_widget.py
2. engine/lipsync_scheduler.py
3. engine/telemetry_store.py
4. tests/test_vision_engine.py
5. tests/test_key_rotation.py
6. tests/test_proactive_engine.py
7. tests/test_memory_pruning.py
8. tests/test_lipsync.py

Modify:
1. sia_desktop.py (wire AvatarFrameWidget, signals, confirm dialogs)
2. engine/animation_engine.py (state transitions + blink timer contracts)
3. engine/brain.py (normalized mood_tag + stream recovery metadata)
4. engine/voice_engine.py (envelope sidecar generation/load)
5. engine/streaming_manager.py (chunk threshold + queue control)
6. engine/memory.py (schema migration + prune + query API)
7. engine/dev_tools.py (hard sandbox whitelist)
8. engine/validation.py (risk classifier)
9. analytics/telemetry.py (delegate to persistent writer)
10. engine/logger.py (rotating file handler for logs/sia_error.log)

---

## 4. Complete Revised memory.db Schema

Authoritative schema is the SQL block in section 3A.

Migration strategy:
1. Introduce schema_version table.
2. Apply idempotent migration scripts in order.
3. Backup memory.db to memory.db.bak before migration.

```sql
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TEXT NOT NULL
);
```

---

## 5. Updated requirements.txt (Proposed)

Keep existing where valid, update/add minimum needed:

```text
PyQt6==6.7.1
PyQt6-Qt6==6.7.2
PyQt6-sip==13.8.0
google-generativeai==0.8.5
librosa==0.10.2.post1
soundfile==0.12.1
numpy==1.26.4
pytest==8.3.2
pytest-mock==3.14.0
pytest-qt==4.4.0
python-dotenv==1.0.1
```

Notes:
1. If keeping current google-genai integration, lock one SDK path only to avoid dual-client confusion.
2. Do not keep both PyQt5 and PyQt6 long-term for production.

---

## 6. Test Specifications Summary (All 7 Gaps)

Coverage matrix:
1. Avatar frame render and transition timing tests
2. Lip-sync schedule conversion and cache sidecar tests
3. Memory schema migration + prune tests
4. Dev tools policy deny/confirm/allow tests
5. Streaming chunk threshold + stream drop recovery tests
6. Telemetry async writer throughput and no-main-thread-block tests
7. End-to-end interrupt behavior tests (speaking interrupted by user voice)

CI execution tiers:
1. fast unit tests on every commit
2. integration tests on main branch merge

---

## 7. Performance Budget per Component

Hard targets:
1. Main Qt frame paint: <= 8 ms per frame at 30 FPS
2. Streaming chunk-to-bubble latency: <= 60 ms
3. First-audio-start latency after first sentence boundary: <= 350 ms
4. Lip-sync offset from audio: target <= 80 ms, max transient <= 120 ms
5. Memory relevant-fact query: <= 25 ms p95
6. Telemetry event enqueue: <= 1 ms on caller thread
7. Telemetry batch write thread: <= 20 ms per batch insert
8. Idle CPU total app: < 5%
9. memory.db size: <= 128 MB hard cap

Budget table:

```text
Component                  Budget (p95)     Thread
UI paint/frame             8 ms             Main Qt thread
Animation tick             2 ms             Main Qt thread
Streaming parse            5 ms             Worker thread
TTS enqueue                2 ms             Worker thread
Audio playback start       350 ms           Worker thread
Lip-sync schedule lookup   1 ms             Main Qt thread
Memory fetch (top facts)   25 ms            Worker thread
Telemetry enqueue          1 ms             Any thread
Telemetry sqlite flush     20 ms/batch      Daemon writer thread
```

---

## Logging and .env Specification

### Logging requirement

Use rotating error log:
1. file: logs/sia_error.log
2. maxBytes: 5 MB
3. backupCount: 5
4. level: ERROR and above

```python
from logging.handlers import RotatingFileHandler
h = RotatingFileHandler("logs/sia_error.log", maxBytes=5*1024*1024, backupCount=5, encoding="utf-8")
```

### .env keys

Required:
1. GEMINI_API_KEY

Optional:
1. GEMINI_API_KEY_2
2. GEMINI_API_KEY_3
3. GEMINI_MODEL
4. ELEVENLABS_API_KEY
5. ELEVENLABS_VOICE_ID
6. ELEVENLABS_MODEL
7. EDGE_TTS_VOICE
8. DB_PATH
9. LOG_LEVEL
10. ENABLE_TELEMETRY
11. WEATHER_URL

Example:

```text
GEMINI_API_KEY=...
GEMINI_API_KEY_2=...
GEMINI_MODEL=gemini-1.5-pro
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
EDGE_TTS_VOICE=hi-IN-SwaraNeural
DB_PATH=memory.db
ENABLE_TELEMETRY=true
LOG_LEVEL=INFO
```

---

## Execution Priority (Implementation Order)

1. Memory schema migration + telemetry persistence foundation
2. Avatar frame widget and transition contract
3. Lip-sync scheduler + sidecar cache path
4. Streaming completion + interrupt reliability
5. Dev tools sandbox + validation risk gate
6. Final test suite and performance profiling

This order minimizes regressions and enables measurable validation per stage.
