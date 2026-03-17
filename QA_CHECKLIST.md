# Sia Virtual Assistant - QA Testing Checklist

## 1. Core Functionality Tests

### Persona & Language
- [ ] Responds in Hinglish (not pure English/Hindi)
- [ ] Addresses user as "Hero" or "Bhai" or "Yaar"
- [ ] No formal language ("Sir", "Madam")
- [ ] Shows emotional support in responses
- [ ] References B.Tech CSE and RIT Roorkee context

### Memory System
- [ ] Loads default preferences (Gun shot games, Roorkee, B.Tech CSE)
- [ ] Remembers new information after restart
- [ ] Incorporates memory context in responses
- [ ] Memory log updates correctly
- [ ] memory.json file created and readable

### Voice Integration
- [ ] ElevenLabs API connects successfully (if API key present)
- [ ] Voice output is clear and natural
- [ ] Text-only fallback works without API key
- [ ] No crashes when voice fails

## 2. Action Commands

### Resume Access
- [ ] Command: "mera resume dikhao" → Opens PDF/DOC
- [ ] Command: "CV open karo" → Opens PDF/DOC
- [ ] Command: "biodata" → Opens PDF/DOC
- [ ] Error handling if file not found
- [ ] Tries multiple common locations

### College Portal
- [ ] Command: "college portal kholo" → Opens CyborgERP
- [ ] Command: "CyborgERP" → Opens correct URL
- [ ] Browser launches successfully
- [ ] Custom URL in memory.json works

### Code Editor
- [ ] Command: "code editor kholo" → Opens VS Code/PyCharm
- [ ] Falls back gracefully if not installed

### General Actions
- [ ] "Google kholo" → Opens Google
- [ ] "YouTube" → Opens YouTube
- [ ] "GitHub" → Opens GitHub
- [ ] "LinkedIn" → Opens LinkedIn
- [ ] "Stack Overflow" → Opens StackOverflow

## 3. UI/Animation Tests

### Overlay Window
- [ ] Window is transparent (character floats on desktop)
- [ ] Character stays on top of other windows
- [ ] Window is draggable (click and drag works)
- [ ] Window can be closed with ✕ button
- [ ] Positioned at bottom-right on startup

### Chat Window
- [ ] Opens alongside overlay
- [ ] Text input works
- [ ] Send button works
- [ ] Enter key sends message
- [ ] Messages display correctly
- [ ] Dark theme renders properly

### Animation Sync
- [ ] Idle animation plays when not speaking (alternates between frames)
- [ ] Talking animation starts when voice begins
- [ ] Animation stops when voice ends
- [ ] No lag between voice and animation
- [ ] Smooth frame transitions (no flickering)
- [ ] Random blinking works

### Visual Quality
- [ ] Character renders clearly (400x400 size)
- [ ] Animations are smooth
- [ ] No artifacts or pixelation
- [ ] Transparent background works correctly
- [ ] All 4 animation frames load

## 4. Voice Recognition

### Microphone
- [ ] Mic button works on overlay
- [ ] Mic button changes to "..." while listening
- [ ] Mic button re-enables after listening
- [ ] Audio is captured correctly
- [ ] Google Speech Recognition works
- [ ] Timeout handling (5 seconds)
- [ ] Unknown audio handling

## 5. Edge Cases

### Error Handling
- [ ] Works without internet (text mode)
- [ ] Handles long responses (>500 words)
- [ ] Handles empty/whitespace input
- [ ] Multiple quick commands don't crash
- [ ] Memory file corruption recovery
- [ ] Missing API keys show clear warnings
- [ ] Missing image files handled gracefully

### Performance
- [ ] Responds within 3 seconds average
- [ ] No memory leaks with extended use
- [ ] Animation doesn't slow down over time
- [ ] Threading doesn't cause UI freezes

## 6. Integration Tests

### Full Flow - Voice
1. [ ] Click mic button
2. [ ] Speak: "Mera resume dikhao"
3. [ ] Verify: Character animates while listening
4. [ ] Verify: Resume opens
5. [ ] Verify: Sia confirms in voice
6. [ ] Verify: Character animates while speaking

### Full Flow - Text
1. [ ] Type: "College portal kholo"
2. [ ] Press Enter
3. [ ] Verify: Message appears in chat
4. [ ] Verify: Browser opens CyborgERP
5. [ ] Verify: Sia responds in Hinglish
6. [ ] Verify: Voice plays response
7. [ ] Verify: Character animates

### Full Flow - Conversation
1. [ ] Say: "Mujhe pizza pasand hai"
2. [ ] Restart application
3. [ ] Say: "Kya mujhe pasand hai?"
4. [ ] Verify: Mentions pizza from memory
5. [ ] Verify: memory.json updated

## 7. User Experience

### First Launch
- [ ] Clear startup messages in console
- [ ] Both windows appear correctly
- [ ] Welcome message in chat
- [ ] Character positioned well
- [ ] No errors or warnings

### Usability
- [ ] Easy to understand how to interact
- [ ] Clear visual feedback for actions
- [ ] Error messages are helpful
- [ ] Voice is pleasant (not robotic)
- [ ] Character feels "alive" and engaging

## 8. Platform Specific (Windows)

- [ ] Runs on Windows 10/11
- [ ] Transparent window works
- [ ] File opening works (os.startfile)
- [ ] Microphone permissions granted
- [ ] Audio playback works (pygame)

---

## Test Results Summary

**Date**: _________________  
**Tester**: _________________  
**Version**: 1.0  
**Total Tests**: 89  
**Passed**: _____  
**Failed**: _____  
**Skipped**: _____  

### Critical Issues Found:
1. 
2. 
3. 

### Notes:
