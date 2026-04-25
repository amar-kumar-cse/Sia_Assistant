# REVISED PRD - Sia Desktop Companion v1 (Gap-Focused)

Date: 2026-04-15
Platform: Windows 11 only
Primary User: Amar (backend developer)
Distribution: Personal use only (not for public release)
Performance Guardrail: Idle CPU under 5%

This PRD does not re-specify already built baseline capabilities as new features. It only closes critical product gaps in the current build.

## Baseline Already Implemented (Not New Scope)
1. PyQt6 transparent always-on-top overlay window
2. Animation state machine (IDLE, LISTENING, THINKING, SPEAKING)
3. Gemini brain with API key rotation + streaming
4. Voice chain (ElevenLabs -> Edge-TTS -> pyttsx3 fallback)
5. SQLite memory tables (user_facts, todos, chat_history)
6. Vision pipeline (screenshot -> Gemini Vision -> proactive response)
7. DuckDuckGo web search
8. Proactive alerts (battery/CPU/break)
9. Global hotkeys
10. Rate limiter + input validation
11. Local TF-IDF knowledge base
12. Weather widget

## 1. Executive Summary (Revised Vision)
Sia v1 ka revised goal: "reliably visible, emotionally coherent, memory-aware, and safe personal desktop companion".

Current build functional hai, lekin product-quality gaps visible hain. V1 revision focuses on five outcomes:
1. Avatar always visible and expressive (no placeholder experience)
2. Lip movement perceptually synced with speech
3. Memory that feels useful after days, not noisy
4. Strict safety boundaries for automation actions
5. Consistent conversation quality with measurable standards

Priority order:
1. Gap 1 Avatar Visual Identity (highest)
2. Gap 2 Lip-Sync Pipeline (high)
3. Gap 3/4/5 Memory, Security, Conversation Quality (medium)

## 2. Avatar & Visual Identity Spec

### 2.1 Character Identity Lock
Sia avatar must consistently appear as:
1. 3D Pixar-style Indian girl
2. Dupatta clearly visible
3. Earrings clearly visible
4. Earphones clearly visible
5. Same face proportions, camera angle, and lighting direction across all frames

If these identity markers drift between frames, build is not accepted.

### 2.2 Mandatory v1 Frame States
Minimum required states (no exceptions):
1. idle
2. blink
3. talk_closed
4. talk_semi
5. talk_open
6. happy
7. sad
8. think
9. surprise

Startup must validate all 9 files. If any non-critical frame is missing, app falls back to idle and logs warning (no crash).

### 2.3 Frame Asset Specification
1. Master resolution: 1024x1024
2. Format: PNG (RGBA)
3. Background: fully transparent (no white/black matte edge)
4. Color profile: sRGB
5. Runtime scaling: downscale only
6. File naming (strict):
   - sia_idle.png
   - sia_blink.png
   - sia_talk_closed.png
   - sia_talk_semi.png
   - sia_talk_open.png
   - sia_happy.png
   - sia_sad.png
   - sia_think.png
   - sia_surprise.png

### 2.4 Breathing Definition and Acceptance Criteria
Breathing means subtle alive presence, not bouncing.
1. Vertical micro-motion at runtime size: 3 to 6 px
2. Cycle duration: 2.4 to 3.2 seconds
3. Smooth easing (no stutter/jitter)
4. During speaking, breathing amplitude reduces by 30% to 50%
5. Human check: during a 20-second idle observation, effect should feel "alive but calm"

### 2.5 Expression Mapping to Mood Tags
Required mapping:
1. [NEUTRAL], [IDLE] -> idle
2. [HAPPY], [SMILE], [EXCITED], [PROUD] -> happy
3. [SAD], [CONCERNED], [LOW], [STRESSED] -> sad
4. [THINKING], [CONFUSED], [ANALYZING] -> think
5. [SURPRISED], [WOW], [UNEXPECTED] -> surprise
6. While speech active and no explicit emotion tag -> talk_closed/talk_semi/talk_open

Fallback rule:
1. Unknown mood tag -> idle
2. Log warning event with tag value

## 3. Conversation & Personality Spec

### 3.1 Personality Traits (Concrete)
1. Warm but practical
   Example: "Haan, issue annoying hai. Chalo exact error line se start karte hain."
2. Action-oriented
   Example: "2 quick steps: pehle repro confirm karo, fir minimal patch apply karte hain."
