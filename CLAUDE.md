# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an emotional and haptic chatbot system using Google ADK Agent framework with MCP (Model Context Protocol) servers. The system processes touch input (manual or via Leap Motion) to generate emotional responses, vibration feedback, and voice synthesis.

## Key Commands

### Running the main agent
```bash
source venv/bin/activate
adk run .
```

### Running tests
```bash
# Test specific components
python test_haptic_integration.py  # Test Arduino haptic feedback
python test_voicevox.py            # Test voice synthesis
python test_emotion_debug.py       # Test emotion system
python leap_motion_demo.py         # Test Leap Motion integration
```

### Running Leap Motion bridge (for real-time gesture input)
```bash
python leap_motion_bridge.py --adk-url http://localhost:8080
# Mock mode without device:
python leap_motion_bridge.py --mock
```

## Architecture

### Core Components

1. **Agent System** (`agent_mcp/agent.py`)
   - Main agent using Google ADK framework
   - Processes TouchInput with emotion parameters (joy, fun, anger, sad)
   - Integrates with 4 MCP servers via MCPToolset

2. **MCP Servers** (separate processes via stdio)
   - `mcp_servers/emoji_server.py`: Emotion to emoji conversion
   - `mcp_servers/vibration_server.py`: Haptic feedback control
   - `mcp_servers/voicevox_server.py`: Text-to-speech synthesis
   - `server_leapmotion/server.py`: Leap Motion gesture detection

3. **Hardware Integration**
   - Arduino Uno R4 WiFi for vibration control (Pin 9 PWM)
   - Leap Motion 2 for gesture input
   - VOICEVOX for Japanese voice synthesis

### Data Flow
```
Input (Touch/Leap Motion) → Agent → Emotion Processing →
  ├→ Emoji Generation
  ├→ Vibration Pattern (Arduino via WiFi)
  └→ Voice Synthesis (VOICEVOX)
```

## Input/Output Format

### Input Schema (TouchInput)
```json
{
  "data": 0.5,              // Touch intensity (0-1)
  "touched_area": "頭",     // Body part
  "gesture_type": "tap",    // Optional: Leap Motion gesture
  "hand_position": {...},   // Optional: 3D coordinates
  "hand_velocity": 150.5,   // Optional: Hand speed
  "leap_confidence": 0.9    // Optional: Detection confidence
}
```

### Output Schema
```json
{
  "emotion": {
    "joy": 3.2,
    "fun": 2.8,
    "anger": 0.5,
    "sad": 0.3
  },
  "message": "Response message"
}
```

## Important Files

- `prompt/system_prompt`: System behavior definition
- `requirements.txt`: Python dependencies
- `arduino/haptic_feedback_controller/`: Arduino firmware
- `play_audio.sh`: Audio playback script for WSL2/Linux

## Environment Specifics

- Python virtual environment at `venv/`
- WSL2 audio through PulseAudio (configured in `play_audio.sh`)
- Arduino connects via WiFi HTTP API
- MCP servers communicate via stdio pipes