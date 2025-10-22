# Leap Motion 2 Integration Guide for ADK

This guide explains how to use Leap Motion 2 to input data into the ADK web interface.

## Overview

The Leap Motion integration allows you to control the ADK input using hand gestures instead of manually typing `{"data": 0.5, "touched_area": "胸"}`. The system automatically converts your hand movements into the appropriate touch intensity and body area.

## Components

1. **Leap Motion MCP Server** (`server_leapmotion/server.py`)
   - Handles Leap Motion sensor data
   - Provides gesture detection
   - Converts gestures to ADK input format

2. **Extended TouchInput Schema** (`agent_mcp/agent.py`)
   - Now supports optional Leap Motion fields
   - Maintains backward compatibility with manual input

3. **Leap Motion Bridge** (`leap_motion_bridge.py`)
   - Real-time bridge between Leap Motion and ADK web
   - Continuously monitors hand gestures
   - Sends converted data to ADK

## Installation

### 1. Install Leap Motion SDK

```bash
# Run the setup script
python server_leapmotion/setup_leap.py

# Or install manually:
# - Download SDK from https://developer.leapmotion.com/tracking-software-download
# - Follow platform-specific instructions in the setup script output
```

### 2. Install Python Dependencies

```bash
cd server_leapmotion
pip install -r requirements.txt
```

## Usage

### Method 1: Direct MCP Integration

The Leap Motion MCP server is already integrated into the agent. When you input data through ADK web, the agent can now access Leap Motion tools.

### Method 2: Real-time Bridge (Recommended)

Run the bridge to continuously send Leap Motion data to ADK:

```bash
# With real Leap Motion device
python leap_motion_bridge.py --adk-url http://localhost:8080

# For testing without device (uses mock data)
python leap_motion_bridge.py --mock
```

### Method 3: Demo Mode

Test the integration:

```bash
python leap_motion_demo.py
```

## Gesture Mappings

| Gesture | Description | Base Intensity | How to Perform |
|---------|-------------|----------------|----------------|
| Swipe | Quick hand movement | 0.3 | Move hand quickly (>500 velocity) |
| Circle | Circular motion | 0.5 | Move hand in circle |
| Tap | Single finger tap | 0.7 | Extend one finger |
| Grab | Close fist | 0.8 | Close all fingers |
| Pinch | Two finger pinch | 0.6 | Extend two fingers, low velocity |

## Body Area Mapping

Hand Y position determines the touched body area:

- **Above 250**: 頭 (head)
- **150-250**: 胸 (chest)
- **50-150**: 腹 (stomach)
- **Below 50**: 足 (feet)

## Input Format

The system automatically generates the ADK input format:

```json
{
  "data": 0.5,           // Touch intensity (0-1)
  "touched_area": "胸",   // Body area
  "gesture_type": "tap",  // Optional: Detected gesture
  "hand_position": {...}, // Optional: 3D position
  "hand_velocity": 150.5, // Optional: Hand speed
  "leap_confidence": 0.9  // Optional: Detection confidence
}
```

## Customization

### Adjust Gesture Sensitivity

Modify gesture detection in `server_leapmotion/server.py`:

```python
# In detect_gesture() method
if velocity > 500:  # Adjust this threshold
    return "swipe"
```

### Custom Gesture Mappings

Use the MCP tool to set custom mappings:

```python
# In your agent or via demo
set_gesture_mapping(
    gesture="swipe",
    intensity=0.9,
    area="頭"
)
```

## Troubleshooting

1. **"Leap Motion SDK not found"**
   - Run `python server_leapmotion/setup_leap.py`
   - Install SDK from official website

2. **"No hand detected"**
   - Ensure Leap Motion device is connected
   - Place hand 10-40cm above sensor
   - Check Leap Motion Control Panel

3. **Bridge connection errors**
   - Verify ADK web is running on correct port
   - Check `--adk-url` parameter

4. **Using mock mode for testing**
   - Run with `--mock` flag to test without device
   - Simulates hand movements automatically

## Integration with ADK Web

1. Start ADK web as usual
2. Run the Leap Motion bridge
3. Select `agent_mcp/agent.py` in ADK web
4. Move your hand over the Leap Motion sensor
5. The input field will be automatically populated with gesture data

The agent will process the Leap Motion data just like manual touch input, generating appropriate emotional responses, vibrations, and voice output.