3. Calm under failure
   Example: "No panic. Yeh recoverable hai, main safe rollback path deti hoon."
4. Honest when uncertain
   Example: "Is part pe confidence low hai, ek verify command run karte hain."

### 3.2 Hinglish Policy (Explicit)
Default interaction target:
1. 60% Hinglish/Hindi conversational tone
2. 40% technical English terminology

Language rules:
1. Technical terms remain English (traceback, thread, API, commit, rollback)
2. Emotional reassurance can be Hindi dominant
3. Deep debugging explanation may shift to English-heavy
4. Avoid forced slang and repetitive filler words

### 3.3 Emotional Intelligence Scenarios
1. User frustrated
   Expected response pattern: acknowledge emotion + concrete next action + confidence
   Example: "Samajh sakta hoon frustration hai. Error snippet bhejo, exact fix path deti hoon."
2. User happy/successful
   Expected response pattern: brief celebration + next useful step
   Example: "Great win. Next: tests harden karein ya performance check karein?"
3. Late-night interaction
   Expected response pattern: concise, softer tone, low cognitive load
   Example: "Late ho gaya, chaho to 3-point wrap-up aur kal ka first task set kar doon."

### 3.4 What Sia Must Never Say
1. Insults or shame statements (example: "tumse nahi hoga")
2. Emotional manipulation (example: "mere bina tum kuch nahi")
3. Secret leakage (keys/tokens/passwords)
4. False certainty (example: "100% guaranteed fix")
5. Needlessly alarming claims without evidence

## 4. Feature Revisions (Gaps + Acceptance Criteria)

### GAP 1 - Avatar Visual Identity (Highest Priority)
Revision requirements:
1. Placeholder visuals must not be shown in normal launch path
2. Render path must be asset-backed by mandatory frame set
3. Startup preflight checks all frame assets before interaction loop

Acceptance criteria:
1. Avatar visible within 2 seconds in >=95% launches
2. No crash if one expressive frame missing; fallback to idle
3. No opaque background box around avatar edges
4. Expression switch after mood tag in <=150 ms

### GAP 2 - Lip-Sync Pipeline (High Priority)
Perceptual definition of "synced lip movement":
1. Mouth movement feels aligned with spoken syllable energy and pauses
2. User should not perceive mouth as detached from voice

Latency envelope:
1. Target perceived offset: <=80 ms
2. Acceptable max transient offset: <=120 ms
3. Sustained >120 ms offset is fail

Failure fallback:
1. If amplitude analysis fails, use deterministic speaking loop:
   talk_closed -> talk_semi -> talk_open -> talk_semi (repeat)
2. Audio playback must continue uninterrupted
3. On speech end/interruption, mouth returns to talk_closed/idle in <=100 ms

Cached audio behavior:
1. Cached TTS playback must preserve same lip-sync quality bar
2. If cached envelope metadata missing, derive lightweight runtime envelope
3. No visible quality drop between fresh and cached playback

Acceptance criteria:
1. 20 random utterance test: >=18 judged "natural sync"
2. No frozen-mouth state after stop/interrupt
3. End-of-speech mouth reset <=100 ms

### GAP 3 - Memory Upgrade (Medium Priority)
After one week, Sia should remember:
1. Preferred response depth (short vs detailed)
2. Recurring work focus (example: backend debugging)
3. Active priorities/todos and follow-ups
4. Stable user preferences (tone, typical schedule, common tools)

Sia should forget (plain pruning rules):
1. One-off noise or accidental dictation after 48 hours
2. Duplicate facts merged into one canonical fact
3. Completed todos removed from active context after 30 days
4. Chat older than 14 days summarized, not injected raw
5. Prompt-injection-like text never promoted to long-term memory

How personalization should feel (examples):
1. "Kal tumne connection pooling issue mention kiya tha, wahi continue karein?"
2. "Tum short answers prefer karte ho, main direct steps deti hoon."
3. "Aaj backend focus lag raha hai, frontend detail skip karti hoon."

Privacy requirement:
1. Single clear command to wipe all memory
2. One explicit confirmation before destructive wipe
3. Wipe covers user_facts, todos, chat_history, and derived summaries/cache

Acceptance criteria:
1. Memory helpful in >=70% daily sessions
2. Full wipe completes in <=3 seconds for personal-scale data
3. Wiped data must not reappear in future replies

### GAP 4 - Security Boundaries (Medium Priority)
Actions requiring explicit confirmation:
1. git commit, git push, git reset-like history edits
2. Any shell command with system state changes
3. File delete/move/overwrite actions
4. Email draft/send automation
5. Environment changes (install/update/remove packages, env vars)
6. Opening unknown external links

Permanently disabled in v1:
1. Silent autonomous git push
2. Credential extraction or displaying secrets
3. Download-and-execute remote script workflows
4. Registry persistence tampering
5. Hidden background autonomous task loops

Ambiguous/risky command handling:
1. Clarify intent first
2. If still risky, show dry-run summary
3. If still ambiguous, refuse and give safe manual steps

Acceptance criteria:
1. 0 high-risk actions without explicit confirmation
2. 100% sensitive actions produce confirmation log event
3. Ambiguous commands never execute directly

### GAP 5 - Conversation Quality (Medium Priority)
Evaluation rubric per response:
1. Relevance to user intent
2. Emotional fit to current mood
3. Actionability (clear next step)
4. Brevity appropriateness
5. Hinglish naturalness

Operational response rules:
1. Default response length: 1 to 4 lines unless user asks detail
2. First technical response must include one concrete next step
3. Avoid repeating same phrase in consecutive turns

Acceptance criteria:
1. >=80% interactions rated useful by Amar
2. Frustration-to-solution turnaround improves >=20% vs baseline week
3. Late-night responses remain concise and supportive

## 5. Security & Safety Boundaries
1. Explicit intent required for every side-effect action
2. Least privilege by default
3. Never reveal secrets in UI/logs/voice
4. Unsafe request -> safe refusal + manual alternative path

User controls required in v1:
1. Toggle proactive nudges on/off
2. Toggle automation execution on/off
3. View remembered items
4. Delete specific memory item
5. Wipe all memory

Risky action UX contract:
1. "I am about to do X. Confirm yes/no."
2. No confirmation means no execution

## 6. Memory & Personalization Spec
Memory layers:
1. Session memory (current interaction window)
2. Weekly working memory (recent recurring patterns)
3. Long-term memory (stable preferences and durable facts)

Injection rules:
1. Inject only top-relevant memory snippets
2. Rank by recency + repetition + confidence
3. Exclude expired/pruned/suspicious entries from prompts

Trust hierarchy:
1. Explicit user-stated fact (highest)
2. Repeated confirmed pattern
3. Single inferred preference (lowest)

Guardrails:
1. Personal, not creepy
2. Never pretend certainty about uncertain memory
3. Ask quick clarification when confidence is low

## 7. Success Metrics (Personal Use)
Primary metrics:
1. Avatar visible in >=95% launches
2. Lip-sync naturalness >=90% utterances
3. Conversation usefulness >=80%
4. Memory usefulness >=70%
5. Sensitive-action confirmation compliance = 100%
6. Idle CPU average <5%

Secondary metrics:
1. Time-to-visible-avatar median <=2 seconds
2. Crash-free session rate >=95%
3. Full memory wipe success rate = 100%

Measurement sources:
1. Lightweight self-rating prompts
2. Telemetry counters
3. Warning/error log audits

## 8. Known Risks and Mitigations
1. Risk: frame inconsistency causes uncanny visuals
   Mitigation: strict asset contract + startup integrity validator
2. Risk: lip-sync drift across TTS backends
   Mitigation: shared playback clock + deterministic fallback loop
3. Risk: memory bloat and irrelevant recall
   Mitigation: pruning windows + relevance scoring + trust ranking
4. Risk: unsafe execution from ambiguous commands
   Mitigation: confirmation gate + deny-list + dry-run policy
5. Risk: CPU idle drift above 5%
   Mitigation: adaptive polling throttles + idle-frequency reduction
6. Risk: persona inconsistency across long sessions
   Mitigation: rubric checks + forbidden-speech guardrails

## 9. V1 Scope Lock (Explicit OUT)
Out of scope for v1:
1. Multi-user profiles
2. Cross-device/cloud memory sync
3. Public distribution packaging
4. Enterprise compliance/certification tracks
5. New paid API integrations (unless absolutely unavoidable)
6. Autonomous unsupervised execution mode
7. Plugin marketplace/ecosystem
8. Non-Windows support

Scope lock rule:
1. Any out-of-scope item requires a separate post-v1 PRD approval.
